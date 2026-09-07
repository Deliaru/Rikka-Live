import { $, text } from "./dom.js";
import { defaultIndexVector, emotionFields, state } from "./state.js";

const ids = {
  llmProvider: "llm-provider",
  llmApiMode: "llm-api-mode",
  llmBaseUrl: "llm-base-url",
  llmModel: "llm-model",
  llmApiKey: "llm-api-key",
  responsePrompt: "response-prompt",
  personaPrompt: "persona-prompt",
  ttsProvider: "tts-provider",
  indexMode: "index-mode",
  indexApiKey: "index-api-key",
  indexVoiceId: "index-voice-id",
  indexBaseUrl: "index-base-url",
  indexModel: "index-model",
  indexApiUrl: "index-api-url",
  indexSpeakerAudio: "index-speaker-audio",
  indexDefaultStyle: "index-default-style",
  indexSegment: "index-segment",
  indexSentenceGap: "index-sentence-gap",
  indexSentenceEnabled: "index-sentence-enabled",
  indexQuietAlpha: "index-quiet-alpha",
  asrProvider: "asr-provider",
  bilibiliRoomIds: "bilibili-room-ids",
  bilibiliSessdata: "bilibili-sessdata",
  bilibiliSpeak: "bilibili-speak",
  bilibiliUseProxy: "bilibili-use-proxy",
  bilibiliProxyUrl: "bilibili-proxy-url",
  bilibiliTestText: "bilibili-test-text",
};
const multimodalProviderOptions = [
  "not_configured",
  "openai_compatible_llm",
  "openai_llm",
  "gemini_llm",
  "zhipu_llm",
  "deepseek_llm",
  "groq_llm",
  "mistral_llm",
  "ollama_llm",
  "lmstudio_llm",
];

export function setupEmotionInputs() {
  const grid = $("index-vector-grid");
  if (!grid || grid.children.length) return;
  emotionFields.forEach((field, index) => {
    const label = document.createElement("label");
    label.textContent = field;
    const input = document.createElement("input");
    input.id = `index-vec-${field}`;
    input.type = "number";
    input.min = "0";
    input.max = "1.2";
    input.step = "0.01";
    input.value = String(defaultIndexVector[index] || 0);
    label.append(input);
    grid.append(label);
  });
}

