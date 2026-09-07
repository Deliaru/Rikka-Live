"""Conservative tail cleanup for generated TTS audio.

Opt-in stage invoked by ``TTSTaskManager._process_tts`` between audio
generation and payload preparation. Default-disabled; when disabled the
TTS payload is byte-compatible with the unprocessed path.

Algorithm (v1, conservative): tail low-energy trim + short linear fade-out.
See task 06-14-tts-audio-tail-cleanup for rationale and contracts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

# Re-use the ffmpeg-configured AudioSegment from stream_audio so the project's
# bundled imageio-ffmpeg bootstrap applies here too. Importing this module also
# runs that bootstrap (module side-effect in stream_audio), so no duplication.
from .stream_audio import AudioSegment

if TYPE_CHECKING:
    from ..rikka.settings import TtsPostProcessingSettings


# RMS scan granularity. Coarse enough to be cheap, fine enough to localise the
# boundary between speech and tail noise.
_CHUNK_MS = 10


@dataclass
class CleanupResult:
    """Privacy-safe diagnostic for a single cleanup invocation.

    Contains only booleans, millisecond counts, dB threshold, and a short
    fixed-vocabulary reason string. Never raw audio, base64, provider payload,
    or text content.
    """

    applied: bool
    skipped: bool
    failed: bool
    reason: str
    trimmed_ms: int
    fade_ms: int
    before_ms: int
    after_ms: int
    threshold_db: float = 0.0


def _disabled_result() -> CleanupResult:
    return CleanupResult(
        applied=False,
        skipped=False,
        failed=False,
        reason="disabled",
        trimmed_ms=0,
        fade_ms=0,
        before_ms=0,
        after_ms=0,
        threshold_db=0.0,
    )


def _failed_result(before_ms: int, reason: str, threshold_db: float) -> CleanupResult:
    return CleanupResult(
        applied=False,
        skipped=False,
        failed=True,
        reason=reason,
        trimmed_ms=0,
        fade_ms=0,
        before_ms=before_ms,
        after_ms=before_ms,
        threshold_db=threshold_db,
    )


def _skipped_result(before_ms: int, reason: str, threshold_db: float) -> CleanupResult:
    return CleanupResult(
        applied=False,
        skipped=True,
        failed=False,
        reason=reason,
        trimmed_ms=0,
        fade_ms=0,
        before_ms=before_ms,
        after_ms=before_ms,
        threshold_db=threshold_db,
    )


def _applied_result(
    before_ms: int,
    after_ms: int,
    trimmed_ms: int,
    fade_ms: int,
    threshold_db: float,
) -> CleanupResult:
    return CleanupResult(
        applied=True,
        skipped=False,
        failed=False,
        reason="trimmed",
        trimmed_ms=trimmed_ms,
        fade_ms=fade_ms,
        before_ms=before_ms,
        after_ms=after_ms,
        threshold_db=threshold_db,
    )


def _apply_linear_fade(seg: AudioSegment, fade_ms: int) -> AudioSegment:
    """Multiply the final ``fade_ms`` of ``seg`` by a linear ramp 1 -> 0.

    Works for any channel count by reshaping the interleaved sample buffer.
    Pure numpy, deterministic; no dependency on pydub's ``fade_out`` semantics.
    """
    if fade_ms <= 0:
        return seg

    import numpy as np

    channels = seg.channels
    sample_rate = seg.frame_rate
    fade_samples = int(sample_rate * fade_ms / 1000)
    if fade_samples < 1:
        return seg

    total_samples = len(seg.get_array_of_samples())
    if total_samples == 0 or fade_samples > total_samples:
        # Fade region longer than the audio: clamp to available samples.
        fade_samples = total_samples
        if fade_samples < 1:
            return seg

    arr = np.asarray(seg.get_array_of_samples(), dtype=np.float64)
    # Reshape to (frames, channels) so the ramp is applied per frame.
    arr = arr.reshape(-1, channels)
    ramp = np.linspace(1.0, 0.0, fade_samples, endpoint=True).reshape(-1, 1)
    arr[-fade_samples:] *= ramp
    clipped = np.clip(arr.reshape(-1), -32768, 32767).astype(np.int16)
    return seg._spawn(clipped.tobytes())


def apply_tail_cleanup(
    audio_path: str, settings: "TtsPostProcessingSettings"
) -> CleanupResult:
    """Process a generated TTS audio file in place.

    Safe no-op when ``settings.enabled`` is False. Never raises: DSP/load
    failures return a ``failed`` result and leave the original file untouched.
    """
    if not settings.enabled:
        return _disabled_result()

    trim_max_ms = settings.trim_max_ms
    threshold_db = settings.trim_rms_threshold_db
    min_tail_ms = settings.trim_min_tail_ms
    fade_ms = settings.fade_out_ms

    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as exc:  # noqa: BLE001 - any load failure is non-fatal here
        logger.debug(f"tts tail cleanup load failed: {type(exc).__name__}")
        return _failed_result(0, type(exc).__name__, threshold_db)

    before_ms = len(audio)

    # Need at least protection band + a scannable window to evaluate safely.
    if before_ms < min_tail_ms + trim_max_ms or trim_max_ms <= 0:
        return _skipped_result(before_ms, "audio too short", threshold_db)

    # Scannable region: [before - min_tail - trim_max, before - min_tail).
    scannable_end_ms = before_ms - min_tail_ms
    scannable_start_ms = scannable_end_ms - trim_max_ms

    # Walk ~10ms chunks backward, find the last chunk at/above threshold.
    cut_offset_ms = trim_max_ms  # default: trim the whole window if all below
    cursor_ms = scannable_end_ms
    while cursor_ms > scannable_start_ms:
        chunk_start = max(cursor_ms - _CHUNK_MS, scannable_start_ms)
        chunk = audio[chunk_start:cursor_ms]
        if chunk.rms > 0 and chunk.dBFS >= threshold_db:
            # This chunk is "speech-like"; cut point is the end of this chunk.
            cut_offset_ms = scannable_end_ms - cursor_ms
            break
        cursor_ms = chunk_start

    trimmed_ms = cut_offset_ms
    if trimmed_ms <= 0:
        return _skipped_result(before_ms, "tail above threshold", threshold_db)

    # Build trimmed audio: keep everything up to scannable_end_ms - trimmed_ms,
    # plus the protection band after it.
    cut_ms = scannable_end_ms - trimmed_ms
    cleaned = audio[:cut_ms] + audio[scannable_end_ms:]
    cleaned = _apply_linear_fade(cleaned, fade_ms)

    try:
        # Overwrite in place. Export to a sibling temp then move it over the
        # original atomically, so a partially-written file is never left behind
        # if the process is interrupted mid-write.
        tmp_path = str(Path(audio_path).with_suffix(".cleanup.tmp.wav"))
        cleaned.export(tmp_path, format="wav")
        Path(tmp_path).replace(audio_path)
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"tts tail cleanup write failed: {type(exc).__name__}")
        # Best-effort: discard any partial temp file. The original may already
        # be gone if the export succeeded but the move failed; the caller
        # (tts_engine.remove_file) tolerates a missing file. Report honestly.
        try:
            Path(tmp_path).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - cleanup failure is non-fatal
            pass
        return _failed_result(before_ms, type(exc).__name__, threshold_db)

    return _applied_result(
        before_ms=before_ms,
        after_ms=len(cleaned),
        trimmed_ms=trimmed_ms,
        fade_ms=fade_ms,
        threshold_db=threshold_db,
    )


def process_tts_audio_tail(audio_path: str) -> CleanupResult:
    """Entry point for ``_process_tts``.

    Reads the ``tts_post_processing`` settings from the default store and
    dispatches. Kept separate from ``apply_tail_cleanup`` so callers do not
    need to import the settings type or the store.
    """
    # Local import to avoid a circular import at module load time
    # (rikka.settings does not import utils; this keeps the dependency one-way).
    from ..rikka.settings import get_default_settings_store

    settings = get_default_settings_store().snapshot().tts_post_processing
    return apply_tail_cleanup(audio_path, settings)


__all__ = ["CleanupResult", "apply_tail_cleanup", "process_tts_audio_tail"]
