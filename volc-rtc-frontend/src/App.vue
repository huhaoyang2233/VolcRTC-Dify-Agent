<template>
  <div class="rtc-app-container">
    <header class="glass-header">
      <div class="brand">
        <span class="bot-icon">🤖</span>
        <h1>讲故事哄睡机器人V1.0</h1>
      </div>

      <div class="timer-display" v-if="currentRoom">
        <div class="timer-box">
          <span class="t-label">房间活跃</span>
          <span class="t-value">{{ formatTime(roomActiveSeconds) }}</span>
        </div>
        <div class="timer-box" v-if="agentOnlineSeconds > 0">
          <span class="t-label">智能体在线</span>
          <span class="t-value">{{ formatTime(agentOnlineSeconds) }}</span>
        </div>
        <div class="timer-box highlight">
          <span class="t-label">{{
            isAiSpeaking ? "AI 说话中" : "AI 沉默中"
          }}</span>
          <span class="t-value">{{ lastStateChangeSeconds }}s</span>
        </div>
      </div>

      <div class="room-status" :class="{ 'is-active': currentRoom }">
        <div class="pulse-dot"></div>
        <span>{{
          currentRoom ? `通话中: ${currentRoom.roomId}` : "未连接"
        }}</span>
      </div>
    </header>

    <main class="workspace">
      <aside class="control-panel">
        <section class="action-card">
          <h3>⚙️ 核心控制</h3>
          <div class="button-group">
            <button
              v-if="!currentRoom && scenes.length === 0"
              @click="fetchScenes"
              class="btn btn-primary"
              :disabled="loading"
            >
              {{ loading ? "同步中..." : "🔑 初始化场景权限" }}
            </button>
            <button @click="testSpeaker" class="btn btn-outline">
              🔊 扬声器测试
            </button>
            <button
              v-if="currentRoom"
              @click="deactivateAgent"
              class="btn btn-danger"
              :disabled="loading"
            >
              🛑 结束通话
            </button>
          </div>
        </section>

        <section class="action-card" v-if="currentRoom">
          <h3>💬 指令操控</h3>
          <div class="control-form">
            <textarea
              v-model="controlText"
              placeholder="输入文字发送给智能体..."
              rows="3"
              class="text-input"
            ></textarea>
            <div class="form-options">
              <label class="checkbox-label">
                <input type="checkbox" v-model="shouldInterrupt" /> 立即打断 AI
              </label>
            </div>
            <button
              @click="controlAgent('ExternalTextToLLM')"
              class="btn btn-action"
              :disabled="!controlText"
            >
              发送文本指令
            </button>
            <div class="mini-btn-group">
              <button @click="controlAgent('Interrupt')" class="btn btn-mini">
                ⚡ 仅打断
              </button>
            </div>
          </div>
        </section>

        <section
          class="scene-selector"
          v-if="!currentRoom && scenes.length > 0"
        >
          <h3>选择场景</h3>
          <div class="scene-grid">
            <div
              v-for="scene in scenes"
              :key="scene.scene.id"
              class="scene-item"
            >
              <div class="scene-info">
                <strong>{{ scene.scene.id }}</strong>
                <code>ID: {{ scene.rtc.RoomId }}</code>
              </div>
              <button
                @click="activateRoomAndAgent(scene)"
                :disabled="loading"
                class="btn-enter"
              >
                进入
              </button>
            </div>
          </div>
        </section>

        <section class="log-section">
          <h3>操作日志</h3>
          <div class="log-list">
            <p v-for="(log, index) in logs" :key="index" v-html="log"></p>
          </div>
        </section>
      </aside>

      <section class="interaction-stage">
        <div class="conversation-view">
          <div class="avatar-wrapper ai-side">
            <div class="avatar-outer" :class="{ 'is-speaking': isAiSpeaking }">
              <div class="avatar-inner">AI</div>
              <div class="wave" v-if="isAiSpeaking"></div>
            </div>
            <span class="label">智能助手</span>
          </div>
          <div class="connector">
            <div class="line" :class="{ active: currentRoom }"></div>
          </div>
          <div class="avatar-wrapper user-side">
            <div
              class="avatar-outer"
              :class="{ 'is-speaking': isUserSpeaking }"
            >
              <div class="avatar-inner">YOU</div>
              <div class="wave" v-if="isUserSpeaking"></div>
            </div>
            <span class="label">儿童</span>
          </div>
        </div>
        <div class="hint-bar">
          <p v-if="!currentRoom">等待开始...</p>
          <p v-else-if="isAiSpeaking" class="ai-status">
            智能体正在讲话 ({{ lastStateChangeSeconds }}s)
          </p>
          <p v-else class="user-status">聆听中...</p>
        </div>
      </section>
    </main>

    <div id="local" style="display: none"></div>
    <div id="remote" style="display: none"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onUnmounted } from "vue";
