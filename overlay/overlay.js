import { Live2DRuntime } from "/overlay/live2d-runtime.js";
import { NaturalLive2DMotion } from "/overlay/live2d-natural-motion.js";
import { SubtitleBubble } from "/overlay/subtitle-bubble.js";

const els = {
  dock: document.querySelector(".overlay-dock"),
  dockToggle: document.getElementById("dock-toggle"),
  dockDragHandle: document.getElementById("dock-drag-handle"),
  hudToggle: document.getElementById("hud-toggle"),
  resetDockPosition: document.getElementById("reset-dock-position"),
  wsState: document.getElementById("ws-state"),
  wsUrl: document.getElementById("ws-url"),
  connect: document.getElementById("connect-ws"),
  mic: document.getElementById("mic-toggle"),
  configSelect: document.getElementById("config-select"),
  switchConfig: document.getElementById("switch-config"),
  modelScale: document.getElementById("model-scale"),
  modelScaleValue: document.getElementById("model-scale-value"),
  modelX: document.getElementById("model-x"),
  modelXValue: document.getElementById("model-x-value"),
  modelY: document.getElementById("model-y"),
  modelYValue: document.getElementById("model-y-value"),
  resetModelLayout: document.getElementById("reset-model-layout"),
  subtitleStage: document.getElementById("subtitle-stage"),
  subtitleResizeHandle: document.getElementById("subtitle-resize-handle"),
  modelState: document.getElementById("model-state"),
  captureState: document.getElementById("capture-state"),
  wakeState: document.getElementById("wake-state"),
  asrState: document.getElementById("asr-state"),
  asrTranscript: document.getElementById("asr-transcript"),
  asrDetail: document.getElementById("asr-detail"),
  asrHud: document.getElementById("asr-hud"),
  asrHudState: document.getElementById("asr-hud-state"),
  asrHudText: document.getElementById("asr-hud-text"),
  asrHudDetail: document.getElementById("asr-hud-detail"),
  motionState: document.getElementById("motion-state"),
};

const subtitle = new SubtitleBubble(document.getElementById("subtitle-bubble"));
const naturalMotion = new NaturalLive2DMotion({ subtitle });
const runtime = new Live2DRuntime({
  onStatus(status) {
    els.motionState.textContent = status;
  },
});

const MODEL_LAYOUT_STORAGE_KEY = "rikkaOverlayModelMatrixLayout";
const MODEL_LAYOUT_DEFAULT = {
  scale: 520,
  x: 0,
  y: 0,
};
const MODEL_LAYOUT_LIMITS = {
  scale: { min: 20, max: 2600 },
  x: { min: -160, max: 160 },
  y: { min: -120, max: 120 },
};
const NATIVE_DRAG_LIMITS = {
  x: { min: -3, max: 3 },
  y: { min: -2.5, max: 2.5 },
};
const MODEL_DRAG_THRESHOLD_PX = 3;
const MODEL_LAYOUT_POSITION_PRECISION = 4;
const MODEL_LAYOUT_SCALE_PRECISION = 1;
const MODEL_WHEEL_SAVE_DELAY_MS = 260;
const MODEL_WHEEL_SCALE_STEP = 3;
const MODEL_POINTER_GAZE_GAIN = 1.15;
const MODEL_POINTER_GAZE_MAX = 0.8;
const GLOBAL_POINTER_POLL_INTERVAL_MS = 160;
const SUBTITLE_LAYOUT_DEFAULT = {
  mode: "anchor",
  left: 44,
  top: 520,
  width: 520,
};
const SUBTITLE_LAYOUT_LIMITS = {
  left: { min: 0, max: 3840 },
  top: { min: 0, max: 2160 },
  width: { min: 240, max: 1400 },
};
const SUBTITLE_LAYOUT_SAVE_DELAY_MS = 280;
const DOCK_LAYOUT_DEFAULT = {
  mode: "corner",
  left: null,
  top: null,
};
const DOCK_LAYOUT_SAVE_DELAY_MS = 180;
const DOCK_REACHABLE_MARGIN_PX = 8;
const MOTION_PRIORITY = {
  idle: 1,
  normal: 2,
  force: 3,
};
const EYE_DRAWABLE_EXCLUDE_PATTERN =
  /(?:brow|mayu|mouth|nose|tear|glasses|hair|ear|眉|口|嘴|鼻|泪|淚|眼泪|眼淚|眼镜|眼鏡|髪|发|耳)/i;
const EYE_DRAWABLE_MATCHERS = [
  /(?:hitomi|pupil|iris|eye[_-]?ball|eyeball|黒目|黑眼|瞳|瞳孔|眼珠)/i,
  /(?:eye|eyes|eyelid|mabataki|目|眼)/i,
];

class Live2DOverlayController {
  constructor({ onLayoutChange, onLayoutSave } = {}) {
    this.adapter = null;
    this.canvas = null;
    this.baselineModel = null;
    this.baselineMatrix = null;
    this.localBoundsModel = null;
    this.localBounds = null;
    this.partDisplayNameModel = null;
    this.partDisplayNameUrl = "";
    this.partDisplayNames = new Map();
    this.partDisplayNamePromise = null;
    this.partDisplayNamesLoaded = false;
    this.layoutFrame = null;
    this.pendingMatrix = null;
    this.pendingDrag = null;
    this.wheelSaveTimer = null;
    this.windowWheelInstalled = false;
    this.lastAppliedLayout = { ...MODEL_LAYOUT_DEFAULT };
    this.onLayoutChange = onLayoutChange || (() => {});
    this.onLayoutSave = onLayoutSave || (() => {});
    this.boundPointerDown = (event) => this.handlePointerDown(event);
    this.boundPointerMove = (event) => this.handlePointerMove(event);
    this.boundPointerUp = (event) => this.handlePointerUp(event);
    this.boundPointerLost = (event) => this.releasePointerSession(event, { force: true });
    this.boundPointerLeave = (event) => this.handlePointerLeave(event);
    this.boundWheel = (event) => this.handleWheel(event);
    this.boundWindowBlur = () => this.releasePointerSession(null, { force: true });
  }

  attach(adapter) {
    this.adapter = adapter || this.adapter;
    this.installCanvasHandlers();
    this.ensureBaseline({ force: true });
    return this.applyModelLayout(modelLayout, { immediate: true });
  }

  installCanvasHandlers() {
    const canvas = this.getCanvas();
    if (!canvas || canvas === this.canvas) return;
    if (this.canvas) this.removeCanvasHandlers();
    this.canvas = canvas;
    canvas.addEventListener("pointerdown", this.boundPointerDown, true);
    canvas.addEventListener("pointermove", this.boundPointerMove, true);
    canvas.addEventListener("pointerup", this.boundPointerUp, true);
    canvas.addEventListener("pointercancel", this.boundPointerUp, true);
    canvas.addEventListener("lostpointercapture", this.boundPointerLost, true);
    canvas.addEventListener("pointerleave", this.boundPointerLeave, true);
    canvas.addEventListener("wheel", this.boundWheel, { capture: true, passive: false });
    window.addEventListener("pointermove", this.boundPointerMove, true);
    window.addEventListener("pointerup", this.boundPointerUp, true);
    window.addEventListener("pointercancel", this.boundPointerUp, true);
    document.addEventListener("pointerup", this.boundPointerUp, true);
    document.addEventListener("pointercancel", this.boundPointerUp, true);
    window.addEventListener("blur", this.boundWindowBlur, true);
    if (!this.windowWheelInstalled) {
      window.addEventListener("wheel", this.boundWheel, { capture: true, passive: false });
      this.windowWheelInstalled = true;
    }
  }

  removeCanvasHandlers() {
    if (!this.canvas) return;
    this.releasePointerSession(null, { force: true, persist: false });
    this.canvas.removeEventListener("pointerdown", this.boundPointerDown, true);
    this.canvas.removeEventListener("pointermove", this.boundPointerMove, true);
    this.canvas.removeEventListener("pointerup", this.boundPointerUp, true);
    this.canvas.removeEventListener("pointercancel", this.boundPointerUp, true);
    this.canvas.removeEventListener("lostpointercapture", this.boundPointerLost, true);
    this.canvas.removeEventListener("pointerleave", this.boundPointerLeave, true);
    this.canvas.removeEventListener("wheel", this.boundWheel, true);
    window.removeEventListener("pointermove", this.boundPointerMove, true);
    window.removeEventListener("pointerup", this.boundPointerUp, true);
    window.removeEventListener("pointercancel", this.boundPointerUp, true);
    document.removeEventListener("pointerup", this.boundPointerUp, true);
    document.removeEventListener("pointercancel", this.boundPointerUp, true);
    window.removeEventListener("blur", this.boundWindowBlur, true);
    if (this.windowWheelInstalled) {
      window.removeEventListener("wheel", this.boundWheel, true);
      this.windowWheelInstalled = false;
    }
    this.canvas = null;
  }

  getCanvas() {
    return document.getElementById("canvas");
  }

  getAdapter() {
    if (this.adapter) return this.adapter;
    return typeof window.getLAppAdapter === "function" ? window.getLAppAdapter() : null;
  }

  getManager() {
    const adapter = this.getAdapter();
    if (adapter && typeof adapter.getMgr === "function") return adapter.getMgr();
    return typeof window.getLive2DManager === "function" ? window.getLive2DManager() : null;
  }

  getModel() {
    const adapter = this.getAdapter();
    return adapter && typeof adapter.getModel === "function" ? adapter.getModel() : null;
  }

  getView() {
    try {
      const delegate =
        typeof window.LAppDelegate !== "undefined" &&
        window.LAppDelegate &&
        typeof window.LAppDelegate.getInstance === "function"
          ? window.LAppDelegate.getInstance()
          : null;
      return delegate && typeof delegate.getView === "function" ? delegate.getView() : null;
    } catch (_error) {
      return null;
    }
  }

  readMatrix() {
    const model = this.getModel();
    if (!model || !model._modelMatrix || typeof model._modelMatrix.getArray !== "function") {
      return null;
    }
    return [...model._modelMatrix.getArray()];
  }

  writeMatrix(matrix) {
    const model = this.getModel();
    if (!model || !model._modelMatrix || typeof model._modelMatrix.setMatrix !== "function") {
      return false;
    }
    model._modelMatrix.setMatrix(matrix);
    return true;
  }

  ensureBaseline({ force = false } = {}) {
    const model = this.getModel();
    const matrix = this.readMatrix();
    if (!model || !matrix) return false;
    if (force || this.baselineModel !== model || !this.baselineMatrix) {
      this.baselineModel = model;
      this.baselineMatrix = matrix;
      this.localBoundsModel = null;
      this.localBounds = null;
      this.resetPartDisplayNames(model);
    }
    this.ensurePartDisplayNames(model);
    return true;
  }

  resetPartDisplayNames(model) {
    this.partDisplayNameModel = model || null;
    this.partDisplayNameUrl = "";
    this.partDisplayNames = new Map();
    this.partDisplayNamePromise = null;
    this.partDisplayNamesLoaded = false;
  }

