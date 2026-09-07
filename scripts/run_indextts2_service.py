"""Run a small FastAPI wrapper around a local IndexTTS2 checkout."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


REQUIRED_MODEL_FILES = (
    "bpe.model",
    "gpt.pth",
    "config.yaml",
    "s2mel.pth",
    "wav2vec2bert_stats.pt",
)

RUNTIME_MODEL_REQUIREMENTS = (
    {
        "repo_id": "facebook/w2v-bert-2.0",
        "files": (
            "config.json",
            "preprocessor_config.json",
            "model.safetensors",
        ),
    },
    {
        "repo_id": "amphion/MaskGCT",
        "files": ("semantic_codec/model.safetensors",),
    },
    {
        "repo_id": "funasr/campplus",
        "files": ("campplus_cn_common.bin",),
    },
    {
        "repo_id": "nvidia/bigvgan_v2_22khz_80band_256x",
        "files": (
            "config.json",
            "bigvgan_generator.pt",
        ),
    },
)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1)
    speaker_audio_path: str = ""
    emo_audio_path: str = ""
    emo_alpha: float = 0.6
    emo_vector: list[float] | None = None
    use_emo_text: bool = False
    emo_text: str = ""
    use_random: bool = False
    audio_format: str = "wav"
    max_text_tokens_per_segment: int = 80


class ServiceState:
    def __init__(self):
        self.args: argparse.Namespace | None = None
        self.tts: Any | None = None
        self.lock = threading.Lock()


state = ServiceState()
app = FastAPI(title="Rikka IndexTTS2 Service")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rikka IndexTTS2 HTTP service")
    parser.add_argument("--repo-dir", default="local_services/index-tts")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7861)
    parser.add_argument("--model-dir", default="checkpoints")
    parser.add_argument("--reference-audio", default="")
    parser.add_argument("--fp16", action="store_true", default=False)
    parser.add_argument("--cuda-kernel", action="store_true", default=False)
    parser.add_argument("--deepspeed", action="store_true", default=False)
    parser.add_argument("--device", default=None)
    parser.add_argument("--verbose", action="store_true", default=False)
    parser.add_argument("--max-text-tokens-per-segment", type=int, default=80)
    parser.add_argument("--manual-runtime-model-dir", default="manual_hf")
    parser.add_argument("--allow-runtime-downloads", action="store_true", default=False)
    return parser.parse_args()


def resolve_path(path: str | Path, base: Path) -> Path:
    resolved = Path(path).expanduser()
    if not resolved.is_absolute():
        resolved = base / resolved
    return resolved.resolve()


def missing_model_files(model_dir: Path) -> list[str]:
    return [name for name in REQUIRED_MODEL_FILES if not (model_dir / name).is_file()]


def manual_runtime_file_path(manual_root: Path, repo_id: str, filename: str) -> Path:
    return manual_root / repo_id / Path(filename)


def missing_runtime_model_files(manual_root: Path) -> list[dict[str, str]]:
    missing: list[dict[str, str]] = []
    for requirement in RUNTIME_MODEL_REQUIREMENTS:
        repo_id = requirement["repo_id"]
        for filename in requirement["files"]:
            expected_path = manual_runtime_file_path(manual_root, repo_id, filename)
            if not expected_path.is_file():
                missing.append(
                    {
                        "repo_id": repo_id,
                        "filename": filename,
                        "url": f"https://huggingface.co/{repo_id}/resolve/main/{filename}",
                        "path": str(expected_path),
                    }
                )
    return missing


def runtime_model_download_message(manual_root: Path, missing: list[dict[str, str]]) -> str:
    lines = [
        "IndexTTS2 manual runtime model directory is incomplete.",
        "Runtime downloads are disabled by default so startup will not hang on HuggingFace.",
        f"Manual model root: {manual_root}",
        "Download each missing URL and save it to the matching local path:",
    ]
    for item in missing:
        lines.append(f"- {item['url']}")
        lines.append(f"  -> {item['path']}")
    lines.append(
        "If you intentionally want startup to download missing runtime files, pass "
        "--allow-runtime-downloads."
    )
    return "\n".join(lines)


def runtime_file_map(manual_root: Path) -> dict[tuple[str, str], Path]:
    mapping: dict[tuple[str, str], Path] = {}
    for requirement in RUNTIME_MODEL_REQUIREMENTS:
        repo_id = requirement["repo_id"]
        for filename in requirement["files"]:
            mapping[(repo_id, filename)] = manual_runtime_file_path(
                manual_root, repo_id, filename
            )
    return mapping


def install_runtime_model_patches(
    manual_root: Path,
    allow_runtime_downloads: bool,
) -> None:
    missing = missing_runtime_model_files(manual_root)
    if missing and not allow_runtime_downloads:
        raise RuntimeError(runtime_model_download_message(manual_root, missing))
    if missing:
        return

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"

    file_map = runtime_file_map(manual_root)

    import huggingface_hub
    import indextts.infer_v2 as infer_v2
    from indextts.s2mel.modules.bigvgan import bigvgan as s2mel_bigvgan
    from transformers import SeamlessM4TFeatureExtractor, Wav2Vec2BertModel

    original_hf_hub_download = huggingface_hub.hf_hub_download

    def local_hf_hub_download(repo_id: str, filename: str, *args: Any, **kwargs: Any):
        normalized_filename = filename.replace("\\", "/")
        local_path = file_map.get((repo_id, normalized_filename))
        if local_path is not None and local_path.is_file():
            return str(local_path)
        if allow_runtime_downloads:
            return original_hf_hub_download(repo_id, filename, *args, **kwargs)
        raise RuntimeError(
            "IndexTTS2 runtime model file is not available offline: "
            f"{repo_id}/{normalized_filename}"
        )

    huggingface_hub.hf_hub_download = local_hf_hub_download
    infer_v2.hf_hub_download = local_hf_hub_download
    s2mel_bigvgan.hf_hub_download = local_hf_hub_download
    try:
        from indextts.BigVGAN import bigvgan as package_bigvgan

        package_bigvgan.hf_hub_download = local_hf_hub_download
    except Exception:
        pass

    w2v_dir = manual_root / "facebook" / "w2v-bert-2.0"

    original_feature_from_pretrained = SeamlessM4TFeatureExtractor.from_pretrained
    original_model_from_pretrained = Wav2Vec2BertModel.from_pretrained

    @classmethod
    def feature_from_pretrained(cls, pretrained_model_name_or_path, *args, **kwargs):
        if str(pretrained_model_name_or_path) == "facebook/w2v-bert-2.0":
            pretrained_model_name_or_path = str(w2v_dir)
        kwargs.setdefault("local_files_only", True)
        return original_feature_from_pretrained(
            pretrained_model_name_or_path, *args, **kwargs
        )

    @classmethod
    def model_from_pretrained(cls, pretrained_model_name_or_path, *args, **kwargs):
        if str(pretrained_model_name_or_path) == "facebook/w2v-bert-2.0":
            pretrained_model_name_or_path = str(w2v_dir)
        kwargs.setdefault("local_files_only", True)
        return original_model_from_pretrained(
            pretrained_model_name_or_path, *args, **kwargs
        )

    SeamlessM4TFeatureExtractor.from_pretrained = feature_from_pretrained
    Wav2Vec2BertModel.from_pretrained = model_from_pretrained


def load_model(args: argparse.Namespace):
    repo_dir = resolve_path(args.repo_dir, Path.cwd())
    model_dir = resolve_path(args.model_dir, repo_dir)
    manual_runtime_model_dir = resolve_path(args.manual_runtime_model_dir, repo_dir)
    missing = missing_model_files(model_dir)
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(
            f"IndexTTS2 model directory is incomplete: {model_dir} missing {joined}"
        )

    sys.path.insert(0, str(repo_dir))
    sys.path.insert(0, str(repo_dir / "indextts"))
    os.environ.setdefault("HF_HUB_CACHE", str(model_dir / "hf_cache"))
    install_runtime_model_patches(
        manual_runtime_model_dir,
        allow_runtime_downloads=args.allow_runtime_downloads,
    )

    from indextts.infer_v2 import IndexTTS2

    return IndexTTS2(
        cfg_path=str(model_dir / "config.yaml"),
        model_dir=str(model_dir),
        use_fp16=args.fp16,
        device=args.device,
        use_cuda_kernel=args.cuda_kernel,
        use_deepspeed=args.deepspeed,
    )


@app.on_event("startup")
async def startup() -> None:
    args = parse_args()
    state.args = args
    state.tts = await asyncio.to_thread(load_model, args)


@app.get("/health")
async def health() -> dict[str, Any]:
    args = state.args or parse_args()
    repo_dir = resolve_path(args.repo_dir, Path.cwd())
    model_dir = resolve_path(args.model_dir, repo_dir)
    manual_runtime_model_dir = resolve_path(args.manual_runtime_model_dir, repo_dir)
    reference_audio = (
        resolve_path(args.reference_audio, Path.cwd()) if args.reference_audio else None
    )
    return {
        "ok": state.tts is not None,
        "repo_dir": str(repo_dir),
        "model_dir_ready": not missing_model_files(model_dir),
        "manual_runtime_model_dir": str(manual_runtime_model_dir),
        "manual_runtime_models_ready": not missing_runtime_model_files(
            manual_runtime_model_dir
        ),
        "allow_runtime_downloads": args.allow_runtime_downloads,
        "reference_audio_ready": bool(reference_audio and reference_audio.is_file()),
        "fp16": args.fp16,
        "cuda_kernel": args.cuda_kernel,
        "deepspeed": args.deepspeed,
        "device": args.device or "auto",
    }


def synthesize(request: TTSRequest) -> Path:
    if state.tts is None or state.args is None:
        raise RuntimeError("IndexTTS2 model is not loaded")

    speaker_audio = request.speaker_audio_path or state.args.reference_audio
    if not speaker_audio:
        raise ValueError("speaker_audio_path or --reference-audio is required")
    speaker_audio_path = resolve_path(speaker_audio, Path.cwd())
    if not speaker_audio_path.is_file():
        raise FileNotFoundError(f"speaker audio not found: {speaker_audio_path}")

    emo_audio_path: Path | None = None
    if request.emo_audio_path:
        emo_audio_path = resolve_path(request.emo_audio_path, Path.cwd())
        if not emo_audio_path.is_file():
            raise FileNotFoundError(f"emotion audio not found: {emo_audio_path}")

    repo_dir = resolve_path(state.args.repo_dir, Path.cwd())
    output_dir = repo_dir / "outputs" / "rikka-service"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"rikka_{int(time.time() * 1000)}.wav"
    max_segment = (
        request.max_text_tokens_per_segment
        or state.args.max_text_tokens_per_segment
    )

    with state.lock:
        result = state.tts.infer(
            spk_audio_prompt=str(speaker_audio_path),
            text=request.text,
            output_path=str(output_path),
            emo_audio_prompt=str(emo_audio_path) if emo_audio_path else None,
            emo_alpha=request.emo_alpha,
            emo_vector=request.emo_vector,
            use_emo_text=request.use_emo_text,
            emo_text=request.emo_text or None,
            use_random=request.use_random,
            verbose=state.args.verbose,
            max_text_tokens_per_segment=max_segment,
        )

    result_path = Path(result or output_path)
    if not result_path.is_file():
        raise RuntimeError("IndexTTS2 did not produce an output file")
    return result_path


@app.post("/tts")
async def tts(request: TTSRequest):
    try:
        output_path = await asyncio.to_thread(synthesize, request)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return FileResponse(
        path=str(output_path),
        media_type="audio/wav",
        filename=output_path.name,
    )


if __name__ == "__main__":
    import uvicorn

    parsed_args = parse_args()
    sys.argv = [sys.argv[0], *sys.argv[1:]]
    uvicorn.run(app, host=parsed_args.host, port=parsed_args.port)