import axios from "axios";
import VERTC from "@volcengine/rtc";

// --- 状态变量 ---
const BACKEND_URL = "YOUR_BACKEND_API_URL";
const scenes = ref<any[]>([]);
const currentRoom = ref<any>(null);
const loading = ref(false);
const logs = ref<string[]>([]);
const volcClient = ref<any>(null);
const isAiSpeaking = ref(false);
const isUserSpeaking = ref(false);

// 指令控制输入
const controlText = ref("");
const shouldInterrupt = ref(true);

// --- 辅助方法 ---
const formatTime = (s: number) => {
  const m = Math.floor(s / 60);
  const rs = s % 60;
  return `${m.toString().padStart(2, "0")}:${rs.toString().padStart(2, "0")}`;
};

const addLog = (message: string) => {
  const timestamp = new Date().toLocaleTimeString();
  logs.value.unshift(`[${timestamp}] ${message}`);
  if (logs.value.length > 20) logs.value.pop();
};

/**
 * 计时器
 * 监听用户与智能体聊天，当用户长时间不说话时自动触发智能体
 */
const roomActiveSeconds = ref(0); //房间创建时长
const agentOnlineSeconds = ref(0); //智能体进入房间时长
const lastStateChangeSeconds = ref(0); //智能体静默时长
let globalTick: any = null;
const AUTO_WAKEUP_THRESHOLD = 10; // 静默阈值（秒）
const autoWakeupSent = ref(false); // 标记位，防止单次静默重复触发
const noResponseCount = ref(0); // 新增：记录连续未响应次数
//结束全局秒表
const stopGlobalTimer = () => {
  if (globalTick) {
    clearInterval(globalTick);
    globalTick = null;
  }
  // 重置所有数值
  roomActiveSeconds.value = 0;
  agentOnlineSeconds.value = 0;
  lastStateChangeSeconds.value = 0;
  autoWakeupSent.value = false;
  noResponseCount.value = 0; // 重置计数器
};

//开始全局秒表
const startGlobalTimer = () => {
  stopGlobalTimer();
  //心跳状态检测：1s 扫描一次计时参数
  globalTick = setInterval(() => {
    if (currentRoom.value) roomActiveSeconds.value++;
    if (agentOnlineSeconds.value > 0) agentOnlineSeconds.value++;
    lastStateChangeSeconds.value++;

    // --- 自动唤醒逻辑 ---
    if (
      !isAiSpeaking.value &&
      agentOnlineSeconds.value > 0 &&
      lastStateChangeSeconds.value >= AUTO_WAKEUP_THRESHOLD &&
      !autoWakeupSent.value
    ) {
      autoWakeupSent.value = true; // 加锁，防止本轮静默重复触发
      noResponseCount.value++; // 未响应次数 +1   （当用户发声时，自动清零）
      if (noResponseCount.value == 3) {
        // --- 超过 3 次发送结束服务信号 ---
        const finalMsg = "[用户长时间未响应，结束本次服务]";
        addLog(`⚠️ 连续 ${noResponseCount.value - 1} 次提醒无果，触发最终信号`);
        controlAgent("ExternalTextToLLM", finalMsg, true);
      } else if (noResponseCount.value <= 3) {
        // --- 普通唤醒信号 ---
        addLog(`⏰ 静默提醒 (${noResponseCount.value}/3)`);
        controlAgent("ExternalTextToLLM", "[用户没有相应，请继续]", true);
      } else {
        // --- 用户离开 ---
        // 销毁房间
        deactivateAgent();
        addLog(`⚠️ 用户长时间未响应，用户可能已经离开`);
      }
    }
  }, 1000);
};

