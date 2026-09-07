const VENDOR_SCRIPTS = [
  "/overlay/vendor/live2dcubismcore.min.js",
  "/overlay/vendor/rikka-lapp-runtime.js",
];

const DEFAULT_MODEL_INFO = {
  name: "rikka_mikazuki",
  description: "Local prepared Yayotsuki Rikka Live2D model.",
  url: "/live2d-models/rikka_mikazuki/rikka_mikazuki.model3.json",
  kScale: 0.28,
  initialXshift: 0,
  initialYshift: 0,
  kXOffset: 1150,
  idleMotionGroupName: "Idle",
  scrollToResize: false,
  pointerInteractive: true,
};

function normalizeUrl(url) {
  try {
    return new URL(url || DEFAULT_MODEL_INFO.url, location.origin).href;
  } catch (_error) {
    return new URL(DEFAULT_MODEL_INFO.url, location.origin).href;
  }
}

function normalizeModelInfo(modelInfo = {}) {
  return {
    ...DEFAULT_MODEL_INFO,
    ...(modelInfo || {}),
    url: normalizeUrl(modelInfo.url || DEFAULT_MODEL_INFO.url),
    scrollToResize: false,
    pointerInteractive: true,
  };
}

export class Live2DRuntime {
  constructor({ onStatus } = {}) {
    this.onStatus = onStatus || (() => {});
    this.adapter = null;
    this.loadingPromise = null;
    this.resizeHandler = null;
  }

  async load() {
    if (this.adapter) return this.adapter;
    if (this.loadingPromise) return this.loadingPromise;
    this.loadingPromise = this.loadOwnedRuntime().finally(() => {
      this.loadingPromise = null;
    });
    return this.loadingPromise;
  }

  async loadOwnedRuntime() {
    this.onStatus("loading");
    this.seedOverlayDefaults();
    this.installTransparentCanvasShim();
    this.ensureCanvas();
    try {
      await this.loadVendorScripts();
      const runtime = this.getRuntime();
      this.adapter = this.wrapAdapter(runtime.initialize(this.readModelInfo()));
      this.disableTapReactions();
      this.installAdapterGlobals();
      this.installResizeHandler();
      this.onStatus(this.adapter ? "ready" : "unavailable");
      return this.adapter;
    } catch (error) {
      console.error("[RikkaLive2D] failed to load LApp runtime", error);
      this.onStatus("unavailable");
      return null;
    }
  }

  async setModelInfo(modelInfo) {
    const normalized = normalizeModelInfo(modelInfo);
    try {
      localStorage.setItem("modelInfo", JSON.stringify(normalized));
    } catch (_error) {
      // Keep loading even if local storage is unavailable.
    }
    const adapter = this.adapter || (await this.load());
    if (!adapter) return null;
    this.getRuntime().setModelInfo(normalized);
    this.adapter = this.wrapAdapter(this.getRuntime().getAdapter());
    this.disableTapReactions();
    this.installAdapterGlobals();
    return this.adapter;
  }

  seedOverlayDefaults() {
    const wsScheme = location.protocol === "https:" ? "wss" : "ws";
    try {
      localStorage.setItem("baseUrl", JSON.stringify(location.origin));
      localStorage.setItem("wsUrl", JSON.stringify(`${wsScheme}://${location.host}/client-ws`));
      const current = this.readModelInfo({ allowDefault: false });
      const next = current && current.name && current.url && !current.url.includes("undefined")
        ? current
        : DEFAULT_MODEL_INFO;
      localStorage.setItem("modelInfo", JSON.stringify(normalizeModelInfo(next)));
    } catch (_error) {
      localStorage.setItem("modelInfo", JSON.stringify(normalizeModelInfo(DEFAULT_MODEL_INFO)));
    }
  }