export function renderSettingsForm(settings = {}) {
  state.settings = settings;
  const capture = settings.capture || {};
  const proactive = settings.proactive || {};
  const audio = settings.audio || {};
  const overlay = settings.overlay || {};
  const agent = settings.agent || {};
  const memory = settings.memory || {};
  const mood = settings.mood || {};
  const innerLife = settings.inner_life || {};
  const identity = settings.identity || {};
  const ttsPost = settings.tts_post_processing || {};

  setChecked("screen-capture-enabled", settings.screen_capture_enabled);
  setChecked("keyframe-upload-enabled", settings.keyframe_upload_enabled);
  setChecked("debug-media-logging-enabled", settings.debug_media_logging_enabled);
  setSelectOptions("multimodal-provider", withCurrentOption(multimodalProviderOptions, settings.multimodal_provider));
  setValue("multimodal-provider", settings.multimodal_provider || "not_configured");
  setChecked("capture-enabled", capture.enabled);
  setValue("capture-mode", capture.mode || "whitelist");
  setChecked("capture-allow-foreground", capture.allow_foreground_debug);
  setChecked("capture-attach-turns", capture.attach_to_user_turns);
  setValue("capture-window-list", listToText(capture.window_title_allowlist));
  setValue("capture-process-list", listToText(capture.process_name_allowlist));

  setChecked("proactive-screen", proactive.screen_comments_enabled);
  setChecked("proactive-idle", proactive.idle_speech_enabled);
  setValue("proactive-interval", proactive.scheduler_interval_ms);
  setValue("proactive-idle-ms", proactive.min_user_idle_ms);
  setValue("proactive-screen-cooldown", proactive.screen_comment_cooldown_ms);
  setValue("proactive-idle-cooldown", proactive.idle_speech_cooldown_ms);
  setChecked("proactive-change-gate", proactive.screen_change_gate_enabled ?? true);
  setValue("proactive-change-threshold", proactive.screen_change_threshold ?? 0.12);
  setValue("proactive-followup-window", proactive.proactive_followup_window_ms ?? 18000);

  setChecked("mood-enabled", mood.enabled ?? true);
  setChecked("mood-tts-adjust", mood.tts_adjustment_enabled ?? true);
  setValue("mood-half-life", mood.half_life_minutes ?? 10);
  setChecked("inner-life-enabled", innerLife.enabled ?? true);
  setValue("inner-life-rotation", innerLife.rotation_minutes ?? 18);
  setValue("inner-life-activities", listToText(innerLife.activities));
  setValue("identity-host-name", identity.host_display_name || "Deliaru");
  setValue("identity-audience-name", identity.audience_display_name || "\u5f39\u5e55");

  setChecked("agent-tools-enabled", agent.tools_enabled);
  setChecked("agent-look-screen", agent.look_at_screen_enabled ?? true);
  setChecked("agent-get-time", agent.get_time_enabled ?? true);
  setChecked("agent-web-search", agent.web_search_enabled ?? true);
  setChecked("agent-filler", agent.filler_enabled ?? true);
  setValue("agent-pre-silence-ms", agent.result_pre_silence_ms ?? 1000);
  setValue("agent-max-rounds", agent.max_tool_rounds ?? 3);
  setValue("agent-search-timeout", agent.web_search_timeout_seconds ?? 15);
  setValue("memory-summary-per-kind", memory.summary_per_kind ?? 5);
  setValue("memory-per-kind-cap", memory.per_kind_cap ?? 50);

  setChecked("wake-gate-enabled", audio.wake_gate_enabled);
  setChecked("mic-conversation-enabled", audio.mic_conversation_enabled);
  setValue("wake-phrases", listToText(audio.wake_phrases));
  setValue("wake-asr-confusions", listToText(audio.wake_asr_confusions));
  setValue("wake-window-ms", audio.wake_active_window_ms);

  setChecked("overlay-asr-hud-visible", overlay.asr_hud_visible ?? true);
  setChecked("overlay-pointer", overlay.global_pointer_tracking_enabled);
  setValue("overlay-pointer-mode", overlay.pointer_tracking_mode || "natural_layered");
  setValue("overlay-pointer-intensity", overlay.pointer_tracking_intensity ?? 1.0);
  setValue("overlay-pointer-smoothness", overlay.pointer_tracking_smoothness ?? 0.65);
  setValue("overlay-pointer-deadzone", overlay.pointer_tracking_deadzone ?? 0.05);
  setChecked("overlay-subtitle-visible", overlay.subtitle_visible);
  setValue("overlay-subtitle-layout", overlay.subtitle_layout_mode || "anchor");
  setValue("overlay-subtitle-anchor", overlay.subtitle_anchor || "bottom_left");
  setValue("overlay-subtitle-width", overlay.subtitle_width_px || overlay.subtitle_max_width_px || 520);
  setValue("overlay-subtitle-x", overlay.subtitle_left_px || overlay.subtitle_offset_x_px || 44);
  setValue("overlay-subtitle-y", overlay.subtitle_top_px || overlay.subtitle_offset_y_px || 520);

  setChecked("tts-post-enabled", ttsPost.enabled);
  setValue("tts-post-trim-max", ttsPost.trim_max_ms ?? 200);
  setValue("tts-post-trim-min-tail", ttsPost.trim_min_tail_ms ?? 80);
  setValue("tts-post-fade-out", ttsPost.fade_out_ms ?? 15);
  setValue("tts-post-threshold-db", ttsPost.trim_rms_threshold_db ?? -40);
}

