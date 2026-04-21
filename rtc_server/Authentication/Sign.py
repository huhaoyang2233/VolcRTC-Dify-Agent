import datetime
import hashlib
import hmac
from urllib.parse import quote
import requests
import json
# -----------------------
# 工具函数（保持你原版的逻辑）
# -----------------------
def load_config(path="./Scenes/Custom.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()
AK = config["AccountConfig"]["accessKeyId"]
SK = config["AccountConfig"]["secretKey"]
HOST = config["AccountConfig"]["host"]
SERVICE = config["AccountConfig"]["service"]
VERSION = config["AccountConfig"]["version"]
REGION = config["AccountConfig"]["region"]

# -----------------------
# 工具函数（保持你原版的逻辑）
# -----------------------

def norm_query(params):
    query = ""
    for key in sorted(params.keys()):
        if isinstance(params[key], list):
            for k in params[key]:
                query += f"{quote(key, safe='-_.~')}={quote(k, safe='-_.~')}&"
        else:
            query += f"{quote(key, safe='-_.~')}={quote(params[key], safe='-_.~')}&"

    return query[:-1].replace("+", "%20")


def hmac_sha256(key: bytes, content: str):
    return hmac.new(key, content.encode("utf-8"), hashlib.sha256).digest()


def hash_sha256(content: str):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def utc_now():
    try:
        from datetime import timezone
        return datetime.datetime.now(timezone.utc)
    except ImportError:
        class UTC(datetime.tzinfo):
            def utcoffset(self, dt):
                return datetime.timedelta(0)

            def tzname(self, dt):
                return "UTC"

            def dst(self, dt):
                return datetime.timedelta(0)

        return datetime.datetime.now(UTC())


# -------------------------------------------------------
# ⭐⭐⭐ 最终封装：统一的 volc_sign_request() 函数 ⭐⭐⭐
# -------------------------------------------------------

def volc_sign_request(
        method,
        action,
        query=None,
        body="",
        content_type="application/json",
        extra_headers=None
):
    """
    自动从 config.json 加载 AK/SK/Host/Service/Region/Version
    用户只需要提供 method/action/query/body
    """

    # -----------------------
    # 自动加载全局配置
    # -----------------------
    ak = AK
    sk = SK
    host = HOST
    service = SERVICE
    region = REGION
    version = VERSION

    date = utc_now()

    # -----------------------
    # 构建请求参数
    # -----------------------
    request_param = {
        "body": body if body is not None else "",
        "host": host,
        "path": "/",
        "method": method,
        # "content_type": content_type,
        "date": date,
        "query": {"Action": action, "Version": version, **(query or {})},
    }

    # -----------------------
    # 计算 canonical request
    # -----------------------
    x_date = date.strftime("%Y%m%dT%H%M%SZ")
    short_x_date = x_date[:8]
    x_content_sha256 = hash_sha256(request_param["body"])

    # signed_headers_str = "content-type;host;x-content-sha256;x-date"
    signed_headers_str = "host;x-content-sha256;x-date"
    canonical_headers = "\n".join([
        # f"content-type:{content_type}",
        f"host:{host}",
        f"x-content-sha256:{x_content_sha256}",
        f"x-date:{x_date}",
    ])

    canonical_request = "\n".join([
        method.upper(),
        request_param["path"],
        norm_query(request_param["query"]),
        canonical_headers,
        "",
        signed_headers_str,
        x_content_sha256
    ])

    hashed_canonical_request = hash_sha256(canonical_request)
    credential_scope = f"{short_x_date}/{region}/{service}/request"

    string_to_sign = "\n".join([
        "HMAC-SHA256",
        x_date,
        credential_scope,
        hashed_canonical_request
    ])

    # -----------------------
    # 计算签名值
    # -----------------------
    k_date = hmac_sha256(sk.encode("utf-8"), short_x_date)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    k_signing = hmac_sha256(k_service, "request")
    signature = hmac_sha256(k_signing, string_to_sign).hex()

    # -----------------------
    # 构建最终请求头
    # -----------------------
    headers = {
        "Content-Type": content_type,
        "Host": host,
        "X-Content-Sha256": x_content_sha256,
        "X-Date": x_date,
        "Authorization": (
            f"HMAC-SHA256 Credential={ak}/{credential_scope}, "
            f"SignedHeaders={signed_headers_str}, "
            f"Signature={signature}"
        )
    }

    if extra_headers:
        headers.update(extra_headers)

    url = f"https://{host}/"
    # 返回给你的调用者
    return {
        "method": method,
        "headers": headers,
        "body": request_param["body"],
        "params": request_param["query"],
    }

# ---------------------------------------------------------
# 使用示例
# ---------------------------------------------------------
# if __name__ == "__main__":
#     req = {
#         "AppId": "YOUR_APP_ID",	
#         "RoomId": "room1",
#         "TaskId": "task1",
#         "Config": {
#             "ASRConfig": {
#                 "Provider": "volcano",
#                 "ProviderParams": {
#                     "Mode": "smallmodel",
#                     "AppId": "YOUR_ASR_APP_ID"
#                 }
#             },
#             "TTSConfig": {
#                 "Provider": "volcano",
#                 "ProviderParams": {
#                     "Credential": {
#                         "AppId": "YOUR_TTS_APP_ID",
#                         "Token": "YOUR_TTS_TOKEN",
#                         "ResourceId": "volcano_tts"
#                     }
#                 }
#             },
#             "LLMConfig": {"Mode": "CustomLLM"}
#         },
#         "AgentConfig": {
#             "TargetUserId": ["user1"],
#             "UserId":"robot1"
#         }
#     }
#     sign_data = volc_sign_request(
#         method="POST",
#         action="StartVoiceChat",
#         query={},
#         body=json.dumps(req)
#     )
#     print(sign_data)