/**
 * RTC服务核心
 *
 */

//RTC服务监听事件
const setupRTCEvents = () => {
  if (!volcClient.value) return;
  volcClient.value.enableAudioPropertiesReport({ interval: 300 });

  // 用户发声事件
  volcClient.value.on(
    VERTC.events.onLocalAudioPropertiesReport,
    (reports: any[]) => {
      const volume = reports[0]?.audioPropertiesInfo?.linearVolume || 0;
      const isNowSpeaking = volume > 20;
      isUserSpeaking.value = isNowSpeaking;

      // 2. 如果用户正在说话，清空“未响应”计数器
      if (isNowSpeaking && noResponseCount.value > 0) {
        noResponseCount.value = 0;
        addLog("👤 检测到用户有回答，重置未响应计数器");
      }
    }
  );

  //用户发声事件
  volcClient.value.on(
    VERTC.events.onRemoteAudioPropertiesReport,
    (reports: any[]) => {
      const isSpeakingNow = reports.some(
        (r) => r.audioPropertiesInfo?.linearVolume > 50
      );
      if (isSpeakingNow && !isAiSpeaking.value) {
        isAiSpeaking.value = true;
        lastStateChangeSeconds.value = 0;
        autoWakeupSent.value = false;
        addLog("🤖 智能体开始说话");
      } else if (!isSpeakingNow && isAiSpeaking.value) {
        isAiSpeaking.value = false;
        lastStateChangeSeconds.value = 0;
        autoWakeupSent.value = false;
        addLog("🤖 智能体说话结束");
      }
    }
  );

  //监听用户进房
  volcClient.value.on(VERTC.events.onUserJoined, (user: any) => {
    addLog(`🤖 智能体入场: ${user.userInfo.userId}`);
    agentOnlineSeconds.value = 1;
  });

  //监听连接状态
  volcClient.value.on(VERTC.events.onConnectionStateChanged, (e) => {
    addLog(`🤖 连接状态: ${e}`);
  });
};

// 初始化RTC服务
const initAndJoinRTC = async (room: any) => {
  volcClient.value = VERTC.createEngine(room.appId);
  setupRTCEvents();

  //房间创建超时检测
  const waitConnected = new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("⏰ 加入房间超时")),
      15000
    );
    const onStateChange = (event: any) => {
      if (event.state === 3) {
        clearTimeout(timeout);
        volcClient.value.off(
          VERTC.events.onConnectionStateChanged,
          onStateChange
        );
        startGlobalTimer();
        resolve();
      }
    };
    volcClient.value.on(VERTC.events.onConnectionStateChanged, onStateChange);
  });
  // 用户进入房间
  await volcClient.value.joinRoom(
    room.token,
    room.roomId,
    { userId: room.userId },
    { isAutoPublish: true, isAutoSubscribeAudio: true }
  );
  await waitConnected;
  await volcClient.value.startAudioCapture("default");
};