  readModelInfo({ allowDefault = true } = {}) {
    try {
      const raw = localStorage.getItem("modelInfo");
      const parsed = raw ? JSON.parse(raw) : null;
      if (parsed && typeof parsed === "object") return normalizeModelInfo(parsed);
    } catch (_error) {
      // Fall through to the default model.
    }
    return allowDefault ? normalizeModelInfo(DEFAULT_MODEL_INFO) : null;
  }

  ensureCanvas() {
    const host = document.getElementById("root");
    if (!host) throw new Error("Overlay Live2D host #root is missing.");
    let canvas = document.getElementById("canvas");
    if (!canvas) {
      host.textContent = "";
      canvas = document.createElement("canvas");
      canvas.id = "canvas";
      canvas.setAttribute("aria-label", "Rikka Live2D canvas");
      host.appendChild(canvas);
    }
    canvas.width = Math.max(1, Math.round(window.innerWidth * (window.devicePixelRatio || 1)));
    canvas.height = Math.max(1, Math.round(window.innerHeight * (window.devicePixelRatio || 1)));
    return canvas;
  }

  installTransparentCanvasShim() {
    if (
      window.HTMLCanvasElement &&
      !window.HTMLCanvasElement.prototype.__rikkaTransparentGetContext
    ) {
      const nativeGetContext = window.HTMLCanvasElement.prototype.getContext;
      window.HTMLCanvasElement.prototype.getContext = function getContext(type, attributes) {
        const isWebGl = type === "webgl" || type === "webgl2" || type === "experimental-webgl";
        const nextAttributes = isWebGl
          ? { ...(attributes || {}), alpha: true, premultipliedAlpha: true }
          : attributes;
        const context = nativeGetContext.call(this, type, nextAttributes);
        if (isWebGl && context && !context.__rikkaTransparentClear) {
          const nativeClearColor = context.clearColor.bind(context);
          context.clearColor = function clearColor(red, green, blue, alpha) {
            if (red === 0 && green === 0 && blue === 0 && alpha === 1) {
              return nativeClearColor(0, 0, 0, 0);
            }
            return nativeClearColor(red, green, blue, alpha);
          };
          context.__rikkaTransparentClear = true;
        }
        return context;
      };
      window.HTMLCanvasElement.prototype.__rikkaTransparentGetContext = true;
    }
    const patch = (Context) => {
      if (!Context || !Context.prototype || Context.prototype.__rikkaTransparentClear) {
        return;
      }
      const nativeClearColor = Context.prototype.clearColor;
      Context.prototype.clearColor = function clearColor(red, green, blue, alpha) {
        if (red === 0 && green === 0 && blue === 0 && alpha === 1) {
          return nativeClearColor.call(this, 0, 0, 0, 0);
        }
        return nativeClearColor.call(this, red, green, blue, alpha);
      };
      Context.prototype.__rikkaTransparentClear = true;
    };
    patch(window.WebGLRenderingContext);
    patch(window.WebGL2RenderingContext);
  }

  async loadVendorScripts() {
    for (const src of VENDOR_SCRIPTS) {
      await this.appendScript(src);
    }
    if (!window.Live2DCubismCore) {
      throw new Error("Live2D Cubism Core did not register.");
    }
    if (!window.RikkaLAppRuntime) {
      throw new Error("Rikka LApp runtime did not register.");
    }
  }

  getRuntime() {
    const runtime = window.RikkaLAppRuntime;
    if (!runtime || typeof runtime.initialize !== "function") {
      throw new Error("Rikka LApp runtime is unavailable.");
    }
    return runtime;
  }

