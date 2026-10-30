"""Forensic video processing service for recorded footage and real-time camera streaming."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Generator

import cv2
import numpy as np

from app.config import (
    CROPS_DIR,
    DEFAULT_CONFIDENCE,
    DEFAULT_IOU,
    FORENSIC_MODEL_PATH,
    GENERAL_MODEL_PATH,
    RESULT_DIR,
    VIDEO_FRAME_STRIDE,
    WEAPON_MODEL_PATH,
    get_evidence_metadata,
)
from app.services.analyzer import assess_crime_scene_threat
from app.services.detector import (
    draw_forensic_annotations,
    load_yolo_model,
    merge_ensemble_detections,
    run_yolo_on_image,
)


def run_yolo_on_frame(
    frame: np.ndarray,
    model_choice: str = "ensemble",
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[dict[str, Any]]:
    """Run model inference directly on an in-memory NumPy frame with accurate multi-model ensemble."""
    h, w = frame.shape[:2]
    total_area = float(h * w)
    all_results: list[list[dict[str, Any]]] = []

    model_choice = model_choice.lower().strip()

    # 1. Specialized Weapons Detector
    if model_choice in ("weapon", "ensemble") and WEAPON_MODEL_PATH.is_file():
        weapon_model = load_yolo_model(str(WEAPON_MODEL_PATH))
        res = weapon_model.predict(frame, conf=confidence, imgsz=640, augment=False, save=False, verbose=False)[0]
        dets: list[dict[str, Any]] = []
        for box in res.boxes:
            cls_name = str(res.names[int(box.cls[0])])
            conf_val = round(float(box.conf[0]) * 100, 1)
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            dets.append(
                {
                    "class": cls_name,
                    "confidence": conf_val,
                    "box": [round(c, 1) for c in xyxy],
                    "norm_box": [
                        round(xyxy[0] / w, 4),
                        round(xyxy[1] / h, 4),
                        round(xyxy[2] / w, 4),
                        round(xyxy[3] / h, 4),
                    ],
                    "source_model": "Weapon Detector",
                }
            )
        if dets:
            all_results.append(dets)

    # 2. General Scene, Suspects & Persons (YOLO11)
    if model_choice in ("weapon", "ensemble") and GENERAL_MODEL_PATH.is_file():
        allowed_coco = {
            "person", "knife", "scissors", "baseball bat", "backpack",
            "handbag", "suitcase", "cell phone", "laptop", "car",
            "motorcycle", "truck", "bottle"
        }
        gen_model = load_yolo_model(str(GENERAL_MODEL_PATH))
        res = gen_model.predict(frame, conf=max(0.30, confidence), imgsz=640, augment=False, save=False, verbose=False)[0]
        gen_dets: list[dict[str, Any]] = []
        for box in res.boxes:
            cls_name = str(res.names[int(box.cls[0])])
            if cls_name not in allowed_coco:
                continue
            conf_val = round(float(box.conf[0]) * 100, 1)
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            gen_dets.append(
                {
                    "class": cls_name,
                    "confidence": conf_val,
                    "box": [round(c, 1) for c in xyxy],
                    "norm_box": [
                        round(xyxy[0] / w, 4),
                        round(xyxy[1] / h, 4),
                        round(xyxy[2] / w, 4),
                        round(xyxy[3] / h, 4),
                    ],
                    "source_model": "Scene & Subjects (YOLO11)",
                }
            )
        if gen_dets:
            all_results.append(gen_dets)

    # 3. Forensic Traces (filtering out corrupted Human-hair)
    if model_choice in ("forensic", "ensemble") and FORENSIC_MODEL_PATH.is_file():
        forensic_model = load_yolo_model(str(FORENSIC_MODEL_PATH))
        res = forensic_model.predict(frame, conf=confidence, imgsz=640, augment=False, save=False, verbose=False)[0]
        dets = []
        for box in res.boxes:
            cls_name = str(res.names[int(box.cls[0])])
            if cls_name == "Human-hair":
                continue
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            box_area = (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1])
            if cls_name in ("Finger-print", "Shoe-print", "Glass") and total_area > 0 and (box_area / total_area) > 0.20:
                continue
            conf_val = round(float(box.conf[0]) * 100, 1)
            dets.append(
                {
                    "class": cls_name,
                    "confidence": conf_val,
                    "box": [round(c, 1) for c in xyxy],
                    "norm_box": [
                        round(xyxy[0] / w, 4),
                        round(xyxy[1] / h, 4),
                        round(xyxy[2] / w, 4),
                        round(xyxy[3] / h, 4),
                    ],
                    "source_model": "Forensic Trace",
                }
            )
        if dets:
            all_results.append(dets)

    if len(all_results) > 1:
        merged = merge_ensemble_detections(all_results, iou_threshold=DEFAULT_IOU)
    elif len(all_results) == 1:
        merged = all_results[0]
    else:
        merged = []

    # Enrich each detection with category, severity, and color
    enriched: list[dict[str, Any]] = []
    for item in merged:
        meta = get_evidence_metadata(item["class"])
        item_copy = dict(item)
        item_copy["category"] = meta["category"]
        item_copy["severity"] = meta["severity"]
        item_copy["color"] = meta["color"]
        enriched.append(item_copy)

    return enriched


def process_crime_scene_video(
    video_path: Path,
    case_id: str,
    model_choice: str = "ensemble",
    confidence: float = DEFAULT_CONFIDENCE,
    frame_stride: int = VIDEO_FRAME_STRIDE,
) -> dict[str, Any]:
    """Process an uploaded video, annotate frames, extract timeline events and crops."""
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    duration_sec = round(total_frames / fps, 2) if total_frames > 0 else 0.0

    output_filename = f"{case_id}_annotated.mp4"
    output_path = RESULT_DIR / output_filename

    # Video writer with mp4v codec
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_idx = 0
    timeline_events: list[dict[str, Any]] = []
    all_seen_detections: list[dict[str, Any]] = []
    last_frame_detections: list[dict[str, Any]] = []
    saved_crops_classes: set[str] = set()

    start_time = time.perf_counter()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_sec = round(frame_idx / fps, 2)
        mins = int(timestamp_sec // 60)
        secs = int(timestamp_sec % 60)
        timecode = f"{mins:02d}:{secs:02d}"

        # Detect on stride
        if frame_idx % frame_stride == 0:
            last_frame_detections = run_yolo_on_frame(
                frame, model_choice=model_choice, confidence=confidence
            )

            # Record timeline events for prominent detections
            for d in last_frame_detections:
                all_seen_detections.append(d)
                cls_name = d["class"]

                # Extract crop for unique or high-confidence events (up to 8 total)
                crop_rel_path = ""
                if cls_name not in saved_crops_classes or len(saved_crops_classes) < 8:
                    box = [int(v) for v in d["box"]]
                    pad_x = int((box[2] - box[0]) * 0.1)
                    pad_y = int((box[3] - box[1]) * 0.1)
                    c_x1 = max(0, box[0] - pad_x)
                    c_y1 = max(0, box[1] - pad_y)
                    c_x2 = min(width, box[2] + pad_x)
                    c_y2 = min(height, box[3] + pad_y)
                    crop = frame[c_y1:c_y2, c_x1:c_x2]
                    if crop.size > 0:
                        crop_filename = f"{case_id}_vid_{frame_idx}_{uuid.uuid4().hex[:6]}.jpg"
                        cv2.imwrite(str(CROPS_DIR / crop_filename), crop)
                        crop_rel_path = f"crops/{crop_filename}"
                        saved_crops_classes.add(cls_name)

                # Add to timeline event if confidence > 35%
                timeline_events.append(
                    {
                        "class": cls_name,
                        "class_name": cls_name,
                        "category": d["category"],
                        "severity": d["severity"],
                        "confidence": d["confidence"],
                        "box": d["box"],
                        "bbox_x1": d["box"][0],
                        "bbox_y1": d["box"][1],
                        "bbox_x2": d["box"][2],
                        "bbox_y2": d["box"][3],
                        "video_timestamp": timestamp_sec,
                        "timecode": timecode,
                        "crop_path": crop_rel_path,
                    }
                )

        # Draw annotations on frame
        annotated_frame = draw_forensic_annotations(frame, last_frame_detections)

        # Watermark: Tactical HUD
        hud_text = f"REC [LIVE EVIDENCE] | TIME: {timecode} | OBJECTS: {len(last_frame_detections)}"
        cv2.putText(
            annotated_frame,
            hud_text,
            (14, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (56, 189, 248),
            2,
            cv2.LINE_AA,
        )

        out.write(annotated_frame)
        frame_idx += 1

    cap.release()
    out.release()

    elapsed_sec = round(time.perf_counter() - start_time, 2)

    # Deduplicate timeline events to key moments (keep highest confidence per class per second)
    unique_timeline: list[dict[str, Any]] = []
    seen_second_class: set[tuple[int, str]] = set()
    for ev in timeline_events:
        sec_bucket = int(ev["video_timestamp"])
        pair = (sec_bucket, ev["class"])
        if pair not in seen_second_class:
            seen_second_class.add(pair)
            unique_timeline.append(ev)

    # Assess overall peak threat
    threat_level, threat_score, category_counts = assess_crime_scene_threat(all_seen_detections)

    return {
        "case_id": case_id,
        "video_duration": duration_sec,
        "total_frames": frame_idx,
        "processing_time_sec": elapsed_sec,
        "annotated_video_path": f"results/{output_filename}",
        "annotated_filename": output_filename,
        "threat_level": threat_level,
        "threat_score": threat_score,
        "category_counts": category_counts,
        "timeline_events": unique_timeline[:40],  # top timeline markers
        "evidence_items": unique_timeline[:40],
    }


def generate_camera_stream(
    device_id: int = 0,
    model_choice: str = "ensemble",
    confidence: float = DEFAULT_CONFIDENCE,
) -> Generator[bytes, None, None]:
    """Yield multipart JPEG frames for server-side camera streaming."""
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        # Yield an error placeholder frame
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(
            blank,
            "CAMERA DEVICE NOT DETECTED (USE BROWSER WEBCAM)",
            (30, 240),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (0, 0, 255),
            2,
        )
        _, buffer = cv2.imencode(".jpg", blank)
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n")
        return

    try:
        frame_count = 0
        last_dets: list[dict[str, Any]] = []
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % 3 == 0:
                last_dets = run_yolo_on_frame(frame, model_choice=model_choice, confidence=confidence)

            annotated = draw_forensic_annotations(frame, last_dets)

            # Draw HUD
            cv2.putText(
                annotated,
                "LIVE FORENSIC CAMERA STREAM",
                (14, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (56, 189, 248),
                2,
                cv2.LINE_AA,
            )

            _, buffer = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            frame_count += 1
            time.sleep(0.04)  # ~25 fps cap
    finally:
        cap.release()


def get_webcam_frame(device_id: int = 0) -> np.ndarray | None:
    """Capture a single frame from the local webcam device."""
    cap = cv2.VideoCapture(device_id)
    if not cap.isOpened():
        return None
    try:
        ret, frame = cap.read()
        return frame if ret else None
    finally:
        cap.release()

