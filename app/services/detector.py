"""Multi-model YOLO inference service for crime-scene evidence detection."""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import (
    DEFAULT_CONFIDENCE,
    DEFAULT_IOU,
    FORENSIC_MODEL_PATH,
    GENERAL_MODEL_PATH,
    WEAPON_MODEL_PATH,
)


@lru_cache(maxsize=4)
def load_yolo_model(model_path_str: str) -> YOLO:
    """Cache YOLO models in memory to avoid reloading checkpoints on every request."""
    path = Path(model_path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Model checkpoint not found: {path}")
    return YOLO(str(path))


def calculate_iou(box_a: list[float], box_b: list[float]) -> float:
    """Calculate Intersection-over-Union between two [x1, y1, x2, y2] boxes."""
    x_a = max(box_a[0], box_b[0])
    y_a = max(box_a[1], box_b[1])
    x_b = min(box_a[2], box_b[2])
    y_b = min(box_a[3], box_b[3])

    inter_w = max(0.0, x_b - x_a)
    inter_h = max(0.0, y_b - y_a)
    inter_area = inter_w * inter_h

    area_a = max(0.0, (box_a[2] - box_a[0]) * (box_a[3] - box_a[1]))
    area_b = max(0.0, (box_b[2] - box_b[0]) * (box_b[3] - box_b[1]))
    union_area = area_a + area_b - inter_area

    if union_area <= 0:
        return 0.0
    return inter_area / union_area


def merge_ensemble_detections(
    detection_lists: list[list[dict[str, Any]]],
    iou_threshold: float = 0.45,
) -> list[dict[str, Any]]:
    """Merge predictions from multiple models, deduplicating overlapping boxes."""
    all_detections: list[dict[str, Any]] = []
    for d_list in detection_lists:
        all_detections.extend(d_list)

    # Sort descending by confidence score
    all_detections.sort(key=lambda d: d["confidence"], reverse=True)

    keep: list[dict[str, Any]] = []
    for candidate in all_detections:
        candidate_box = candidate["box"]
        overlap = False
        for chosen in keep:
            iou = calculate_iou(candidate_box, chosen["box"])
            if iou > iou_threshold:
                overlap = True
                break
        if not overlap:
            keep.append(candidate)

    return keep


def draw_forensic_annotations(
    image: np.ndarray,
    detections: list[dict[str, Any]],
) -> np.ndarray:
    """Draw professional cyber-forensic bounding boxes and badges on the image."""
    canvas = image.copy()
    h, w = canvas.shape[:2]

    # Palette for forensic severity
    color_map = {
        "CRITICAL": (34, 34, 239),    # BGR Red
        "HIGH": (11, 158, 245),       # BGR Amber
        "MEDIUM": (212, 182, 6),      # BGR Cyan
        "LOW": (180, 163, 148),       # BGR Slate
    }

    for item in detections:
        box = item["box"]
        x1, y1, x2, y2 = [int(v) for v in box]
        severity = item.get("severity", "LOW")
        color = color_map.get(severity, (212, 182, 6))

        # Main bounding box
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)

        # Tactical corner reticles
        corner_len = min(20, max(6, int((x2 - x1) * 0.15)), max(6, int((y2 - y1) * 0.15)))
        t = 3
        # Top-left
        cv2.line(canvas, (x1, y1), (x1 + corner_len, y1), color, t)
        cv2.line(canvas, (x1, y1), (x1, y1 + corner_len), color, t)
        # Top-right
        cv2.line(canvas, (x2, y1), (x2 - corner_len, y1), color, t)
        cv2.line(canvas, (x2, y1), (x2, y1 + corner_len), color, t)
        # Bottom-left
        cv2.line(canvas, (x1, y2), (x1 + corner_len, y2), color, t)
        cv2.line(canvas, (x1, y2), (x1, y2 - corner_len), color, t)
        # Bottom-right
        cv2.line(canvas, (x2, y2), (x2 - corner_len, y2), color, t)
        cv2.line(canvas, (x2, y2), (x2 - corner_len, y2), color, t)

        # Forensic Tag Badge
        label = f"{item['class'].upper()} {item['confidence']:.1f}%"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.55
        font_thick = 1
        (label_w, label_h), baseline = cv2.getTextSize(label, font, font_scale, font_thick)

        badge_y1 = max(0, y1 - label_h - 10)
        badge_y2 = y1
        badge_x2 = min(w, x1 + label_w + 14)

        # Semi-transparent dark pill background behind label
        overlay = canvas.copy()
        cv2.rectangle(overlay, (x1, badge_y1), (badge_x2, badge_y2), (14, 23, 38), -1)
        cv2.rectangle(overlay, (x1, badge_y1), (badge_x2, badge_y2), color, 1)
        cv2.addWeighted(overlay, 0.85, canvas, 0.15, 0, canvas)

        # Text in white
        cv2.putText(
            canvas,
            label,
            (x1 + 6, y1 - 6),
            font,
            font_scale,
            (255, 255, 255),
            font_thick,
            cv2.LINE_AA,
        )

    return canvas


