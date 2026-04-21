# 🌋 VolcRTC-Dify Agent

> 基于火山引擎 RTC + Dify 构建的智能体语音对话系统，实现 Web/H5 端实时语音交互，兼容 iOS/Android 移动端权限，支持智能体接入和自定义 LLM 集成。

## ✨ 项目特性

- 🎯 **跨平台兼容**: 完美支持 iOS、Android 移动端网页和桌面端浏览器
- 🔊 **实时语音交互**: 基于火山引擎 RTC 实现低延迟语音通话
- 🤖 **Dify 智能体对接**: 无缝集成 Dify 平台，支持自定义智能体接入
- ⏰ **自动唤醒机制**: 用户长时间静默时自动触发智能体交互
- 📊 **实时状态监控**: 显示房间状态、通话时长、AI 说话状态等
- 🔒 **安全认证**: 基于 Token 的身份认证机制

## 🛠️ 技术栈

### 后端
| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 服务端语言 |
| Flask | 2.0+ | Web 框架 |
| Flask-CORS | 4.0+ | 跨域支持 |
| Requests | 2.31+ | HTTP 请求库 |

### 前端
| 技术 | 版本 | 说明 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| TypeScript | 5.4+ | 类型安全 |
| Vite | 5.2+ | 构建工具 |
| Axios | 1.6+ | HTTP 客户端 |
| VolcEngine RTC | latest | 火山引擎 RTC SDK |

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端层 (Web/H5)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  UI 界面     │  │  RTC 引擎    │  │  状态管理           │  │
│  │  (Vue 3)    │  │ (VERTC SDK) │  │  (Composition API)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                        后端层 (Flask)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Proxy API   │  │ Token 生成   │  │  Dify 智能体对接    │  │
│  │ (/proxy)    │  │ (/getScenes) │  │  (/llm_proxy)       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     服务层                                      │
│  ┌───────────────────────────────────┐  ┌─────────────────┐   │
│  │    火山引擎                       │  │    Dify         │   │
│  │  RTC │ ASR │ TTS │ LLM API      │  │  智能体平台     │   │
│  └───────────────────────────────────┘  └─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- 火山引擎账号（需开通 RTC、ASR、TTS 服务）

### 后端部署

```bash
# 进入后端目录
cd rtc_server

# 安装依赖
pip install -r requirements.txt

# 配置参数 (详见配置说明)
# 修改 Scenes/Custom.json 中的配置

# 启动服务
python server_main.py
```

### 前端运行

```bash
# 进入前端目录
cd volc-rtc-frontend

# 安装依赖
npm install

# 配置后端地址 (详见配置说明)
# 修改 src/App.vue 中的 BACKEND_URL

# 开发模式运行
npm run dev

# 构建生产版本
npm run build
```

## ⚙️ 配置说明

### 后端配置 (`rtc_server/Scenes/Custom.json`)

```json
{
  "AccountConfig": {
    "accessKeyId": "YOUR_ACCESS_KEY_ID",
    "secretKey": "YOUR_SECRET_KEY",
    "host": "rtc.volcengineapi.com",
    "service": "rtc",
    "version": "2024-12-01",
    "region": "cn-north-1"
  },
  "RTCConfig": {
    "AppId": "YOUR_RTC_APP_ID",
    "AppKey": "YOUR_RTC_APP_KEY"
  },
  "VoiceChat": {
    "Config": {
      "ASRConfig": {
        "Provider": "volcano",
        "ProviderParams": {
          "Mode": "smallmodel",
          "AppId": "YOUR_ASR_APP_ID"
        }
      },
      "TTSConfig": {
        "Provider": "volcano_bidirection",
        "ProviderParams": {
          "app": {
            "appid": "YOUR_TTS_APP_ID",
            "token": "YOUR_TTS_TOKEN"
          }
        }
      },
      "LLMConfig": {
        "Mode": "CustomLLM",
        "Url": "YOUR_LLM_API_URL"
      }
    }
  }
}
```

### 前端配置 (`volc-rtc-frontend/src/App.vue`)

