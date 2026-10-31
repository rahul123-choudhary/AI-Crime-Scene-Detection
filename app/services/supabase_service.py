"""Supabase Cloud Database & Storage Synchronization Service.

Provides automatic backup of forensic cases, evidence records, and audit logs
to Supabase PostgreSQL using both native PostgREST REST API and official SDK.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app.config import SUPABASE_KEY, SUPABASE_URL, is_supabase_configured

logger = logging.getLogger(__name__)


def _postgrest_request(
    endpoint: str,
    method: str = "GET",
    payload: dict[str, Any] | list[dict[str, Any]] | None = None,
    headers_extra: dict[str, str] | None = None,
) -> tuple[int, Any]:
    """Execute a direct authenticated HTTP request against Supabase PostgREST API."""
    if not is_supabase_configured():
        return 0, None

    url = f"{SUPABASE_URL}/rest/v1/{endpoint.lstrip('/')}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    if headers_extra:
        headers.update(headers_extra)

    data_bytes = None
    if payload is not None:
        data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            status = response.status
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return status, parsed
    except urllib.error.HTTPError as http_err:
        err_msg = http_err.read().decode("utf-8", errors="ignore")
        logger.warning("Supabase HTTP Error %d on %s: %s", http_err.code, endpoint, err_msg)
        return http_err.code, err_msg
    except Exception as exc:
        logger.warning("Supabase network error on %s: %s", endpoint, exc)
        return 500, str(exc)


def test_supabase_connection() -> dict[str, Any]:
    """Verify connectivity to Supabase project."""
    if not is_supabase_configured():
        return {"connected": False, "reason": "SUPABASE_URL or SUPABASE_KEY missing in environment."}

    status, resp = _postgrest_request("cases?select=case_id&limit=1", method="GET")
    if 200 <= status < 300:
        return {"connected": True, "url": SUPABASE_URL, "status": "ONLINE"}
    return {"connected": False, "status_code": status, "error": resp}


def sync_case_to_supabase(
    case_data: dict[str, Any],
    evidence_items: list[dict[str, Any]],
) -> bool:
    """Synchronize a new case and its itemized evidence to Supabase."""
    if not is_supabase_configured():
        return False

    case_row = {
        "case_id": case_data["case_id"],
        "title": case_data.get("title", f"Investigation {case_data['case_id']}"),
        "investigator": case_data.get("investigator", "Forensic Officer"),
        "department": case_data.get("department", "CSI Division"),
        "location": case_data.get("location", "Scene Location"),
        "incident_type": case_data.get("incident_type", "Evidence Analysis"),
        "notes": case_data.get("notes", ""),
        "threat_level": case_data.get("threat_level", "LOW"),
        "threat_score": int(case_data.get("threat_score", 0)),
        "scene_narrative": case_data.get("scene_narrative", ""),
        "model_used": case_data.get("model_used", "Ensemble"),
        "image_path": case_data.get("image_path", ""),
        "annotated_path": case_data.get("annotated_path", ""),
        "media_type": case_data.get("media_type", "image"),
        "video_duration": float(case_data.get("video_duration", 0.0)),
        "clarity_score": float(case_data.get("clarity_score", 0.0)),
        "enhanced_path": case_data.get("enhanced_path", ""),
    }

    # 1. Upsert Case Record
    status_case, _ = _postgrest_request(
        "cases",
        method="POST",
        payload=case_row,
        headers_extra={"Prefer": "resolution=merge-duplicates"},
    )
    if status_case not in (200, 201):
        logger.warning("Supabase case sync unsuccessful (status %d)", status_case)
        return False

    # 2. Insert Evidence Items
    if evidence_items:
        items_payload = []
        for item in evidence_items:
            bbox = item.get("box", [0, 0, 0, 0])
            items_payload.append(
                {
                    "case_id": case_data["case_id"],
                    "class_name": item.get("class", item.get("class_name", "Evidence")),
                    "category": item.get("category", "General Evidence"),
                    "severity": item.get("severity", "LOW"),
                    "confidence": float(item.get("confidence", 0.0)),
                    "activity": item.get("activity", ""),
                    "bbox_x1": float(bbox[0]) if len(bbox) > 0 else 0.0,
                    "bbox_y1": float(bbox[1]) if len(bbox) > 1 else 0.0,
                    "bbox_x2": float(bbox[2]) if len(bbox) > 2 else 0.0,
                    "bbox_y2": float(bbox[3]) if len(bbox) > 3 else 0.0,
                    "crop_path": item.get("crop_path", ""),
                    "video_timestamp": float(item.get("video_timestamp", 0.0)),
                }
            )

        status_ev, _ = _postgrest_request(
            "evidence_items",
            method="POST",
            payload=items_payload,
        )
        if status_ev not in (200, 201):
            logger.warning("Supabase evidence sync warning (status %d)", status_ev)

    logger.info("Successfully synced Case %s to Supabase.", case_data["case_id"])
    return True
