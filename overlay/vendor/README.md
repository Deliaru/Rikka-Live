# Overlay Live2D Vendor Assets

These browser assets are intentionally vendored so `/overlay/` can render Live2D
models without loading the inherited Open-LLM-VTuber frontend bundle.

## Files

- `live2dcubismcore.min.js`
  - Source: copied from the previously inherited frontend runtime asset at
    `app/frontend/libs/live2dcubismcore.min.js`
  - Upstream owner: Live2D Inc.
  - License: Live2D Cubism Core / proprietary redistributable runtime license.

- `rikka-lapp-runtime.js`
  - Source: bundled from the previously inherited Open-LLM-VTuber WebSDK LApp
    runtime under `app/frontend/src/renderer/WebSDK` at `origin/main`.
  - Upstream: https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web
  - License: follows the upstream project and bundled Live2D Cubism SDK/runtime
    license terms.
  - Status: active Overlay runtime. This preserves the old LApp
    `LAppLive2DManager.onDrag -> LAppModel.setDragging -> CubismTargetPoint`
    mouse-tracking path inside a project-owned vendor file.

Do not replace these with CDN script tags at runtime; OBS overlay startup should
remain local and deterministic.
