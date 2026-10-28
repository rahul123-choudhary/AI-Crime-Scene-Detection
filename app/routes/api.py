"""REST API v1 endpoints for crime scene evidence detection and case retrieval."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from flask import Blueprint, jsonify, request, url_for
from werkzeug.utils import secure_filename

from app.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_VIDEO_EXTENSIONS,
    DEFAULT_CONFIDENCE,
    DEFAULT_IOU,
    FORENSIC_MODEL_PATH,
    GENERAL_MODEL_PATH,
    RESULT_DIR,
    SAMPLES_DIR,
    STATIC_DIR,
    UPLOAD_DIR,
    WEAPON_MODEL_PATH,
)
from app.database import (
    backup_sqlite_database,
    get_analytics_summary,
    get_case_by_id,
    list_cases,
    list_database_backups,
    record_analytics_event,
)
from app.services.analyzer import process_scene_analysis
from app.services.detector import detect_evidence
from app.services.enhancer import (
    apply_clahe_enhancement,
    apply_low_light_boost,
    apply_unsharp_mask,
    enhance_forensic_image,
    generate_and_save_clarity_suite,
    measure_image_clarity,
)


api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@api_bp.get("/health")
def health_check() -> Any:
    """System health, GPU status, and loaded model checkpoints."""
    return jsonify(
        {
            "status": "healthy",
            "service": "AI Crime Scene Detection Engine",
            "version": "2.0.0",
            "cuda_available": torch.cuda.is_available(),
            "device": "CUDA" if torch.cuda.is_available() else "CPU",
            "models": {
                "weapon_detector": {
                    "available": WEAPON_MODEL_PATH.is_file(),
                    "path": str(WEAPON_MODEL_PATH.name),
                },
                "forensic_detector": {
                    "available": FORENSIC_MODEL_PATH.is_file(),
                    "path": str(FORENSIC_MODEL_PATH.name),
                },
                "general_detector": {
                    "available": GENERAL_MODEL_PATH.is_file(),
                    "path": str(GENERAL_MODEL_PATH.name),
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.post("/detect")
def api_detect() -> Any:
    """Programmatic evidence detection endpoint."""
    if "image" not in request.files:
        return jsonify({"error": "Missing 'image' file in multipart/form-data payload"}), 400

    file = request.files["image"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format. Provide JPG, PNG, or WEBP."}), 400

    # Read bytes and validate image
    image_bytes = file.read()
    raw_img = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
    if raw_img is None:
        return jsonify({"error": "Uploaded payload could not be decoded as an image."}), 400

    # Parse parameters
    model_choice = request.form.get("model", "ensemble")
    try:
        confidence = float(request.form.get("confidence", DEFAULT_CONFIDENCE))
        confidence = max(0.10, min(confidence, 0.95))
    except ValueError:
        confidence = DEFAULT_CONFIDENCE

    case_id = f"CRIME-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    safe_stem = Path(secure_filename(file.filename)).stem or "evidence"
    upload_name = f"{case_id}_{safe_stem}.jpg"
    upload_path = UPLOAD_DIR / upload_name

    cv2.imwrite(str(upload_path), raw_img)

    # Forensic clarity measurement and optional auto-enhancement
    auto_enhance = request.form.get("auto_enhance", "true").lower() in ("true", "1", "yes", "on")
    clarity_info = measure_image_clarity(raw_img)
    detection_path = upload_path
    enhanced_url = None

    if auto_enhance or clarity_info["quality_score"] < 65.0:
        enh_res = enhance_forensic_image(raw_img, mode="full_forensic")
        enhanced_name = f"{case_id}_enhanced.jpg"
        enhanced_path = UPLOAD_DIR / enhanced_name
        cv2.imwrite(str(enhanced_path), enh_res["enhanced_image"], [cv2.IMWRITE_JPEG_QUALITY, 96])
        detection_path = enhanced_path
        enhanced_url = url_for("static", filename=f"uploads/{enhanced_name}", _external=True)

    # Pre-generate clarity suite
    generate_and_save_clarity_suite(raw_img, RESULT_DIR, case_id)

    try:
        det_result = detect_evidence(
            detection_path,
            model_choice=model_choice,
            confidence=confidence,
            iou_thresh=DEFAULT_IOU,
        )
        analysis_result = process_scene_analysis(raw_img, det_result["detections"], case_id)
    except Exception as exc:
        return jsonify({"error": f"Detection failed: {str(exc)}"}), 500

    detections = analysis_result["enriched_items"]
    for item in detections:
        if item.get("crop_path"):
            item["crop_url"] = url_for("static", filename=item["crop_path"], _external=True)

    return jsonify(
        {
            "case_id": case_id,
            "threat_level": analysis_result["threat_level"],
            "threat_score": analysis_result["threat_score"],
            "evidence_count": len(detections),
            "inference_ms": det_result["inference_ms"],
            "models_executed": det_result["models_executed"],
            "image_dimensions": {
                "width": det_result["image_width"],
                "height": det_result["image_height"],
            },
            "clarity_score": clarity_info["quality_score"],
            "clarity_metrics": clarity_info,
            "enhanced_image_url": enhanced_url,
            "clarity_variants": {
                "full_enhanced": url_for("static", filename=f"results/{case_id}_full_enhanced.jpg", _external=True),
                "clahe": url_for("static", filename=f"results/{case_id}_clahe.jpg", _external=True),
                "sharpened": url_for("static", filename=f"results/{case_id}_sharpened.jpg", _external=True),
                "night_vision": url_for("static", filename=f"results/{case_id}_night_vision.jpg", _external=True),
            },
            "annotated_image_url": url_for(
                "static", filename=analysis_result["annotated_rel_path"], _external=True
            ),
            "detections": detections,
            "category_counts": analysis_result["category_counts"],
        }
    )


@api_bp.get("/cases")
def api_list_cases() -> Any:
    """Retrieve indexed forensic cases."""
    query = request.args.get("q", "")
    threat = request.args.get("threat", "")
    limit = min(100, max(1, int(request.args.get("limit", 20))))
    offset = max(0, int(request.args.get("offset", 0)))

    cases = list_cases(limit=limit, offset=offset, query=query, threat=threat)
    return jsonify({"count": len(cases), "cases": cases})


@api_bp.get("/cases/<case_id>")
def api_get_case(case_id: str) -> Any:
    """Retrieve full detail for a specific case."""
    case = get_case_by_id(case_id)
    if not case:
        return jsonify({"error": f"Case not found: {case_id}"}), 404
    return jsonify(case)


@api_bp.post("/detect_frame")
def api_detect_frame() -> Any:
    """Ultra-low latency inference for real-time live webcam streams."""
    import base64
    import time
    from app.services.analyzer import assess_crime_scene_threat
    from app.services.video_service import run_yolo_on_frame

    start = time.perf_counter()
    raw_img: np.ndarray | None = None

    # 1. Try base64 from JSON payload
    if request.is_json:
        payload = request.get_json() or {}
        b64_str = payload.get("frame_base64", "")
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        if b64_str:
            try:
                img_bytes = base64.b64decode(b64_str)
                raw_img = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception:
                raw_img = None

    # 2. Try multipart file
    if raw_img is None:
        file = request.files.get("frame") or request.files.get("image")
        if file and file.filename:
            img_bytes = file.read()
            raw_img = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    if raw_img is None:
        return jsonify({"error": "No valid image frame payload provided."}), 400

    model_choice = request.values.get("model", "ensemble") if not request.is_json else request.get_json().get("model", "ensemble")
    try:
        conf_val = float(request.values.get("confidence", DEFAULT_CONFIDENCE) if not request.is_json else request.get_json().get("confidence", DEFAULT_CONFIDENCE))
    except ValueError:
        conf_val = DEFAULT_CONFIDENCE

    detections = run_yolo_on_frame(raw_img, model_choice=model_choice, confidence=conf_val)
    threat_level, threat_score, category_counts = assess_crime_scene_threat(detections)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    return jsonify(
        {
            "detections": detections,
            "threat_level": threat_level,
            "threat_score": threat_score,
            "category_counts": category_counts,
            "latency_ms": latency_ms,
            "count": len(detections),
            "frame_width": raw_img.shape[1],
            "frame_height": raw_img.shape[0],
        }
    )


@api_bp.post("/auto_detect_metadata")
def api_auto_detect_metadata() -> Any:
    """Instant AI Pre-Scan: visually analyzes uploaded photo or video frame and

    auto-generates all 6 forensic parameters (Engine, Confidence,
    Investigator, Location, Title, Incident Classification) based on detected
    evidence.
    """
    import base64
    import time
    from app.services.analyzer import assess_crime_scene_threat
    from app.services.video_service import run_yolo_on_frame

    start = time.perf_counter()
    raw_img: np.ndarray | None = None
    is_video = request.values.get("is_video", "false").lower() in ("true", "1", "yes")
    filename = request.values.get("filename", "")
    sample_name = request.values.get("sample", "")

    # 1. Check sample file if provided
    if sample_name:
        sample_path = SAMPLES_DIR / secure_filename(sample_name)
        if sample_path.is_file():
            if sample_path.suffix.lstrip(".").lower() in ALLOWED_VIDEO_EXTENSIONS:
                is_video = True
                cap = cv2.VideoCapture(str(sample_path))
                success, frame = cap.read()
                cap.release()
                if success:
                    raw_img = frame
            else:
                raw_img = cv2.imread(str(sample_path))

    # 2. Base64 payload in JSON
    if raw_img is None and request.is_json:
        payload = request.get_json() or {}
        b64_str = payload.get("frame_base64", "") or payload.get("image_base64", "")
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        if b64_str:
            try:
                img_bytes = base64.b64decode(b64_str)
                raw_img = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception:
                raw_img = None
        if "is_video" in payload:
            is_video = bool(payload["is_video"])
        if "filename" in payload:
            filename = payload["filename"]

    # 3. Multipart file upload
    if raw_img is None:
        file = (
            request.files.get("file")
            or request.files.get("image")
            or request.files.get("frame")
            or request.files.get("video")
        )
        if file and file.filename:
            filename = file.filename
            ext = Path(file.filename).suffix.lstrip(".").lower()
            if ext in ALLOWED_VIDEO_EXTENSIONS:
                is_video = True
                temp_vid_path = UPLOAD_DIR / f"temp_prescan_{uuid.uuid4().hex[:6]}.{ext}"
                file.save(str(temp_vid_path))
                cap = cv2.VideoCapture(str(temp_vid_path))
                success, frame = cap.read()
                cap.release()
                temp_vid_path.unlink(missing_ok=True)
                if success:
                    raw_img = frame
            else:
                img_bytes = file.read()
                raw_img = cv2.imdecode(np.frombuffer(img_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    # Fallback placeholder if video couldn't read frame
    if raw_img is None and not is_video:
        return jsonify({"error": "Unable to decode visual media for AI pre-scan."}), 400

    # 4. Run multi-model detection on the frame if available
    detections: list[dict[str, Any]] = []
    if raw_img is not None:
        detections = run_yolo_on_frame(raw_img, model_choice="ensemble", confidence=0.18)

    threat_level, threat_score, category_counts = assess_crime_scene_threat(detections)

    # Classify detected items
    weapon_classes = {
        "gun", "pistol", "handgun", "rifle", "shotgun", "knife", "blade",
        "submachine-gun", "revolver", "grenade", "rocket", "hammer", "blunt-object"
    }
    trace_classes = {
        "blood", "blood-splatter", "bloodstain", "footprint", "fingerprint",
        "hair", "glass", "shell-casing", "bullet-casing", "cartridge"
    }
    homicide_classes = {"body", "corpse", "victim"}

    detected_weapons = [d["class"] for d in detections if d["class"].lower() in weapon_classes]
    detected_traces = [d["class"] for d in detections if d["class"].lower() in trace_classes]
    detected_severe = [d["class"] for d in detections if d["class"].lower() in homicide_classes]

    unique_items = sorted(list(set(d["class"] for d in detections)))
    unique_items_str = ", ".join(unique_items) if unique_items else "No immediate weapons/traces"

    # Clean filename fallback for subject
    clean_name = ""
    if filename:
        stem = Path(filename).stem
        clean_name = stem.replace("-", " ").replace("_", " ").title()

    # Determine optimal parameters based on actual AI visual analysis
    if is_video:
        rec_model = "ensemble"
        rec_conf = 0.30
        rec_conf_pct = "30%"
        rec_investigator = "CCTV & Video Forensics Specialist"
        rec_location = "Perimeter CCTV Surveillance Feed"
        rec_incident = "CCTV / Video Surveillance Sweep"
        if detected_weapons:
            rec_title = f"Video Evidence: Motion Detection ({', '.join(set(detected_weapons))})"
        else:
            rec_title = f"CCTV Video Sweep: {clean_name or 'Security Footage Analysis'}"
        rec_explanation = "AI identified video footage. Motion-stabilized 30% threshold applied to filter compression noise across frames."
        badge_style = "video"
        badge_engine = "Surveillance Suite"
        badge_conf = "30% Noise Filter"

    elif detected_severe or (detected_weapons and detected_traces):
        rec_model = "ensemble"
        rec_conf = 0.20
        rec_conf_pct = "20%"
        rec_investigator = "Senior Homicide Detective & CSI Lead"
        rec_location = "Primary Homicide Scene / Incident Perimeter"
        rec_incident = "Homicide Investigation"
        rec_title = f"Homicide Sweep: {unique_items_str} Identified"
        rec_explanation = f"AI visually detected critical multi-evidence ({unique_items_str}). Dual-Ensemble configured with 20% high-sensitivity sweep."
        badge_style = "homicide"
        badge_engine = "Dual Ensemble"
        badge_conf = "20% Sensitive"

    elif detected_weapons:
        rec_model = "weapon"
        rec_conf = 0.25
        rec_conf_pct = "25%"
        rec_investigator = "Ballistics & Firearms Forensic Specialist"
        rec_location = "Primary Firearms Recovery Scene"
        rec_incident = "Armed Assault / Violent Incident"
        rec_title = f"Armed Incident: {', '.join(set(detected_weapons))} Recovery Sweep"
        rec_explanation = f"AI visually detected weaponry ({', '.join(set(detected_weapons))}). Specialized Weapon Engine engaged with 25% precision threshold."
        badge_style = "weapon"
        badge_engine = "Weapon Specialist"
        badge_conf = "25% Ballistics"

    elif detected_traces:
        rec_model = "forensic"
        rec_conf = 0.15
        rec_conf_pct = "15%"
        rec_investigator = "Latent Print & Serology Specialist"
        rec_location = "Forensic Surface & Trace Examination Sector"
        rec_incident = "Biological & Latent Trace Sweep"
        rec_title = f"Biological Trace Sweep: {', '.join(set(detected_traces))} Analysis"
        rec_explanation = f"AI visually detected latent traces ({', '.join(set(detected_traces))}). High-Sensitivity 15% threshold engaged for faint biological evidence."
        badge_style = "trace"
        badge_engine = "Trace Specialist"
        badge_conf = "15% High Sensitivity"

    else:
        rec_model = "ensemble"
        rec_conf = 0.25
        rec_conf_pct = "25%"
        rec_investigator = "Forensic Crime Scene Investigator"
        rec_location = "Sector 4 Scene Investigation"
        rec_incident = "Suspicious Scene Audit"
        rec_title = f"Crime Scene Evidence Sweep: {clean_name or 'Visual Inspection'}"
        rec_explanation = "AI visual pre-scan completed. Dual-Ensemble engine engaged with balanced 25% threshold for complete scene sweep."
        badge_style = ""
        badge_engine = "Dual Ensemble"
        badge_conf = "25% Balanced"

    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    return jsonify({
        "success": True,
        "latency_ms": latency_ms,
        "is_video": is_video,
        "threat_level": threat_level,
        "threat_score": threat_score,
        "detected_items": unique_items,
        "evidence_count": len(detections),
        "fields": {
            "model": rec_model,
            "confidence": rec_conf,
            "confidence_pct": rec_conf_pct,
            "investigator": rec_investigator,
            "location": rec_location,
            "title": rec_title,
            "incident_type": rec_incident,
        },
        "badges": {
            "style": badge_style,
            "engine": badge_engine,
            "confidence": badge_conf,
            "investigator": rec_investigator.split()[0] + " Specialist",
            "location": rec_location.split("/")[0].strip(),
            "title": "AI Generated",
            "incident": rec_incident.split("/")[0].strip(),
        },
        "explanation": rec_explanation,
    })


@api_bp.post("/enhance")
def api_enhance() -> Any:
    """Forensic image enhancement & de-blurring API.

    Accepts:
      - 'image' multipart file OR 'case_id' parameter OR base64 'frame'
      - 'mode': 'full' | 'clahe' | 'sharpen' | 'night_vision' | 'all'
      - 'clahe_clip': float (default 3.0)
      - 'sharpen_strength': float (default 1.5)
      - 'low_light_boost': bool (default True)
      - 'denoise': bool (default True)
    """
    raw_img: np.ndarray | None = None
    case_id: str | None = None

    # 1. Check if case_id provided
    req_case_id = request.values.get("case_id") or (request.json.get("case_id") if request.is_json else None)
    if req_case_id:
        case = get_case_by_id(req_case_id)
        if not case:
            return jsonify({"error": f"Case not found: {req_case_id}"}), 404
        case_id = req_case_id
        src_path = STATIC_DIR / case["image_path"]
        if not src_path.is_file():
            src_path = UPLOAD_DIR / Path(case["image_path"]).name
        if src_path.is_file():
            if src_path.suffix.lstrip(".").lower() in ALLOWED_VIDEO_EXTENSIONS:
                cap = cv2.VideoCapture(str(src_path))
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret:
                        raw_img = frame
                cap.release()
            else:
                raw_img = cv2.imread(str(src_path))

    # 2. Check if file uploaded
    if raw_img is None and "image" in request.files:
        file = request.files["image"]
        if file.filename:
            image_bytes = file.read()
            raw_img = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)

    # 3. Check if base64 frame provided
    if raw_img is None and request.is_json:
        frame_b64 = request.json.get("frame")
        if frame_b64:
            if "," in frame_b64:
                frame_b64 = frame_b64.split(",", 1)[1]
            try:
                import base64
                decoded = base64.b64decode(frame_b64)
                raw_img = cv2.imdecode(np.frombuffer(decoded, dtype=np.uint8), cv2.IMREAD_COLOR)
            except Exception as e:
                return jsonify({"error": f"Invalid base64 frame: {e}"}), 400

    if raw_img is None:
        return jsonify({"error": "No valid image payload or case_id provided"}), 400

    if not case_id:
        case_id = f"ENH-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    # Parse parameters
    mode = (request.values.get("mode") or (request.json.get("mode") if request.is_json else "full")).lower()
    try:
        clahe_clip = float(request.values.get("clahe_clip") or (request.json.get("clahe_clip", 3.0) if request.is_json else 3.0))
    except (ValueError, TypeError):
        clahe_clip = 3.0

    try:
        sharpen_strength = float(request.values.get("sharpen_strength") or (request.json.get("sharpen_strength", 1.5) if request.is_json else 1.5))
    except (ValueError, TypeError):
        sharpen_strength = 1.5

    low_light_boost = str(request.values.get("low_light_boost", "true")).lower() in ("true", "1", "yes")
    denoise = str(request.values.get("denoise", "true")).lower() in ("true", "1", "yes")

    before_metrics = measure_image_clarity(raw_img)

    if mode == "all":
        paths = generate_and_save_clarity_suite(raw_img, RESULT_DIR, case_id)
        full_enh_rel = paths.get("full_enhanced", "")
        full_enh_abs = RESULT_DIR.parent / full_enh_rel if full_enh_rel else None
        after_img = cv2.imread(str(full_enh_abs)) if (full_enh_abs and full_enh_abs.is_file()) else raw_img
        after_metrics = measure_image_clarity(after_img)
        gain_pct = round(((after_metrics["sharpness"] - before_metrics["sharpness"]) / max(1e-6, before_metrics["sharpness"])) * 100, 1)

        variants = {
            k: url_for("static", filename=v, _external=True)
            for k, v in paths.items()
        }
        return jsonify({
            "success": True,
            "case_id": case_id,
            "mode": "all",
            "before_metrics": before_metrics,
            "after_metrics": after_metrics,
            "sharpness_gain_pct": gain_pct,
            "variants": variants,
            "enhanced_url": variants.get("full_enhanced"),
        })

    # Single mode enhancement
    if mode == "clahe":
        enhanced = apply_clahe_enhancement(raw_img, clip_limit=clahe_clip)
        tag = "clahe"
    elif mode == "sharpen":
        enhanced = apply_unsharp_mask(raw_img, strength=sharpen_strength)
        tag = "sharpened"
    elif mode == "night_vision":
        enhanced = apply_low_light_boost(raw_img)
        tag = "night_vision"
    else:
        res = enhance_forensic_image(
            raw_img,
            mode="full_forensic",
            clahe_clip=clahe_clip,
            sharpen_strength=sharpen_strength,
            low_light_boost=low_light_boost,
            denoise=denoise,
        )
        enhanced = res["enhanced_image"]
        tag = "full_enhanced"

    out_name = f"{case_id}_{tag}.jpg"
    out_path = RESULT_DIR / out_name
    cv2.imwrite(str(out_path), enhanced, [cv2.IMWRITE_JPEG_QUALITY, 96])

    after_metrics = measure_image_clarity(enhanced)
    gain_pct = round(((after_metrics["laplacian_variance"] - before_metrics["laplacian_variance"]) / max(1e-6, before_metrics["laplacian_variance"])) * 100, 1)

    return jsonify({
        "success": True,
        "case_id": case_id,
        "mode": tag,
        "before_metrics": before_metrics,
        "after_metrics": after_metrics,
        "sharpness_gain_pct": gain_pct,
        "enhanced_url": url_for("static", filename=f"results/{out_name}", _external=True),
    })


@api_bp.get("/firebase/status")
def api_firebase_status() -> Any:
    """Check connectivity and credentials status of Firebase Cloud Services."""
    from app.services.firebase_service import get_firebase_status
    return jsonify(get_firebase_status())


@api_bp.post("/firebase/sync_all")
def api_firebase_sync_all() -> Any:
    """Synchronize all local SQLite forensic cases into Firebase Firestore."""
    from app.database import list_cases, get_case_by_id
    from app.services.firebase_service import sync_case_to_firebase, get_firebase_status

    status = get_firebase_status()
    if not status["connected"]:
        return jsonify({"success": False, "error": "Firebase is not initialized or credentials missing."}), 400

    cases = list_cases(limit=100)
    synced_count = 0
    failed_count = 0

    for c in cases:
        full_case = get_case_by_id(c["case_id"])
        if full_case:
            ok = sync_case_to_firebase(full_case, full_case.get("evidence_items", []))
            if ok:
                synced_count += 1
            else:
                failed_count += 1

    msg = f"Successfully synced {synced_count} cases to Firebase Firestore."
    if synced_count == 0:
        msg = f"Firebase Auth is active for project '{status['project_id']}'. To sync cases to Firestore, click to enable Cloud Firestore in your Firebase Console."

    return jsonify({
        "success": True,
        "total_cases": len(cases),
        "synced_count": synced_count,
        "failed_count": failed_count,
        "project_id": status["project_id"],
        "message": msg,
        "activation_url": f"https://console.firebase.google.com/project/{status['project_id']}/firestore"
    })


@api_bp.get("/system/logs")
def get_system_diagnostic_logs() -> Any:
    """Return recent application logs and error diagnostics for in-app tracking."""
    from app.config import BASE_DIR
    log_file = BASE_DIR / "logs" / "app_errors.log"
    app_log = BASE_DIR / "logs" / "app.log"
    
    error_logs = []
    if log_file.is_file():
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f.readlines()[-30:]:
                    s = line.strip()
                    if s:
                        error_logs.append(s)
        except Exception as e:
            error_logs.append(f"Log read exception: {e}")

    activity_logs = []
    if app_log.is_file():
        try:
            with open(app_log, "r", encoding="utf-8", errors="ignore") as f:
                for line in f.readlines()[-30:]:
                    s = line.strip()
                    if s:
                        activity_logs.append(s)
        except Exception as e:
            activity_logs.append(f"Log read exception: {e}")

    recent_logs = (error_logs + activity_logs) if (error_logs or activity_logs) else ["[INFO] Forensic AI Command Center logging operational."]
    return jsonify({
        "success": True,
        "status": "healthy" if len(error_logs) == 0 else "attention",
        "error_count": len(error_logs),
        "recent_logs": recent_logs,
        "errors": error_logs,
        "recent_activity": activity_logs,
        "monitoring": "active",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


@api_bp.route("/analytics/event", methods=["POST"])
def post_analytics_event() -> Any:
    """Record a client-side telemetry event."""
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type", "client_action")
    event_data = data.get("event_data", {})
    record_analytics_event(event_type, event_data, request.remote_addr)
    return jsonify({"success": True, "recorded": event_type})


@api_bp.route("/analytics/summary", methods=["GET"])
def get_analytics_summary_route() -> Any:
    """Return platform analytics summary and usage telemetry."""
    summary = get_analytics_summary()
    return jsonify({"success": True, "analytics": summary})


@api_bp.route("/system/backup", methods=["POST"])
def trigger_database_backup() -> Any:
    """Trigger an atomic snapshot backup of SQLite database."""
    res = backup_sqlite_database(max_backups=10)
    return jsonify(res)


@api_bp.route("/system/backups", methods=["GET"])
def get_database_backups_list() -> Any:
    """List all available SQLite database backups."""
    backups = list_database_backups()
    return jsonify({"success": True, "total": len(backups), "backups": backups})