  wrapAdapter(adapter) {
    if (!adapter) return null;
    if (adapter.__rikkaOverlayAdapter) return adapter;

    const wrapper = Object.create(adapter);
    Object.defineProperties(wrapper, {
      __rikkaOverlayAdapter: { value: true },
      __rikkaRawAdapter: { value: adapter },
    });

    wrapper.getCanvas = () => document.getElementById("canvas");
    wrapper.getMgr = () => {
      if (typeof adapter.getMgr === "function") return adapter.getMgr();
      if (typeof window.getLive2DManager === "function") return window.getLive2DManager();
      return null;
    };
    wrapper.getModel = () => {
      if (typeof adapter.getModel === "function") return adapter.getModel();
      const manager = wrapper.getMgr();
      return manager && typeof manager.getModel === "function" ? manager.getModel(0) : null;
    };
    wrapper.getIdManager = () => {
      if (typeof adapter.getIdManager === "function") return adapter.getIdManager();
      const framework = window.Live2DCubismFramework;
      const cubismFramework = framework && framework.CubismFramework;
      return cubismFramework && typeof cubismFramework.getIdManager === "function"
        ? cubismFramework.getIdManager()
        : null;
    };
    wrapper.startMotion = (group, index, priority, onFinishedMotionHandler) => {
      if (typeof adapter.startMotion === "function") {
        return adapter.startMotion(group, index, priority, onFinishedMotionHandler);
      }
      const model = wrapper.getModel();
      return model && typeof model.startMotion === "function"
        ? model.startMotion(group, index, priority, onFinishedMotionHandler)
        : -1;
    };
    wrapper.setLipSyncValue = (value) => {
      if (typeof adapter.setLipSyncValue === "function") {
        adapter.setLipSyncValue(value);
        return true;
      }
      const model = wrapper.getModel();
      if (model && typeof model.setExternalLipSyncValue === "function") {
        model.setExternalLipSyncValue(value);
        return true;
      }
      return false;
    };
    wrapper.setEyeBlinkValue = (value) => {
      if (typeof adapter.setEyeBlinkValue === "function") {
        adapter.setEyeBlinkValue(value);
        return true;
      }
      const model = wrapper.getModel();
      if (model && typeof model.setExternalEyeBlinkValue === "function") {
        model.setExternalEyeBlinkValue(value);
        return true;
      }
      return false;
    };

    return wrapper;
  }

  disableTapReactions() {
    // Tap reactions are disabled by product decision: head-tap random expressions
    // and body-tap random motions must never fire. Patch the vendor manager class
    // prototype (exposed by the runtime, vendor file untouched) so every manager
    // instance — including ones recreated on model switch — dispatches taps as a
    // no-op. Press/drag positioning is unaffected: it flows through onDrag, not onTap.
    const managerClass = window.LAppLive2DManager;
    const proto = managerClass && managerClass.prototype;
    if (!proto || typeof proto.onTap !== "function" || proto.__rikkaTapReactionsDisabled) {
      return;
    }
    proto.onTap = () => {};
    proto.__rikkaTapReactionsDisabled = true;
  }

  installAdapterGlobals() {
    const runtime = this.getRuntime();
    window.RikkaLive2DAdapter = this.adapter;
    window.getLAppAdapter = () => this.adapter || this.wrapAdapter(runtime.getAdapter());
    if (typeof window.getLive2DManager !== "function") {
      window.getLive2DManager = () => {
        const adapter = this.adapter || this.wrapAdapter(runtime.getAdapter());
        return adapter && typeof adapter.getMgr === "function" ? adapter.getMgr() : null;
      };
    }
  }

  installResizeHandler() {
    if (this.resizeHandler) return;
    this.resizeHandler = () => {
      this.ensureCanvas();
      const delegate = window.LAppDelegate;
      if (delegate && typeof delegate.getInstance === "function") {
        delegate.getInstance().onResize();
      }
    };
    window.addEventListener("resize", this.resizeHandler);
  }

  appendScript(src) {
    return new Promise((resolve, reject) => {
      const absoluteSrc = new URL(src, location.origin).href;
      if ([...document.scripts].some((script) => script.src === absoluteSrc)) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`failed to load ${src}`));
      document.head.appendChild(script);
    });
  }
}

window.RikkaLive2DRuntime = Live2DRuntime;
