import unittest
from pathlib import Path


class OverlayOwnedRuntimeTests(unittest.TestCase):
    def test_overlay_runtime_uses_owned_vendor_assets(self):
        runtime = Path("overlay/live2d-runtime.js").read_text(encoding="utf-8")

        self.assertIn("/overlay/vendor/live2dcubismcore.min.js", runtime)
        self.assertIn("/overlay/vendor/rikka-lapp-runtime.js", runtime)
        self.assertNotIn("/overlay/vendor/pixi.min.js", runtime)
        self.assertNotIn("/overlay/vendor/pixi-live2d-display.cubism4.min.js", runtime)
        self.assertNotIn("fetchFrontendManifest", runtime)
        self.assertNotRegex(runtime, r"fetch\(\s*['\"]\/['\"]")
        self.assertNotIn("/assets/main-", runtime)
        self.assertNotIn("loadLegacyHost", runtime)
        self.assertIn("wrapAdapter", runtime)
        self.assertIn("wrapper.getCanvas", runtime)
        self.assertIn("window.getLAppAdapter", runtime)

    def test_overlay_runtime_preserves_lapp_drag_smoothing(self):
        runtime = Path("overlay/vendor/rikka-lapp-runtime.js").read_text(encoding="utf-8")

        self.assertIn("CubismTargetPoint", runtime)
        self.assertIn("var FrameRate = 30", runtime)
        self.assertIn("const faceParamMaxV = 40 / 10", runtime)
        self.assertIn("const timeToMaxSpeed = 0.15", runtime)
        self.assertIn("this._dragManager = new CubismTargetPoint()", runtime)
        self.assertIn("setDragging(x, y)", runtime)
        self.assertIn("this._dragManager.update(deltaTimeSeconds)", runtime)
        self.assertIn("this._dragX = this._dragManager.getX()", runtime)
        self.assertIn(
            "this._model.addParameterValueById(this._idParamAngleX, this._dragX * 30)",
            runtime,
        )
        self.assertIn(
            "this._model.addParameterValueById(this._idParamAngleY, this._dragY * 30)",
            runtime,
        )
        self.assertIn("this._dragX * this._dragY * -30", runtime)
        self.assertIn("this._idParamBodyAngleX", runtime)
        self.assertIn(
            "this._model.addParameterValueById(this._idParamEyeBallX, this._dragX)",
            runtime,
        )
        self.assertIn(
            "this._model.addParameterValueById(this._idParamEyeBallY, this._dragY)",
            runtime,
        )
        self.assertIn("model.setDragging(x, y)", runtime)
        self.assertNotIn("focusController.focus", runtime)
        self.assertNotIn("requestAnimationFrame((now) => this.tickDrag(now))", runtime)
        self.assertNotIn("DRAG_RESPONSE_MS", runtime)

    def test_global_pointer_tracking_keeps_legacy_polling_path(self):
        motion = Path("overlay/live2d-natural-motion.js").read_text(encoding="utf-8")
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")

        self.assertIn("naturalMotion.configurePointer(settings)", overlay)
        self.assertIn("MODEL_POINTER_GAZE_MAX = 0.8", overlay)
        self.assertIn('mode: "natural_layered"', motion)
        self.assertIn("POINTER_DRAG_MAX = 0.8", motion)
        self.assertIn("function clampPointerDrag", motion)
        self.assertIn('this.pointerConfig.mode === "classic_lapp"', motion)
        self.assertIn('this.pointerConfig.mode === "off"', motion)
        self.assertIn("this.applyLayeredNativeDrag(", motion)
        self.assertIn("if (performance.now() < this.globalPointerActiveUntil) return;", motion)
        self.assertIn("this.globalPointerActiveUntil = performance.now() + 520", motion)
        self.assertIn("GLOBAL_POINTER_POLL_INTERVAL_MS = 160", overlay)
        self.assertIn("relativeGlobalPointerGaze(pointer)", overlay)
        self.assertIn("relativeClientPointerGaze(clientX, clientY)", overlay)
        self.assertIn("viewFromPrimaryPointer(pointer)", overlay)
        self.assertIn('pointer.coordinate_space !== "primary_screen"', overlay)
        self.assertIn("pointerWithRelativeGaze(pointer)", overlay)
        self.assertIn("naturalMotion.setGlobalPointer(pointerWithRelativeGaze(pointer))", overlay)
        self.assertIn("this.nativeDrag.relativeClientPointerGaze", motion)
        self.assertIn("const relativeX = Number(pointer.relative_x)", motion)
        self.assertIn("const relativeY = Number(pointer.relative_y)", motion)
        self.assertIn("max: POINTER_DRAG_MAX", motion)
        self.assertIn("{ max: POINTER_DRAG_MAX }", motion)
        self.assertIn("{ max: MODEL_POINTER_GAZE_MAX }", overlay)
        self.assertNotIn("clientX < rect.left - margin", overlay)
        self.assertNotIn("clientX > rect.right + margin", overlay)
        self.assertIn(
            "window.setInterval(refreshGlobalPointer, GLOBAL_POINTER_POLL_INTERVAL_MS)",
            overlay,
        )
        self.assertNotIn("GlobalPointerInterpolator", overlay)
        self.assertNotIn("PREDICTION", overlay)
        self.assertNotIn("hasLocalPointerPriority", motion)
        self.assertNotIn("applyGlobalPointerSample", overlay)
        self.assertNotIn("setGlobalPointerTakeoverEnabled", overlay)
        self.assertNotIn("setInterval(refreshGlobalPointer, 48)", overlay)

    def test_overlay_audio_playback_uses_browser_clock_for_subtitles_and_lip_sync(self):
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")
        motion = Path("overlay/live2d-natural-motion.js").read_text(encoding="utf-8")

        self.assertIn("response received; waiting for audio payload", overlay)
        self.assertIn("payload.speak === false", overlay)
        self.assertIn("awaitingPlaybackPayload", overlay)
        self.assertIn("audioPlaybackQueue", overlay)
        self.assertIn("function playNextAudioPayload", overlay)
        self.assertIn("function playQueuedAudioPayload", overlay)
        self.assertIn("audioPlaybackQueue.push({ payload, flowId })", overlay)
        self.assertIn("if (audioPlaybackQueue.length > 0)", overlay)
        self.assertIn("!audioQueuePlaying", overlay)
        self.assertIn("naturalMotion.playAudioLipSync(audio", overlay)
        self.assertIn("lip_sync_source", overlay)
        self.assertIn('"browser_audio_rms"', motion)
        self.assertIn('"payload_volumes_fallback"', motion)
        self.assertIn("audio.currentTime", motion)
        self.assertIn("naturalMotion.stopLipSync()", overlay)
        self.assertIn("this.applyNativeLipSync(this.mouth)", motion)
        self.assertIn("MOUTH_VOLUME_GAIN = 0.7", motion)
        self.assertIn("MOUTH_VOLUME_MAX = 0.84", motion)
        self.assertIn("const nativeLipSyncApplied = this.applyNativeLipSync(this.mouth)", motion)
        self.assertIn("if (!nativeLipSyncApplied) this.setParameter(\"ParamMouthOpenY\", this.mouth);", motion)
        self.assertIn("const blink = this.blinkValue(now)", motion)
        self.assertIn("const nativeBlinkApplied = this.applyNativeBlink(blink)", motion)
        self.assertIn("if (!nativeBlinkApplied)", motion)
        self.assertIn("applyNativeBlink(value)", motion)
        self.assertNotIn("hasNativeEyeBlink()", motion)
        self.assertIn(
            "wrapper.setLipSyncValue",
            Path("overlay/live2d-runtime.js").read_text(encoding="utf-8"),
        )
        self.assertIn(
            "wrapper.setEyeBlinkValue",
            Path("overlay/live2d-runtime.js").read_text(encoding="utf-8"),
        )
        self.assertIn('postFrontendAction("complete", status', overlay)
        self.assertIn('type: "frontend-playback-complete"', overlay)
        self.assertIn("flow_id: flowId || \"\"", overlay)
        self.assertIn("status,", overlay)
        self.assertIn("has_audio: metadata.has_audio === true", overlay)
        self.assertIn("function maybeCompleteFrontendPlayback", overlay)
        self.assertIn("maybeCompleteFrontendPlayback(flowId, \"frontend playback complete\"", overlay)
        self.assertIn("waiting for backend synth complete", overlay)
        self.assertIn("}, status);", overlay)
        self.assertNotIn('naturalMotion.playVolumes(payload.volumes || [], payload.slice_length || 20);', overlay)

    def test_overlay_uses_separate_layer_for_mood_idle_expression(self):
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")
        motion = Path("overlay/live2d-natural-motion.js").read_text(encoding="utf-8")

        self.assertIn("actions.mood_idle_expression", overlay)
        self.assertIn('startParameterLayer("mood_idle_expression"', overlay)
        self.assertIn("mood_idle_expression: 35", motion)
        self.assertIn('excludeParameters: ["ParamMouthForm"]', motion)
        self.assertIn('includeParameters: ["ParamMouthForm"]', motion)
        self.assertIn("function suspendMoodIdleExpression", overlay)
        self.assertIn("applyMoodIdleExpression();", overlay)

    def test_console_mic_level_does_not_rebuild_logs_on_every_audio_frame(self):
        always_on = Path("web_tool/rikka/always_on.js").read_text(encoding="utf-8")
        render = Path("web_tool/rikka/render.js").read_text(encoding="utf-8")

        self.assertIn("function setMicLevel(level)", always_on)
        self.assertIn("now - lastLevelRenderAt < 250", always_on)
        self.assertIn("setMicLevel(level)", always_on)
        self.assertNotIn("setMicState({ audioLevel: level })", always_on)
        self.assertIn('if (state.view !== "logs") return;', render)

    def test_overlay_surfaces_asr_recording_transcript_and_wake_feedback(self):
        html = Path("overlay/index.html").read_text(encoding="utf-8")
        css = Path("overlay/overlay.css").read_text(encoding="utf-8")
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")

        self.assertIn('id="asr-hud"', html)
        self.assertIn('id="hud-toggle"', html)
        self.assertIn('id="asr-state"', html)
        self.assertIn('id="asr-transcript"', html)
        self.assertIn(".asr-hud", css)
        self.assertIn("function setAsrStatus", overlay)
        self.assertIn("function effectiveAsrHudVisible", overlay)
        self.assertIn("function toggleAsrHudSessionVisibility", overlay)
        self.assertIn("asrHudSavedVisible = settings.asr_hud_visible !== false", overlay)
        self.assertIn("asrHudSessionOverride = !effectiveAsrHudVisible()", overlay)
        self.assertIn('case "user-input-transcription"', overlay)
        self.assertIn('case "wake-gate"', overlay)
        self.assertIn('"transcribing"', overlay)
        self.assertIn("micSampleCount", overlay)
        self.assertIn("sample_rate", overlay)

    def test_overlay_dock_position_controls_are_persistent_and_clamped(self):
        html = Path("overlay/index.html").read_text(encoding="utf-8")
        css = Path("overlay/overlay.css").read_text(encoding="utf-8")
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")

        self.assertIn('id="dock-drag-handle"', html)
        self.assertIn('id="reset-dock-position"', html)
        self.assertIn('.overlay-dock[data-layout-mode="free"]', css)
        self.assertIn("--dock-left", css)
        self.assertIn("--dock-top", css)
        self.assertIn("function normalizeDockLayout", overlay)
        self.assertIn("function saveDockLayout", overlay)
        self.assertIn('dock_layout_mode: "free"', overlay)
        self.assertIn('dock_layout_mode: "corner"', overlay)
        self.assertIn("DOCK_REACHABLE_MARGIN_PX", overlay)
        self.assertIn("beginDockLayoutDrag", overlay)
        self.assertIn("handleDockLayoutMove", overlay)
        self.assertIn("resetDockLayout", overlay)
        self.assertIn("event.stopPropagation()", overlay)

    def test_overlay_registers_microphone_owner_protocol(self):
        overlay = Path("overlay/overlay.js").read_text(encoding="utf-8")

        self.assertIn('"client-capabilities"', overlay)
        self.assertIn('"mic-owner-request"', overlay)
        self.assertIn('"mic-owner-release"', overlay)
        self.assertIn('"asr-owner-state"', overlay)
        self.assertIn('"asr-streaming-partial"', overlay)
        self.assertIn("micOwnerUid", overlay)

    def test_owned_lapp_runtime_exposes_browser_lip_sync_bridge(self):
        runtime = Path("overlay/vendor/rikka-lapp-runtime.js").read_text(encoding="utf-8")

        self.assertIn("_externalLipSyncValue", runtime)
        self.assertIn("setExternalLipSyncValue(value)", runtime)
        self.assertIn("setLipSyncValue(value)", runtime)
        self.assertIn("Number.isFinite(this._externalLipSyncValue) ? 1 : 4", runtime)
        lip_sync_start = runtime.index("if (this._lipsync) {")
        self.assertLess(
            runtime.index("if (Number.isFinite(this._externalLipSyncValue))", lip_sync_start),
            runtime.index("this._model.update();", lip_sync_start),
        )

    def test_owned_lapp_runtime_exposes_natural_blink_bridge(self):
        runtime = Path("overlay/vendor/rikka-lapp-runtime.js").read_text(encoding="utf-8")

        self.assertIn("_externalEyeBlinkValue", runtime)
        self.assertIn("setExternalEyeBlinkValue(value)", runtime)
        self.assertIn("setEyeBlinkValue(value)", runtime)
        self.assertIn("if (Number.isFinite(this._externalEyeBlinkValue))", runtime)
        self.assertIn("this._model.setParameterValueById(this._eyeBlinkIds.at(i), value)", runtime)

    def test_cubism_update_hook_applies_lip_sync_before_core_drawable_update(self):
        motion = Path("overlay/live2d-natural-motion.js").read_text(encoding="utf-8")
        hook_start = motion.index("installCubismUpdateHook()")
        wrapper_start = motion.index("cubismModel.update = (...args) => {", hook_start)
        wrapper_end = motion.index("cubismModel.__rikkaNaturalCoreHooked = true;", wrapper_start)
        wrapper = motion[wrapper_start:wrapper_end]

        self.assertLess(
            wrapper.index("controller.updateMotionFrame(performance.now());"),
            wrapper.index("return originalUpdate(...args);"),
        )
        self.assertNotIn("const result = originalUpdate(...args);", wrapper)

    def test_overlay_host_is_project_owned(self):
        html = Path("overlay/index.html").read_text(encoding="utf-8")
        css = Path("overlay/overlay.css").read_text(encoding="utf-8")

        self.assertIn('class="live2d-host"', html)
        self.assertNotIn("legacy-live2d-host", html)
        self.assertIn(".live2d-host canvas", css)
        self.assertNotIn("legacy-live2d-host", css)

    def test_console_opens_overlay_route(self):
        console_js = Path("web_tool/rikka.js").read_text(encoding="utf-8")
        console_html = Path("web_tool/rikka.html").read_text(encoding="utf-8")

        self.assertIn('window.open("/overlay/"', console_js)
        self.assertNotRegex(console_js, r"window\.open\(\s*['\"]\/['\"]")
        self.assertIn("打开 Overlay", console_html)

    def test_console_provider_menus_preserve_current_unknown_values(self):
        settings_js = Path("web_tool/rikka/settings.js").read_text(encoding="utf-8")

        self.assertIn("withCurrentOption(llm.available_providers", settings_js)
        self.assertIn("withCurrentOption(selectValues(ids.ttsProvider)", settings_js)
        self.assertIn("withCurrentOption(asr.available_providers", settings_js)
        self.assertIn("withCurrentOption(multimodalProviderOptions", settings_js)
        self.assertIn("providerPatchValue(", settings_js)
        self.assertIn("if (llmProvider) patch.llm.provider = llmProvider", settings_js)
        self.assertIn("if (state.config?.asr && asrProvider)", settings_js)
        self.assertIn("function selectValues(id)", settings_js)

    def test_console_exposes_rikka_prompt_editors(self):
        console_html = Path("web_tool/rikka.html").read_text(encoding="utf-8")
        settings_js = Path("web_tool/rikka/settings.js").read_text(encoding="utf-8")

        self.assertIn('id="response-prompt"', console_html)
        self.assertIn('id="persona-prompt"', console_html)
        self.assertIn("prompts.response?.text", settings_js)
        self.assertIn("prompts.persona?.text", settings_js)
        self.assertIn("prompts: {", settings_js)

    def test_console_exposes_source_identity_settings(self):
        console_html = Path("web_tool/rikka.html").read_text(encoding="utf-8")
        settings_js = Path("web_tool/rikka/settings.js").read_text(encoding="utf-8")

        self.assertIn('id="identity-host-name"', console_html)
        self.assertIn('id="identity-audience-name"', console_html)
        self.assertIn("identity.host_display_name", settings_js)
        self.assertIn("identity.audience_display_name", settings_js)
        self.assertIn("host_display_name: value", settings_js)
        self.assertIn("audience_display_name: value", settings_js)

    def test_console_exposes_overlay_operator_settings(self):
        console_html = Path("web_tool/rikka.html").read_text(encoding="utf-8")
        settings_js = Path("web_tool/rikka/settings.js").read_text(encoding="utf-8")

        self.assertIn('id="overlay-asr-hud-visible"', console_html)
        self.assertIn("overlay.asr_hud_visible", settings_js)
        self.assertIn("asr_hud_visible: checked", settings_js)
        self.assertIn("dock_layout_mode: state.settings?.overlay?.dock_layout_mode", settings_js)

    def test_vendor_assets_are_documented(self):
        vendor = Path("overlay/vendor")
        readme = (vendor / "README.md").read_text(encoding="utf-8")

        for file_name in [
            "live2dcubismcore.min.js",
            "rikka-lapp-runtime.js",
        ]:
            self.assertTrue((vendor / file_name).is_file(), file_name)
            self.assertIn(file_name, readme)
        self.assertNotIn("pixi-live2d-display", readme)
        self.assertIn("CubismTargetPoint", readme)

    def test_pointer_polling_access_logs_are_quiet_on_success(self):
        server = Path("run_server.py").read_text(encoding="utf-8")

        self.assertIn("class PointerAccessLogFilter", server)
        self.assertIn('POINTER_PATH = "/rikka/overlay/pointer"', server)
        self.assertIn("status < 400", server)
        self.assertIn('logging.getLogger("uvicorn.access").addFilter', server)
        self.assertIn("install_access_log_filters()", server)


if __name__ == "__main__":
    unittest.main()
