"""Prepare a local Live2D model folder for the Rikka demo."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


DEFAULT_TARGET_NAME = "rikka_mikazuki"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def find_one(source: Path, pattern: str) -> Path:
    matches = sorted(source.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no {pattern} found under {source}")
    return matches[0]


def has_parameter_id(cdi_text: str, parameter_id: str) -> bool:
    return f'"Id": "{parameter_id}"' in cdi_text


def collect_expressions(target: Path) -> list[dict[str, str]]:
    expressions = []
    for path in sorted(target.glob("*.exp3.json")):
        expressions.append({"Name": path.stem.replace(".exp3", ""), "File": path.name})
    return expressions


def collect_motions(target: Path) -> dict[str, list[dict[str, str]]]:
    motion_files = sorted(target.glob("*.motion3.json"))
    motion_files.extend(sorted((target / "animations").glob("*.motion3.json")))

    idle = []
    reactions = []
    for path in motion_files:
        rel = path.relative_to(target).as_posix()
        if "idle" in path.name.lower() and not idle:
            idle.append({"File": rel})
        else:
            reactions.append({"File": rel})

    if not idle and reactions:
        idle.append(reactions.pop(0))

    motions: dict[str, list[dict[str, str]]] = {}
    if idle:
        motions["Idle"] = idle
    if reactions:
        motions[""] = reactions
    return motions


def patch_model_manifest(target: Path, target_name: str) -> Path:
    source_model = find_one(target, "*.model3.json")
    model = read_json(source_model)
    file_refs = model.setdefault("FileReferences", {})

    expressions = collect_expressions(target)
    if expressions:
        file_refs["Expressions"] = expressions

    motions = collect_motions(target)
    if motions:
        file_refs["Motions"] = motions

    cdi_path = target / file_refs.get("DisplayInfo", "")
    cdi_text = cdi_path.read_text(encoding="utf-8") if cdi_path.is_file() else ""

    eye_blink_ids = [
        value
        for value in ("ParamEyeLOpen", "ParamEyeROpen")
        if has_parameter_id(cdi_text, value)
    ]
    lip_sync_ids = [
        value
        for value in ("ParamMouthOpenY", "ParamA")
        if has_parameter_id(cdi_text, value)
    ]
    model["Groups"] = [
        {"Target": "Parameter", "Name": "EyeBlink", "Ids": eye_blink_ids},
        {"Target": "Parameter", "Name": "LipSync", "Ids": lip_sync_ids[:1]},
    ]
    model["HitAreas"] = [
        {"Id": "HitAreaHead", "Name": "Head"},
        {"Id": "HitAreaBody", "Name": "Body"},
    ]

    patched_path = target / f"{target_name}.model3.json"
    write_json(patched_path, model)
    return patched_path


def prepare_model(source: Path, output_root: Path, target_name: str, overwrite: bool) -> Path:
    if not source.is_dir():
        raise FileNotFoundError(f"source model directory not found: {source}")

    target = output_root / target_name
    if target.exists():
        if not overwrite:
            raise FileExistsError(f"target already exists: {target}")
        shutil.rmtree(target)

    output_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target)
    return patch_model_manifest(target, target_name)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Copy a Live2D Cubism model into app/live2d-models and patch its manifest."
    )
    parser.add_argument("source", type=Path, help="Source Live2D model directory.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("live2d-models"),
        help="App-local Live2D model root.",
    )
    parser.add_argument(
        "--target-name",
        default=DEFAULT_TARGET_NAME,
        help="Stable model name used by model_dict.json and conf.yaml.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Replace target.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = prepare_model(
        args.source,
        args.output_root,
        args.target_name,
        args.overwrite,
    )
    print(f"prepared_live2d_manifest={manifest}")
    print(f"model_name={args.target_name}")
    print(f"url=/live2d-models/{args.target_name}/{manifest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
