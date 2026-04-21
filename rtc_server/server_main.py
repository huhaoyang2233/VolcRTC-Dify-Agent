from flask import Flask, Response, request
from util.util import read_files, assert_true
from Authentication.AccessToken import AccessToken, PrivPublishStream, PrivSubscribeStream
from Authentication.Sign import volc_sign_request
from flask_cors import CORS
import requests
import uuid
import time
import base64
import json

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def load_config(path="./Scenes/Custom.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
config = load_config()

VOLC_API = "https://rtc.volcengineapi.com"

'''
    智能体进出房间
    1.StartVoiceChat智能体进入房间body输入：
    {
    "Action": "StartVoiceChat",
    "Version": "2024-12-01",
    "SceneID": "bedtime_assistant",
    "Dynamic": {
        "AppId": "YOUR_APP_ID",
        "RoomId": "YOUR_ROOM_ID",
        "TaskId": "YOUR_TASK_ID",
        "AgentConfig":{
            "UserId":"Bot001",
            "TargetUserId":["USER_ID"],
            "WelcomeMessage":"你好呀，我是儿童陪伴师"
        }
    }
    
    2.StartVoiceChat智能体离开房间body输入：
    {
    "Action": "StopVoiceChat",
    "Version": "2024-12-01",
    "SceneID": "bedtime_assistant",
    "Dynamic": {
        "AppId": "YOUR_APP_ID",
        "RoomId": "YOUR_ROOM_ID",
        "TaskId": "YOUR_TASK_ID"
    }
    
    3.UpdateVoiceChat更新智能体body输入：
    {
        "Action": "UpdateVoiceChat",
        "Version": "2024-12-01",
        "SceneID": "bedtime_assistant",
        "Dynamic": {
            "AppId": "YOUR_APP_ID",
            "RoomId": "room1",
            "TaskId": "task1",
            "Command": "ExternalTextToLLM",
            "Message": "hi",
            "InterruptMode": 1
        }
    }
}
    
}
'''
@app.route("/proxy", methods=["POST"])
def proxy():
    #解析请求体
    try:
        data = json.loads(request.data.decode("utf-8"))
    except Exception as e:
        print("解析JSON失败:", e)
        return "Invalid JSON", 400
    #外部参数
    Action=data.get("Action","")
    Version=data.get("Version","")
    Dynamic=data.get("Dynamic",{})
    AppId=Dynamic.get("AppId","")
    RoomId=Dynamic.get("RoomId","")
    TaskId=Dynamic.get("TaskId","")
    Command=Dynamic.get("Command","")
    Message=Dynamic.get("Message","")
    InterruptMode=Dynamic.get("InterruptMode","")
    url=f"{VOLC_API}"
    
    request_body={}
    headers={}
    params={}
    if Action=="StartVoiceChat":
        # 补全输入参数
        request_body=config["VoiceChat"]
        request_body["AppId"]=AppId
        request_body["RoomId"]=RoomId
        request_body["TaskId"]=TaskId
        request_body["AgentConfig"]["TargetUserId"]=Dynamic.get("AgentConfig",{}).get("TargetUserId",[])
        request_body["AgentConfig"]["UserId"]=Dynamic.get("AgentConfig",{}).get("UserId","")
        request_body["AgentConfig"]["WelcomeMessage"]=Dynamic.get("AgentConfig",{}).get("WelcomeMessage","")
        #鉴权
        sign_result=volc_sign_request("POST","StartVoiceChat",query=None,body=json.dumps(request_body),content_type="application/json",extra_headers=None)
        print("===== StartVoiceChat  智能体启动=====")
        print(sign_result)
        headers=sign_result["headers"]
        request_body=sign_result["body"]
        params=sign_result["params"]
        
    elif Action=="StopVoiceChat":
        request_body={
            "AppId":AppId,
            "RoomId":RoomId,
            "TaskId": TaskId
        }
        sign_result=volc_sign_request("POST","StopVoiceChat",query=None,body=json.dumps(request_body),content_type="application/json",extra_headers=None)
        print("===== stopVoiceChat  智能体关闭=====")
        print(sign_result)
        headers=sign_result["headers"]
        request_body=sign_result["body"]
        params=sign_result["params"]
    elif Action=="UpdateVoiceChat":
        request_body={
            "AppId":AppId,
            "RoomId":RoomId,
            "TaskId": TaskId,
            "Command":Command,
            "Message":Message,
            "InterruptMode":InterruptMode
        }
        sign_result=volc_sign_request("POST","UpdateVoiceChat",query=None,body=json.dumps(request_body),content_type="application/json",extra_headers=None)
        print("===== stopVoiceChat  智能体更新=====")
        print(sign_result)
        headers=sign_result["headers"]
        request_body=sign_result["body"]
        params=sign_result["params"]
    #发送请求
    resp = requests.request(
        method="POST",
        url=url,
        data=request_body,
        headers=headers,
        params=params
    )
    return resp.json()

'''
    用户进入房间
    
'''
@app.route("/getScenes", methods=["POST"])
def get_scenes():
    result = []
    SCENES = read_files("./scenes")
    for name, scene in SCENES.items():
        scene_cfg = scene["SceneConfig"]
        rtc = scene["RTCConfig"]
        voice = scene["VoiceChat"]

        app_id = rtc["AppId"]
        room_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        app_key = rtc["AppKey"]

        # 自动生成 Token
        token = AccessToken(app_id, app_key, room_id, user_id)
        token.add_privilege(PrivSubscribeStream, 0)
        token.add_privilege(PrivPublishStream, int(time.time()) + 86400)
        token.expire_time(int(time.time()) + 86400)

        rtc.update({
            "RoomId": room_id,
            "UserId": user_id,
            "Token": token.serialize()
        })

        del rtc["AppKey"]
        print("===== 用户进入房间=====")
        result.append({
            "scene": {**scene_cfg, "id": name},
            "rtc": rtc
        })
        print(result)

    return {"scenes": result}


'''
    RTC接入dify
'''

def call_dify_stream(headers,body):
    url = "YOUR_DIFY_API_URL"
    return requests.post(url, headers=headers, json=body, stream=True)

@app.route("/llm_proxy", methods=["POST"])
def llm_proxy():
    """
    🔥 llm_proxy 是火山引擎 RTC 里的自定义 LLM 代理入口。

    火山引擎会在以下两种场景调用该接口：

    1. StartVoiceChat（开启语音对话）
        - body.messages：包含用户问句（ASR 转成文本后放入）
        - body.model：当前使用的智能体（即 StartVoiceChat.LLMConfig.ModelName）
    
    2. 智能体执行过程中的每次 LLM 调用
        - body.custom：透传业务参数
            - aiBotId：Dify 中对应的智能体 ID
            - clientConvId：用户会话 ID
            - clientUserId：用户唯一 ID

    本接口作用：
    step1：解析火山传入的 LLM 请求
    step2：使用这些参数向 Dify 智能体发起流式请求  
    step3：将 Dify 的流式结果转换为「OpenAI SSE 标准格式」返回给火山（火山必须 SSE 才能驱动实时语音）
    """
    
    # 1️⃣step1: 解析火山引擎发来的智能体调用请求
    print("================== ✅火山引擎发来请求 ==================")
    print(f'''
        ==== 请求头（火山） ====   
    ''')
    for k, v in request.headers.items():
        print(f"{k}: {v}")
    print(f'''==== 请求体（火山） ===
        {request.data}  
        ''')
    
    #解析火山请求体
    try:
        data = json.loads(request.data.decode("utf-8"))
    except Exception as e:
        print("解析JSON失败:", e)
        return "Invalid JSON", 400
    query = ""
    for m in data["messages"]:
        if m.get("role") == "user":
            query = m.get("content")
    aiBotId=data.get("custom",{}).get("aiBotId","")
    clientConvId=data.get("custom",{}).get("clientConvId","")
    clientUserId=data.get("custom",{}).get("clientUserId","")
    
    # 2️⃣step2: 流失式调用dify智能体
    headers={
        "x-access-token":"",
        "Content-Type":"application/json"
    }
    body={
        "aiBotId":aiBotId,
        "clientUserId":clientUserId,
        "clientConvId":clientConvId,
        "query":query
    }
    print("================== ✅向dify发起流式请求 ==================")
    print(f'''
        请求头:
        {headers}
        请求体：
        {body}       
    ''')
    
    
    # 3️⃣step3：解析dify返回为openAI标准(模拟)
    print("================== ✅流返回 ==================")
    def sse_stream():
        # dify_stream = call_dify_stream(headers,body)
        # chunk 1: 角色 delta
        chunk1="data: " + json.dumps({
            "id": str(uuid.uuid4()),
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "storyagent",
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant"}
            }]
        }, ensure_ascii=False) + "\n\n"
        print(chunk1)
        yield chunk1

        time.sleep(0.2)

        # chunk 2: 内容（逐字）
        for ch in "你好，我是自定义LLM":
            chunk="data: " + json.dumps({
                "id": str(uuid.uuid4()),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "storyagent",
                "choices": [{
                    "index": 0,
                    "delta": {"content": ch}
                }]
            }, ensure_ascii=False) + "\n\n"
            print(chunk)
            yield chunk
            time.sleep(0.1)

        # chunk 3: 停止
        chunk3="data: " + json.dumps({
            "id": str(uuid.uuid4()),
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "storyagent",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }],
            "usage":{
                "prompt_tokens":1,
                "completion_tokens":2,
                "total_tokens":3
            }
        }, ensure_ascii=False) + "\n\n"
        print(chunk3)
        yield chunk3

        # End
        chunk4="data: [DONE]\n\n"
        print(chunk4)
        yield chunk4

    return Response(sse_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0",port=8086, debug=True)