  ensurePartDisplayNames(model) {
    if (!model) return;
    const modelUrl = this.getActiveModelUrl();
    if (!modelUrl) return;
    if (
      this.partDisplayNameModel === model &&
      this.partDisplayNameUrl === modelUrl &&
      (this.partDisplayNamesLoaded || this.partDisplayNamePromise)
    ) {
      return;
    }
    this.partDisplayNameModel = model;
    this.partDisplayNameUrl = modelUrl;
    this.partDisplayNames = new Map();
    this.partDisplayNamesLoaded = false;
    this.partDisplayNamePromise = this.loadPartDisplayNames(modelUrl)
      .then((names) => {
        if (this.partDisplayNameModel === model && this.partDisplayNameUrl === modelUrl) {
          this.partDisplayNames = names;
          this.partDisplayNamesLoaded = true;
        }
      })
      .catch(() => {
        if (this.partDisplayNameModel === model && this.partDisplayNameUrl === modelUrl) {
          this.partDisplayNames = new Map();
          this.partDisplayNamesLoaded = true;
        }
      })
      .finally(() => {
        if (this.partDisplayNameModel === model && this.partDisplayNameUrl === modelUrl) {
          this.partDisplayNamePromise = null;
        }
      });
  }

  getActiveModelUrl() {
    try {
      const raw = localStorage.getItem("modelInfo");
      const modelInfo = raw ? JSON.parse(raw) : null;
      const url = modelInfo && typeof modelInfo.url === "string" ? modelInfo.url : "";
      return url ? new URL(url, location.origin).href : "";
    } catch (_error) {
      return "";
    }
  }

  async loadPartDisplayNames(modelUrl) {
    const modelResponse = await fetch(modelUrl, { cache: "force-cache" });
    if (!modelResponse.ok) return new Map();
    const modelJson = await modelResponse.json();
    const displayInfo =
      modelJson &&
      modelJson.FileReferences &&
      typeof modelJson.FileReferences.DisplayInfo === "string"
        ? modelJson.FileReferences.DisplayInfo
        : "";
    if (!displayInfo) return new Map();

    const displayResponse = await fetch(new URL(displayInfo, modelUrl).href, {
      cache: "force-cache",
    });
    if (!displayResponse.ok) return new Map();
    const displayJson = await displayResponse.json();
    const names = new Map();
    const parts = Array.isArray(displayJson && displayJson.Parts) ? displayJson.Parts : [];
    for (const part of parts) {
      if (!part || typeof part.Id !== "string" || typeof part.Name !== "string") continue;
      names.set(part.Id, part.Name);
    }
    return names;
  }

  applyModelLayout(layout, { immediate = true } = {}) {
    this.installCanvasHandlers();
    if (!this.ensureBaseline()) return false;
    const normalized = normalizeModelLayout(layout);
    const matrix = this.matrixFromLayout(normalized);
    if (!matrix) return false;
    this.lastAppliedLayout = normalized;
    return this.writeMatrixOnFrame(matrix, immediate);
  }

  matrixFromLayout(layout) {
    const next = [...this.baselineMatrix];
    const normalized = normalizeModelLayout(layout);
    const scale = normalized.scale / 100;
    if (Number.isFinite(this.baselineMatrix[0])) next[0] = this.baselineMatrix[0] * scale;
    if (Number.isFinite(this.baselineMatrix[5])) next[5] = this.baselineMatrix[5] * scale;
    next[12] = this.baselineMatrix[12] + normalized.x;
    next[13] = this.baselineMatrix[13] + normalized.y;
    return next;
  }

  writeMatrixOnFrame(matrix, immediate) {
    if (immediate) {
      if (this.layoutFrame) {
        window.cancelAnimationFrame(this.layoutFrame);
        this.layoutFrame = null;
      }
      this.pendingMatrix = null;
      return this.writeMatrix(matrix);
    }
    this.pendingMatrix = matrix;
    if (this.layoutFrame) return true;
    this.layoutFrame = window.requestAnimationFrame(() => {
      const next = this.pendingMatrix;
      this.pendingMatrix = null;
      this.layoutFrame = null;
      if (next) this.writeMatrix(next);
    });
    return true;
  }

  getViewportBounds() {
    const canvas = this.getCanvas();
    if (!canvas || !canvas.width || !canvas.height) return null;
    const aspect = canvas.width / Math.max(1, canvas.height);
    return {
      left: -aspect,
      right: aspect,
      bottom: -1,
      top: 1,
    };
  }

  getTransformedModelBounds(matrix) {
    const localBounds = this.getModelLocalBounds();
    return this.getTransformedLocalBounds(localBounds, matrix);
  }

  getTransformedEyeBounds(matrix) {
    const model = this.getModel();
    if (!model) return null;
    const localBounds = this.getEyeLocalBounds(model);
    return this.getTransformedLocalBounds(localBounds, matrix);
  }

  getTransformedLocalBounds(localBounds, matrix) {
    if (!localBounds) return null;
    const points = [
      this.transformModelPoint(matrix, localBounds.left, localBounds.bottom),
      this.transformModelPoint(matrix, localBounds.left, localBounds.top),
      this.transformModelPoint(matrix, localBounds.right, localBounds.bottom),
      this.transformModelPoint(matrix, localBounds.right, localBounds.top),
    ].filter(Boolean);
    if (!points.length) return null;
    return {
      left: Math.min(...points.map((point) => point.x)),
      right: Math.max(...points.map((point) => point.x)),
      bottom: Math.min(...points.map((point) => point.y)),
      top: Math.max(...points.map((point) => point.y)),
    };
  }

  transformModelPoint(matrix, x, y) {
    if (!matrix || matrix.length < 14) return null;
    return {
      x: matrix[0] * x + matrix[4] * y + matrix[12],
      y: matrix[1] * x + matrix[5] * y + matrix[13],
    };
  }

  getModelLocalBounds() {
    const model = this.getModel();
    if (!model) return null;
    if (this.localBoundsModel === model && this.localBounds) return this.localBounds;

    const drawableBounds = this.getDrawableLocalBounds(model);
    const fallbackBounds = drawableBounds || this.getCanvasLocalBounds(model);
    this.localBoundsModel = model;
    this.localBounds = fallbackBounds;
    return this.localBounds;
  }

  getEyeLocalBounds(model) {
    this.ensurePartDisplayNames(model);
    return this.getDrawableLocalBounds(model, {
      matchDrawable: (candidate, index) => {
        const text = this.getDrawableSemanticText(candidate, index);
        return Boolean(
          text &&
            EYE_DRAWABLE_MATCHERS.some((matcher) => matcher.test(text)) &&
            !EYE_DRAWABLE_EXCLUDE_PATTERN.test(text)
        );
      },
    });
  }

  getDrawableLocalBounds(model, { matchDrawable = null } = {}) {
    const candidates = [model && model._model, model && model._model && model._model._model, model];
    for (const candidate of candidates) {
      if (!candidate || typeof candidate.getDrawableCount !== "function") continue;
      const count = Number(candidate.getDrawableCount());
      if (!Number.isFinite(count) || count <= 0) continue;
      const xs = [];
      const ys = [];
      for (let index = 0; index < count; index += 1) {
        if (
          typeof candidate.getDrawableOpacity === "function" &&
          Number(candidate.getDrawableOpacity(index)) <= 0.01
        ) {
          continue;
        }
        if (typeof matchDrawable === "function" && !matchDrawable(candidate, index)) {
          continue;
        }
        const vertices =
          typeof candidate.getDrawableVertices === "function"
            ? candidate.getDrawableVertices(index)
            : null;
        if (!vertices || typeof vertices.length !== "number") continue;
        for (let offset = 0; offset + 1 < vertices.length; offset += 2) {
          const x = Number(vertices[offset]);
          const y = Number(vertices[offset + 1]);
          if (Number.isFinite(x) && Number.isFinite(y)) {
            xs.push(x);
            ys.push(y);
          }
        }
      }
      if (xs.length && ys.length) {
        return {
          left: Math.min(...xs),
          right: Math.max(...xs),
          bottom: Math.min(...ys),
          top: Math.max(...ys),
        };
      }
    }
    return null;
  }

  getDrawableSemanticText(candidate, index) {
    const parts = [
      this.getDrawableId(candidate, index),
      this.getDrawableParentPartText(candidate, index),
    ].filter(Boolean);
    return parts.join(" ");
  }

  getDrawableId(candidate, index) {
    if (!candidate) return "";
    try {
      if (typeof candidate.getDrawableId === "function") {
        const id = this.normalizeCubismId(candidate.getDrawableId(index));
        if (id) return id;
      }
    } catch (_error) {
      // Drawable ids are best-effort; Part names may still identify the eye.
    }

    const model = candidate._model || candidate;
    const ids = model && model.drawables && model.drawables.ids;
    if (ids && ids[index] !== undefined) return this.normalizeCubismId(ids[index]);
    if (candidate._drawableIds && typeof candidate._drawableIds.at === "function") {
      return this.normalizeCubismId(candidate._drawableIds.at(index));
    }
    return "";
  }

  getDrawableParentPartText(candidate, index) {
    if (!candidate) return "";
    let partId = "";
    try {
      if (
        typeof candidate.getDrawableParentPartIndex === "function" &&
        typeof candidate.getPartId === "function"
      ) {
        const partIndex = Number(candidate.getDrawableParentPartIndex(index));
        if (Number.isFinite(partIndex) && partIndex >= 0) {
          partId = this.normalizeCubismId(candidate.getPartId(partIndex));
        }
      }
    } catch (_error) {
      partId = "";
    }

    if (!partId) {
      const model = candidate._model || candidate;
      const parentIndices = model && model.drawables && model.drawables.parentPartIndices;
      const partIds = model && model.parts && model.parts.ids;
      const partIndex =
        parentIndices && parentIndices[index] !== undefined ? Number(parentIndices[index]) : -1;
      if (Number.isFinite(partIndex) && partIndex >= 0 && partIds && partIds[partIndex] !== undefined) {
        partId = this.normalizeCubismId(partIds[partIndex]);
      }
    }

    const partName = partId ? this.partDisplayNames.get(partId) || "" : "";
    return [partId, partName].filter(Boolean).join(" ");
  }

  normalizeCubismId(value, depth = 0) {
    if (value == null || depth > 4) return "";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    if (typeof value.getString === "function") {
      const normalized = this.normalizeCubismId(value.getString(), depth + 1);
      if (normalized) return normalized;
    }
    for (const key of ["s", "_s", "id", "_id", "value", "_value", "str", "_str", "_stringBuffer"]) {
      if (value && Object.prototype.hasOwnProperty.call(value, key)) {
        const normalized = this.normalizeCubismId(value[key], depth + 1);
        if (normalized) return normalized;
      }
    }
    try {
      const text = String(value);
      return text && text !== "[object Object]" ? text : "";
    } catch (_error) {
      return "";
    }
  }

