import numpy as np

from .asr_interface import ASRInterface


class ASRDisabledError(RuntimeError):
    """Raised when audio transcription is requested while ASR is disabled."""


class VoiceRecognition(ASRInterface):
    is_disabled = True

    def streaming_status(self) -> str:
        return "asr_disabled"

    def transcribe_np(self, audio: np.ndarray) -> str:
        raise ASRDisabledError(
            "ASR is disabled by configuration. Use text input or Rikka live events."
        )
