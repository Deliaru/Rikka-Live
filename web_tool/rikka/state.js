export const state = {
  view: "overview",
  health: null,
  clients: null,
  flow: null,
  events: [],
  expandedEventGroups: new Set(),
  // 各 flow 渲染区域上一帧的内容指纹；指纹未变时跳过 DOM 重建，
  // 避免轮询导致滚动位置丢失。键：stageGrid / timeline / eventList。
  flowFingerprints: {},
  settings: null,
  config: null,
  bilibili: null,
  capture: null,
  windows: null,
  proactive: null,
  overlay: null,
  logs: null,
  errors: null,
  mic: {
    status: "unknown",
    reason: "尚未测试",
    permission: "unknown",
    asr: "unknown",
    transcript: "",
    wakeDecision: "unknown",
    owner: null,
    ownerClientUid: "",
    clientUid: "",
    alwaysOnEnabled: false,
    listening: false,
    audioLevel: 0,
    streamingStatus: "unknown",
    finalCount: 0,
    chunksCaptured: 0,
    chunksSent: 0,
    chunksDroppedNotOwner: 0,
    chunksDroppedQuiet: 0,
    endpointsSent: 0,
    updatedAt: null,
  },
};

export const viewMeta = {
  overview: ["总览", "连接、阻塞点和最近动作"],
  lab: ["测试台", "主动验证 Live2D、TTS、捕捉、主动发言和麦克风"],
  flow: ["事件与 Flow", "处理链路、前端回执和 Recent Events 回放边界"],
  config: ["配置", "按 LLM、TTS、Overlay、Capture、Proactive、Mic 分组"],
  logs: ["日志", "Provider errors 和本地日志尾部"],
};

export const emotionFields = [
  "happy",
  "angry",
  "sad",
  "fear",
  "disgust",
  "melancholy",
  "surprise",
  "calm",
];

export const defaultIndexVector = [0.10, 0, 0, 0, 0, 0.20, 0, 0.10];
