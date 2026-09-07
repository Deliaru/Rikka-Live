"""Shared IndexTTS2 emotion-vector helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

EMOTION_KEYS = (
    "happy",
    "angry",
    "sad",
    "fear",
    "disgust",
    "melancholy",
    "surprise",
    "calm",
)
DEFAULT_QUIET_COMPANION_VECTOR = (0.10, 0, 0, 0, 0, 0.20, 0, 0.10)
MAX_EMOTION_VALUE = 1.2
MAX_EMOTION_VECTOR_SUM = 1.5


def clamp_quiet_companion_alpha(value: float | int | str | None) -> float:
    if value is None:
        return 1.0
    numeric = float(value)
    return min(MAX_EMOTION_VALUE, max(0.0, numeric))


def normalize_emotion_vector(
    value: Sequence[float] | Mapping[str, float] | None,
    *,
    default: Sequence[float] = DEFAULT_QUIET_COMPANION_VECTOR,
) -> list[float]:
    if value is None:
        vector = [float(item) for item in default]
    elif isinstance(value, Mapping):
        vector = [float(item) for item in default]
        for index, key in enumerate(EMOTION_KEYS):
            if key in value:
                vector[index] = float(value[key])
    else:
        if isinstance(value, (str, bytes)) or len(value) != len(EMOTION_KEYS):
            raise ValueError("IndexTTS2 emotion vector must have 8 dimensions")
        vector = [float(item) for item in value]

    if any(item < 0 or item > MAX_EMOTION_VALUE for item in vector):
        raise ValueError("IndexTTS2 emotion values must be within [0, 1.2]")
    if sum(vector) > MAX_EMOTION_VECTOR_SUM:
        raise ValueError("IndexTTS2 emotion vector sum must not exceed 1.5")
    return vector