export function renderConfigForm(config = {}) {
  state.config = config;
  const llm = config.llm || {};
  const tts = config.tts || {};
  const index = tts.indextts2_tts || {};
  const asr = config.asr || {};
  const live = config.live || {};
  const bilibili = live.bilibili_live || {};
  const bilibiliRoomIds = bilibili.room_ids || state.bilibili?.configured_room_ids || [];
  const prompts = config.prompts || {};

  setSelectOptions(
    ids.llmProvider,
    withCurrentOption(llm.available_providers || ["openai_compatible_llm"], llm.provider)
  );
  setValue(ids.llmProvider, llm.provider || "");
  setValue(ids.llmApiMode, llm.api_mode || "");
  setValue(ids.llmBaseUrl, llm.base_url || "");
  setValue(ids.llmModel, llm.model || "");
  setValue(ids.llmApiKey, "");
  setValue(ids.responsePrompt, prompts.response?.text || "");
  setValue(ids.personaPrompt, prompts.persona?.text || "");
  setSelectOptions(
    ids.ttsProvider,
    withCurrentOption(selectValues(ids.ttsProvider), tts.provider || "indextts2_tts")
  );
  setValue(ids.ttsProvider, tts.provider || "indextts2_tts");
  setValue(ids.indexMode, index.mode || "cloud");
  setValue(ids.indexApiKey, "");
  setValue(ids.indexVoiceId, "");
  setValue(ids.indexBaseUrl, index.base_url || "");
  setValue(ids.indexModel, index.model || "IndexTeam/IndexTTS-2");
  setValue(ids.indexApiUrl, index.api_url || "");
  setValue(ids.indexSpeakerAudio, index.speaker_audio_path || "");
  setValue(ids.indexDefaultStyle, index.default_tts_style || "default");
  setValue(ids.indexSegment, index.max_text_tokens_per_segment || 80);
  setValue(ids.indexSentenceGap, index.sentence_interval_ms || 0);
  setChecked(ids.indexSentenceEnabled, index.sentence_split_enabled);
  setValue(ids.indexQuietAlpha, index.quiet_companion_emo_alpha ?? 1.0);
  setSelectOptions(
    ids.asrProvider,
    withCurrentOption(asr.available_providers || ["none"], asr.provider || "none")
  );
  setValue(ids.asrProvider, asr.provider || "none");
  setValue(ids.bilibiliRoomIds, listToText(bilibiliRoomIds));
  setValue(ids.bilibiliSessdata, "");
  setChecked(ids.bilibiliSpeak, true);
  setChecked(ids.bilibiliUseProxy, false);
  setValue(ids.bilibiliProxyUrl, "");
  setText(
    "bilibili-secret-preview",
    bilibili.sessdata_configured
      ? `SESSDATA 已配置: ${bilibili.sessdata_preview || "configured"}`
      : "SESSDATA 未配置；公开房间可留空。"
  );

  const vector = Array.isArray(index.quiet_companion_emo_vec)
    ? index.quiet_companion_emo_vec
    : defaultIndexVector;
  emotionFields.forEach((field, index) => {
    setValue(`index-vec-${field}`, vector[index] ?? 0);
  });
}

export function buildSettingsPatch() {
  return {
    screen_capture_enabled: checked("screen-capture-enabled"),
    keyframe_upload_enabled: checked("keyframe-upload-enabled"),
    debug_media_logging_enabled: checked("debug-media-logging-enabled"),
    multimodal_provider: value("multimodal-provider") || "not_configured",
    capture: {
      enabled: checked("capture-enabled"),
      mode: value("capture-mode") || "whitelist",
      allow_foreground_debug: checked("capture-allow-foreground"),
      attach_to_user_turns: checked("capture-attach-turns"),
      window_title_allowlist: textToList(value("capture-window-list")),
      process_name_allowlist: textToList(value("capture-process-list")),
    },
    proactive: {
      screen_comments_enabled: checked("proactive-screen"),
      idle_speech_enabled: checked("proactive-idle"),
      scheduler_interval_ms: intValue("proactive-interval", 15000),
      min_user_idle_ms: intValue("proactive-idle-ms", 45000),
      screen_comment_cooldown_ms: intValue("proactive-screen-cooldown", 180000),
      idle_speech_cooldown_ms: intValue("proactive-idle-cooldown", 900000),
      screen_change_gate_enabled: checked("proactive-change-gate"),
      screen_change_threshold: numberValue("proactive-change-threshold", 0.12),
      proactive_followup_window_ms: intValue("proactive-followup-window", 18000),
    },
    mood: {
      enabled: checked("mood-enabled"),
      tts_adjustment_enabled: checked("mood-tts-adjust"),
      half_life_minutes: numberValue("mood-half-life", 10),
    },
    inner_life: {
      enabled: checked("inner-life-enabled"),
      rotation_minutes: numberValue("inner-life-rotation", 18),
      activities: textToList(value("inner-life-activities")),
    },
    identity: {
      host_display_name: value("identity-host-name") || "Deliaru",
      audience_display_name: value("identity-audience-name") || "\u5f39\u5e55",
    },
    agent: {
      tools_enabled: checked("agent-tools-enabled"),
      look_at_screen_enabled: checked("agent-look-screen"),
      get_time_enabled: checked("agent-get-time"),
      web_search_enabled: checked("agent-web-search"),
      filler_enabled: checked("agent-filler"),
      result_pre_silence_ms: intValue("agent-pre-silence-ms", 1000),
      max_tool_rounds: intValue("agent-max-rounds", 3),
      web_search_timeout_seconds: intValue("agent-search-timeout", 15),
    },
    memory: {
      summary_per_kind: intValue("memory-summary-per-kind", 5),
      per_kind_cap: intValue("memory-per-kind-cap", 50),
    },
    audio: {
      wake_gate_enabled: checked("wake-gate-enabled"),
      mic_conversation_enabled: checked("mic-conversation-enabled"),
      wake_phrases: textToList(value("wake-phrases")),
      wake_asr_confusions: textToList(value("wake-asr-confusions")),
      wake_active_window_ms: intValue("wake-window-ms", 18000),
    },
    overlay: {
      asr_hud_visible: checked("overlay-asr-hud-visible"),
      dock_layout_mode: state.settings?.overlay?.dock_layout_mode || "corner",
      dock_left_px: state.settings?.overlay?.dock_left_px ?? null,
      dock_top_px: state.settings?.overlay?.dock_top_px ?? null,
      global_pointer_tracking_enabled: checked("overlay-pointer"),
      pointer_tracking_mode: value("overlay-pointer-mode") || "natural_layered",
      pointer_tracking_intensity: numberValue("overlay-pointer-intensity", 1.0),
      pointer_tracking_smoothness: numberValue("overlay-pointer-smoothness", 0.65),
      pointer_tracking_deadzone: numberValue("overlay-pointer-deadzone", 0.05),
      subtitle_visible: checked("overlay-subtitle-visible"),
      subtitle_layout_mode: value("overlay-subtitle-layout") || "anchor",
      subtitle_anchor: value("overlay-subtitle-anchor") || "bottom_left",
      subtitle_width_px: intValue("overlay-subtitle-width", 520),
      subtitle_left_px: intValue("overlay-subtitle-x", 44),
      subtitle_top_px: intValue("overlay-subtitle-y", 520),
    },
    tts_post_processing: {
      enabled: checked("tts-post-enabled"),
      trim_max_ms: intValue("tts-post-trim-max", 200),
      trim_min_tail_ms: intValue("tts-post-trim-min-tail", 80),
      fade_out_ms: intValue("tts-post-fade-out", 15),
      trim_rms_threshold_db: numberValue("tts-post-threshold-db", -40),
    },
  };
}