// 智能体进入房间
const activateRoomAndAgent = async (sceneData: any) => {
  if (currentRoom.value) return;
  const { AppId, RoomId, UserId, Token } = sceneData.rtc;
  currentRoom.value = {
    roomId: RoomId,
    userId: UserId,
    appId: AppId,
    token: Token,
    taskId: `task-${Date.now()}`,
  };

  try {
    await initAndJoinRTC(currentRoom.value);
    // 接口 1: StartVoiceChat
    await axios.post(`${BACKEND_URL}/proxy`, {
      Action: "StartVoiceChat",
      Version: "2024-12-01",
      Dynamic: {
        AppId,
        RoomId,
        TaskId: currentRoom.value.taskId,
        AgentConfig: {
          TargetUserId: [UserId],
          UserId: `Agent_${sceneData.scene.id}`,
          WelcomeMessage: "你好呀，我是儿童陪伴师",
        },
      },
    });
    addLog("✅ 智能体激活指令已下发");
    controlAgent("ExternalTextToLLM", "[用户来了，开始聊天]", true);
  } catch (error) {
    addLog(`❌ 启动失败: ${error}`);
    currentRoom.value = null;
  }
};

// 智能体退出房间
const deactivateAgent = async () => {
  if (!currentRoom.value) return;
  const room = currentRoom.value; // 闭包存储，防止置空后无法访问
  loading.value = true;

  try {
    stopGlobalTimer();
    await volcClient.value?.leaveRoom();
    VERTC.destroyEngine(volcClient.value);
    volcClient.value = null;
    currentRoom.value = null;

    // 接口 2: StopVoiceChat
    await axios.post(`${BACKEND_URL}/proxy`, {
      Action: "StopVoiceChat",
      Version: "2024-12-01",
      Dynamic: { AppId: room.appId, RoomId: room.roomId, TaskId: room.taskId },
    });
    addLog("✅ 智能体退出指令已下发");
  } catch (error) {
    addLog("❌ 停止指令下发异常");
  } finally {
    loading.value = false;
  }
};

// 智能体控制（发送指令）
const controlAgent = async (
  actionType: "ExternalTextToLLM" | "Interrupt",
  customMsg?: string,
  overrideInterrupt?: boolean
) => {
  if (!currentRoom.value) return;

  try {
    const payload: any = {
      Action: "UpdateVoiceChat",
      Version: "2024-12-01",
      Dynamic: {
        AppId: currentRoom.value.appId,
        RoomId: currentRoom.value.roomId,
        TaskId: currentRoom.value.taskId,
        Command: actionType,
        // 如果有传入 overrideInterrupt 则用传入的，否则用 UI 上的 shouldInterrupt
        InterruptMode: (
          overrideInterrupt !== undefined
            ? overrideInterrupt
            : shouldInterrupt.value
        )
          ? 1
          : 0,
      },
    };

    // 优先使用 customMsg（自动唤醒），否则使用 controlText.value（用户手动输入）
    if (actionType === "ExternalTextToLLM") {
      payload.Dynamic.Message = customMsg || controlText.value;
    }

    await axios.post(`${BACKEND_URL}/proxy`, payload);
    addLog(`✅ 指令 [${actionType}] 已下发${customMsg ? " (系统触发)" : ""}`);

    // 如果是手动发的，才清空输入框
    if (!customMsg && actionType === "ExternalTextToLLM")
      controlText.value = "";
  } catch (error) {
    addLog(`❌ 指令下发失败: ${actionType}`);
    if (customMsg) autoWakeupSent.value = false; // 自动唤醒失败了允许重试
  }
};

// 用户获取进入房间权限
const fetchScenes = async () => {
  loading.value = true;
  try {
    const response = await axios.post(`${BACKEND_URL}/getScenes`);
    scenes.value = response.data.scenes;
    addLog("🔑 场景同步成功");
  } catch (e) {
    addLog("❌ 同步场景失败");
  } finally {
    loading.value = false;
  }
};

//扬声器测试
const testSpeaker = async () => {
  const ctx = new AudioContext();
  const osc = ctx.createOscillator();
  osc.connect(ctx.destination);
  osc.start();
  setTimeout(() => {
    osc.stop();
    ctx.close();
  }, 500);
};

onUnmounted(() => stopGlobalTimer());
</script>

<style scoped>
.timer-display {
  display: flex;
  gap: 15px;
  background: #f1f5f9;
  padding: 5px 15px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.timer-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
}

.timer-box.highlight .t-value {
  color: #3182ce;
  font-weight: 800;
}

