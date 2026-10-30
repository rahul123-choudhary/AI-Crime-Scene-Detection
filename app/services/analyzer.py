"""Forensic intelligence analyzer, threat assessment, and evidence crop extractor."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.config import CROPS_DIR, RESULT_DIR, get_evidence_metadata
from app.services.detector import draw_forensic_annotations


def infer_evidence_activity(
    item: dict[str, Any],
    all_detections: list[dict[str, Any]],
    img_h: int,
    img_w: int,
    person_idx: int = 0,
    total_persons: int = 1,
) -> str:
    """Infer contextual activity, posture, and operational state for detected evidence items."""
    cls_name = item.get("class", item.get("class_name", "")).lower()
    box = item.get("box", [0, 0, 0, 0])
    if len(box) >= 4:
        x1, y1, x2, y2 = [float(v) for v in box[:4]]
    else:
        x1, y1, x2, y2 = 0.0, 0.0, 0.0, 0.0

    box_w = max(1.0, x2 - x1)
    box_h = max(1.0, y2 - y1)
    aspect = box_h / box_w
    norm_h = box_h / max(1.0, float(img_h))
    bottom_y = y2 / max(1.0, float(img_h))

    # Detect adjacent or overlapping weapons
    has_weapon_nearby = False
    for other in all_detections:
        o_cls = other.get("class", other.get("class_name", "")).lower()
        if any(w in o_cls for w in ("knife", "gun", "pistol", "revolver", "firearm", "rifle", "weapon")):
            obox = other.get("box", [0, 0, 0, 0])
            if len(obox) >= 4:
                ox1, oy1, ox2, oy2 = [float(v) for v in obox[:4]]
                dx = max(0.0, max(x1, ox1) - min(x2, ox2))
                dy = max(0.0, max(y1, oy1) - min(y2, oy2))
                dist = (dx**2 + dy**2) ** 0.5
                if dist < 120.0:
                    has_weapon_nearby = True
                    break

    if "person" in cls_name or "suspect" in cls_name or "subject" in cls_name:
        if has_weapon_nearby:
            return "Armed Threat / Weapon Wielding Stance"

        # Fallen subject / potential casualty (grounded, horizontal orientation)
        if aspect < 0.9 and bottom_y > 0.6:
            return "Fallen Subject / Potential Casualty (Grounded)"

        # Low crouch or concealment posture
        if aspect < 1.35 and norm_h < 0.35:
            return "Crouching / Low-Profile Concealment"

        # Multi-person tactical formation
        if total_persons > 1:
            if person_idx == 0:
                return "Perimeter Ingress / Entry Portal Breach"
            elif person_idx == 1:
                return "Secondary Ingress / Trailing Formation"
            else:
                return f"Support Formation / Perimeter Sector #{person_idx + 1}"
        else:
            if bottom_y > 0.7:
                return "Active Traversal / Advancing into Scene"
            return "Perimeter Ingress / Advancing into Scene"

    # Weapon classifications
    if any(w in cls_name for w in ("gun", "pistol", "revolver", "firearm", "rifle")):
        return "Exposed Firearm / Active Ballistic Threat"
    if any(w in cls_name for w in ("knife", "blade", "dagger", "sword")):
        return "Drawn Edged Weapon / Lethal Contact Threat"

    # Traces & Biometric Evidence
    if "footprint" in cls_name or "shoe" in cls_name:
        return "Impression Vector / Ingress-Egress Movement Path"
    if "blood" in cls_name:
        return "Trauma Pattern / High-Velocity Impact Spatter"
    if "fingerprint" in cls_name:
        return "Latent Biometric Deposit / Surface Contact Ridge"
    if "casing" in cls_name or "bullet" in cls_name or "cartridge" in cls_name:
        return "Discharged Ballistic Munition / Point of Fire Indicator"
    if "hair" in cls_name:
        return "Trace Biological Transfer / Follicular Deposit"
    if "glass" in cls_name:
        return "Forced Entry Impact / Fractured Barrier Shards"
    if "backpack" in cls_name or "bag" in cls_name:
        return "Carried Concealment Gear / Ingress Transport Item"
    if "phone" in cls_name:
        return "Digital Device / Electronic Telecommunication Trace"
    if any(v in cls_name for v in ("car", "truck", "motorcycle", "vehicle")):
        return "Transit Vehicle / Ingress-Egress Transport Vector"

    return "Physical Evidence / Forensic Marker"


def generate_scene_narrative(
    enriched_items: list[dict[str, Any]],
    threat_level: str,
    threat_score: int,
) -> str:
    """Generate high-fidelity forensic dynamics narrative explaining observed actions."""
    if not enriched_items:
        return "No verifiable subjects or forensic evidence items detected. Perimeter appears secure and clear."

    persons = [item for item in enriched_items if "person" in item.get("class", item.get("class_name", "")).lower()]
    weapons = [
        item for item in enriched_items
        if any(w in item.get("class", item.get("class_name", "")).lower() for w in ("gun", "knife", "pistol", "revolver", "firearm", "rifle", "weapon"))
    ]
    traces = [
        item for item in enriched_items
        if any(t in item.get("class", item.get("class_name", "")).lower() for t in ("footprint", "blood", "fingerprint", "casing", "bullet", "hair"))
    ]

    parts: list[str] = []

    if len(persons) >= 2:
        act1 = persons[0].get("activity", "Perimeter Ingress / Entry Portal Breach")
        act2 = persons[1].get("activity", "Secondary Ingress / Trailing Formation")
        parts.append(
            f"Multi-subject tactical activity detected ({len(persons)} persons in frame). "
            f"Lead subject (#1) is observed in '{act1}', followed closely by secondary subject (#2) in '{act2}'."
        )
    elif len(persons) == 1:
        act = persons[0].get("activity", "Active Traversal / Advancing into Scene")
        parts.append(
            f"Single subject identified within the sector exhibiting '{act}'."
        )

    if weapons:
        weap_names = ", ".join(sorted(set(w.get("class", w.get("class_name", "")) for w in weapons)))
        parts.append(
            f"High-threat weapon assets ({weap_names}) isolated on scene, escalating threat assessment to {threat_level} ({threat_score}/100)."
        )

    if traces:
        trace_names = ", ".join(sorted(set(t.get("class", t.get("class_name", "")) for t in traces)))
        parts.append(
            f"Latent physical forensic vectors recovered: {trace_names}, corroborating contact dynamics."
        )

    if not parts:
        parts.append(
            f"Sector analysis cataloged {len(enriched_items)} evidence items with aggregate Threat Index of {threat_score}/100 ({threat_level})."
        )

    return " ".join(parts)


def extract_evidence_crops(
    image: np.ndarray,
    detections: list[dict[str, Any]],
    case_stem: str,
) -> list[dict[str, Any]]:
    """Crop individual detected evidence regions with context padding and save to disk."""
    h, w = image.shape[:2]
    enriched_detections: list[dict[str, Any]] = []

    # Count total persons for formation intelligence
    total_persons = sum(
        1 for it in detections if "person" in it.get("class", it.get("class_name", "")).lower()
    )
    person_idx = 0

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

        # Determine activity
        cls_lower = item.get("class", item.get("class_name", "")).lower()
        if "person" in cls_lower:
            activity = infer_evidence_activity(item, detections, h, w, person_idx, total_persons)
            person_idx += 1
        else:
            activity = infer_evidence_activity(item, detections, h, w)

        # Enrich with metadata
        meta = get_evidence_metadata(item["class"])
        item_copy = dict(item)
        item_copy["category"] = meta["category"]
        item_copy["severity"] = meta["severity"]
        item_copy["color"] = meta["color"]
        item_copy["crop_path"] = crop_rel_path
        item_copy["item_number"] = idx + 1
        item_copy["dimensions"] = f"{box_w} × {box_h} px"
        item_copy["activity"] = activity

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

    # 4. Synthesize AI behavioral scene narrative
    scene_narrative = generate_scene_narrative(enriched_items, threat_level, threat_score)

    # 5. Generate high-res annotated forensic image
    annotated_bgr = draw_forensic_annotations(raw_image, enriched_items)
    annotated_filename = f"{case_stem}_annotated.jpg"
    annotated_path = RESULT_DIR / annotated_filename
    cv2.imwrite(str(annotated_path), annotated_bgr)

    return {
        "enriched_items": enriched_items,
        "threat_level": threat_level,
        "threat_score": threat_score,
        "category_counts": category_counts,
        "scene_narrative": scene_narrative,
        "annotated_filename": annotated_filename,
        "annotated_rel_path": f"results/{annotated_filename}",
    }