  getCanvasLocalBounds(model) {
    const candidates = [model, model && model._model, model && model._model && model._model._model];
    for (const candidate of candidates) {
      if (!candidate) continue;
      const width =
        typeof candidate.getCanvasWidth === "function" ? Number(candidate.getCanvasWidth()) : null;
      const height =
        typeof candidate.getCanvasHeight === "function"
          ? Number(candidate.getCanvasHeight())
          : null;
      if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
        return {
          left: -width * 0.5,
          right: width * 0.5,
          bottom: -height * 0.5,
          top: height * 0.5,
        };
      }
    }
    return null;
  }

  hasNativeDrag() {
    const manager = this.getManager();
    return Boolean(manager && typeof manager.onDrag === "function" && this.getCanvas());
  }

  resetNativeDrag() {
    const manager = this.getManager();
    if (!manager || typeof manager.onDrag !== "function") return false;
    manager.onDrag(0, 0);
    return true;
  }

  applyNativeDrag(x, y, { max = null } = {}) {
    const manager = this.getManager();
    if (!manager || typeof manager.onDrag !== "function") return false;
    const xLimit = Number.isFinite(max)
      ? { min: -max, max }
      : NATIVE_DRAG_LIMITS.x;
    const yLimit = Number.isFinite(max)
      ? { min: -max, max }
      : NATIVE_DRAG_LIMITS.y;
    manager.onDrag(
      clamp(x, xLimit.min, xLimit.max),
      clamp(y, yLimit.min, yLimit.max)
    );
    return true;
  }

  trackClientPointer(clientX, clientY) {
    const point = this.viewFromClient(clientX, clientY);
    if (!point) return false;
    return this.applyPointerGaze(point);
  }

  relativeClientPointerGaze(clientX, clientY) {
    const point = this.viewFromClient(clientX, clientY);
    if (!point) return null;
    const gaze = this.relativePointerGaze(point);
    if (!gaze) return null;
    return {
      x: clamp(gaze.x, -1, 1),
      y: clamp(gaze.y, -1, 1),
    };
  }

  trackGlobalPointer(pointer) {
    if (!pointer || pointer.status !== "tracked") return this.resetNativeDrag();
    const point = this.viewFromGlobalPointer(pointer);
    if (!point) return false;
    return this.applyPointerGaze(point);
  }

  relativeGlobalPointerGaze(pointer) {
    if (!pointer || pointer.status !== "tracked") return null;
    const point = this.viewFromGlobalPointer(pointer);
    if (!point) return null;
    const gaze = this.relativePointerGaze(point);
    if (!gaze) return null;
    return {
      x: clamp(gaze.x, -1, 1),
      y: clamp(gaze.y, -1, 1),
    };
  }

  applyPointerGaze(point) {
    const gaze = this.relativePointerGaze(point);
    if (!gaze) {
      return this.applyNativeDrag(point.x, point.y, { max: MODEL_POINTER_GAZE_MAX });
    }
    return this.applyNativeDrag(gaze.x, gaze.y, { max: MODEL_POINTER_GAZE_MAX });
  }

  relativePointerGaze(point) {
    if (!point) return null;
    const focus = this.getModelFocusPoint();
    if (!focus) return null;
    return {
      x: (point.x - focus.x) * MODEL_POINTER_GAZE_GAIN,
      y: (point.y - focus.y) * MODEL_POINTER_GAZE_GAIN,
    };
  }

  getModelFocusPoint() {
    const matrix = this.readMatrix();
    const bounds =
      matrix && (this.getTransformedEyeBounds(matrix) || this.getTransformedModelBounds(matrix));
    if (!bounds) return null;
    return {
      x: (bounds.left + bounds.right) * 0.5,
      y: (bounds.bottom + bounds.top) * 0.5,
    };
  }

  viewFromGlobalPointer(pointer) {
    const primaryPoint = this.viewFromPrimaryPointer(pointer);
    if (primaryPoint) return primaryPoint;

    const screenClient = this.clientFromPointerScreen(pointer);
    if (screenClient) return this.viewFromClient(screenClient.x, screenClient.y);

    const canvas = this.getCanvas();
    const x = Number(pointer && pointer.normalized_x);
    const y = Number(pointer && pointer.normalized_y);
    if (!canvas || !Number.isFinite(x) || !Number.isFinite(y)) return null;
    const aspect = canvas.width / Math.max(1, canvas.height);
    return {
      x: clamp(x, -1, 1) * aspect,
      y: clamp(y, -1, 1),
    };
  }

  viewFromPrimaryPointer(pointer) {
    if (!pointer || pointer.coordinate_space !== "primary_screen") return null;
    const canvas = this.getCanvas();
    const x = Number(pointer.normalized_x);
    const y = Number(pointer.normalized_y);
    if (!canvas || !Number.isFinite(x) || !Number.isFinite(y)) return null;
    const aspect = canvas.width / Math.max(1, canvas.height);
    return {
      x: clamp(x, -1, 1) * aspect,
      y: clamp(y, -1, 1),
    };
  }

  clientFromPointerScreen(pointer) {
    const canvas = this.getCanvas();
    const screenX = Number(pointer && pointer.x);
    const screenY = Number(pointer && pointer.y);
    const windowX = Number(window.screenX ?? window.screenLeft);
    const windowY = Number(window.screenY ?? window.screenTop);
    if (
      !canvas ||
      !Number.isFinite(screenX) ||
      !Number.isFinite(screenY) ||
      !Number.isFinite(windowX) ||
      !Number.isFinite(windowY)
    ) {
      return null;
    }

    const frameX = Math.max(0, (window.outerWidth - window.innerWidth) / 2);
    const frameY = Math.max(0, window.outerHeight - window.innerHeight - frameX);
    const clientX = screenX - windowX - frameX;
    const clientY = screenY - windowY - frameY;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    return { x: clientX, y: clientY };
  }

  viewFromClient(clientX, clientY) {
    return this.screenFromClient(clientX, clientY);
  }

  screenFromClient(clientX, clientY) {
    const canvas = this.getCanvas();
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    if (!rect.width || !rect.height || !canvas.width || !canvas.height) return null;
    const view = this.getView();
    const deviceX = (clientX - rect.left) * (canvas.width / rect.width);
    const deviceY = (clientY - rect.top) * (canvas.height / rect.height);
    if (
      view &&
      view._deviceToScreen &&
      typeof view._deviceToScreen.transformX === "function" &&
      typeof view._deviceToScreen.transformY === "function"
    ) {
      return {
        x: view._deviceToScreen.transformX(deviceX),
        y: view._deviceToScreen.transformY(deviceY),
      };
    }
    const scale = 2 / Math.max(1, canvas.height);
    return {
      x: (deviceX - canvas.width * 0.5) * scale,
      y: (deviceY - canvas.height * 0.5) * -scale,
    };
  }

  isOverModel(clientX, clientY) {
    const model = this.getModel();
    const point = this.screenFromClient(clientX, clientY);
    if (!model || !point) return false;
    const hasHitApi =
      typeof model.anyhitTest === "function" || typeof model.isHitOnModel === "function";
    if (!hasHitApi) return true;
    try {
      if (typeof model.anyhitTest === "function" && model.anyhitTest(point.x, point.y) !== null) {
        return true;
      }
    } catch (_error) {
      // Hit tests are optional; fall through to the model-wide test.
    }
    try {
      return typeof model.isHitOnModel === "function" && model.isHitOnModel(point.x, point.y);
    } catch (_error) {
      return false;
    }
  }

  handlePointerDown(event) {
    if (event.button !== 0 || !this.isOverModel(event.clientX, event.clientY)) return;
    if (this.pendingDrag) this.releasePointerSession(null, { force: true, persist: false });
    this.ensureBaseline();
    const matrix = this.readMatrix();
    const startPoint = this.screenFromClient(event.clientX, event.clientY);
    if (!matrix || !startPoint) return;
    this.pendingDrag = {
      startedAt: performance.now(),
      dragging: false,
      pointerId: event.pointerId,
      startClient: { x: event.clientX, y: event.clientY },
      startPoint,
      startPosition: { x: matrix[12], y: matrix[13] },
      startLayout: { ...modelLayout },
      lastClient: { x: event.clientX, y: event.clientY },
    };
    if (event.currentTarget && typeof event.currentTarget.setPointerCapture === "function") {
      try {
        event.currentTarget.setPointerCapture(event.pointerId);
      } catch (_error) {
        // Pointer capture is best-effort; regular pointermove still works.
      }
    }
    const canvas = this.getCanvas();
    if (canvas) {
      delete canvas.dataset.rikkaModelHover;
      delete canvas.dataset.rikkaDragging;
    }
    event.preventDefault();
  }

  handlePointerMove(event) {
    if (!this.pendingDrag) {
      this.updateHoverState(event.clientX, event.clientY);
      return;
    }
    if (event.buttons !== undefined && (event.buttons & 1) === 0) {
      this.releasePointerSession(event, { force: true });
      return;
    }
    this.pendingDrag.lastClient = { x: event.clientX, y: event.clientY };
    const moved = Math.hypot(
      event.clientX - this.pendingDrag.startClient.x,
      event.clientY - this.pendingDrag.startClient.y
    );
    if (!this.pendingDrag.dragging && moved > MODEL_DRAG_THRESHOLD_PX) {
      this.activatePendingDrag();
    }
    if (!this.pendingDrag || !this.pendingDrag.dragging) return;
    const point = this.screenFromClient(event.clientX, event.clientY);
    if (!point || !this.pendingDrag.startPoint) return;
    const absoluteX =
      this.pendingDrag.startPosition.x + point.x - this.pendingDrag.startPoint.x;
    const absoluteY =
      this.pendingDrag.startPosition.y + point.y - this.pendingDrag.startPoint.y;
    this.onLayoutChange(
      {
        ...this.pendingDrag.startLayout,
        x: absoluteX - this.baselineMatrix[12],
        y: absoluteY - this.baselineMatrix[13],
      },
      { persist: false, immediate: false }
    );
    event.preventDefault();
    event.stopPropagation();
  }

  handlePointerUp(event) {
    this.releasePointerSession(event);
  }

  releasePointerSession(event, { force = false, persist = true } = {}) {
    if (!this.pendingDrag) {
      if (force) this.clearCanvasPointerState();
      return false;
    }
    const wasDragging = this.pendingDrag.dragging;
    const pointerId = this.pendingDrag.pointerId;
    this.pendingDrag = null;
    this.clearCanvasPointerState(pointerId);
    if (force) this.resetNativeDrag();
    if (wasDragging && persist) {
      this.onLayoutSave();
    }
    if (wasDragging && event) {
      event.preventDefault();
      event.stopPropagation();
    }
    return wasDragging;
  }

  clearCanvasPointerState(pointerId) {
    const canvas = this.getCanvas();
    if (canvas) {
      delete canvas.dataset.rikkaDragging;
      delete canvas.dataset.rikkaModelHover;
      if (typeof canvas.releasePointerCapture === "function" && pointerId !== undefined) {
        try {
          canvas.releasePointerCapture(pointerId);
        } catch (_error) {
          // Pointer capture can already be released by the browser.
        }
      }
    }
  }

  handlePointerLeave() {
    const canvas = this.getCanvas();
    if (!canvas || this.pendingDrag) return;
    delete canvas.dataset.rikkaModelHover;
  }

  handleWheel(event) {
    if (
      event.target &&
      typeof event.target.closest === "function" &&
      event.target.closest(".overlay-dock")
    ) {
      return;
    }
    if (!this.isOverModel(event.clientX, event.clientY)) return;
    const direction = event.deltaY > 0 ? -1 : 1;
    this.onLayoutChange(
      {
        ...modelLayout,
        scale: modelLayout.scale + MODEL_WHEEL_SCALE_STEP * direction,
      },
      { persist: false, immediate: false }
    );
    window.clearTimeout(this.wheelSaveTimer);
    this.wheelSaveTimer = window.setTimeout(() => this.onLayoutSave(), MODEL_WHEEL_SAVE_DELAY_MS);
    event.preventDefault();
    event.stopPropagation();
  }

  activatePendingDrag() {
    if (!this.pendingDrag || this.pendingDrag.dragging) return;
    this.pendingDrag.dragging = true;
    const canvas = this.getCanvas();
    if (canvas) {
      delete canvas.dataset.rikkaModelHover;
      canvas.dataset.rikkaDragging = "true";
    }
  }

  updateHoverState(clientX, clientY) {
    const canvas = this.getCanvas();
    if (!canvas) return;
    canvas.dataset.rikkaModelHover = this.isOverModel(clientX, clientY) ? "true" : "false";
  }
}

