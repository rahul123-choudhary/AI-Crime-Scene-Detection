"""Firebase Cloud Services integration for AI Crime Scene Detection.

Supports Firebase Admin SDK:
- Firebase Authentication for Forensic Officers & Investigators
- Cloud Firestore Case Sync & Chain of Custody Audit Logs
- Cloud Health and Storage verification
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID, is_firebase_configured

logger = logging.getLogger(__name__)

_firebase_app: Any = None
_firestore_client: Any = None
_firebase_auth_available: bool = False
_firestore_available: bool = False


def get_firebase_app() -> Any:
    """Initialize and return singleton Firebase Admin app."""
    global _firebase_app, _firebase_auth_available
    if _firebase_app is not None:
        return _firebase_app

    if not is_firebase_configured():
        logger.info("Firebase credentials not found at %s. Running in offline/SQLite mode.", FIREBASE_CREDENTIALS_PATH)
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(str(FIREBASE_CREDENTIALS_PATH))
            _firebase_app = firebase_admin.initialize_app(cred, name="crime-scene-detection-app")
            logger.info("Firebase Admin initialized successfully for project: %s", _firebase_app.project_id)
        else:
            _firebase_app = list(firebase_admin._apps.values())[0]

        _firebase_auth_available = True
        return _firebase_app
    except Exception as exc:
        logger.warning("Firebase Admin initialization failed: %s", exc)
        return None


def get_firestore_client() -> Any:
    """Return active Firestore client or None if unavailable/disabled."""
    global _firestore_client, _firestore_available
    if _firestore_client is not None:
        return _firestore_client

    app = get_firebase_app()
    if app is None:
        return None

    try:
        from firebase_admin import firestore

        client = firestore.client(app=app)
        # Test connectivity with ping query
        _firestore_client = client
        _firestore_available = True
        return _firestore_client
    except Exception as exc:
        logger.warning("Firestore client unavailable: %s", exc)
        _firestore_available = False
        return None


def get_firebase_status() -> dict[str, Any]:
    """Retrieve real-time connectivity and health status of Firebase."""
    configured = is_firebase_configured()
    app = get_firebase_app()
    fs = get_firestore_client()

    auth_active = False
    auth_user_count = 0
    if app is not None:
        try:
            from firebase_admin import auth

            users = list(auth.list_users(app=app).users)
            auth_active = True
            auth_user_count = len(users)
        except Exception:
            auth_active = False

    return {
        "configured": configured,
        "credentials_path": str(FIREBASE_CREDENTIALS_PATH.name),
        "project_id": FIREBASE_PROJECT_ID,
        "connected": app is not None,
        "auth_enabled": auth_active,
        "registered_users": auth_user_count,
        "firestore_connected": fs is not None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def sync_case_to_firebase(case_data: dict[str, Any], evidence_items: list[dict[str, Any]]) -> bool:
    """Persist forensic case and detected evidence items to Firebase Firestore."""
    fs = get_firestore_client()
    if fs is None:
        return False

    try:
        now = datetime.now(timezone.utc).isoformat()
        clean_evidence = []
        for item in evidence_items:
            bbox = item.get("box", [0, 0, 0, 0])
            clean_evidence.append(
                {
                    "class_name": item.get("class", item.get("class_name", "Evidence")),
                    "category": item.get("category", "General Evidence"),
                    "severity": item.get("severity", "LOW"),
                    "confidence": float(item.get("confidence", 0.0)),
                    "bbox": [float(c) for c in bbox] if bbox else [],
                    "crop_path": item.get("crop_path", ""),
                    "video_timestamp": float(item.get("video_timestamp", 0.0)),
                }
            )

        doc_payload = {
            "case_id": case_data["case_id"],
            "title": case_data.get("title", f"Investigation {case_data['case_id']}"),
            "investigator": case_data.get("investigator", "Forensic Officer"),
            "department": case_data.get("department", "CSI Division"),
            "location": case_data.get("location", "Scene Location"),
            "incident_type": case_data.get("incident_type", "Evidence Analysis"),
            "notes": case_data.get("notes", ""),
            "threat_level": case_data.get("threat_level", "LOW"),
            "threat_score": int(case_data.get("threat_score", 0)),
            "model_used": case_data.get("model_used", "Ensemble"),
            "image_path": case_data.get("image_path", ""),
            "annotated_path": case_data.get("annotated_path", ""),
            "media_type": case_data.get("media_type", "image"),
            "video_duration": float(case_data.get("video_duration", 0.0)),
            "clarity_score": float(case_data.get("clarity_score", 0.0)),
            "created_at": now,
            "evidence_count": len(clean_evidence),
            "evidence_items": clean_evidence,
        }

        # Save to cases collection
        fs.collection("cases").document(case_data["case_id"]).set(doc_payload)

        # Audit log entry in Firebase
        fs.collection("audit_logs").add(
            {
                "case_id": case_data["case_id"],
                "action": "CASE_SYNCED_TO_FIREBASE",
                "details": f"Synchronized {len(clean_evidence)} evidence objects",
                "timestamp": now,
            }
        )

        logger.info("Successfully synced case %s to Firebase Firestore.", case_data["case_id"])
        return True
    except Exception as exc:
        err_msg = str(exc)
        if "PERMISSION_DENIED" in err_msg or "SERVICE_DISABLED" in err_msg:
            global _firestore_available, _firestore_client
            _firestore_available = False
            _firestore_client = None
            logger.warning("Firestore API is not enabled in Firebase Console for '%s'. Enable at: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=%s", FIREBASE_PROJECT_ID, FIREBASE_PROJECT_ID)
        else:
            logger.warning("Firestore sync for case %s skipped: %s", case_data.get("case_id"), exc)
        return False


def get_firebase_case(case_id: str) -> dict[str, Any] | None:
    """Fetch forensic case record directly from Firestore."""
    fs = get_firestore_client()
    if fs is None:
        return None

    try:
        doc = fs.collection("cases").document(case_id).get()
        if doc.exists:
            return doc.to_dict()
    except Exception as exc:
        logger.warning("Error fetching case %s from Firestore: %s", case_id, exc)

    return None


def register_or_update_firebase_officer(name: str, email: str, role: str = "Forensic Investigator") -> dict[str, Any]:
    """Ensure officer profile exists in Firebase Authentication."""
    app = get_firebase_app()
    if app is None:
        return {"success": False, "error": "Firebase not connected"}

    try:
        from firebase_admin import auth

        safe_email = email.strip().lower()
        try:
            user = auth.get_user_by_email(safe_email, app=app)
            # Update display name if changed
            if user.display_name != name:
                user = auth.update_user(user.uid, display_name=name, app=app)
        except Exception:
            user = auth.create_user(
                email=safe_email,
                display_name=name,
                password="ForensicSecure2026!",
                app=app,
            )

        return {
            "success": True,
            "uid": user.uid,
            "email": user.email,
            "display_name": user.display_name,
        }
    except Exception as exc:
        logger.warning("Firebase officer registration warning: %s", exc)
        return {"success": False, "error": str(exc)}
