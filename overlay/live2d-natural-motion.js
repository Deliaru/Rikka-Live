const PARAM_ALIASES = {
  ParamAngleX: ["ParamAngleX", "PARAM_ANGLE_X"],
  ParamAngleY: ["ParamAngleY", "PARAM_ANGLE_Y"],
  ParamAngleZ: ["ParamAngleZ", "PARAM_ANGLE_Z"],
  ParamEyeBallX: ["ParamEyeBallX", "PARAM_EYE_BALL_X"],
  ParamEyeBallY: ["ParamEyeBallY", "PARAM_EYE_BALL_Y"],
  ParamEyeLOpen: ["ParamEyeLOpen", "PARAM_EYE_L_OPEN"],
  ParamEyeROpen: ["ParamEyeROpen", "PARAM_EYE_R_OPEN"],
  ParamMouthOpenY: ["ParamMouthOpenY", "PARAM_MOUTH_OPEN_Y"],
  ParamMouthForm: ["ParamMouthForm", "PARAM_MOUTH_FORM"],
  ParamBodyAngleX: ["ParamBodyAngleX", "PARAM_BODY_ANGLE_X"],
};

function lerp(current, target, amount) {
  return current + (target - current) * amount;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

const MOUTH_VOLUME_EXPONENT = 1.08;
const MOUTH_VOLUME_GAIN = 0.7;
const MOUTH_VOLUME_MAX = 0.84;
const POINTER_DRAG_MAX = 0.8;
const SPEAKING_SMILE_DEFAULTS = { gain: 0.02, max: 0.25 };
const IDENTITY_PARAMS_FALLBACK = { Param84: 1.0 };

function clampPointerDrag(value) {
  return clamp(Number(value) || 0, -POINTER_DRAG_MAX, POINTER_DRAG_MAX);
}

function volumeToMouth(volume) {
  const normalized = clamp(Number(volume) || 0, 0, 1);
  return clamp(Math.pow(normalized, MOUTH_VOLUME_EXPONENT) * MOUTH_VOLUME_GAIN, 0, MOUTH_VOLUME_MAX);
}

// Hands/arms/wrists must never be animated (model layer separation constraint).
const FORBIDDEN_ANIMATION_PARAM_PATTERN = /arm|hand|wrist/i;
const FORBIDDEN_ANIMATION_PARAM_IDS = new Set(["Param60", "Param63", "Param68", "Param73"]); // 挥手1-4

function isForbiddenAnimationParam(parameterId) {
  return (
    FORBIDDEN_ANIMATION_PARAM_PATTERN.test(parameterId) ||
    FORBIDDEN_ANIMATION_PARAM_IDS.has(parameterId)
  );
}

function sanitizeParamTargets(params) {
  const targets = {};
  if (!params || typeof params !== "object") return targets;
  for (const [parameterId, raw] of Object.entries(params)) {
    const value = Number(raw);
    if (!Number.isFinite(value)) continue;
    if (isForbiddenAnimationParam(parameterId)) {
      console.warn(`[RikkaNaturalMotion] dropped forbidden animation param "${parameterId}"`);
      continue;
    }
    targets[parameterId] = value;
  }
  return targets;
}

// Parameter layer stack priorities; higher layers win on overlapping params.
// Layers below `preview` are applied before lip-sync/blink, `preview` after.
export const ENVELOPE_LAYERS = {
  microIdle: 10,
  thinking: 20,
  gesture: 30,
  mood_idle_expression: 35,
  expression: 40,
  preview: 90,
};

const ENVELOPE_EASINGS = {
  linear: (t) => clamp(t, 0, 1),
  smoothstep: (t) => {
    const x = clamp(t, 0, 1);
    return x * x * (3 - 2 * x);
  },
};

function resolveEnvelopeEasing(easing) {
  if (typeof easing === "function") return easing;
  return ENVELOPE_EASINGS[easing] || ENVELOPE_EASINGS.smoothstep;
}

function envelopeClock() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

/**
 * Fade-in -> hold -> fade-out parameter envelopes, blended per layer.
 * Shared by micro-idle, thinking pose, gestures, expressions, and panel preview.
 * An envelope spec: { layer, params: {id: target}, fadeInMs, holdMs (omit for
 * open-ended), fadeOutMs, easing ("smoothstep" | "linear" | fn), jitter (0..1) }.
 */
export class EnvelopeEngine {
  constructor() {
    this.envelopes = new Map();
    this.nextId = 1;
  }

  start(spec = {}) {
    const targets = sanitizeParamTargets(spec.params);
    const entries = Object.entries(targets);
    if (entries.length === 0) return 0;
    const layer =
      typeof spec.layer === "string" ? ENVELOPE_LAYERS[spec.layer] : Number(spec.layer);
    const jitter = clamp(Number(spec.jitter) || 0, 0, 1);
    const scale = jitter > 0 ? 1 + (Math.random() * 2 - 1) * jitter : 1;
    const holdMs = Number(spec.holdMs);
    const id = this.nextId;
    this.nextId += 1;
    this.envelopes.set(id, {
      id,
      layer: Number.isFinite(layer) ? layer : ENVELOPE_LAYERS.gesture,
      paramEntries: entries.map(([parameterId, target]) => [parameterId, target * scale]),
      fadeInMs: Math.max(1, Number(spec.fadeInMs) || 240),
      holdMs: Number.isFinite(holdMs) ? Math.max(0, holdMs) : Infinity,
      fadeOutMs: Math.max(0, Number(spec.fadeOutMs) || 320),
      easing: resolveEnvelopeEasing(spec.easing),
      startedAt: envelopeClock(),
      releasedAt: null,
      releaseWeight: 1,
    });
    return id;
  }

  stop(id, { fadeOutMs } = {}) {
    const envelope = this.envelopes.get(id);
    if (!envelope) return false;
    if (Number.isFinite(fadeOutMs)) envelope.fadeOutMs = Math.max(0, fadeOutMs);
    const now = envelopeClock();
    const weight = this.weightAt(envelope, now);
    if (weight === null || envelope.fadeOutMs <= 0) {
      this.envelopes.delete(id);
      return true;
    }
    if (envelope.releasedAt === null) {
      envelope.releasedAt = now;
      envelope.releaseWeight = weight;
    }
    return true;
  }

  stopLayer(layer, options = {}) {
    const target = typeof layer === "string" ? ENVELOPE_LAYERS[layer] : Number(layer);
    let stopped = 0;
    for (const envelope of [...this.envelopes.values()]) {
      if (envelope.layer !== target) continue;
      if (this.stop(envelope.id, options)) stopped += 1;
    }
    return stopped;
  }

  stopAll(options = {}) {
    for (const id of [...this.envelopes.keys()]) this.stop(id, options);
  }

  isActive(id) {
    return this.envelopes.has(id);
  }

  /**
   * Returns ordered writes [{parameterId, target, weight}] for layers within
   * [minLayer, maxLayer], lowest layer first; finished envelopes are pruned.
   */
  evaluate(now, { minLayer = -Infinity, maxLayer = Infinity } = {}) {
    const active = [];
    for (const envelope of this.envelopes.values()) {
      const weight = this.weightAt(envelope, now);
      if (weight === null) {
        this.envelopes.delete(envelope.id);
        continue;
      }
      if (envelope.layer < minLayer || envelope.layer > maxLayer || weight <= 0) continue;
      active.push({ envelope, weight });
    }
    active.sort((a, b) => a.envelope.layer - b.envelope.layer || a.envelope.id - b.envelope.id);
    const writes = [];
    for (const { envelope, weight } of active) {
      for (const [parameterId, target] of envelope.paramEntries) {
        writes.push({ parameterId, target, weight });
      }
    }
    return writes;
  }

  weightAt(envelope, now) {
    if (envelope.releasedAt === null && Number.isFinite(envelope.holdMs)) {
      const releaseAt = envelope.startedAt + envelope.fadeInMs + envelope.holdMs;
      if (now >= releaseAt) {
        envelope.releasedAt = releaseAt;
        envelope.releaseWeight = envelope.easing(
          clamp((releaseAt - envelope.startedAt) / envelope.fadeInMs, 0, 1)
        );
      }
    }
    if (envelope.releasedAt !== null) {
      const fadeOut = Math.max(1, envelope.fadeOutMs);
      const progress = (now - envelope.releasedAt) / fadeOut;
      if (progress >= 1) return null;
      return envelope.releaseWeight * (1 - envelope.easing(clamp(progress, 0, 1)));
    }
    return envelope.easing(clamp((now - envelope.startedAt) / envelope.fadeInMs, 0, 1));
  }
}

export class NaturalLive2DMotion {
  constructor({ subtitle } = {}) {
    this.subtitle = subtitle;
    this.adapter = null;
    this.model = null;
    this.ready = false;
    this.gaze = { x: 0, y: 0 };
    this.targetGaze = { x: 0, y: 0 };
    this.mouth = 0;
    this.targetMouth = 0;
    this.nextBlinkAt = performance.now() + this.randomBlinkDelay();
    this.blinkStartedAt = 0;
    this.blinkPhase = "open";
    this.lastFrame = performance.now();
    this.globalPointerActiveUntil = 0;
    this.frame = null;
    this.lastAppliedAt = 0;
    this.usesModelUpdateHook = false;
    this.usesCoreUpdateHook = false;
    this.parameterCacheModel = null;
    this.parameterIndexCache = new Map();
    this.nativeDrag = null;
    this.audioContext = null;
    this.lipSyncFrame = null;
    this.lipSyncToken = 0;
    this.pointerConfig = {
      mode: "natural_layered",
      intensity: 1,
      smoothness: 0.65,
      deadzone: 0.05,
    };
    this.layeredDrag = { x: 0, y: 0 };
    this.envelopeEngine = new EnvelopeEngine();
    this.identityParamEntries = Object.entries(IDENTITY_PARAMS_FALLBACK);
    this.speakingSmile = { ...SPEAKING_SMILE_DEFAULTS };
    this.idleMicro = { enabled: false, posture_interval_s: [6, 14], ear_interval_s: [9, 22], tail_period_s: 7, amplitude: 1.0 };
    this.nextIdlePostureAt = 0;
    this.nextIdleEarAt = 0;
    this.idleTailPhase = 0;
    this.nativeDragGesture = null;
    this.nextNativeDragGestureId = 1;
    this.configureModel(this.readStoredModelConf());
    this.installPointerTracking();
  }

  attach(adapter) {
    this.adapter = adapter;
    this.model = adapter && typeof adapter.getModel === "function" ? adapter.getModel() : null;
    this.ready = Boolean(this.model);
    this.configureModel(this.readStoredModelConf());
    this.resetParameterCache();
    this.installModelUpdateHook();
    if (!this.frame) this.frame = window.requestAnimationFrame((now) => this.tick(now));
    return this.ready;
  }

  setNativeDrag(nativeDrag) {
    this.nativeDrag = nativeDrag || null;
  }

  configurePointer(config = {}) {
    const mode = config.pointer_tracking_mode || config.mode || "natural_layered";
    this.pointerConfig = {
      mode: ["classic_lapp", "natural_layered", "off"].includes(mode)
        ? mode
        : "natural_layered",
      intensity: clamp(Number(config.pointer_tracking_intensity ?? config.intensity ?? 1), 0, 2),
      smoothness: clamp(Number(config.pointer_tracking_smoothness ?? config.smoothness ?? 0.65), 0, 1),
      deadzone: clamp(Number(config.pointer_tracking_deadzone ?? config.deadzone ?? 0.05), 0, 0.4),
    };
    if (this.pointerConfig.mode === "off") {
      this.targetGaze.x = 0;
      this.targetGaze.y = 0;
      this.layeredDrag.x = 0;
      this.layeredDrag.y = 0;
      if (this.nativeDrag && typeof this.nativeDrag.resetNativeDrag === "function") {
        this.nativeDrag.resetNativeDrag();
      }
    }
  }

  configureModel(modelConf) {
    const conf = modelConf && typeof modelConf === "object" ? modelConf : {};
    const identity =
      conf.identityParams && typeof conf.identityParams === "object"
        ? sanitizeParamTargets(conf.identityParams)
        : { ...IDENTITY_PARAMS_FALLBACK };
    this.identityParamEntries = Object.entries(identity);
    const smile =
      conf.speakingSmile && typeof conf.speakingSmile === "object" ? conf.speakingSmile : {};
    const gain = Number(smile.gain);
    const max = Number(smile.max);
    this.speakingSmile = {
      gain: Number.isFinite(gain) ? gain : SPEAKING_SMILE_DEFAULTS.gain,
      max: Number.isFinite(max) && max >= 0 ? max : SPEAKING_SMILE_DEFAULTS.max,
    };
    const idle = conf.idleMicro && typeof conf.idleMicro === "object" ? conf.idleMicro : {};
    const postureInterval = Array.isArray(idle.posture_interval_s) && idle.posture_interval_s.length >= 2
      ? [Number(idle.posture_interval_s[0]) || 6, Number(idle.posture_interval_s[1]) || 14]
      : [6, 14];
    const earInterval = Array.isArray(idle.ear_interval_s) && idle.ear_interval_s.length >= 2
      ? [Number(idle.ear_interval_s[0]) || 9, Number(idle.ear_interval_s[1]) || 22]
      : [9, 22];
    const tailPeriod = Number(idle.tail_period_s);
    const amplitude = Number(idle.amplitude);
    this.idleMicro = {
      enabled: Boolean(idle.enabled),
      posture_interval_s: postureInterval,
      ear_interval_s: earInterval,
      tail_period_s: Number.isFinite(tailPeriod) && tailPeriod > 0 ? tailPeriod : 7,
      amplitude: Number.isFinite(amplitude) && amplitude > 0 ? amplitude : 1.0,
    };
  }

  readStoredModelConf() {
    // Same storage the runtime fills from "set-model-and-conf" (live2d-runtime.js setModelInfo).
    try {
      const raw = window.localStorage.getItem("modelInfo");
      const parsed = raw ? JSON.parse(raw) : null;
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_error) {
      return null;
    }
  }

  installModelUpdateHook() {
    const model = this.model;
    if (!model) return false;
    this.usesModelUpdateHook = false;
    this.usesCoreUpdateHook = false;
    const hookedCore = this.installCubismUpdateHook();
    if (typeof model.update !== "function") {
      this.usesModelUpdateHook = hookedCore;
      return hookedCore;
    }
    model.__rikkaNaturalMotionController = this;
    if (model.__rikkaNaturalMotionHooked) {
      this.usesModelUpdateHook = true;
      this.usesCoreUpdateHook = hookedCore;
      return true;
    }
    const originalUpdate = model.update.bind(model);
    model.update = (...args) => {
      const result = originalUpdate(...args);
      const controller = model.__rikkaNaturalMotionController;
      if (
        controller &&
        typeof controller.flushFrame === "function"
      ) {
        controller.flushFrame(performance.now());
      }
      return result;
    };
    model.__rikkaNaturalMotionHooked = true;
    this.usesModelUpdateHook = true;
    this.usesCoreUpdateHook = hookedCore;
    return true;
  }

  installCubismUpdateHook() {
    const cubismModel = this.getCubismModel();
    if (!cubismModel || typeof cubismModel.update !== "function") return false;
    cubismModel.__rikkaNaturalMotionController = this;
    if (cubismModel.__rikkaNaturalCoreHooked) {
      this.usesCoreUpdateHook = true;
      return true;
    }
    const originalUpdate = cubismModel.update.bind(cubismModel);
    cubismModel.update = (...args) => {
      const controller = cubismModel.__rikkaNaturalMotionController;
      if (controller && typeof controller.updateMotionFrame === "function") {
        controller.updateMotionFrame(performance.now());
      }
      return originalUpdate(...args);
    };
    cubismModel.__rikkaNaturalCoreHooked = true;
    this.usesCoreUpdateHook = true;
    return true;
  }

  installPointerTracking() {
    window.addEventListener("pointermove", (event) => {
      if (this.pointerConfig.mode === "off") return;
      if (performance.now() < this.globalPointerActiveUntil) return;
      if (
        this.pointerConfig.mode === "classic_lapp" &&
        this.nativeDrag &&
        typeof this.nativeDrag.trackClientPointer === "function" &&
        this.nativeDrag.trackClientPointer(event.clientX, event.clientY)
      ) {
        return;
      }
      if (
        this.pointerConfig.mode === "natural_layered" &&
        this.nativeDrag &&
        typeof this.nativeDrag.relativeClientPointerGaze === "function"
      ) {
        const gaze = this.nativeDrag.relativeClientPointerGaze(
          event.clientX,
          event.clientY
        );
        const relativeX = Number(gaze && gaze.x);
        const relativeY = Number(gaze && gaze.y);
        if (Number.isFinite(relativeX) && Number.isFinite(relativeY)) {
          this.targetGaze.x = clampPointerDrag(relativeX);
          this.targetGaze.y = clampPointerDrag(relativeY);
          return;
        }
      }
      const nx = event.clientX / Math.max(1, window.innerWidth) - 0.5;
      const ny = event.clientY / Math.max(1, window.innerHeight) - 0.5;
      this.targetGaze.x = clampPointerDrag(nx * 2);
      this.targetGaze.y = clampPointerDrag(-ny * 2);
    });
    window.addEventListener("pointerleave", () => {
      if (
        this.pointerConfig.mode === "classic_lapp" &&
        this.nativeDrag &&
        typeof this.nativeDrag.resetNativeDrag === "function" &&
        this.nativeDrag.resetNativeDrag()
      ) {
        return;
      }
      this.targetGaze.x = 0;
      this.targetGaze.y = 0;
    });
  }

  setGlobalPointer(pointer) {
    if (this.pointerConfig.mode === "off") return false;
    if (!pointer) {
      this.globalPointerActiveUntil = 0;
      if (
        this.nativeDrag &&
        typeof this.nativeDrag.resetNativeDrag === "function" &&
        this.nativeDrag.resetNativeDrag()
      ) {
        return false;
      }
      this.targetGaze.x = 0;
      this.targetGaze.y = 0;
      return false;
    }
    if (pointer.status !== "tracked") {
      this.globalPointerActiveUntil = 0;
      if (
        this.nativeDrag &&
        typeof this.nativeDrag.resetNativeDrag === "function"
      ) {
        this.nativeDrag.resetNativeDrag();
      }
      return false;
    }
    if (
      this.pointerConfig.mode === "classic_lapp" &&
      this.nativeDrag &&
      typeof this.nativeDrag.trackGlobalPointer === "function" &&
      this.nativeDrag.trackGlobalPointer(pointer)
    ) {
      this.globalPointerActiveUntil = performance.now() + 520;
      return true;
    }
    const relativeX = Number(pointer.relative_x);
    const relativeY = Number(pointer.relative_y);
    if (
      this.pointerConfig.mode === "natural_layered" &&
      Number.isFinite(relativeX) &&
      Number.isFinite(relativeY)
    ) {
      this.targetGaze.x = clampPointerDrag(relativeX);
      this.targetGaze.y = clampPointerDrag(relativeY);
      this.globalPointerActiveUntil = performance.now() + 520;
      return true;
    }
    const x = Number(pointer.normalized_x);
    const y = Number(pointer.normalized_y);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return false;
    this.targetGaze.x = clampPointerDrag(x);
    this.targetGaze.y = clampPointerDrag(y);
    this.globalPointerActiveUntil = performance.now() + 520;
    return true;
  }

  applyActionGaze(gaze) {
    if (!gaze || !gaze.parameters) return;
    const x = Number(gaze.parameters.ParamEyeBallX || 0);
    const y = Number(gaze.parameters.ParamEyeBallY || 0);
    if (
      this.nativeDrag &&
      typeof this.nativeDrag.applyNativeDrag === "function" &&
      this.nativeDrag.applyNativeDrag(
        clampPointerDrag(x * 2),
        clampPointerDrag(y * 2),
        { max: POINTER_DRAG_MAX }
      )
    ) {
      window.setTimeout(() => {
        if (
          this.nativeDrag &&
          typeof this.nativeDrag.resetNativeDrag === "function"
        ) {
          this.nativeDrag.resetNativeDrag();
        }
      }, Number(gaze.hold_ms || 1100) + Number(gaze.restore_ms || 500));
      return;
    }
    this.targetGaze.x = Math.max(-1, Math.min(1, x * 2));
    this.targetGaze.y = Math.max(-1, Math.min(1, y * 2));
    window.setTimeout(() => {
      this.targetGaze.x = 0;
      this.targetGaze.y = 0;
    }, Number(gaze.hold_ms || 1100) + Number(gaze.restore_ms || 500));
  }

  playVolumes(volumes, sliceLength = 20) {
    this.stopLipSync();
    if (!Array.isArray(volumes) || volumes.length === 0) {
      this.targetMouth = 0;
      return;
    }
    let index = 0;
    window.clearInterval(this.volumeTimer);
    this.volumeTimer = window.setInterval(() => {
      const volume = Number(volumes[index] || 0);
      this.targetMouth = volumeToMouth(volume);
      if (this.subtitle) this.subtitle.setVolume(this.targetMouth);
      index += 1;
      if (index >= volumes.length) {
        window.clearInterval(this.volumeTimer);
        this.targetMouth = 0;
        if (this.subtitle) this.subtitle.setVolume(0);
      }
    }, Math.max(16, Number(sliceLength || 20)));
  }

  async playAudioLipSync(audio, { audioBase64, fallbackVolumes, sliceLength = 20, onSource } = {}) {
    this.stopLipSync();
    const token = ++this.lipSyncToken;
    let source = "unavailable";
    let volumes = [];
    try {
      volumes = await this.decodeVolumesFromBase64(audioBase64, sliceLength);
      source = "browser_audio_rms";
    } catch (_error) {
      volumes = Array.isArray(fallbackVolumes) ? fallbackVolumes : [];
      source = volumes.length ? "payload_volumes_fallback" : "unavailable";
    }
    if (token !== this.lipSyncToken) return source;
    if (typeof onSource === "function") onSource(source);
    if (!volumes.length || !audio) {
      this.targetMouth = 0;
      if (this.subtitle) this.subtitle.setVolume(0);
      return source;
    }
    const frameMs = Math.max(16, Number(sliceLength || 20));
    const update = () => {
      if (token !== this.lipSyncToken) return;
      if (audio.ended || audio.paused) {
        this.targetMouth = 0;
        if (this.subtitle) this.subtitle.setVolume(0);
        return;
      }
      const index = Math.min(
        volumes.length - 1,
        Math.max(0, Math.floor((audio.currentTime * 1000) / frameMs))
      );
      const volume = Number(volumes[index] || 0);
      this.targetMouth = volumeToMouth(volume);
      if (this.subtitle) this.subtitle.setVolume(this.targetMouth);
      this.lipSyncFrame = window.requestAnimationFrame(update);
    };
    update();
    return source;
  }

  stopLipSync() {
    window.clearInterval(this.volumeTimer);
    this.volumeTimer = null;
    if (this.lipSyncFrame) {
      window.cancelAnimationFrame(this.lipSyncFrame);
      this.lipSyncFrame = null;
    }
    this.lipSyncToken += 1;
    this.targetMouth = 0;
    this.applyNativeLipSync(0);
    if (this.subtitle) this.subtitle.setVolume(0);
  }

  async decodeVolumesFromBase64(audioBase64, sliceLength = 20) {
    if (!audioBase64) return [];
    const bytes = this.base64ToBytes(audioBase64);
    const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    const audioBuffer = await this.getAudioContext().decodeAudioData(buffer);
    return this.computeRmsVolumes(audioBuffer, sliceLength);
  }

  getAudioContext() {
    if (!this.audioContext) {
      const Context = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new Context();
    }
    return this.audioContext;
  }

  base64ToBytes(audioBase64) {
    const clean = String(audioBase64 || "").includes(",")
      ? String(audioBase64).split(",", 2)[1]
      : String(audioBase64 || "");
    const binary = window.atob(clean);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }

  computeRmsVolumes(audioBuffer, sliceLength = 20) {
    const sampleRate = audioBuffer.sampleRate || 44100;
    const frameSize = Math.max(1, Math.round(sampleRate * (Math.max(16, Number(sliceLength || 20)) / 1000)));
    const frameCount = Math.max(1, Math.ceil(audioBuffer.length / frameSize));
    const volumes = [];
    let maxRms = 0;
    for (let frame = 0; frame < frameCount; frame += 1) {
      const start = frame * frameSize;
      const end = Math.min(audioBuffer.length, start + frameSize);
      let sum = 0;
      let count = 0;
      for (let channel = 0; channel < audioBuffer.numberOfChannels; channel += 1) {
        const samples = audioBuffer.getChannelData(channel);
        for (let index = start; index < end; index += 1) {
          const value = samples[index] || 0;
          sum += value * value;
          count += 1;
        }
      }
      const rms = count ? Math.sqrt(sum / count) : 0;
      volumes.push(rms);
      if (rms > maxRms) maxRms = rms;
    }
    if (maxRms <= 0) return volumes.map(() => 0);
    return volumes.map((volume) => volume / maxRms);
  }

  tick(now) {
    this.frame = window.requestAnimationFrame((next) => this.tick(next));
    if (!this.adapter && typeof window.getLAppAdapter === "function") {
      this.attach(window.getLAppAdapter());
    }
    const nextModel =
      this.adapter && typeof this.adapter.getModel === "function" ? this.adapter.getModel() : null;
    if (nextModel && nextModel !== this.model) {
      this.model = nextModel;
      this.ready = Boolean(this.model);
      this.configureModel(this.readStoredModelConf());
      this.resetParameterCache();
      this.installModelUpdateHook();
    }
    if (!this.model) return;
    if (this.usesModelUpdateHook && now - this.lastAppliedAt < 32) return;
    this.updateMotionFrame(now);
  }

  updateMotionFrame(now) {
    const delta = Math.min(48, now - this.lastFrame);
    this.lastFrame = now;
    const ease = Math.min(1, delta / 120);
    this.gaze.x = lerp(this.gaze.x, this.targetGaze.x, ease);
    this.gaze.y = lerp(this.gaze.y, this.targetGaze.y, ease);
    const gestureDrag = this.evaluateNativeDragGesture(now);
    const usingLayeredNativeDrag = this.applyLayeredNativeDrag(
      this.targetGaze.x,
      this.targetGaze.y,
      delta,
      gestureDrag
    );
    this.mouth = lerp(this.mouth, this.targetMouth, Math.min(1, delta / 80));
    const nativeLipSyncApplied = this.applyNativeLipSync(this.mouth);

    const breath = Math.sin(now / 950) * 0.5;
    const blink = this.blinkValue(now);
    const nativeBlinkApplied = this.applyNativeBlink(blink);

    this.scheduleIdleMicro(now);

    if (!this.hasNativeDrag() && !usingLayeredNativeDrag) {
      this.setParameter("ParamAngleX", this.gaze.x * 10);
      this.setParameter("ParamAngleY", this.gaze.y * 7);
      this.setParameter("ParamAngleZ", this.gaze.x * -2.5);
      this.setParameter("ParamEyeBallX", this.gaze.x * 0.42);
      this.setParameter("ParamEyeBallY", this.gaze.y * 0.32);
      this.setParameter("ParamBodyAngleX", this.gaze.x * 3 + breath * 0.35);
    }
    this.applyIdentityParams();
    this.applyEnvelopes(now, {
      maxLayer: ENVELOPE_LAYERS.preview - 1,
      excludeParameters: ["ParamMouthForm"],
    });
    if (!nativeLipSyncApplied) this.setParameter("ParamMouthOpenY", this.mouth);
    this.setParameter(
      "ParamMouthForm",
      clamp(this.mouth * this.speakingSmile.gain, -this.speakingSmile.max, this.speakingSmile.max)
    );
    this.applyEnvelopes(now, {
      maxLayer: ENVELOPE_LAYERS.preview - 1,
      includeParameters: ["ParamMouthForm"],
    });
    if (!nativeBlinkApplied) {
      this.setParameter("ParamEyeLOpen", blink);
      this.setParameter("ParamEyeROpen", blink);
    }
    this.applyEnvelopes(now, { minLayer: ENVELOPE_LAYERS.preview });
    this.lastAppliedAt = now;
  }

  startEnvelope(spec) {
    return this.envelopeEngine.start(spec);
  }

  probeParameters(parameterIds = []) {
    const cubismModel = this.getCubismModel();
    const result = {};
    for (const parameterId of parameterIds) {
      const parameter = cubismModel ? this.resolveParameter(cubismModel, parameterId) : null;
      result[parameterId] = {
        exists: Boolean(parameter),
        value: this.getParameterValue(parameterId),
      };
    }
    return result;
  }

  stopEnvelope(envelopeId, options) {
    return this.envelopeEngine.stop(envelopeId, options);
  }

  stopEnvelopeLayer(layer, options) {
    return this.envelopeEngine.stopLayer(layer, options);
  }

  startParameterLayer(
    layer,
    { params = {}, fadeInMs = 240, holdMs = undefined, fadeOutMs = 320, jitter = 0, easing = "smoothstep" } = {}
  ) {
    const envelopeId = this.startEnvelope({
      layer,
      params,
      fadeInMs,
      holdMs,
      fadeOutMs,
      jitter,
      easing,
    });
    return envelopeId ? { layer, envelopeId, primaryId: envelopeId } : null;
  }

  stopParameterLayer(handle, { fadeOutMs } = {}) {
    if (!handle || typeof handle !== "object" || !handle.envelopeId) return false;
    return this.stopEnvelope(handle.envelopeId, { fadeOutMs });
  }

  flushFrame(now = performance.now()) {
    this.updateMotionFrame(now);
    const cubismModel = this.getCubismModel();
    if (cubismModel && typeof cubismModel.update === "function") {
      try {
        cubismModel.update();
      } catch (_error) {
        // Best-effort preview flush; the normal runtime frame loop remains active.
      }
    }
  }

  playGesture(kind, { amplitude = 1.0, duration_ms = 1000, jitter = 0.15 } = {}) {
    const handle = this.startGesturePose(kind, { amplitude, duration_ms, jitter });
    return handle ? handle.primaryId : 0;
  }

  startGesturePose(
    kind,
    {
      amplitude = 1.0,
      duration_ms = 1000,
      jitter = 0.15,
      layer = "gesture",
      openEnded = false,
      fadeInMs = null,
      holdMs = null,
      fadeOutMs = null,
    } = {}
  ) {
    const choreography = this.getGestureChoreography(kind);
    if (!choreography) return null;
    const fadeIn = Number.isFinite(fadeInMs) ? fadeInMs : choreography.fadeInMs(duration_ms);
    const hold = openEnded
      ? Infinity
      : Number.isFinite(holdMs)
        ? holdMs
        : choreography.holdMs(duration_ms);
    const fadeOut = Number.isFinite(fadeOutMs) ? fadeOutMs : choreography.fadeOutMs(duration_ms);
    const easing = choreography.easing || "smoothstep";
    const envelopeId = this.startEnvelope({
      layer,
      params: choreography.params(amplitude),
      fadeInMs: fadeIn,
      holdMs: hold,
      fadeOutMs: fadeOut,
      easing,
      jitter,
    });
    const drag = typeof choreography.drag === "function" ? choreography.drag(amplitude) : null;
    const dragId = drag
      ? this.startNativeDragGesture({
          ...drag,
          fadeInMs: fadeIn,
          holdMs: hold,
          fadeOutMs: fadeOut,
          easing,
        })
      : 0;
    const primaryId = envelopeId || dragId;
    if (!primaryId) return null;
    return { kind, envelopeId, dragId, primaryId };
  }

  stopGesturePose(handle, { fadeOutMs } = {}) {
    if (!handle || typeof handle !== "object") return false;
    let stopped = false;
    if (handle.envelopeId) {
      stopped = this.stopEnvelope(handle.envelopeId, { fadeOutMs }) || stopped;
    }
    if (handle.dragId) {
      stopped = this.stopNativeDragGesture(handle.dragId, { fadeOutMs }) || stopped;
    }
    return stopped;
  }

  getGestureChoreography(kind) {
    const shapes = {
      nod: {
        drag: (amp) => ({ x: 0, y: -0.55 * amp }),
        params: (amp) => ({
          ParamEyeBallY: -0.55 * amp,
          ParamEyeLOpen: 0.58,
          ParamEyeROpen: 0.58,
          ParamearLe: 7 * amp,
          ParamearRe: 7 * amp,
        }),
        fadeInMs: (d) => d * 0.35,
        holdMs: (d) => d * 0.08,
        fadeOutMs: (d) => d * 0.65,
        easing: "smoothstep",
      },
      tilt: {
        drag: (amp) => ({ x: 0.4 * amp, y: 0 }),
        params: (amp) => ({
          ParamEyeBallX: 0.65 * amp,
          ParamearLe: -9 * amp,
          ParamearRe: 9 * amp,
          ParamMouthForm: 0.12 * amp,
        }),
        fadeInMs: (d) => d * 0.25,
        holdMs: (d) => d * 0.4,
        fadeOutMs: (d) => d * 0.35,
        easing: "smoothstep",
      },
      lean_in: {
        drag: (amp) => ({ x: 0, y: 0.35 * amp }),
        params: (amp) => ({
          ParamEyeLOpen: 1.22,
          ParamEyeROpen: 1.22,
          ParamEyeBallY: 0.28 * amp,
          dengyan: 0.35 * amp,
        }),
        fadeInMs: (d) => d * 0.4,
        holdMs: (d) => d * 0.2,
        fadeOutMs: (d) => d * 0.4,
        easing: "smoothstep",
      },
      look_away: {
        drag: (amp) => ({ x: 0.65 * amp, y: -0.08 * amp }),
        params: (amp) => ({
          ParamEyeBallX: 0.9 * amp,
          ParamEyeBallY: -0.16 * amp,
          ParamEyeLOpen: 0.78,
          ParamEyeROpen: 0.78,
        }),
        fadeInMs: (d) => d * 0.3,
        holdMs: (d) => d * 0.35,
        fadeOutMs: (d) => d * 0.35,
        easing: "smoothstep",
      },
      greeting_bob: {
        drag: (amp) => ({ x: -0.25 * amp, y: -0.35 * amp }),
        params: (amp) => ({
          ParamearLe: 14 * amp,
          ParamearRe: 14 * amp,
          Param97: 12 * amp,
          ParamEyeBallY: -0.25 * amp,
        }),
        fadeInMs: (d) => d * 0.35,
        holdMs: (d) => d * 0.1,
        fadeOutMs: (d) => d * 0.55,
        easing: "smoothstep",
      },
      think_pose: {
        drag: (amp) => ({ x: -0.48 * amp, y: -0.12 * amp }),
        params: (amp) => ({
          ParamEyeBallX: -0.52 * amp,
          ParamEyeBallY: -0.14 * amp,
          ParamEyeLOpen: 0.42,
          ParamEyeROpen: 0.42,
          ParamAngleZ: 4.8 * amp,
          ParamearLe: -7 * amp,
          ParamearRe: 7 * amp,
        }),
        fadeInMs: (d) => d * 0.32,
        holdMs: (d) => d * 0.36,
        fadeOutMs: (d) => d * 0.32,
        easing: "smoothstep",
      },
    };
    return shapes[kind] || null;
  }

  startNativeDragGesture({ x = 0, y = 0, fadeInMs = 240, holdMs = 0, fadeOutMs = 320, easing = "smoothstep" } = {}) {
    const id = this.nextNativeDragGestureId;
    this.nextNativeDragGestureId += 1;
    this.nativeDragGesture = {
      id,
      x: clamp(Number(x) || 0, -0.9, 0.9),
      y: clamp(Number(y) || 0, -0.9, 0.9),
      fadeInMs: Math.max(1, Number(fadeInMs) || 240),
      holdMs: Math.max(0, Number(holdMs) || 0),
      fadeOutMs: Math.max(1, Number(fadeOutMs) || 320),
      easing: resolveEnvelopeEasing(easing),
      startedAt: performance.now(),
      releasedAt: null,
      releaseWeight: 1,
    };
    return id;
  }

  stopNativeDragGesture(id = null, { fadeOutMs } = {}) {
    const gesture = this.nativeDragGesture;
    if (!gesture) return false;
    if (id !== null && gesture.id !== id) return false;
    if (Number.isFinite(fadeOutMs)) gesture.fadeOutMs = Math.max(1, fadeOutMs);
    const now = performance.now();
    const weight = this.nativeDragGestureWeightAt(gesture, now);
    if (weight === null) {
      this.nativeDragGesture = null;
      return true;
    }
    gesture.releaseWeight = weight;
    gesture.releasedAt = now;
    return true;
  }

  evaluateNativeDragGesture(now) {
    const gesture = this.nativeDragGesture;
    if (!gesture) return null;
    const weight = this.nativeDragGestureWeightAt(gesture, now);
    if (weight === null) {
      this.nativeDragGesture = null;
      return null;
    }
    return { x: gesture.x * weight, y: gesture.y * weight };
  }

  nativeDragGestureWeightAt(gesture, now) {
    const elapsed = now - gesture.startedAt;
    if (gesture.releasedAt !== null) {
      const progress = (now - gesture.releasedAt) / gesture.fadeOutMs;
      if (progress >= 1) return null;
      return gesture.releaseWeight * (1 - gesture.easing(clamp(progress, 0, 1)));
    }
    const releaseAt = gesture.fadeInMs + gesture.holdMs;
    const endAt = releaseAt + gesture.fadeOutMs;
    if (elapsed >= endAt) return null;
    if (elapsed < gesture.fadeInMs) return gesture.easing(clamp(elapsed / gesture.fadeInMs, 0, 1));
    if (elapsed > releaseAt) {
      return 1 - gesture.easing(clamp((elapsed - releaseAt) / gesture.fadeOutMs, 0, 1));
    }
    return 1;
  }

  applyIdentityParams() {
    for (const [parameterId, value] of this.identityParamEntries) {
      this.setParameter(parameterId, value);
    }
  }

  applyEnvelopes(now, range = {}) {
    const include = Array.isArray(range.includeParameters)
      ? new Set(range.includeParameters)
      : null;
    const exclude = Array.isArray(range.excludeParameters)
      ? new Set(range.excludeParameters)
      : null;
    const writes = this.envelopeEngine.evaluate(now, range);
    for (const write of writes) {
      if (include && !include.has(write.parameterId)) continue;
      if (exclude && exclude.has(write.parameterId)) continue;
      if (write.weight >= 1) {
        this.setParameter(write.parameterId, write.target);
        continue;
      }
      const current = this.getParameterValue(write.parameterId);
      const base = current === null ? 0 : current;
      const blended = lerp(base, write.target, write.weight);
      this.setParameter(write.parameterId, blended);
    }
  }

  applyNativeLipSync(value) {
    if (this.adapter && typeof this.adapter.setLipSyncValue === "function") {
      return this.adapter.setLipSyncValue(value);
    }
    const model = this.model;
    if (model && typeof model.setExternalLipSyncValue === "function") {
      model.setExternalLipSyncValue(value);
      return true;
    }
    return false;
  }

  applyNativeBlink(value) {
    if (this.adapter && typeof this.adapter.setEyeBlinkValue === "function") {
      return this.adapter.setEyeBlinkValue(value);
    }
    const model = this.model;
    if (model && typeof model.setExternalEyeBlinkValue === "function") {
      model.setExternalEyeBlinkValue(value);
      return true;
    }
    return false;
  }

  hasNativeDrag() {
    return Boolean(
      this.nativeDrag &&
        typeof this.nativeDrag.hasNativeDrag === "function" &&
        this.nativeDrag.hasNativeDrag()
    );
  }

  applyLayeredNativeDrag(targetX, targetY, delta, gestureDrag = null) {
    if (this.pointerConfig.mode !== "natural_layered" && !gestureDrag) return false;
    if (!this.nativeDrag || typeof this.nativeDrag.applyNativeDrag !== "function") return false;
    const intensity = this.pointerConfig.intensity;
    const deadzone = this.pointerConfig.deadzone;
    const magnitude = Math.hypot(targetX, targetY);
    let nextX = 0;
    let nextY = 0;
    if (magnitude > deadzone) {
      const scaled = Math.max(0, (magnitude - deadzone) / Math.max(0.001, 1 - deadzone));
      nextX = (targetX / magnitude) * scaled * intensity;
      nextY = (targetY / magnitude) * scaled * intensity;
    }
    const ease = Math.min(1, delta / (70 + this.pointerConfig.smoothness * 260));
    this.layeredDrag.x = lerp(this.layeredDrag.x, nextX, ease);
    this.layeredDrag.y = lerp(this.layeredDrag.y, nextY, ease);
    const dragX = this.layeredDrag.x + (gestureDrag ? gestureDrag.x : 0);
    const dragY = this.layeredDrag.y + (gestureDrag ? gestureDrag.y : 0);
    return this.nativeDrag.applyNativeDrag(dragX, dragY, {
      max: POINTER_DRAG_MAX,
    });
  }

  blinkValue(now) {
    if (this.blinkPhase === "open" && now >= this.nextBlinkAt) {
      this.blinkPhase = "closing";
      this.blinkStartedAt = now;
    }
    const elapsed = now - this.blinkStartedAt;
    if (this.blinkPhase === "closing") {
      if (elapsed >= 92) {
        this.blinkPhase = "hold";
        this.blinkStartedAt = now;
        return 0;
      }
      return 1 - elapsed / 92;
    }
    if (this.blinkPhase === "hold") {
      if (elapsed >= 54) {
        this.blinkPhase = "opening";
        this.blinkStartedAt = now;
      }
      return 0;
    }
    if (this.blinkPhase === "opening") {
      if (elapsed >= 138) {
        this.blinkPhase = "open";
        this.nextBlinkAt = now + this.randomBlinkDelay();
        return 1;
      }
      return elapsed / 138;
    }
    return 1;
  }

  randomBlinkDelay() {
    return 2500 + Math.random() * 3500;
  }

  scheduleIdleMicro(now) {
    if (!this.idleMicro.enabled) return;
    if (this.isIdleSuspended()) return;
    if (now >= this.nextIdlePostureAt) {
      this.triggerIdlePosture();
      const [min, max] = this.idleMicro.posture_interval_s;
      this.nextIdlePostureAt = now + (min + Math.random() * (max - min)) * 1000;
    }
    if (now >= this.nextIdleEarAt) {
      this.triggerIdleEar();
      const [min, max] = this.idleMicro.ear_interval_s;
      this.nextIdleEarAt = now + (min + Math.random() * (max - min)) * 1000;
    }
    this.updateIdleTail(now);
  }

  isIdleSuspended() {
    if (this.targetMouth > 0.01) return true;
    for (const envelope of this.envelopeEngine.envelopes.values()) {
      if (envelope.layer === ENVELOPE_LAYERS.gesture || envelope.layer === ENVELOPE_LAYERS.thinking || envelope.layer === ENVELOPE_LAYERS.expression) {
        return true;
      }
    }
    return false;
  }

  triggerIdlePosture() {
    const amp = this.idleMicro.amplitude;
    const angleX = (Math.random() * 2 - 1) * 2 * amp;
    const angleZ = (Math.random() * 2 - 1) * 1.5 * amp;
    this.startEnvelope({
      layer: "microIdle",
      params: { ParamBodyAngleX: angleX, ParamBodyAngleZ: angleZ },
      fadeInMs: 1200,
      holdMs: 800,
      fadeOutMs: 1400,
      easing: "smoothstep",
    });
  }

  triggerIdleEar() {
    const amp = this.idleMicro.amplitude;
    const side = Math.random() < 0.5 ? "earL_button" : "earR_button";
    this.startEnvelope({
      layer: "microIdle",
      params: { [side]: 1.0 * amp },
      fadeInMs: 80,
      holdMs: 60,
      fadeOutMs: 180,
      easing: "smoothstep",
    });
  }

  updateIdleTail(now) {
    const visible = this.getParameterValue("Param94");
    if (visible === null || visible < 0.5) return;
    const period = this.idleMicro.tail_period_s * 1000;
    this.idleTailPhase = (now % period) / period;
    const swing = Math.sin(this.idleTailPhase * Math.PI * 2) * 8 * this.idleMicro.amplitude;
    this.setParameter("Param97", swing);
  }

  setParameter(parameterId, value) {
    const cubismModel = this.getCubismModel();
    if (!cubismModel) return false;
    const parameter = this.resolveParameter(cubismModel, parameterId);
    if (!parameter) return false;
    try {
      if (
        Number.isInteger(parameter.index) &&
        typeof cubismModel.setParameterValueByIndex === "function"
      ) {
        cubismModel.setParameterValueByIndex(parameter.index, value);
        return true;
      }
      if (parameter.id && typeof cubismModel.setParameterValueById === "function") {
        cubismModel.setParameterValueById(parameter.id, value);
        return true;
      }
    } catch (_error) {
      return false;
    }
    return false;
  }

  getParameterValue(parameterId) {
    const cubismModel = this.getCubismModel();
    if (!cubismModel) return null;
    const parameter = this.resolveParameter(cubismModel, parameterId);
    if (!parameter) return null;
    try {
      if (
        Number.isInteger(parameter.index) &&
        typeof cubismModel.getParameterValueByIndex === "function"
      ) {
        const value = Number(cubismModel.getParameterValueByIndex(parameter.index));
        return Number.isFinite(value) ? value : null;
      }
      if (parameter.id && typeof cubismModel.getParameterValueById === "function") {
        const value = Number(cubismModel.getParameterValueById(parameter.id));
        return Number.isFinite(value) ? value : null;
      }
    } catch (_error) {
      return null;
    }
    return null;
  }

  getCubismModel() {
    return this.model && this.model._model ? this.model._model : null;
  }

  resetParameterCache() {
    const cubismModel = this.getCubismModel();
    if (this.parameterCacheModel !== cubismModel) {
      this.parameterCacheModel = cubismModel;
      this.parameterIndexCache = new Map();
    }
  }

  resolveParameter(cubismModel, parameterId) {
    if (this.parameterCacheModel !== cubismModel) {
      this.parameterCacheModel = cubismModel;
      this.parameterIndexCache = new Map();
    }
    if (this.parameterIndexCache.has(parameterId)) {
      return this.parameterIndexCache.get(parameterId);
    }

    const idManager =
      this.adapter && typeof this.adapter.getIdManager === "function"
        ? this.adapter.getIdManager()
        : null;
    const aliases = PARAM_ALIASES[parameterId] || [parameterId];
    for (const alias of aliases) {
      const id = idManager && typeof idManager.getId === "function" ? idManager.getId(alias) : alias;
      const index = this.findParameterIndex(cubismModel, id, alias);
      if (Number.isInteger(index) && index >= 0) {
        const parameter = { id, index };
        this.parameterIndexCache.set(parameterId, parameter);
        return parameter;
      }
    }
    this.parameterIndexCache.set(parameterId, null);
    return null;
  }

  findParameterIndex(cubismModel, id, alias) {
    const count =
      typeof cubismModel.getParameterCount === "function"
        ? Number(cubismModel.getParameterCount())
        : NaN;
    if (Number.isFinite(count) && count > 0 && typeof cubismModel.getParameterId === "function") {
      const target = this.normalizeCubismId(id) || String(alias);
      for (let index = 0; index < count; index += 1) {
        const existingId = cubismModel.getParameterId(index);
        if (existingId === id || this.normalizeCubismId(existingId) === target) return index;
      }
      return -1;
    }

    const ids = cubismModel && cubismModel._model && cubismModel._model.parameters
      ? cubismModel._model.parameters.ids
      : null;
    if (ids && typeof ids.length === "number") {
      const target = this.normalizeCubismId(id) || String(alias);
      for (let index = 0; index < ids.length; index += 1) {
        if (this.normalizeCubismId(ids[index]) === target) return index;
      }
    }
    return -1;
  }

  normalizeCubismId(value, depth = 0) {
    if (value === null || value === undefined || depth > 4) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number") return String(value);
    if (typeof value.getString === "function") {
      const normalized = this.normalizeCubismId(value.getString(), depth + 1);
      if (normalized) return normalized;
    }
    if (typeof value === "object") {
      for (const key of ["_id", "id", "s", "str", "value"]) {
        if (value[key] === undefined) continue;
        const normalized = this.normalizeCubismId(value[key], depth + 1);
        if (normalized) return normalized;
      }
    }
    return "";
  }
}

window.RikkaNaturalLive2DMotion = NaturalLive2DMotion;
