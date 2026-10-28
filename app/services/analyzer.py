"""Forensic intelligence analyzer, threat assessment, and evidence crop extractor."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import CROPS_DIR, RESULT_DIR, get_evidence_metadata
from app.services.detector import draw_forensic_annotations


def extract_evidence_crops(
    image: np.ndarray,
    detections: list[dict[str, Any]],
    case_stem: str,
) -> list[dict[str, Any]]:
    """Crop individual detected evidence regions with context padding and save to disk."""
    h, w = image.shape[:2]
    enriched_detections: list[dict[str, Any]] = []

    for idx, item in enumerate(detections):
        box = item["box"]
        x1, y1, x2, y2 = [int(v) for v in box]

        # 10% context padding around bounding box
        box_w = max(1, x2 - x1)
        box_h = max(1, y2 - y1)
        pad_x = int(box_w * 0.10)
        pad_y = int(box_h * 0.10)

        crop_x1 = max(0, x1 - pad_x)
        crop_y1 = max(0, y1 - pad_y)
        crop_x2 = min(w, x2 + pad_x)
        crop_y2 = min(h, y2 + pad_y)

        crop_img = image[crop_y1:crop_y2, crop_x1:crop_x2]
        crop_filename = f"{case_stem}_item{idx + 1}_{uuid.uuid4().hex[:8]}.jpg"
        crop_save_path = CROPS_DIR / crop_filename

        crop_rel_path = ""
        if crop_img.size > 0:
            cv2.imwrite(str(crop_save_path), crop_img)
            crop_rel_path = f"crops/{crop_filename}"

        # Enrich with metadata
        meta = get_evidence_metadata(item["class"])
        item_copy = dict(item)
        item_copy["category"] = meta["category"]
        item_copy["severity"] = meta["severity"]
        item_copy["color"] = meta["color"]
        item_copy["crop_path"] = crop_rel_path
        item_copy["item_number"] = idx + 1
        item_copy["dimensions"] = f"{box_w} × {box_h} px"

        enriched_detections.append(item_copy)

    return enriched_detections


def assess_crime_scene_threat(detections: list[dict[str, Any]]) -> tuple[str, int, dict[str, int]]:
    """Calculate overall crime-scene danger level and category counts."""
    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "firearms": 0,
        "edged_weapons": 0,
        "biological": 0,
        "traces": 0,
    }

    score = 0
    for item in detections:
        severity = item.get("severity", "LOW")
        cat = item.get("category", "")

        if severity == "CRITICAL":
            counts["critical"] += 1
            score += 35
        elif severity == "HIGH":
            counts["high"] += 1
            score += 20
        elif severity == "MEDIUM":
            counts["medium"] += 1
            score += 10
        else:
            counts["low"] += 1
            score += 5

        if "Firearm" in cat or "Munition" in cat:
            counts["firearms"] += 1
        elif "Edged" in cat or "Blunt" in cat:
            counts["edged_weapons"] += 1
        elif "Biological" in cat or "Victim" in cat or "Remains" in cat:
            counts["biological"] += 1
        elif "Trace" in cat or "Print" in cat:
            counts["traces"] += 1

    threat_score = min(100, score)

    if not detections:
        threat_level = "CLEAR / UNVERIFIED"
    elif counts["critical"] > 0 or threat_score >= 70:
        threat_level = "CRITICAL"
    elif counts["high"] > 0 or threat_score >= 40:
        threat_level = "HIGH"
    elif counts["medium"] > 0 or threat_score >= 15:
        threat_level = "MEDIUM"
    else:
        threat_level = "LOW"

    return threat_level, threat_score, counts


def process_scene_analysis(
    raw_image: np.ndarray,
    detections: list[dict[str, Any]],
    case_stem: str,
) -> dict[str, Any]:
    """Execute complete forensic enrichment, crop generation, and annotated render."""
    # 1. Enrich detections and extract crops
    enriched_items = extract_evidence_crops(raw_image, detections, case_stem)

    # 2. Sort by confidence and severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    enriched_items.sort(key=lambda d: (severity_order.get(d["severity"], 4), -d["confidence"]))

    # 3. Assess scene threat
    threat_level, threat_score, category_counts = assess_crime_scene_threat(enriched_items)

    # 4. Generate high-res annotated forensic image
    annotated_bgr = draw_forensic_annotations(raw_image, enriched_items)
    annotated_filename = f"{case_stem}_annotated.jpg"
    annotated_path = RESULT_DIR / annotated_filename
    cv2.imwrite(str(annotated_path), annotated_bgr)

    return {
        "enriched_items": enriched_items,
        "threat_level": threat_level,
        "threat_score": threat_score,
        "category_counts": category_counts,
        "annotated_filename": annotated_filename,
        "annotated_rel_path": f"results/{annotated_filename}",
    }