export function buildDebugConfigPatch() {
  const llmProvider = providerPatchValue(
    value(ids.llmProvider),
    state.config?.llm?.provider,
    state.config?.llm?.available_providers
  );
  const asrProvider = providerPatchValue(
    value(ids.asrProvider),
    state.config?.asr?.provider,
    state.config?.asr?.available_providers
  );
  const patch = {
    llm: {
      api_mode: value(ids.llmApiMode),
      base_url: value(ids.llmBaseUrl),
      model: value(ids.llmModel),
    },
    tts: {
      provider: value(ids.ttsProvider),
      indextts2_tts: buildIndexPatch(),
    },
    prompts: {
      response: { text: rawValue(ids.responsePrompt) },
      persona: { text: rawValue(ids.personaPrompt) },
    },
    live: {
      bilibili_live: buildBilibiliConfigPatch(),
    },
  };
  if (llmProvider) patch.llm.provider = llmProvider;
  if (state.config?.asr && asrProvider) {
    patch.asr = {
      provider: asrProvider,
    };
  }
  if (value(ids.llmApiKey)) patch.llm.api_key = value(ids.llmApiKey);
  if (value(ids.indexApiKey)) patch.tts.indextts2_tts.api_key = value(ids.indexApiKey);
  if (value(ids.indexVoiceId)) patch.tts.indextts2_tts.voice_id = value(ids.indexVoiceId);
  return patch;
}

export function buildRuntimeTtsPatch() {
  return { indextts2_tts: buildIndexPatch() };
}

export function buildBilibiliConnectPayload() {
  const payload = {
    room_ids: textToPositiveIntList(value(ids.bilibiliRoomIds)),
    sessdata: value(ids.bilibiliSessdata),
    speak: checked(ids.bilibiliSpeak),
    use_proxy: checked(ids.bilibiliUseProxy),
    proxy_url: value(ids.bilibiliProxyUrl) || null,
  };
  if (!payload.use_proxy) payload.proxy_url = null;
  return payload;
}

export function buildBilibiliTestEventPayload() {
  return {
    text: value(ids.bilibiliTestText) || "六花，B站测试弹幕来了。",
    user_name: "B站观众",
    user_id: "debug-bilibili",
    room_id: String(textToPositiveIntList(value(ids.bilibiliRoomIds))[0] || "0"),
  };
}