```typescript
const BACKEND_URL = "YOUR_BACKEND_API_URL"; // 如: "http://your-server:8086"
```

## 🔌 API 接口

### 1. 获取场景配置

**POST** `/getScenes`

获取可用的场景列表和对应的 RTC Token。

**响应示例**:
```json
{
  "scenes": [
    {
      "scene": { "id": "custom", "name": "自定义助手" },
      "rtc": {
        "AppId": "xxx",
        "RoomId": "xxx",
        "UserId": "xxx",
        "Token": "xxx"
      }
    }
  ]
}
```

### 2. 代理请求

**POST** `/proxy`

转发请求到火山引擎 RTC 服务，支持以下操作：

#### StartVoiceChat - 启动智能体
```json
{
  "Action": "StartVoiceChat",
  "Version": "2024-12-01",
  "Dynamic": {
    "AppId": "xxx",
    "RoomId": "xxx",
    "TaskId": "xxx",
    "AgentConfig": {
      "UserId": "Bot001",
      "TargetUserId": ["user1"],
      "WelcomeMessage": "你好呀！"
    }
  }
}
```

#### StopVoiceChat - 停止智能体
```json
{
  "Action": "StopVoiceChat",
  "Version": "2024-12-01",
  "Dynamic": {
    "AppId": "xxx",
    "RoomId": "xxx",
    "TaskId": "xxx"
  }
}
```

#### UpdateVoiceChat - 更新智能体
```json
{
  "Action": "UpdateVoiceChat",
  "Version": "2024-12-01",
  "Dynamic": {
    "AppId": "xxx",
    "RoomId": "xxx",
    "TaskId": "xxx",
    "Command": "ExternalTextToLLM",
    "Message": "你好",
    "InterruptMode": 1
  }
}
```

### 3. LLM 代理

**POST** `/llm_proxy`

火山引擎 RTC 自定义 LLM 代理入口，将火山请求转换为标准 SSE 格式返回。

## 📱 移动端兼容性

### iOS Safari 权限处理

```typescript
// 必须在用户交互事件中请求媒体权限
async requestMediaPermission() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: false
    });
    // 释放流，仅用于获取权限
    stream.getTracks().forEach(track => track.stop());
  } catch (error) {
    console.error('Media permission denied:', error);
  }
}
```

### Android Chrome 注意事项

- 确保使用 HTTPS 协议（HTTP 下某些 API 受限）
- 建议在用户点击事件中初始化 RTC
- 注意后台音频播放限制

## 🧠 核心功能实现

### 自动唤醒机制

系统内置智能唤醒逻辑，当用户长时间未响应时自动触发：

1. **静默检测**: 监听用户语音输入状态
2. **唤醒策略**: 
   - 首次静默 10 秒后发送提醒
   - 连续 3 次提醒无果后发送结束信号
   - 用户发声时重置计数器

### 语音状态监控

```typescript
// 监听本地音频状态（用户说话）
volcClient.on(VERTC.events.onLocalAudioPropertiesReport, (reports) => {
  const volume = reports[0]?.audioPropertiesInfo?.linearVolume || 0;
  isUserSpeaking.value = volume > 20;
});

// 监听远端音频状态（AI 说话）
volcClient.on(VERTC.events.onRemoteAudioPropertiesReport, (reports) => {
  const isSpeaking = reports.some(r => r.audioPropertiesInfo?.linearVolume > 50);
  isAiSpeaking.value = isSpeaking;
});
```

### 自定义 LLM 集成（对接通用模型）

本项目支持对接任意第三方 LLM 模型（如 OpenAI、Dify、本地模型等），而非局限于火山引擎内置模型。核心实现通过 `CustomLLM` 模式完成：

#### 对接原理

