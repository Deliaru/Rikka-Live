# Rikka Live Fork Notes

Base project: Open-LLM-VTuber

Locked upstream commit: `3afa41014b4548a0842e9ee2f576f4b164b48886`

Local branch: `rikka-live-first-demo`

First implementation policy:

- Keep Rikka-specific product code behind adapter-style modules under `src/open_llm_vtuber/rikka/`.
- Treat OBS as an external capture tool only; the app remains independent.
- Use `prompt.txt` from the workspace root as the canonical Yayotsuki Rikka persona source.
- Require structured `RikkaResponse` objects before anything reaches subtitles or TTS.
- Strip hidden thinking tags and prompt scaffolding before public output.
- Persist only structured events/settings/memory by default; do not persist raw screen/audio captures.
- Xiaomi MiMo V2.5 TTS VoiceClone is the first cloud TTS provider spike. Its current low-latency streaming path is compatibility-only, so the demo uses short non-streaming lines and a waiting/reading Live2D state.
