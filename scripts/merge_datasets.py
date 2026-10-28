"""Merge source datasets into the unified 20-class YOLO dataset.

Use ``--labels-only --dataset weapon`` to repair only weapon labels after a
class-map change; this leaves all existing images untouched.
"""

from __future__ import annotations

import argparse
import shutil
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "Datasets"
UNIFIED_DIR = DATASETS_DIR / "unified"
SOURCES = {
    "blood": DATASETS_DIR / "blood",
    "crime": DATASETS_DIR / "crime scene",
    "danger": DATASETS_DIR / "Dangerous objects",
    "weapon": DATASETS_DIR / "weapon",
}

# Source dataset class ID -> unified dataset class ID.
# Note: Datasets/weapon/data.yaml is stale (it says 6 classes), but its actual
# Roboflow export labels use IDs 0-8. Only the six evidence-object labels below
# belong in this project; IDs 0, 4, and 5 are person/attacker-type annotations.
CLASS_MAP = {
    "blood": {0: 0},
    "crime": {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9, 9: 10},
    "danger": {0: 11, 1: 12, 2: 13},
    "weapon": {1: 14, 2: 15, 3: 16, 6: 17, 7: 18, 8: 19},
}
SKIPPED_CLASS_IDS = {"weapon": {0, 4, 5}}
SPLITS = ("train", "valid", "test")


def remap_label_file(label_path: Path, dataset_name: str) -> tuple[list[str], Counter[int]]:
    remapped_lines: list[str] = []
    class_counts: Counter[int] = Counter()

    for line_number, line in enumerate(label_path.read_text(encoding="utf-8").splitlines(), start=1):
        values = line.split()
        if not values:
            continue
        try:
            source_class = int(values[0])
        except ValueError as error:
            raise ValueError(f"Invalid class ID in {label_path} at line {line_number}") from error
        if source_class in SKIPPED_CLASS_IDS.get(dataset_name, set()):
            continue
        if source_class not in CLASS_MAP[dataset_name]:
            raise ValueError(f"Unknown class ID {source_class} in {label_path} at line {line_number}")

        unified_class = CLASS_MAP[dataset_name][source_class]
        values[0] = str(unified_class)
        remapped_lines.append(" ".join(values))
        class_counts[unified_class] += 1

    return remapped_lines, class_counts


def merge_split(dataset_name: str, split: str, labels_only: bool) -> Counter[int]:
    source_images = SOURCES[dataset_name] / split / "images"
    source_labels = SOURCES[dataset_name] / split / "labels"
    destination_images = UNIFIED_DIR / split / "images"
    destination_labels = UNIFIED_DIR / split / "labels"
    counts: Counter[int] = Counter()

    if not source_images.is_dir():
        print(f"Skipping {dataset_name}/{split}: source images folder not found.")
        return counts

    destination_images.mkdir(parents=True, exist_ok=True)
    destination_labels.mkdir(parents=True, exist_ok=True)
    image_paths = [path for path in source_images.iterdir() if path.is_file()]

    for image_path in image_paths:
        destination_image = destination_images / f"{dataset_name}_{image_path.name}"
        if not labels_only:
            shutil.copy2(image_path, destination_image)
        elif not destination_image.is_file():
            raise FileNotFoundError(
                f"Cannot perform labels-only repair: missing unified image {destination_image}. "
                "Run the full merge instead."
            )

        label_path = source_labels / f"{image_path.stem}.txt"
        if not label_path.is_file():
            continue
        remapped_lines, label_counts = remap_label_file(label_path, dataset_name)
        destination_label = destination_labels / f"{dataset_name}_{image_path.stem}.txt"
        destination_label.write_text("\n".join(remapped_lines), encoding="utf-8")
        counts.update(label_counts)

    print(f"Processed {dataset_name}/{split}: {len(image_paths)} images, {sum(counts.values())} labels.")
    return counts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge crime-scene datasets with a verified class map.")
    parser.add_argument("--dataset", choices=tuple(SOURCES), help="Merge only one source dataset.")
    parser.add_argument("--labels-only", action="store_true", help="Rewrite labels without copying images.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    datasets_to_merge = (args.dataset,) if args.dataset else tuple(SOURCES)
    total_counts: Counter[int] = Counter()

    for dataset_name in datasets_to_merge:
        for split in SPLITS:
            total_counts.update(merge_split(dataset_name, split, args.labels_only))

    print("Unified class counts written:", dict(sorted(total_counts.items())))


if __name__ == "__main__":
    main()