let socket = null;
let clientUid = null;
let micOwnerUid = "";
let micOwnerKind = "";
let audioContext = null;
let micStream = null;
let micNode = null;
let micSource = null;
let micSampleCount = 0;
let asrHudHideTimer = null;
let asrHudSavedVisible = true;
let asrHudSessionOverride = null;
let asrHudState = {
  status: "idle",
  label: "idle",
  transcript: "",
  detail: "",
  autoHide: true,
  hideMs: 9000,
  autoHidden: true,
};
let globalPointerEnabled = true;
let pointerBackoffUntil = 0;
let configFiles = [];
let currentConfigName = "";
let currentConfigFile = "";
let currentFlowId = null;
let activeAudioPlaybackCount = 0;
let pendingSynthComplete = false;
let previewHandle = null;
let previewExpireTimer = null;
let previewPumpFrame = null;
let gesturePreviewPumpFrame = null;
let gesturePreviewHandle = null;
let awaitingPlaybackPayload = false;
let completedPlaybackFlowId = null;
const audioPlaybackQueue = [];
let audioQueuePlaying = false;
let hasPlayedAudioThisTurn = false;
let subtitleLayout = { ...SUBTITLE_LAYOUT_DEFAULT };
let subtitleLayoutDrag = null;
let subtitleLayoutSaveTimer = null;
let dockLayout = { ...DOCK_LAYOUT_DEFAULT };
let dockLayoutDrag = null;
let dockLayoutSaveTimer = null;
let dockSuppressToggleClick = false;
let modelLayout = readModelLayout();
let live2dController = null;
live2dController = new Live2DOverlayController({
  onLayoutChange: (layout, options) => setModelLayout(layout, options),
  onLayoutSave: saveModelLayout,
});
naturalMotion.setNativeDrag(live2dController);
let pendingExpression = null;
let activeExpression = null;
let expressionHoldTimer = null;
let desiredMoodIdleExpression = null;
let activeMoodIdleExpression = null;
let thinkingPoseHandle = null;
let thinkingTimeoutTimer = null;
const THINKING_TIMEOUT_MS = 20000;
const activeGestures = new Map();
let modelGestureMap = null;

function clamp(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.min(max, Math.max(min, number));
}

function roundToPrecision(value, precision) {
  const factor = 10 ** precision;
  return Math.round(Number(value) * factor) / factor;
}

function normalizeModelLayout(layout) {
  const next = { ...MODEL_LAYOUT_DEFAULT, ...(layout || {}) };
  return {
    scale: roundToPrecision(
      clamp(
        next.scale,
        MODEL_LAYOUT_LIMITS.scale.min,
        MODEL_LAYOUT_LIMITS.scale.max
      ),
      MODEL_LAYOUT_SCALE_PRECISION
    ),
    x: roundToPrecision(
      clamp(next.x, MODEL_LAYOUT_LIMITS.x.min, MODEL_LAYOUT_LIMITS.x.max),
      MODEL_LAYOUT_POSITION_PRECISION
    ),
    y: roundToPrecision(
      clamp(next.y, MODEL_LAYOUT_LIMITS.y.min, MODEL_LAYOUT_LIMITS.y.max),
      MODEL_LAYOUT_POSITION_PRECISION
    ),
  };
}

function formatScaleValue(scale) {
  return Number.isInteger(scale) ? String(scale) : scale.toFixed(1);
}

function syncModelLayoutControlRanges() {
  els.modelScale.min = String(MODEL_LAYOUT_LIMITS.scale.min);
  els.modelScale.max = String(MODEL_LAYOUT_LIMITS.scale.max);
  els.modelScale.step = "0.1";
  els.modelX.min = String(MODEL_LAYOUT_LIMITS.x.min);
  els.modelX.max = String(MODEL_LAYOUT_LIMITS.x.max);
  els.modelX.step = "0.01";
  els.modelY.min = String(MODEL_LAYOUT_LIMITS.y.min);
  els.modelY.max = String(MODEL_LAYOUT_LIMITS.y.max);
  els.modelY.step = "0.01";
}

function readModelLayout() {
  try {
    const raw = localStorage.getItem(MODEL_LAYOUT_STORAGE_KEY);
    if (!raw) return normalizeModelLayout(MODEL_LAYOUT_DEFAULT);
    const parsed = JSON.parse(raw);
    return normalizeModelLayout(parsed);
  } catch (_error) {
    return { ...MODEL_LAYOUT_DEFAULT };
  }
}

function saveModelLayout() {
  try {
    localStorage.setItem(MODEL_LAYOUT_STORAGE_KEY, JSON.stringify(modelLayout));
  } catch (_error) {
    // Local persistence is best-effort; the current overlay view still updates.
  }
}

function applyModelLayout({ persist = true, immediate = true } = {}) {
  modelLayout = normalizeModelLayout(modelLayout);
  if (live2dController && live2dController.applyModelLayout(modelLayout, { immediate })) {
    modelLayout = normalizeModelLayout(live2dController.lastAppliedLayout);
  }
  syncModelLayoutControlRanges();
  els.modelScale.value = String(modelLayout.scale);
  els.modelX.value = String(modelLayout.x);
  els.modelY.value = String(modelLayout.y);
  els.modelScaleValue.textContent = `${formatScaleValue(modelLayout.scale)}%`;
  els.modelXValue.textContent = modelLayout.x.toFixed(2);
  els.modelYValue.textContent = modelLayout.y.toFixed(2);
  if (persist) saveModelLayout();
}

function updateModelLayoutField(field, value, options = {}) {
  modelLayout = normalizeModelLayout({ ...modelLayout, [field]: value });
  applyModelLayout(options);
}

function setModelLayout(layout, options = {}) {
  modelLayout = normalizeModelLayout(layout);
  applyModelLayout(options);
}

function normalizeSubtitleFreeLayout(layout = {}) {
  const viewportWidth = Math.max(1, window.innerWidth || 1);
  const viewportHeight = Math.max(1, window.innerHeight || 1);
  const rawWidth = Number(layout.width ?? layout.subtitle_width_px ?? subtitleLayout.width);
  const width = roundToPrecision(
    clamp(
      rawWidth,
      SUBTITLE_LAYOUT_LIMITS.width.min,
      Math.min(SUBTITLE_LAYOUT_LIMITS.width.max, Math.max(260, viewportWidth - 24))
    ),
    0
  );
  const leftMax = Math.min(
    SUBTITLE_LAYOUT_LIMITS.left.max,
    Math.max(0, viewportWidth - Math.min(width, viewportWidth - 24) - 8)
  );
  const topMax = Math.min(
    SUBTITLE_LAYOUT_LIMITS.top.max,
    Math.max(0, viewportHeight - 56)
  );
  return {
    mode: "free",
    left: roundToPrecision(
      clamp(layout.left ?? layout.subtitle_left_px ?? subtitleLayout.left, 0, leftMax),
      0
    ),
    top: roundToPrecision(
      clamp(layout.top ?? layout.subtitle_top_px ?? subtitleLayout.top, 0, topMax),
      0
    ),
    width,
  };
}

function applySubtitleLayout(layout, { persist = false } = {}) {
  const mode = layout && layout.mode === "free" ? "free" : "anchor";
  subtitleLayout =
    mode === "free"
      ? normalizeSubtitleFreeLayout(layout)
      : { ...subtitleLayout, mode: "anchor" };
  els.subtitleStage.dataset.layoutMode = mode;
  if (mode === "free") {
    document.documentElement.style.setProperty("--subtitle-left", `${subtitleLayout.left}px`);
    document.documentElement.style.setProperty("--subtitle-top", `${subtitleLayout.top}px`);
    document.documentElement.style.setProperty("--subtitle-width", `${subtitleLayout.width}px`);
  }
  if (persist && mode === "free") scheduleSubtitleLayoutSave();
}

function ensureFreeSubtitleLayout() {
  if (subtitleLayout.mode === "free") return normalizeSubtitleFreeLayout(subtitleLayout);
  const rect = els.subtitleStage.getBoundingClientRect();
  return normalizeSubtitleFreeLayout({
    left: rect.left || SUBTITLE_LAYOUT_DEFAULT.left,
    top: rect.top || SUBTITLE_LAYOUT_DEFAULT.top,
    width: rect.width || SUBTITLE_LAYOUT_DEFAULT.width,
  });
}

function scheduleSubtitleLayoutSave() {
  window.clearTimeout(subtitleLayoutSaveTimer);
  subtitleLayoutSaveTimer = window.setTimeout(saveSubtitleLayout, SUBTITLE_LAYOUT_SAVE_DELAY_MS);
}

async function saveSubtitleLayout() {
  if (subtitleLayout.mode !== "free") return;
  const layout = normalizeSubtitleFreeLayout(subtitleLayout);
  try {
    const response = await fetch("/rikka/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        overlay: {
          subtitle_layout_mode: "free",
          subtitle_left_px: layout.left,
          subtitle_top_px: layout.top,
          subtitle_width_px: layout.width,
        },
      }),
    });
    if (response.ok) {
      const payload = await response.json();
      if (payload.settings && payload.settings.overlay && !subtitleLayoutDrag) {
        applyOverlaySettings(payload.settings.overlay);
      }
    }
  } catch (_error) {
    // Overlay layout persistence is best-effort; local drag state remains usable.
  }
}

function effectiveAsrHudVisible() {
  return asrHudSessionOverride === null
    ? asrHudSavedVisible
    : asrHudSessionOverride;
}

function updateAsrHudToggle() {
  if (!els.hudToggle) return;
  const visible = effectiveAsrHudVisible();
  els.hudToggle.textContent = visible ? "Hide HUD" : "Show HUD";
  els.hudToggle.dataset.active = String(visible);
}

function renderAsrHud({ forceShow = false } = {}) {
  updateAsrHudToggle();
  if (!els.asrHud) return;
  if (asrHudHideTimer) {
    window.clearTimeout(asrHudHideTimer);
    asrHudHideTimer = null;
  }
  els.asrHud.dataset.state = asrHudState.status || "idle";
  if (els.asrHudState) els.asrHudState.textContent = asrHudState.label;
  if (els.asrHudText) {
    els.asrHudText.textContent = asrHudState.transcript || asrHudState.label;
  }
  if (els.asrHudDetail) els.asrHudDetail.textContent = asrHudState.detail;
  if (!effectiveAsrHudVisible()) {
    els.asrHud.hidden = true;
    return;
  }
  if (forceShow) asrHudState.autoHidden = false;
  els.asrHud.hidden = asrHudState.autoHidden;
  if (!els.asrHud.hidden && asrHudState.autoHide) {
    asrHudHideTimer = window.setTimeout(() => {
      asrHudState.autoHidden = true;
      if (els.asrHud) els.asrHud.hidden = true;
      asrHudHideTimer = null;
    }, asrHudState.hideMs);
  }
}