def run_yolo_on_image(
    model: YOLO,
    image_input: Path | str | np.ndarray,
    confidence: float,
    model_name: str,
    imgsz: int | None = None,
    augment: bool = True,
) -> list[dict[str, Any]]:
    """Execute prediction on a single YOLO model and format detections with optimal resolution and TTA."""
    predict_kwargs: dict[str, Any] = {
        "conf": confidence,
        "save": False,
        "verbose": False,
        "augment": augment,
    }
    if imgsz is not None:
        predict_kwargs["imgsz"] = imgsz

    source = image_input if isinstance(image_input, np.ndarray) else str(image_input)
    results = model.predict(source, **predict_kwargs)[0]
    names = results.names
    h, w = results.orig_shape

    detections: list[dict[str, Any]] = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = str(names[cls_id])
        conf_val = round(float(box.conf[0]) * 100, 1)
        xyxy = [float(v) for v in box.xyxy[0].tolist()]

        # Normalized coordinates (0-1) for client canvas rendering
        norm_box = [
            round(xyxy[0] / w, 4),
            round(xyxy[1] / h, 4),
            round(xyxy[2] / w, 4),
            round(xyxy[3] / h, 4),
        ]

        detections.append(
            {
                "class": cls_name,
                "confidence": conf_val,
                "box": [round(c, 1) for c in xyxy],
                "norm_box": norm_box,
                "source_model": model_name,
            }
        )

    return detections


def detect_evidence(
    image_path: Path,
    model_choice: str = "ensemble",
    confidence: float = DEFAULT_CONFIDENCE,
    iou_thresh: float = DEFAULT_IOU,
    enable_multi_pass: bool = True,
) -> dict[str, Any]:
    """
    Main detection pipeline supporting:
    - 'weapon': High precision weapon detection model
    - 'forensic': 10-class forensic trace & body model
    - 'ensemble': Fuses weapons & forensic models for comprehensive scene analysis
    - Multi-scale TTA & CLAHE enhancement fusion for high precision.
    """
    if not image_path.is_file():
        raise FileNotFoundError(f"Target image not found: {image_path}")

    start_time = time.perf_counter()
    raw_img = cv2.imread(str(image_path))
    if raw_img is None:
        raise ValueError(f"Could not decode image at {image_path}")

    h, w = raw_img.shape[:2]
    # Optimal high-resolution inference dimension (preserves fine trace evidence without loss)
    max_dim = max(h, w)
    optimal_imgsz = min(1280, max(640, int((max_dim + 31) // 32) * 32))

    all_results: list[list[dict[str, Any]]] = []
    models_executed: list[str] = []

    model_choice = model_choice.lower().strip()

    # Pre-generate enhanced pass (CLAHE contrast normalization) for low-contrast/blurry regions
    enhanced_img: np.ndarray | None = None
    if enable_multi_pass:
        try:
            lab = cv2.cvtColor(raw_img, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            enhanced_img = cv2.cvtColor(cv2.merge((cl, a_channel, b_channel)), cv2.COLOR_LAB2BGR)
        except Exception:
            enhanced_img = None

    if model_choice in ("weapon", "ensemble"):
        if WEAPON_MODEL_PATH.is_file():
            weapon_model = load_yolo_model(str(WEAPON_MODEL_PATH))
            weapon_dets = run_yolo_on_image(
                weapon_model, raw_img, confidence, "Weapons Specialist", imgsz=optimal_imgsz, augment=True
            )
            all_results.append(weapon_dets)

            # Enhanced pass for faint/shadowed weapons
            if enhanced_img is not None:
                enh_w_dets = run_yolo_on_image(
                    weapon_model, enhanced_img, confidence, "Weapons Specialist (Enhanced)", imgsz=optimal_imgsz, augment=True
                )
                if enh_w_dets:
                    all_results.append(enh_w_dets)

            models_executed.append("Weapon Detector (6-Class)")

    if model_choice in ("forensic", "ensemble"):
        if FORENSIC_MODEL_PATH.is_file():
            forensic_model = load_yolo_model(str(FORENSIC_MODEL_PATH))
            forensic_dets = run_yolo_on_image(
                forensic_model, raw_img, confidence, "Forensic Evidence", imgsz=optimal_imgsz, augment=True
            )
            all_results.append(forensic_dets)

            # Enhanced pass for latent/trace evidence
            if enhanced_img is not None:
                enh_f_dets = run_yolo_on_image(
                    forensic_model, enhanced_img, confidence, "Forensic Evidence (Enhanced)", imgsz=optimal_imgsz, augment=True
                )
                if enh_f_dets:
                    all_results.append(enh_f_dets)

            models_executed.append("Forensic Trace (10-Class)")

    # Fallback to general YOLO if no models were loaded
    if not all_results:
        if GENERAL_MODEL_PATH.is_file():
            general_model = load_yolo_model(str(GENERAL_MODEL_PATH))
            gen_dets = run_yolo_on_image(
                general_model, raw_img, confidence, "General YOLO11", imgsz=optimal_imgsz, augment=True
            )
            all_results.append(gen_dets)
            models_executed.append("YOLO11 General")

    # Merge detections
    if len(all_results) > 1:
        merged_detections = merge_ensemble_detections(all_results, iou_threshold=iou_thresh)
    elif len(all_results) == 1:
        merged_detections = all_results[0]
    else:
        merged_detections = []

    inference_ms = round((time.perf_counter() - start_time) * 1000)

    return {
        "detections": merged_detections,
        "inference_ms": inference_ms,
        "image_width": w,
        "image_height": h,
        "models_executed": models_executed,
        "raw_image": raw_img,
    }