```
┌─────────────────────────────────────────────────────────────────┐
│                    火山引擎 RTC 服务                            │
│                    LLMConfig: CustomLLM                        │
│                          │                                     │
│                          ▼                                     │
│              ┌─────────────────────┐                           │
│              │   /llm_proxy 接口   │  ← 自定义 LLM 代理入口     │
│              └─────────┬───────────┘                           │
│                        │                                       │
│                        ▼                                       │
│              ┌─────────────────────┐                           │
│              │    标准 SSE 转换    │  ← 转换为 OpenAI SSE 格式  │
│              └─────────┬───────────┘                           │
│                        │                                       │
│                        ▼                                       │
│              ┌─────────────────────┐                           │
│              │   Dify/OpenAI/自定义│  ← 对接任意 LLM 服务      │
│              └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

#### 配置方式

在 `Scenes/Custom.json` 中配置自定义 LLM：

```json
{
  "VoiceChat": {
    "Config": {
      "LLMConfig": {
        "Mode": "CustomLLM",
        "Url": "YOUR_LLM_API_URL",
        "APIKey": "",
        "ModelName": "",
        "Feature": "{\"Http\":true}"
      }
    }
  }
}
```

#### 对接流程

1. **配置 CustomLLM 模式**: 将 `LLMConfig.Mode` 设置为 `"CustomLLM"`
2. **设置 API 地址**: 在 `LLMConfig.Url` 中配置你的 LLM 服务地址
3. **实现代理转换**: 后端 `/llm_proxy` 接口负责：
   - 解析火山引擎发来的请求格式
   - 转换为目标 LLM 的请求格式
   - 将响应转换为标准 SSE 格式返回

#### Dify 智能体对接示例

后端通过 `/llm_proxy` 接口对接 Dify 智能体：

```python
def call_dify_stream(headers, body):
    url = "YOUR_DIFY_API_URL"
    return requests.post(url, headers=headers, json=body, stream=True)
```

请求参数透传机制：

| 火山引擎参数 | Dify 参数 | 说明 |
|-------------|----------|------|
| `custom.aiBotId` | `aiBotId` | Dify 智能体 ID |
| `custom.clientConvId` | `clientConvId` | 用户会话 ID |
| `custom.clientUserId` | `clientUserId` | 用户唯一标识 |
| `messages[].content` | `query` | 用户提问内容 |

#### 支持的模型类型

- ✅ **Dify 智能体**: 通过 Dify 平台部署的自定义智能体
- ✅ **OpenAI API**: 标准 OpenAI 兼容接口
- ✅ **自定义 API**: 任意支持流式响应的 LLM 服务
- ✅ **本地模型**: 部署在本地的开源模型（如 Llama、Qwen 等）

## 📁 项目结构

```
volcengine_rtc/
├── rtc_server/                    # 后端服务
│   ├── Authentication/            # 认证模块
│   │   ├── AccessToken.py         # Token 生成
│   │   └── Sign.py                # 签名认证
│   ├── Scenes/                    # 场景配置
│   │   └── Custom.json            # 自定义配置
│   ├── util/                      # 工具函数
│   │   └── util.py
│   ├── requirements.txt           # 依赖清单
│   └── server_main.py             # 主服务入口
├── volc-rtc-frontend/             # 前端应用
│   ├── src/
│   │   ├── components/            # 组件
│   │   ├── App.vue               # 主应用组件
│   │   ├── main.ts               # 入口文件
│   │   └── style.css             # 全局样式
│   ├── index.html                # HTML 模板
│   ├── package.json              # 依赖配置
│   ├── vite.config.ts            # Vite 配置
│   └── tsconfig.json             # TypeScript 配置
└── README.md                     # 项目说明
```

## 🔒 安全注意事项

1. **敏感信息保护**: 不要将 AK/SK 等敏感信息硬编码到代码中
2. **Token 管理**: RTC Token 应设置合理的过期时间
3. **HTTPS 强制**: 生产环境必须使用 HTTPS
4. **输入验证**: 对用户输入进行严格验证，防止注入攻击

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**提示**: 部署前请确保已在火山引擎控制台完成以下配置：
1. 创建 RTC 应用并获取 AppId/AppKey
2. 开通 ASR 服务并获取相关凭证
3. 开通 TTS 服务并获取相关凭证
4. 创建 API 密钥（AK/SK）