function toggleAsrHudSessionVisibility() {
  asrHudSessionOverride = !effectiveAsrHudVisible();
  renderAsrHud({ forceShow: true });
}

function normalizeDockLayout(layout = {}) {
  const mode = layout.dock_layout_mode === "free" || layout.mode === "free"
    ? "free"
    : "corner";
  if (mode !== "free") return { ...DOCK_LAYOUT_DEFAULT };
  const toggleRect = els.dockToggle
    ? els.dockToggle.getBoundingClientRect()
    : { width: 44, height: 44 };
  const toggleWidth = Math.max(32, toggleRect.width || 44);
  const toggleHeight = Math.max(32, toggleRect.height || 44);
  const leftMax = Math.max(
    DOCK_REACHABLE_MARGIN_PX,
    window.innerWidth - toggleWidth - DOCK_REACHABLE_MARGIN_PX
  );
  const topMax = Math.max(
    DOCK_REACHABLE_MARGIN_PX,
    window.innerHeight - toggleHeight - DOCK_REACHABLE_MARGIN_PX
  );
  return {
    mode: "free",
    left: roundToPrecision(
      clamp(layout.left ?? layout.dock_left_px ?? 0, DOCK_REACHABLE_MARGIN_PX, leftMax),
      0
    ),
    top: roundToPrecision(
      clamp(layout.top ?? layout.dock_top_px ?? 0, DOCK_REACHABLE_MARGIN_PX, topMax),
      0
    ),
  };
}

function applyDockLayout(layout, { persist = false } = {}) {
  dockLayout = normalizeDockLayout(layout);
  if (!els.dock) return;
  els.dock.dataset.layoutMode = dockLayout.mode;
  if (dockLayout.mode === "free") {
    document.documentElement.style.setProperty("--dock-left", `${dockLayout.left}px`);
    document.documentElement.style.setProperty("--dock-top", `${dockLayout.top}px`);
  } else {
    document.documentElement.style.removeProperty("--dock-left");
    document.documentElement.style.removeProperty("--dock-top");
  }
  if (persist) scheduleDockLayoutSave();
}

function scheduleDockLayoutSave() {
  window.clearTimeout(dockLayoutSaveTimer);
  dockLayoutSaveTimer = window.setTimeout(saveDockLayout, DOCK_LAYOUT_SAVE_DELAY_MS);
}

async function saveDockLayout() {
  window.clearTimeout(dockLayoutSaveTimer);
  dockLayoutSaveTimer = null;
  const layout = normalizeDockLayout(dockLayout);
  const overlay =
    layout.mode === "free"
      ? {
          dock_layout_mode: "free",
          dock_left_px: layout.left,
          dock_top_px: layout.top,
        }
      : { dock_layout_mode: "corner" };
  try {
    const response = await fetch("/rikka/settings", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ overlay }),
    });
    if (response.ok) {
      const payload = await response.json();
      if (payload.settings && payload.settings.overlay && !dockLayoutDrag) {
        applyDockLayout(payload.settings.overlay);
      }
    }
  } catch (_error) {
    // Dock persistence is best-effort; the current overlay view remains usable.
  }
}

function beginDockLayoutDrag(event) {
  if (!els.dock || event.button !== 0) return;
  const rect = els.dock.getBoundingClientRect();
  const startLayout = normalizeDockLayout({
    mode: "free",
    left: rect.left,
    top: rect.top,
  });
  dockLayoutDrag = {
    pointerId: event.pointerId,
    startClient: { x: event.clientX, y: event.clientY },
    startLayout,
    moved: false,
  };
  els.dock.dataset.moving = "true";
  if (typeof event.currentTarget.setPointerCapture === "function") {
    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch (_error) {
      // Pointer capture is best-effort; window listeners finish the gesture.
    }
  }
}

function handleDockLayoutMove(event) {
  if (!dockLayoutDrag) return;
  if (event.buttons !== undefined && (event.buttons & 1) === 0) {
    finishDockLayoutDrag(event);
    return;
  }
  const dx = event.clientX - dockLayoutDrag.startClient.x;
  const dy = event.clientY - dockLayoutDrag.startClient.y;
  if (!dockLayoutDrag.moved && Math.hypot(dx, dy) <= MODEL_DRAG_THRESHOLD_PX) {
    return;
  }
  if (!dockLayoutDrag.moved) {
    dockLayoutDrag.moved = true;
    dockSuppressToggleClick = true;
  }
  applyDockLayout({
    mode: "free",
    left: dockLayoutDrag.startLayout.left + dx,
    top: dockLayoutDrag.startLayout.top + dy,
  });
  event.preventDefault();
  event.stopPropagation();
}

function finishDockLayoutDrag(event) {
  if (!dockLayoutDrag) return;
  const moved = dockLayoutDrag.moved;
  dockLayoutDrag = null;
  if (els.dock) delete els.dock.dataset.moving;
  if (moved) saveDockLayout();
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
}

function resetDockLayout() {
  applyDockLayout({ mode: "corner" }, { persist: true });
}

function pointerWithRelativeGaze(pointer) {
  if (
    !pointer ||
    !live2dController ||
    typeof live2dController.relativeGlobalPointerGaze !== "function"
  ) {
    return pointer;
  }
  const gaze = live2dController.relativeGlobalPointerGaze(pointer);
  if (!gaze) return pointer;
  return {
    ...pointer,
    relative_x: gaze.x,
    relative_y: gaze.y,
    gaze_reference: "model_focus",
  };
}

function flowIdFromPayload(payload) {
  return (
    (payload && payload.flow && payload.flow.id) ||
    (payload && payload.event && payload.event.id) ||
    (payload && payload.response && payload.response.id) ||
    currentFlowId ||
    null
  );
}

function setCurrentFlowFromPayload(payload) {
  const flowId = flowIdFromPayload(payload);
  if (flowId) currentFlowId = flowId;
  return currentFlowId;
}

function postFrontendAction(kind, status = "ok", detail = "", metadata = {}, flowId = null) {
  const payload = {
    flow_id: flowId || currentFlowId,
    kind,
    status,
    detail,
    metadata: {
      ...metadata,
      active_expression: activeExpression ? activeExpression.name : null,
    },
  };
  try {
    fetch("/rikka/debug/frontend-action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {});
  } catch (_error) {
    // Telemetry must never break audio, subtitles, or Live2D actions.
  }
}

function priorityValue(value) {
  if (typeof value === "number") return value;
  return MOTION_PRIORITY[String(value || "normal").toLowerCase()] || MOTION_PRIORITY.normal;
}

function motionStarted(result) {
  return result !== false && result !== -1 && result !== null && result !== undefined;
}

function applyMotionAction(motion) {
  if (!motion || typeof motion !== "object") return false;
  const adapter = live2dController && live2dController.getAdapter();
  const model = adapter && typeof adapter.getModel === "function"
    ? adapter.getModel()
    : live2dController && live2dController.getModel();
  const group = String(motion.group || "");
  const index = Number(motion.index);
  const priority = priorityValue(motion.priority);
  let ok = false;
  try {
    if (adapter && typeof adapter.startMotion === "function" && Number.isInteger(index)) {
      ok = motionStarted(adapter.startMotion(group, index, priority));
    }
    if (!ok && model && typeof model.startMotion === "function" && Number.isInteger(index)) {
      ok = motionStarted(model.startMotion(group, index, priority));
    }
    if (!ok && model && typeof model.startRandomMotion === "function") {
      ok = motionStarted(model.startRandomMotion(group, priority));
    }
  } catch (_error) {
    ok = false;
  }
  postFrontendAction(
    "motion",
    ok ? "ok" : "error",
    ok ? "motion applied" : "motion API returned invalid handle",
    {
      name: motion.name || "",
      group,
      index: Number.isInteger(index) ? index : null,
    }
  );
  return ok;
}

function applyGestureMotion(motion) {
  if (!motion || typeof motion !== "object") return false;
  const name = String(motion.name || "");
  if (!name || !modelGestureMap) {
    return applyMotionAction(motion);
  }
  const gestureSpec = modelGestureMap[name];
  if (!gestureSpec || !gestureSpec.kind) {
    return applyMotionAction(motion);
  }
  const now = performance.now();
  const record = activeGestures.get(name);
  if (record && now < record.cooledAt) {
    postFrontendAction("gesture", "cooldown", "gesture on cooldown", { name, kind: gestureSpec.kind });
    return false;
  }
  const amplitude = Number(gestureSpec.amplitude) || 1.0;
  const duration_ms = Number(gestureSpec.duration_ms) || 1000;
  const cooldown_ms = Number(gestureSpec.cooldown_ms) || 1200;
  const handle = naturalMotion.startGesturePose(gestureSpec.kind, { amplitude, duration_ms });
  if (!handle) {
    postFrontendAction("gesture", "error", "unknown gesture kind", { name, kind: gestureSpec.kind });
    return false;
  }
  activeGestures.set(name, { handle, cooledAt: now + cooldown_ms });
  postFrontendAction("gesture", "ok", "gesture started", {
    name,
    kind: gestureSpec.kind,
    amplitude,
    duration_ms,
  });
  return true;
}

function applyActionBundle(actions, source) {
  if (!actions || typeof actions !== "object") return;
  if (Array.isArray(actions.motions)) {
    for (const motion of actions.motions) {
      applyGestureMotion(motion);
    }
  }
  if (actions.gaze) {
    naturalMotion.applyActionGaze(actions.gaze);
    postFrontendAction("gaze", "ok", "gaze applied", { source });
  }
  if (Array.isArray(actions.expressions) && actions.expressions.length > 0) {
    const expression = actions.expressions[0];
    if (expression && expression.preset && typeof expression.preset === "object") {
      pendingExpression = {
        name: String(expression.name || ""),
        preset: expression.preset,
        source,
      };
    }
  }
  if (
    actions.mood_idle_expression &&
    actions.mood_idle_expression.preset &&
    typeof actions.mood_idle_expression.preset === "object"
  ) {
    setMoodIdleExpression({
      name: String(actions.mood_idle_expression.name || ""),
      preset: actions.mood_idle_expression.preset,
      source,
    });
  }
}

function beginSubtitleLayoutDrag(event, mode) {
  if (event.button !== 0) return;
  const layout = ensureFreeSubtitleLayout();
  applySubtitleLayout(layout);
  subtitleLayoutDrag = {
    mode,
    pointerId: event.pointerId,
    startClient: { x: event.clientX, y: event.clientY },
    startLayout: { ...layout },
  };
  subtitle.root.dataset.layoutMoving = "true";
  if (typeof subtitle.root.setPointerCapture === "function") {
    try {
      subtitle.root.setPointerCapture(event.pointerId);
    } catch (_error) {
      // Pointer capture is best-effort; window listeners finish the gesture.
    }
  }
  event.preventDefault();
  event.stopPropagation();
}

function handleSubtitleLayoutMove(event) {
  if (!subtitleLayoutDrag) return;
  if (event.buttons !== undefined && (event.buttons & 1) === 0) {
    finishSubtitleLayoutDrag(event);
    return;
  }
  const dx = event.clientX - subtitleLayoutDrag.startClient.x;
  const dy = event.clientY - subtitleLayoutDrag.startClient.y;
  const start = subtitleLayoutDrag.startLayout;
  const next =
    subtitleLayoutDrag.mode === "resize"
      ? normalizeSubtitleFreeLayout({
          ...start,
          width: start.width + dx,
        })
      : normalizeSubtitleFreeLayout({
          ...start,
          left: start.left + dx,
          top: start.top + dy,
        });
  applySubtitleLayout(next);
  event.preventDefault();
  event.stopPropagation();
}

function finishSubtitleLayoutDrag(event) {
  if (!subtitleLayoutDrag) return;
  const pointerId = subtitleLayoutDrag.pointerId;
  subtitleLayoutDrag = null;
  delete subtitle.root.dataset.layoutMoving;
  if (typeof subtitle.root.releasePointerCapture === "function" && pointerId !== undefined) {
    try {
      subtitle.root.releasePointerCapture(pointerId);
    } catch (_error) {
      // Pointer capture can already be released by the browser.
    }
  }
  saveSubtitleLayout();
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }
}

