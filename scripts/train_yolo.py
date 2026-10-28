"""Train and deploy the 20-class crime-scene evidence model.

Run from the project root on a CUDA-enabled machine:
    .\\venv\\Scripts\\python.exe scripts\\train_yolo.py

The existing models/best.pt is replaced only after training produces a valid
20-class checkpoint, so a failed run never leaves the web application without
a working model.
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = BASE_DIR / "Datasets" / "unified" / "data.yaml"
DEFAULT_PRETRAINED_MODEL = BASE_DIR / "yolo11n.pt"
RUNS_DIRECTORY = BASE_DIR / "runs" / "train"
DEPLOYED_MODEL = BASE_DIR / "models" / "best.pt"
MODEL_METADATA = BASE_DIR / "models" / "model_metadata.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the crime-scene evidence detector.")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--name", default="crime_scene_20class")
    parser.add_argument("--pretrained", default=str(DEFAULT_PRETRAINED_MODEL))
    parser.add_argument("--device", default="auto", help="'auto', a CUDA device such as '0', or 'cpu'.")
    parser.add_argument("--allow-cpu", action="store_true", help="Allow the much slower CPU-only training path.")
    return parser.parse_args()


def resolve_device(requested_device: str, allow_cpu: bool) -> str | int:
    if requested_device != "auto":
        if requested_device.lower() == "cpu" and not allow_cpu:
            raise RuntimeError("CPU training requires --allow-cpu because this dataset is large.")
        return requested_device
    if torch.cuda.is_available():
        return 0
    if allow_cpu:
        return "cpu"
    raise RuntimeError(
        "No CUDA GPU is available. Train on a CUDA-enabled machine, or explicitly use --allow-cpu "
        "if you accept a very long CPU training run."
    )


def load_class_names() -> list[str]:
    if not DATA_YAML.is_file():
        raise FileNotFoundError(f"Dataset config not found: {DATA_YAML}")
    data = yaml.safe_load(DATA_YAML.read_text(encoding="utf-8"))
    class_names = data.get("names", [])
    expected_count = data.get("nc")
    if not isinstance(class_names, list) or len(class_names) != expected_count:
        raise ValueError("data.yaml must define a names list with exactly nc entries.")
    return class_names


def deploy_model(best_weights: Path, expected_classes: list[str]) -> None:
    trained_model = YOLO(str(best_weights))
    trained_classes = [trained_model.names[index] for index in sorted(trained_model.names)]
    if trained_classes != expected_classes:
        raise ValueError(
            f"Refusing to deploy {best_weights}: expected {len(expected_classes)} classes but received "
            f"{len(trained_classes)} ({trained_classes})."
        )

    DEPLOYED_MODEL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best_weights, DEPLOYED_MODEL)
    metadata = {
        "model_file": DEPLOYED_MODEL.name,
        "class_names": trained_classes,
        "source_weights": str(best_weights.relative_to(BASE_DIR)),
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    MODEL_METADATA.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Deployed verified {len(trained_classes)}-class model to: {DEPLOYED_MODEL}")


def main() -> None:
    args = parse_args()
    class_names = load_class_names()
    device = resolve_device(args.device, args.allow_cpu)
    pretrained_model = Path(args.pretrained)
    if not pretrained_model.is_absolute():
        pretrained_model = BASE_DIR / pretrained_model
    if not pretrained_model.is_file():
        raise FileNotFoundError(f"Pretrained model not found: {pretrained_model}")

    print(f"Training {len(class_names)} classes on device: {device}")
    print(f"Class names: {', '.join(class_names)}")
    model = YOLO(str(pretrained_model))
    model.train(
        data=str(DATA_YAML),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        device=device,
        pretrained=True,
        patience=25,
        optimizer="auto",
        seed=42,
        project=str(RUNS_DIRECTORY),
        name=args.name,
        exist_ok=False,
    )

    best_weights = Path(model.trainer.best)
    if not best_weights.is_file():
        raise FileNotFoundError(f"Training completed without a best checkpoint: {best_weights}")
    deploy_model(best_weights, class_names)


if __name__ == "__main__":
    main()
