"""Prepare a short WAV reference clip for MiMo voice cloning."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def find_ffmpeg(explicit_path: str | None = None) -> str:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_file():
            raise FileNotFoundError(f"ffmpeg not found: {path}")
        return str(path)

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "ffmpeg is not on PATH. Install the project-local helper with "
            "`python -m pip install imageio-ffmpeg`, or pass --ffmpeg."
        ) from exc

    return imageio_ffmpeg.get_ffmpeg_exe()


def convert_reference_audio(
    source: Path,
    output: Path,
    *,
    ffmpeg_path: str,
    sample_rate: int,
    duration_seconds: float,
) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"source audio not found: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
    ]
    if duration_seconds > 0:
        command.extend(["-t", str(duration_seconds)])
    command.extend(["-af", "loudnorm=I=-18:TP=-1.5:LRA=11", str(output)])

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffmpeg conversion failed")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a user voice sample to a small mono WAV reference clip."
    )
    parser.add_argument("source", type=Path, help="Input audio file, such as .m4a.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("private/voice/rikka_voice_clone.wav"),
        help="Output WAV path. Defaults to the ignored local private directory.",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=24000,
        help="Output sample rate in Hz.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=20.0,
        help="Maximum seconds to keep. Use 0 to keep the full source.",
    )
    parser.add_argument("--ffmpeg", help="Optional explicit ffmpeg executable path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ffmpeg_path = find_ffmpeg(args.ffmpeg)
    convert_reference_audio(
        args.source,
        args.output,
        ffmpeg_path=ffmpeg_path,
        sample_rate=args.sample_rate,
        duration_seconds=args.duration,
    )
    size = args.output.stat().st_size
    print(f"prepared_voice_sample={args.output}")
    print(f"bytes={size}")
    print("mime_type=audio/wav")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