function setWsState(state) {
  els.wsState.textContent = state;
  els.wsState.dataset.state = state;
}

function wsUrl() {
  const value = els.wsUrl.value.trim() || "/client-ws";
  if (value.startsWith("ws://") || value.startsWith("wss://")) return value;
  const scheme = location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${location.host}${value.startsWith("/") ? value : `/${value}`}`;
}

function connect() {
  if (socket) socket.close();
  setWsState("connecting");
  socket = new WebSocket(wsUrl());
  socket.addEventListener("open", () => {
    setWsState("connected");
    send({ type: "request-init-config" });
    send({ type: "fetch-configs" });
    send({
      type: "client-capabilities",
      client_kind: "overlay",
      always_on_enabled: false,
      mic_permission: "unknown",
      listening: false,
      reason: "overlay_connected",
    });
  });
  socket.addEventListener("close", () => setWsState("closed"));
  socket.addEventListener("error", () => setWsState("error"));
  socket.addEventListener("message", (event) => {
    let payload = null;
    try {
      payload = JSON.parse(event.data);
    } catch (_error) {
      return;
    }
    handleMessage(payload);
  });
}

function send(payload) {
  if (!socket || socket.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(payload));
  return true;
}

function handleLive2dParamPreview(payload) {
  const parameters = payload.parameters;
  if (!parameters || typeof parameters !== "object") {
    return;
  }

  const ttlMs = Math.max(0, Number(payload.ttl_ms) || 1500);

  window.clearTimeout(previewExpireTimer);
  previewExpireTimer = null;
  if (previewPumpFrame) {
    window.cancelAnimationFrame(previewPumpFrame);
    previewPumpFrame = null;
  }
  if (previewHandle) {
    naturalMotion.stopParameterLayer(previewHandle, { fadeOutMs: 0 });
    previewHandle = null;
  }

  previewHandle = naturalMotion.startParameterLayer("preview", {
    params: parameters,
    fadeInMs: 120,
    holdMs: ttlMs,
    fadeOutMs: 200,
    easing: "smoothstep",
  });

  if (typeof naturalMotion.updateMotionFrame === "function") {
    naturalMotion.flushFrame(performance.now());
  }
  const parameterProbe = naturalMotion.probeParameters(Object.keys(parameters));
  if (previewHandle) {
    const pumpUntil = performance.now() + ttlMs + 220;
    const pumpPreview = (now) => {
      naturalMotion.flushFrame(now);
      if (now < pumpUntil) {
        previewPumpFrame = window.requestAnimationFrame(pumpPreview);
      } else {
        previewPumpFrame = null;
      }
    };
    previewPumpFrame = window.requestAnimationFrame(pumpPreview);
    postFrontendAction("live2d-preview", "ok", "preview envelope started", {
      parameter_count: Object.keys(parameters).length,
      parameter_probe: parameterProbe,
      ttl_ms: ttlMs,
    });
    send({
      type: "live2d-param-preview-result",
      ok: true,
      detail: "preview envelope started",
      probe: parameterProbe,
    });
    previewExpireTimer = window.setTimeout(() => {
      if (previewPumpFrame) {
        window.cancelAnimationFrame(previewPumpFrame);
        previewPumpFrame = null;
      }
      previewHandle = null;
      previewExpireTimer = null;
    }, ttlMs + 260);
    window.setTimeout(() => {
      send({
        type: "live2d-param-preview-result",
        ok: true,
        detail: "preview delayed probe",
        probe: naturalMotion.probeParameters(Object.keys(parameters)),
      });
    }, 180);
  } else {
    postFrontendAction("live2d-preview", "error", "preview envelope rejected", {
      parameter_count: Object.keys(parameters).length,
      ttl_ms: ttlMs,
    });
    send({
      type: "live2d-param-preview-result",
      ok: false,
      detail: "preview envelope rejected",
      probe: parameterProbe,
    });
  }
}

function handleLive2dGesturePreview(payload) {
  const gesture = payload.gesture;
  const name = String(payload.name || "");
  if (!gesture || typeof gesture !== "object") {
    return;
  }
  const kind = String(gesture.kind || "");
  const amplitude = Number(gesture.amplitude) || 1.0;
  const duration_ms = Number(gesture.duration_ms) || 1000;
  if (gesturePreviewPumpFrame) {
    window.cancelAnimationFrame(gesturePreviewPumpFrame);
    gesturePreviewPumpFrame = null;
  }
  if (gesturePreviewHandle) {
    naturalMotion.stopGesturePose(gesturePreviewHandle, { fadeOutMs: 0 });
    gesturePreviewHandle = null;
  }
  gesturePreviewHandle = naturalMotion.startGesturePose(kind, {
    amplitude,
    duration_ms,
    jitter: 0,
  });
  const ok = Boolean(gesturePreviewHandle);
  if (ok) {
    const pumpUntil = performance.now() + duration_ms + 260;
    const pumpGesturePreview = (now) => {
      naturalMotion.flushFrame(now);
      if (now < pumpUntil) {
        gesturePreviewPumpFrame = window.requestAnimationFrame(pumpGesturePreview);
      } else {
        gesturePreviewPumpFrame = null;
        gesturePreviewHandle = null;
      }
    };
    gesturePreviewPumpFrame = window.requestAnimationFrame(pumpGesturePreview);
    window.setTimeout(() => {
      send({
        type: "live2d-gesture-preview-result",
        ok: true,
        name,
        detail: "gesture delayed probe",
        probe: naturalMotion.probeParameters([
          "ParamAngleX",
          "ParamAngleY",
          "ParamAngleZ",
          "ParamBodyAngleX",
          "ParamBodyAngleZ",
          "ParamEyeBallX",
          "ParamEyeBallY",
          "ParamEyeLOpen",
          "ParamEyeROpen",
          "dengyan",
          "ParamearLe",
          "ParamearRe",
          "Param97",
        ]),
      });
    }, Math.min(240, Math.max(80, duration_ms * 0.35)));
  }
  postFrontendAction(
    "gesture-preview",
    ok ? "ok" : "error",
    ok ? "gesture preview started" : "gesture preview rejected",
    { name, kind, amplitude, duration_ms }
  );
  send({
    type: "live2d-gesture-preview-result",
    ok,
    name,
    detail: ok ? "gesture preview started" : "gesture preview rejected",
  });
}

function handleMessage(payload) {
  if (!payload || typeof payload !== "object") return;
  const flowId = setCurrentFlowFromPayload(payload);
  switch (payload.type) {
    case "set-model-and-conf":
      clientUid = payload.client_uid || clientUid;
      currentConfigName = payload.conf_name || currentConfigName;
      els.modelState.textContent =
        (payload.model_info && payload.model_info.name) || payload.conf_name || "ready";
      updateRuntimeModel(payload.model_info);
      syncSelectedConfig();
      break;
    case "config-files":
      updateConfigOptions(payload.configs || []);
      break;
    case "config-switched":
      send({ type: "request-init-config" });
      break;
    case "control":
      handleControl(payload.text);
      break;
    case "rikka-live-event":
      postFrontendAction("receive", "ok", "live event received", {
        type: payload.event && payload.event.type,
        source: payload.event && payload.event.source,
      }, flowId);
      break;
    case "audio":
      handleAudio(payload);
      break;
    case "tool_call_status": {
      const label = {
        look_at_screen: "正在看屏幕…",
        web_search: "正在查资料…",
      }[payload.tool_name];
      if (payload.status === "running" && label && !audioQueuePlaying) {
        subtitle.show(label, {
          speaking: false,
          autoHide: false,
          variant: "thinking",
        });
        startThinkingState();
      }
      break;
    }
    case "rikka-response":
      if (payload.response && payload.response.subtitle_text) {
        if (payload.speak === false) {
          subtitle.show(payload.response.subtitle_text, {
            autoHide: true,
            holdMs: 11000,
            variant: "response",
          });
          postFrontendAction("response", "ok", "subtitle displayed", {
            variant: "response",
            has_audio: false,
          }, flowId);
          applyActionBundle(payload.actions, "rikka-response");
        } else {
          awaitingPlaybackPayload = true;
          postFrontendAction("response", "running", "response received; waiting for audio payload", {
            variant: "response",
            has_audio: true,
          }, flowId);
        }
      }
      break;
    case "backend-synth-complete":
      pendingSynthComplete = true;
      maybeCompleteFrontendPlayback(flowId, "backend synth complete");
      break;
    case "wake-gate": {
      const wakeMatchDetail = payload.match_kind ? ` / ${payload.match_kind}` : "";
      els.wakeState.textContent = payload.active ? "active" : "waiting";
      setAsrStatus(payload.should_process ? "accepted" : "rejected", {
        transcript: payload.text || "",
        detail: `${payload.source || "wake"} / ${payload.reason || "wake gate updated"}${wakeMatchDetail}`,
        persistent: !payload.should_process,
      });
      postFrontendAction("wake", payload.should_process ? "ok" : "skipped", payload.reason || "wake gate updated", {
        active: Boolean(payload.active),
        should_process: Boolean(payload.should_process),
        woke: Boolean(payload.woke),
        match_kind: payload.match_kind || null,
      }, flowId);
      break;
    }
    case "asr-streaming-partial":
      els.wakeState.textContent = "partial";
      setAsrStatus("partial", {
        transcript: payload.text || "",
        detail: "streaming partial transcript",
        persistent: true,
      });
      break;
    case "user-input-transcription":
      els.wakeState.textContent = "heard";
      setAsrStatus("transcript", {
        transcript: payload.text || payload.transcript || "",
        detail: "transcript heard; waiting for wake gate",
        persistent: true,
      });
      postFrontendAction("mic", "ok", "transcript heard", {
        has_text: Boolean(payload.text || payload.transcript),
      }, flowId);
      break;
    case "asr-owner-state":
      handleMicOwnerState(payload);
      break;
    case "live2d-param-preview":
      handleLive2dParamPreview(payload);
      break;
    case "live2d-gesture-preview":
      handleLive2dGesturePreview(payload);
      break;
    default:
      break;
  }
}

function handleMicOwnerState(payload) {
  micOwnerUid = payload.owner_client_uid || "";
  const owner = payload.owner || {};
  micOwnerKind = owner.client_kind || "";
  const ownsMic = micOwnerUid && micOwnerUid === clientUid;
  setAsrStatus(ownsMic ? "owner" : micOwnerUid ? "non_owner" : "ready", {
    detail: ownsMic
      ? "Overlay owns microphone"
      : micOwnerUid
        ? `${micOwnerKind || "another client"} owns microphone`
        : payload.streaming_status || "No active microphone owner",
    persistent: true,
  });
}

function setAsrStatus(status, options = {}) {
  const transcript = options.transcript == null ? "" : String(options.transcript);
  const detail = options.detail == null ? "" : String(options.detail);
  const labels = {
    idle: "idle",
    ready: "ready",
    owner: "mic owner",
    non_owner: "mic locked",
    recording: "recording",
    transcribing: "transcribing",
    partial: "partial",
    transcript: "heard",
    accepted: "wake accepted",
    rejected: "wake rejected",
    disabled: "asr off",
    error: "error",
  };
  const label = labels[status] || status || "unknown";
  if (els.asrState) els.asrState.textContent = label;
  if (els.asrTranscript) {
    els.asrTranscript.textContent = transcript
      ? `Transcript: ${transcript}`
      : "No transcript text";
  }
  if (els.asrDetail) els.asrDetail.textContent = detail || "No ASR detail yet.";
  asrHudState = {
    status: status || "idle",
    label,
    transcript,
    detail,
    autoHide: options.autoHide !== false && !options.persistent,
    hideMs: options.hideMs || 9000,
    autoHidden: false,
  };
  renderAsrHud();
}

function updateConfigOptions(configs) {
  configFiles = Array.isArray(configs) ? configs : [];
  els.configSelect.innerHTML = "";
  if (!configFiles.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "not found";
    els.configSelect.appendChild(option);
    els.configSelect.disabled = true;
    els.switchConfig.disabled = true;
    return;
  }
  els.configSelect.disabled = false;
  els.switchConfig.disabled = false;
  for (const config of configFiles) {
    const option = document.createElement("option");
    option.value = config.filename || "";
    option.textContent = config.name || config.filename || "config";
    els.configSelect.appendChild(option);
  }
  syncSelectedConfig();
}

function syncSelectedConfig() {
  if (!configFiles.length) return;
  const match =
    configFiles.find((config) => config.filename === currentConfigFile) ||
    configFiles.find((config) => config.name === currentConfigName);
  if (match && match.filename) {
    currentConfigFile = match.filename;
    els.configSelect.value = match.filename;
  }
}

function handleControl(text) {
  if (text === "mic-disabled") {
    els.wakeState.textContent = "asr off";
    els.mic.dataset.active = "false";
    setAsrStatus("disabled", {
      detail: "ASR is disabled by configuration",
      autoHide: false,
    });
    postFrontendAction("mic", "skipped", "asr_disabled", {
      reason: "asr_disabled",
    });
  }
  if (text === "start-mic") {
    els.wakeState.textContent = "ready";
    setAsrStatus("ready", {
      detail: "ASR is ready; click Mic to record",
      hideMs: 5000,
    });
    postFrontendAction("mic", "ok", "mic capture requested");
  }
  if (text === "conversation-chain-start") {
    startThinkingState();
  }
  if (text === "conversation-chain-end") {
    clearThinkingState();
  }
}

function handleAudio(payload) {
  const flowId = setCurrentFlowFromPayload(payload);
  if (flowId && completedPlaybackFlowId !== flowId) completedPlaybackFlowId = null;
  awaitingPlaybackPayload = false;
  const text = payload.display_text && payload.display_text.text;
  if (!payload.audio) {
    if (text) {
      subtitle.show(text, { speaking: true, autoHide: false, variant: "speech" });
      postFrontendAction("response", "ok", "speech subtitle displayed", {
        variant: "speech",
      }, flowId);
    }
    naturalMotion.stopLipSync();
    applyActionBundle(payload.actions, "audio");
    window.setTimeout(() => {
      completeFrontendPlayback(flowId, "silent payload complete", {
        has_audio: false,
      });
    }, 900);
    return;
  }
  postFrontendAction("audio", "running", "waiting for browser audio playback", {
    has_audio: true,
    volume_frames: Array.isArray(payload.volumes) ? payload.volumes.length : 0,
  }, flowId);
  audioPlaybackQueue.push({ payload, flowId });
  playNextAudioPayload();
}

function playNextAudioPayload() {
  if (audioQueuePlaying || audioPlaybackQueue.length <= 0) return;
  const next = audioPlaybackQueue.shift();
  if (!next) return;
  audioQueuePlaying = true;
  const preSilenceMs = Number(next.payload && next.payload.pre_silence_ms) || 0;
  if (preSilenceMs > 0 && hasPlayedAudioThisTurn) {
    window.setTimeout(
      () => playQueuedAudioPayload(next.payload, next.flowId),
      Math.min(preSilenceMs, 5000)
    );
    return;
  }
  playQueuedAudioPayload(next.payload, next.flowId);
}

function playQueuedAudioPayload(payload, flowId) {
  const text = payload.display_text && payload.display_text.text;
  const audio = new Audio(`data:audio/wav;base64,${payload.audio}`);
  let visualsStarted = false;
  let playbackFinished = false;
  let lipSyncSource = "unavailable";
  activeAudioPlaybackCount += 1;
  const startPlaybackVisuals = () => {
    if (visualsStarted) return;
    visualsStarted = true;
    hasPlayedAudioThisTurn = true;
    clearThinkingState();
    send({ type: "frontend-playback-state", playing: true });
    if (text) {
      subtitle.show(text, { speaking: true, autoHide: false, variant: "speech" });
      postFrontendAction("response", "ok", "speech subtitle displayed", {
        variant: "speech",
      }, flowId);
    }
    naturalMotion.playAudioLipSync(audio, {
      audioBase64: payload.audio,
      fallbackVolumes: payload.volumes || [],
      sliceLength: payload.slice_length || 20,
      onSource: (source) => {
        lipSyncSource = source || "unavailable";
        postFrontendAction(
          "lip_sync",
          lipSyncSource === "unavailable" ? "skipped" : "ok",
          "lip sync source selected",
          {
            lip_sync_source: lipSyncSource,
            volume_frames: Array.isArray(payload.volumes) ? payload.volumes.length : 0,
          },
          flowId
        );
      },
    });
    applyActionBundle(payload.actions, "audio");
    activateExpression();
    postFrontendAction("audio", "ok", "audio playback started", {
      has_audio: true,
      lip_sync_source: "preparing",
      volume_frames: Array.isArray(payload.volumes) ? payload.volumes.length : 0,
    }, flowId);
  };
  const finishAudioPlayback = (status, detail) => {
    if (playbackFinished) return;
    playbackFinished = true;
    send({ type: "frontend-playback-state", playing: false, status });
    activeAudioPlaybackCount = Math.max(0, activeAudioPlaybackCount - 1);
    audioQueuePlaying = false;
    naturalMotion.stopLipSync();
    subtitle.setSpeaking(false);
    if (status === "ok") {
      subtitle.hide(2200);
      scheduleExpressionFadeOut();
    } else {
      fadeOutExpression();
    }
    postFrontendAction("audio", status, detail, {
      has_audio: true,
      lip_sync_source: lipSyncSource,
    }, flowId);
    if (audioPlaybackQueue.length > 0) {
      playNextAudioPayload();
      return;
    }
    maybeCompleteFrontendPlayback(flowId, "frontend playback complete", {
      has_audio: true,
      lip_sync_source: lipSyncSource,
      playback_status: status,
    }, status);
  };
  audio.addEventListener("playing", startPlaybackVisuals, { once: true });
  audio.addEventListener("ended", () => {
    finishAudioPlayback("ok", "audio playback ended");
  });
  audio.addEventListener("error", () => {
    finishAudioPlayback("error", "audio playback error");
  });
  audio.play().catch(() => {
    finishAudioPlayback("error", "audio playback rejected");
  });
}

function activateExpression() {
  if (!pendingExpression) return;
  const preset = pendingExpression.preset;
  const presetName = pendingExpression.name;
  if (activeExpression && activeExpression.name === presetName) {
    window.clearTimeout(expressionHoldTimer);
    expressionHoldTimer = null;
    pendingExpression = null;
    return;
  }
  if (activeExpression) {
    naturalMotion.stopParameterLayer(activeExpression.handle, { fadeOutMs: 0 });
    activeExpression = null;
  }
  suspendMoodIdleExpression(180);
  const fadeInMs = Number(preset.fade_ms) || 300;
  const params = preset.parameters || {};
  if (Object.keys(params).length === 0) {
    activeExpression = null;
    pendingExpression = null;
    return;
  }
  const handle = naturalMotion.startParameterLayer("expression", {
    params,
    fadeInMs,
    easing: "smoothstep",
  });
  if (handle) {
    activeExpression = {
      name: presetName,
      handle,
      preset,
    };
  }
  pendingExpression = null;
}

function scheduleExpressionFadeOut() {
  if (!activeExpression) return;
  const holdMs = Number(activeExpression.preset.hold_after_speech_ms) || 0;
  if (holdMs > 0) {
    window.clearTimeout(expressionHoldTimer);
    expressionHoldTimer = window.setTimeout(() => {
      fadeOutExpression();
    }, holdMs);
  } else {
    fadeOutExpression();
  }
}

function fadeOutExpression() {
  window.clearTimeout(expressionHoldTimer);
  expressionHoldTimer = null;
  if (activeExpression) {
    const fadeOutMs = Number(activeExpression.preset.fade_ms) || 320;
    naturalMotion.stopParameterLayer(activeExpression.handle, { fadeOutMs });
    activeExpression = null;
  }
  pendingExpression = null;
  applyMoodIdleExpression();
}

function setMoodIdleExpression(expression) {
  desiredMoodIdleExpression = expression;
  if (!activeExpression) {
    applyMoodIdleExpression();
  }
}

function applyMoodIdleExpression() {
  if (activeExpression || !desiredMoodIdleExpression) return;
  const preset = desiredMoodIdleExpression.preset || {};
  const presetName = desiredMoodIdleExpression.name || "";
  const params = preset.parameters || {};
  if (Object.keys(params).length === 0) {
    suspendMoodIdleExpression(Number(preset.fade_ms) || 420);
    return;
  }
  if (activeMoodIdleExpression && activeMoodIdleExpression.name === presetName) {
    return;
  }
  suspendMoodIdleExpression(Number(preset.fade_ms) || 420);
  const handle = naturalMotion.startParameterLayer("mood_idle_expression", {
    params,
    fadeInMs: Number(preset.fade_ms) || 500,
    easing: "smoothstep",
  });
  if (handle) {
    activeMoodIdleExpression = {
      name: presetName,
      handle,
      preset,
    };
    postFrontendAction("mood_idle_expression", "ok", "mood idle expression applied", {
      name: presetName,
    });
  }
}

function suspendMoodIdleExpression(fadeOutMs = 320) {
  if (!activeMoodIdleExpression) return;
  naturalMotion.stopParameterLayer(activeMoodIdleExpression.handle, { fadeOutMs });
  activeMoodIdleExpression = null;
}

function startThinkingState() {
  if (thinkingPoseHandle) return;
  thinkingPoseHandle = naturalMotion.startGesturePose("think_pose", {
    amplitude: 1,
    duration_ms: 1800,
    layer: "thinking",
    openEnded: true,
    fadeInMs: 800,
    fadeOutMs: 600,
    jitter: 0,
  });
  subtitle.show("…", { speaking: false, autoHide: false, variant: "thinking" });
  window.clearTimeout(thinkingTimeoutTimer);
  thinkingTimeoutTimer = window.setTimeout(() => {
    clearThinkingState();
  }, THINKING_TIMEOUT_MS);
}

function clearThinkingState() {
  window.clearTimeout(thinkingTimeoutTimer);
  thinkingTimeoutTimer = null;
  if (thinkingPoseHandle) {
    naturalMotion.stopGesturePose(thinkingPoseHandle, { fadeOutMs: 600 });
    thinkingPoseHandle = null;
  }
  if (subtitle.currentText === "…") {
    subtitle.hide(0);
  }
}

function maybeCompleteFrontendPlayback(flowId, detail, metadata = {}, status = "ok") {
  if (!pendingSynthComplete) {
    postFrontendAction("complete", "running", "waiting for backend synth complete", {
      active_audio: activeAudioPlaybackCount,
      queued_audio: audioPlaybackQueue.length,
      awaiting_payload: awaitingPlaybackPayload,
    }, flowId);
    return false;
  }
  if (
    activeAudioPlaybackCount <= 0 &&
    !awaitingPlaybackPayload &&
    !audioQueuePlaying &&
    audioPlaybackQueue.length <= 0
  ) {
    completeFrontendPlayback(flowId, detail, metadata, status);
    return true;
  }
  postFrontendAction("complete", "running", "waiting for browser audio playback", {
    active_audio: activeAudioPlaybackCount,
    queued_audio: audioPlaybackQueue.length,
    awaiting_payload: awaitingPlaybackPayload,
  }, flowId);
  return false;
}

function completeFrontendPlayback(flowId, detail, metadata = {}, status = "ok") {
  if (flowId && completedPlaybackFlowId === flowId) return;
  pendingSynthComplete = false;
  awaitingPlaybackPayload = false;
  hasPlayedAudioThisTurn = false;
  subtitle.setSpeaking(false);
  subtitle.hide(1800);
  send({
    type: "frontend-playback-complete",
    flow_id: flowId || "",
    flow: flowId ? { id: flowId } : {},
    status,
    detail,
    has_audio: metadata.has_audio === true,
    metadata,
  });
  postFrontendAction("complete", status, detail, metadata, flowId);
  if (flowId) completedPlaybackFlowId = flowId;
}

async function refreshStatus() {
  try {
    const response = await fetch("/rikka/overlay/status");
    const payload = await response.json();
    if (payload.settings) {
      applyOverlaySettings(payload.settings);
    }
    els.captureState.textContent =
      (payload.capture && payload.capture.status) || "unknown";
    const audio = payload.privacy && payload.privacy.audio;
    if (!micStream) {
      els.wakeState.textContent = audio && audio.wake_gate_enabled ? "wake" : "off";
    }
  } catch (_error) {
    els.captureState.textContent = "unknown";
  }
}

function applyOverlaySettings(settings) {
  asrHudSavedVisible = settings.asr_hud_visible !== false;
  renderAsrHud();
  if (!dockLayoutDrag) {
    applyDockLayout({
      mode: settings.dock_layout_mode || "corner",
      left: settings.dock_left_px,
      top: settings.dock_top_px,
    });
  }
  subtitle.setEnabled(settings.subtitle_visible !== false);
  naturalMotion.configurePointer(settings);
  globalPointerEnabled = settings.global_pointer_tracking_enabled !== false;
  if (!globalPointerEnabled) naturalMotion.setGlobalPointer(null);
  const anchor = settings.subtitle_anchor || "bottom_left";
  els.subtitleStage.dataset.anchor = anchor;
  els.subtitleStage.dataset.layoutMode = settings.subtitle_layout_mode || "anchor";
  document.documentElement.style.setProperty(
    "--subtitle-max-width",
    `${settings.subtitle_max_width_px || 520}px`
  );
  document.documentElement.style.setProperty(
    "--subtitle-offset-x",
    `${settings.subtitle_offset_x_px || 44}px`
  );
  document.documentElement.style.setProperty(
    "--subtitle-offset-y",
    `${settings.subtitle_offset_y_px || 96}px`
  );
  applySubtitleLayout(
    {
      mode: settings.subtitle_layout_mode === "free" ? "free" : "anchor",
      left: settings.subtitle_left_px || SUBTITLE_LAYOUT_DEFAULT.left,
      top: settings.subtitle_top_px || SUBTITLE_LAYOUT_DEFAULT.top,
      width: settings.subtitle_width_px || settings.subtitle_max_width_px || 520,
    },
    { persist: false }
  );
}

async function refreshGlobalPointer() {
  if (!globalPointerEnabled) return;
  if (performance.now() < pointerBackoffUntil) return;
  try {
    const response = await fetch("/rikka/overlay/pointer", { cache: "no-store" });
    const payload = await response.json();
    const pointer = payload.pointer;
    if (naturalMotion.setGlobalPointer(pointerWithRelativeGaze(pointer))) return;
    const status = pointer && pointer.status;
    pointerBackoffUntil =
      performance.now() + (status === "disabled" || status === "unavailable" ? 3000 : 900);
  } catch (_error) {
    naturalMotion.setGlobalPointer(null);
    pointerBackoffUntil = performance.now() + 1500;
  }
}

async function toggleMic() {
  if (micStream) {
    stopMic(true);
    return;
  }
  try {
    micSampleCount = 0;
    setAsrStatus("recording", {
      detail: "Recording microphone; click Mic again to transcribe",
      autoHide: false,
    });
    audioContext = new AudioContext();
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    send({
      type: "mic-owner-request",
      client_kind: "overlay",
      always_on_enabled: true,
      mic_permission: "granted",
      listening: true,
      explicit_owner: true,
      reason: "overlay_manual_mic",
    });
    micSource = audioContext.createMediaStreamSource(micStream);
    micNode = audioContext.createScriptProcessor(4096, 1, 1);
    micNode.onaudioprocess = (event) => {
      if (micOwnerUid && micOwnerUid !== clientUid) return;
      const input = event.inputBuffer.getChannelData(0);
      micSampleCount += input.length;
      send({
        type: "mic-audio-data",
        audio: Array.from(input),
        sample_rate: event.inputBuffer.sampleRate || audioContext.sampleRate || 16000,
      });
    };
    micSource.connect(micNode);
    micNode.connect(audioContext.destination);
    els.mic.dataset.active = "true";
    els.wakeState.textContent = "recording";
  } catch (_error) {
    els.wakeState.textContent = "mic denied";
    setAsrStatus("error", {
      detail: "Browser microphone permission was denied or unavailable",
      autoHide: false,
    });
    send({
      type: "client-capabilities",
      client_kind: "overlay",
      always_on_enabled: false,
      mic_permission: "denied_or_unavailable",
      listening: false,
      reason: "overlay_mic_denied",
    });
    stopMic(false);
  }
}

function stopMic(submit) {
  if (micNode) micNode.disconnect();
  if (micSource) micSource.disconnect();
  if (micStream) micStream.getTracks().forEach((track) => track.stop());
  if (audioContext) audioContext.close().catch(() => {});
  micNode = null;
  micSource = null;
  micStream = null;
  audioContext = null;
  els.mic.dataset.active = "false";
  if (submit) {
    setAsrStatus("transcribing", {
      detail: micSampleCount > 0
        ? `Captured ${micSampleCount} samples; waiting for ASR`
        : "No microphone samples captured before submit",
      autoHide: false,
    });
    send({ type: "mic-audio-end" });
  }
  send({ type: "mic-owner-release", reason: submit ? "manual_submit" : "stopped" });
  micSampleCount = 0;
}

function switchConfig() {
  const file = els.configSelect.value;
  if (!file || file === currentConfigFile) return;
  currentConfigFile = file;
  els.modelState.textContent = "switching";
  send({ type: "switch-config", file });
}

function bindUi() {
  els.dockToggle.addEventListener("pointerdown", beginDockLayoutDrag);
  if (els.dockDragHandle) {
    els.dockDragHandle.addEventListener("pointerdown", beginDockLayoutDrag);
  }
  els.dockToggle.addEventListener("click", (event) => {
    if (dockSuppressToggleClick) {
      dockSuppressToggleClick = false;
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    const open = els.dock.dataset.open === "true";
    els.dock.dataset.open = open ? "false" : "true";
  });
  if (els.hudToggle) {
    els.hudToggle.addEventListener("click", toggleAsrHudSessionVisibility);
  }
  if (els.resetDockPosition) {
    els.resetDockPosition.addEventListener("click", resetDockLayout);
  }
  els.connect.addEventListener("click", connect);
  els.mic.addEventListener("click", toggleMic);
  els.switchConfig.addEventListener("click", switchConfig);
  els.modelScale.addEventListener("input", () => {
    updateModelLayoutField("scale", els.modelScale.value);
  });
  els.modelX.addEventListener("input", () => {
    updateModelLayoutField("x", els.modelX.value);
  });
  els.modelY.addEventListener("input", () => {
    updateModelLayoutField("y", els.modelY.value);
  });
  els.resetModelLayout.addEventListener("click", () => {
    setModelLayout({ ...MODEL_LAYOUT_DEFAULT });
  });
  subtitle.root.addEventListener("pointerdown", (event) => {
    if (event.target === els.subtitleResizeHandle) return;
    beginSubtitleLayoutDrag(event, "move");
  });
  if (els.subtitleResizeHandle) {
    els.subtitleResizeHandle.addEventListener("pointerdown", (event) => {
      beginSubtitleLayoutDrag(event, "resize");
    });
  }
  window.addEventListener("pointermove", handleDockLayoutMove, true);
  window.addEventListener("pointerup", finishDockLayoutDrag, true);
  window.addEventListener("pointercancel", finishDockLayoutDrag, true);
  window.addEventListener("blur", () => finishDockLayoutDrag(null), true);
  window.addEventListener("pointermove", handleSubtitleLayoutMove, true);
  window.addEventListener("pointerup", finishSubtitleLayoutDrag, true);
  window.addEventListener("pointercancel", finishSubtitleLayoutDrag, true);
  window.addEventListener("blur", () => finishSubtitleLayoutDrag(null), true);
  window.addEventListener("resize", () => {
    if (dockLayout.mode === "free") applyDockLayout(dockLayout, { persist: true });
    if (subtitleLayout.mode === "free") applySubtitleLayout(subtitleLayout, { persist: true });
  });
}

function attachLive2DAdapter(adapter) {
  if (!adapter) return;
  live2dController.attach(adapter);
  naturalMotion.attach(adapter);
  els.motionState.textContent = "ready";
}

function updateRuntimeModel(modelInfo) {
  if (!modelInfo || typeof runtime.setModelInfo !== "function") return;
  modelGestureMap = modelInfo.gestureMap && typeof modelInfo.gestureMap === "object"
    ? modelInfo.gestureMap
    : null;
  runtime
    .setModelInfo(modelInfo)
    .then((adapter) => attachLive2DAdapter(adapter))
    .catch((error) => {
      console.warn("[RikkaOverlay] failed to switch Live2D model", error);
      els.motionState.textContent = "unavailable";
    });
}

async function boot() {
  bindUi();
  applyModelLayout({ persist: false });
  refreshStatus();
  window.setInterval(refreshStatus, 5000);
  window.setInterval(refreshGlobalPointer, GLOBAL_POINTER_POLL_INTERVAL_MS);
  const adapter = await runtime.load();
  attachLive2DAdapter(adapter);
  connect();
}

window.addEventListener("beforeunload", () => stopMic(false));
window.RikkaOverlay = {
  subtitle,
  naturalMotion,
  runtime,
  live2dController,
};
boot();
