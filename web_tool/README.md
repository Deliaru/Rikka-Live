# Web Tool


## Why?
The Open-LLM-VTuber project leverages TTS and ASR (speech recognition) models to deliver an immersive, voice-to-voice AI companion experience.

While ASR and TTS technologies are powerful on their own, setting them up can be challenging. Previously, although our users installed the TTS and ASR models into our project, they were exclusively accessible as a part of the Open-LLM-VTuber's AI companion feature, preventing their use for other purposes like transcription or speech generation.

## What is Web Tool?

This is a dedicated web page within the Open-LLM-VTuber backend that provides direct access to the ASR and TTS models initialized by the Open-LLM-VTuber server.

Access the ASR/TTS page at: http://localhost:12393/web-tool.

Access the Rikka Live co-streaming console at: http://localhost:12393/web-tool/rikka.html. The console calls the `/rikka/*` debug, memory, provider, and privacy endpoints directly.

Note that the ASR and TTS models are the same ones you've set in the `conf.yaml` file, and switching models at runtime is not possible at this point.