function buildIndexPatch() {
  return {
    mode: value(ids.indexMode),
    base_url: value(ids.indexBaseUrl),
    model: value(ids.indexModel),
    api_url: value(ids.indexApiUrl),
    speaker_audio_path: value(ids.indexSpeakerAudio),
    default_tts_style: value(ids.indexDefaultStyle),
    quiet_companion_emo_alpha: numberValue(ids.indexQuietAlpha, 1.0),
    quiet_companion_emo_vec: emotionFields.map((field) => numberValue(`index-vec-${field}`, 0)),
    sentence_split_enabled: checked(ids.indexSentenceEnabled),
    max_text_tokens_per_segment: intValue(ids.indexSegment, 80),
    sentence_interval_ms: intValue(ids.indexSentenceGap, 0),
  };
}

function buildBilibiliConfigPatch() {
  const patch = {
    room_ids: textToPositiveIntList(value(ids.bilibiliRoomIds)),
  };
  const sessdata = value(ids.bilibiliSessdata);
  if (sessdata) patch.sessdata = sessdata;
  return patch;
}

export function setConfigState(message) {
  text($("config-state"), message);
}

function value(id) {
  return $(id)?.value?.trim() || "";
}

function rawValue(id) {
  return $(id)?.value || "";
}

function intValue(id, fallback) {
  const numeric = Number(value(id));
  return Number.isFinite(numeric) ? Math.round(numeric) : fallback;
}

function numberValue(id, fallback) {
  const numeric = Number(value(id));
  return Number.isFinite(numeric) ? numeric : fallback;
}

function checked(id) {
  return Boolean($(id)?.checked);
}

function setValue(id, newValue) {
  const node = $(id);
  if (node) node.value = newValue == null ? "" : String(newValue);
}

function setChecked(id, newValue) {
  const node = $(id);
  if (node) node.checked = Boolean(newValue);
}

function setText(id, newValue) {
  const node = $(id);
  if (node) node.textContent = newValue == null ? "" : String(newValue);
}

function setSelectOptions(id, options) {
  const node = $(id);
  if (!node || node.tagName !== "SELECT") return;
  const current = node.value;
  node.textContent = "";
  (options || []).forEach((optionValue) => {
    const option = document.createElement("option");
    option.value = optionValue;
    option.textContent = providerLabel(optionValue);
    node.append(option);
  });
  if (current && [...node.options].some((option) => option.value === current)) {
    node.value = current;
  }
}

function withCurrentOption(options, current) {
  const values = [...(options || [])];
  if (current && !values.includes(current)) values.push(current);
  return values;
}

function providerPatchValue(selected, current, availableProviders) {
  if (!selected) return null;
  if (
    selected === current &&
    Array.isArray(availableProviders) &&
    !availableProviders.includes(selected)
  ) {
    return null;
  }
  return selected;
}

function selectValues(id) {
  const node = $(id);
  if (!node || node.tagName !== "SELECT") return [];
  return [...node.options].map((option) => option.value).filter(Boolean);
}

function providerLabel(value) {
  const labels = {
    not_configured: "未配置",
    none: "关闭 ASR",
    openai_compatible_llm: "OpenAI Compatible",
    stateless_llm_with_template: "Stateless Template",
    claude_llm: "Claude",
    llama_cpp_llm: "llama.cpp",
    ollama_llm: "Ollama",
    lmstudio_llm: "LM Studio",
    openai_llm: "OpenAI",
    gemini_llm: "Gemini",
    zhipu_llm: "智谱",
    deepseek_llm: "DeepSeek",
    groq_llm: "Groq",
    mistral_llm: "Mistral",
    faster_whisper: "Faster Whisper",
    whisper_cpp: "Whisper.cpp",
    whisper: "Whisper",
    azure_asr: "Azure ASR",
    fun_asr: "FunASR",
    groq_whisper_asr: "Groq Whisper",
    sherpa_onnx_asr: "Sherpa ONNX",
  };
  return labels[value] || value || "unknown";
}

function textToList(raw) {
  return String(raw || "")
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function textToPositiveIntList(raw) {
  const seen = new Set();
  const values = [];
  textToList(raw).forEach((item) => {
    const numeric = Number.parseInt(item, 10);
    if (!Number.isFinite(numeric) || numeric <= 0 || seen.has(numeric)) return;
    values.push(numeric);
    seen.add(numeric);
  });
  return values;
}

function listToText(list) {
  return Array.isArray(list) ? list.join("\n") : "";
}