.t-label {
  font-size: 10px;
  color: #64748b;
  text-transform: uppercase;
}

.t-value {
  font-family: "Monaco", "Courier New", monospace;
  font-size: 14px;
  color: #1e293b;
}
/* 核心布局 */
.rtc-app-container {
  min-height: 100vh;
  background-color: #f4f7f9;
  display: flex;
  flex-direction: column;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.glass-header {
  background: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 10;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand h1 {
  font-size: 1.25rem;
  margin: 0;
  color: #1a1a1a;
}

.room-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  color: #666;
  padding: 6px 12px;
  border-radius: 20px;
  background: #eee;
}

.room-status.is-active {
  background: #e6fffa;
  color: #059669;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  background: currentColor;
  border-radius: 50%;
}

.is-active .pulse-dot {
  animation: pulse 1.5s infinite;
}

/* 工作区 */
.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 350px 1fr;
  padding: 20px;
  gap: 20px;
}

.control-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.action-card,
.scene-selector,
.log-section {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
}

h3 {
  font-size: 1rem;
  margin-top: 0;
  margin-bottom: 15px;
  color: #4a5568;
  border-bottom: 1px solid #edf2f7;
  padding-bottom: 10px;
}

/* 按钮样式 */
.btn {
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 10px;
  transition: all 0.2s;
}

.btn-primary {
  background: #3182ce;
  color: white;
}
.btn-primary:hover {
  background: #2b6cb0;
}
.btn-outline {
  background: transparent;
  border: 1.5px solid #cbd5e0;
  color: #4a5568;
}
.btn-danger {
  background: #e53e3e;
  color: white;
}

.scene-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: #f8fafc;
  border-radius: 8px;
  margin-bottom: 8px;
}

.scene-info {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
}

.btn-enter {
  padding: 5px 15px;
  background: #3182ce;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* 日志列表 */
.log-list {
  height: 200px;
  overflow-y: auto;
  font-size: 12px;
  color: #718096;
  line-height: 1.6;
}

/* 交互舞台 */
.interaction-stage {
  background: white;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.conversation-view {
  display: flex;
  align-items: center;
  gap: 40px;
  margin-bottom: 50px;
}

.avatar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.avatar-outer {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  background: #f1f5f9;
  transition: transform 0.3s;
}

.avatar-inner {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: #3182ce;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 1.2rem;
  z-index: 2;
}

.user-side .avatar-inner {
  background: #38a169;
}

.is-speaking.avatar-outer {
  transform: scale(1.05);
}

/* 语音波纹 */
.wave {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid currentColor;
  border-radius: 50%;
  color: #3182ce;
  animation: ripple 1.5s infinite ease-out;
}

.user-side .wave {
  color: #38a169;
}

@keyframes ripple {
  0% {
    transform: scale(1);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.8);
    opacity: 0;
  }
}

.connector {
  width: 150px;
  height: 2px;
  background: #edf2f7;
  position: relative;
}

.connector .line.active {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, #3182ce, #38a169);
  animation: glow 2s infinite alternate;
}

@keyframes glow {
  from {
    opacity: 0.3;
  }
  to {
    opacity: 1;
  }
}

.hint-bar {
  font-size: 1.1rem;
  color: #4a5568;
  height: 30px;
}

.ai-status {
  color: #3182ce;
  font-weight: 500;
}
.user-status {
  color: #38a169;
  font-weight: 500;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
  100% {
    opacity: 1;
  }
}
/* 指令控制表单样式 (新增) */
.control-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.text-input {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #cbd5e0;
  resize: none;
  font-size: 13px;
}
.checkbox-label {
  font-size: 12px;
  color: #4a5568;
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}
.btn-action {
  background: #4a5568;
  color: white;
  margin-bottom: 5px;
}
.mini-btn-group {
  display: flex;
  gap: 5px;
}
.btn-mini {
  padding: 5px;
  font-size: 11px;
  background: #edf2f7;
  color: #4a5568;
}
</style>
