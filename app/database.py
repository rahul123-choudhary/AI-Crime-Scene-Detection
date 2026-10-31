"""Database management for forensic cases, evidence records, and audit logs.

Supports local SQLite storage and seamless cloud synchronization with MongoDB Atlas.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import secrets
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Generator

try:
    from pymongo import MongoClient
    from pymongo.errors import PyMongoError
except ImportError:
    MongoClient = None
    PyMongoError = Exception

from werkzeug.security import check_password_hash, generate_password_hash

from app.config import (
    DATABASE_PATH,
    MONGO_DB_NAME,
    MONGO_URI,
    is_mongo_configured,
)

logger = logging.getLogger(__name__)

_mongo_client: Any = None


def get_mongo_client() -> Any:
    """Return active MongoDB client instance if configured and reachable."""
    global _mongo_client
    if not is_mongo_configured() or MongoClient is None:
        return None
    if _mongo_client is None:
        try:
            client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
            )
            # Verify connectivity
            client.admin.command("ping")
            _mongo_client = client
            logger.info("Connected to MongoDB Atlas successfully.")
        except Exception as exc:
            logger.warning("MongoDB Atlas connection failed (%s). Operating on SQLite.", exc)
            return None
    return _mongo_client


def get_mongo_db() -> Any:
    """Return MongoDB forensic database or None."""
    client = get_mongo_client()
    if client is not None:
        return client[MONGO_DB_NAME]
    return None


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional database connection."""
    conn = sqlite3.connect(str(DATABASE_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize SQLite database tables and apply backward-compatible schema migrations."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                investigator TEXT DEFAULT 'Forensic Officer',
                department TEXT DEFAULT 'Crime Scene Investigation Unit',
                location TEXT DEFAULT 'Unspecified Scene',
                incident_type TEXT DEFAULT 'Homicide / Scene Analysis',
                notes TEXT DEFAULT '',
                threat_level TEXT DEFAULT 'LOW',
                threat_score INTEGER DEFAULT 0,
                model_used TEXT NOT NULL,
                image_path TEXT NOT NULL,
                annotated_path TEXT NOT NULL,
                media_type TEXT DEFAULT 'image',
                video_duration REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS evidence_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                class_name TEXT NOT NULL,
                category TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL NOT NULL,
                bbox_x1 REAL NOT NULL,
                bbox_y1 REAL NOT NULL,
                bbox_x2 REAL NOT NULL,
                bbox_y2 REAL NOT NULL,
                crop_path TEXT DEFAULT '',
                video_timestamp REAL DEFAULT 0.0,
                FOREIGN KEY (case_id) REFERENCES cases (case_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                action TEXT NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                fullname TEXT NOT NULL,
                badge TEXT DEFAULT '',
                unit TEXT DEFAULT 'Crime Scene Investigation Unit',
                role TEXT DEFAULT 'Forensic Investigator',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                event_data TEXT DEFAULT '{}',
                ip_hash TEXT DEFAULT '',
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cases_created ON cases(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_items(case_id);
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_analytics_ts ON analytics_events(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_analytics_type ON analytics_events(event_type);
            """
        )

        # Migration: ensure existing database tables have the video/clarity/RLS columns
        cases_cols = [r["name"] for r in conn.execute("PRAGMA table_info(cases)").fetchall()]
        if "media_type" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN media_type TEXT DEFAULT 'image'")
        if "video_duration" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN video_duration REAL DEFAULT 0.0")
        if "clarity_score" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN clarity_score REAL DEFAULT 0.0")
        if "enhanced_path" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN enhanced_path TEXT DEFAULT ''")
        if "user_id" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN user_id INTEGER DEFAULT 0")

        evidence_cols = [r["name"] for r in conn.execute("PRAGMA table_info(evidence_items)").fetchall()]
        if "video_timestamp" not in evidence_cols:
            conn.execute("ALTER TABLE evidence_items ADD COLUMN video_timestamp REAL DEFAULT 0.0")
        if "activity" not in evidence_cols:
            conn.execute("ALTER TABLE evidence_items ADD COLUMN activity TEXT DEFAULT ''")

        if "scene_narrative" not in cases_cols:
            conn.execute("ALTER TABLE cases ADD COLUMN scene_narrative TEXT DEFAULT ''")

        # Migration: ensure users table has email verification & password reset columns
        users_cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "email_verified" not in users_cols:
            conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0")
        if "verification_token" not in users_cols:
            conn.execute("ALTER TABLE users ADD COLUMN verification_token TEXT DEFAULT ''")
        if "reset_token" not in users_cols:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token TEXT DEFAULT ''")
        if "reset_token_expires" not in users_cols:
            conn.execute("ALTER TABLE users ADD COLUMN reset_token_expires TEXT DEFAULT ''")

    # Initialize MongoDB collections and indexes if accessible
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        try:
            mongo_db.cases.create_index([("created_at", -1)])
            mongo_db.cases.create_index([("threat_level", 1)])
            mongo_db.cases.create_index([("case_id", 1)], unique=True)
            mongo_db.audit_logs.create_index([("timestamp", -1)])
            logger.info("MongoDB indexes successfully created/verified.")
        except Exception as exc:
            logger.warning("MongoDB index initialization warning: %s", exc)

    # Seed default investigator account if users table is empty
    seed_default_user()


def insert_case(
    case_data: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    log_action: str = "CASE_CREATED",
) -> str:
    """Save a new case and its evidence items atomically to SQLite and sync to MongoDB."""
    now = datetime.now(timezone.utc).isoformat()

    # 1. Local SQLite Persistence
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO cases (
                case_id, title, investigator, department, location,
                incident_type, notes, threat_level, threat_score,
                scene_narrative,
                model_used, image_path, annotated_path, media_type,
                video_duration, clarity_score, enhanced_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_data["case_id"],
                case_data.get("title", f"Investigation {case_data['case_id']}"),
                case_data.get("investigator", "Forensic Officer"),
                case_data.get("department", "CSI Division"),
                case_data.get("location", "Scene Location"),
                case_data.get("incident_type", "Evidence Analysis"),
                case_data.get("notes", ""),
                case_data.get("threat_level", "LOW"),
                case_data.get("threat_score", 0),
                case_data.get("scene_narrative", ""),
                case_data.get("model_used", "Ensemble"),
                case_data["image_path"],
                case_data["annotated_path"],
                case_data.get("media_type", "image"),
                float(case_data.get("video_duration", 0.0)),
                float(case_data.get("clarity_score", 0.0)),
                case_data.get("enhanced_path", ""),
                now,
            ),
        )

        for item in evidence_items:
            bbox = item.get("box", [0, 0, 0, 0])
            conn.execute(
                """
                INSERT INTO evidence_items (
                    case_id, class_name, category, severity, confidence,
                    activity,
                    bbox_x1, bbox_y1, bbox_x2, bbox_y2, crop_path, video_timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_data["case_id"],
                    item.get("class", item.get("class_name", "Evidence")),
                    item.get("category", "General Evidence"),
                    item.get("severity", "LOW"),
                    float(item["confidence"]),
                    item.get("activity", ""),
                    float(bbox[0]) if len(bbox) > 0 else 0.0,
                    float(bbox[1]) if len(bbox) > 1 else 0.0,
                    float(bbox[2]) if len(bbox) > 2 else 0.0,
                    float(bbox[3]) if len(bbox) > 3 else 0.0,
                    item.get("crop_path", ""),
                    float(item.get("video_timestamp", 0.0)),
                ),
            )

        conn.execute(
            """
            INSERT INTO audit_logs (case_id, action, details, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (
                case_data["case_id"],
                log_action,
                f"Generated case with {len(evidence_items)} detected evidence items",
                now,
            ),
        )

    # 2. Cloud MongoDB Atlas Synchronization
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        try:
            mongo_evidence = []
            for item in evidence_items:
                bbox = item.get("box", [0, 0, 0, 0])
                mongo_evidence.append(
                    {
                        "class_name": item.get("class", item.get("class_name", "Evidence")),
                        "category": item.get("category", "General Evidence"),
                        "severity": item.get("severity", "LOW"),
                        "confidence": float(item.get("confidence", 0.0)),
                        "activity": item.get("activity", ""),
                        "bbox": [float(c) for c in bbox] if bbox else [],
                        "crop_path": item.get("crop_path", ""),
                        "video_timestamp": float(item.get("video_timestamp", 0.0)),
                    }
                )

            mongo_doc = {
                "_id": case_data["case_id"],
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
                "image_path": case_data["image_path"],
                "annotated_path": case_data["annotated_path"],
                "media_type": case_data.get("media_type", "image"),
                "video_duration": float(case_data.get("video_duration", 0.0)),
                "clarity_score": float(case_data.get("clarity_score", 0.0)),
                "enhanced_path": case_data.get("enhanced_path", ""),
                "created_at": now,
                "evidence_items": mongo_evidence,
                "evidence_count": len(mongo_evidence),
            }
            mongo_db.cases.update_one({"_id": case_data["case_id"]}, {"$set": mongo_doc}, upsert=True)
            mongo_db.audit_logs.insert_one(
                {
                    "case_id": case_data["case_id"],
                    "action": log_action,
                    "details": f"Generated case with {len(evidence_items)} detected evidence items",
                    "timestamp": now,
                }
            )
        except Exception as exc:
            logger.warning("MongoDB write failed (%s). SQLite record preserved.", exc)

    # 3. Cloud Firebase Firestore Synchronization
    try:
        from app.services.firebase_service import sync_case_to_firebase
        sync_case_to_firebase(case_data, evidence_items)
    except Exception as fb_err:
        logger.debug("Firebase auto-sync notice: %s", fb_err)

    # 4. Cloud Supabase PostgreSQL Synchronization
    try:
        from app.services.supabase_service import sync_case_to_supabase
        sync_case_to_supabase(case_data, evidence_items)
    except Exception as sb_err:
        logger.debug("Supabase auto-sync notice: %s", sb_err)

    return case_data["case_id"]


def get_case_by_id(case_id: str) -> dict[str, Any] | None:
    """Fetch full case record with evidence items."""
    with get_db() as conn:
        case_row = conn.execute(
            "SELECT * FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
        if case_row:
            case_dict = dict(case_row)
            evidence_rows = conn.execute(
                "SELECT * FROM evidence_items WHERE case_id = ? ORDER BY confidence DESC",
                (case_id,),
            ).fetchall()
            case_dict["evidence_items"] = [dict(row) for row in evidence_rows]

            # Populate forensic clarity variants if generated
            from app.config import RESULT_DIR

            variants = {}
            for k in ("full_enhanced", "clahe", "sharpened", "night_vision"):
                p = RESULT_DIR / f"{case_id}_{k}.jpg"
                if p.is_file():
                    variants[k] = f"results/{case_id}_{k}.jpg"
            case_dict["clarity_variants"] = variants

            return case_dict

    # Fallback to MongoDB if not in SQLite
    mongo_db = get_mongo_db()
    if mongo_db is not None:
        try:
            doc = mongo_db.cases.find_one({"_id": case_id})
            if doc:
                doc.pop("_id", None)
                from app.config import RESULT_DIR

                variants = {}
                for k in ("full_enhanced", "clahe", "sharpened", "night_vision"):
                    p = RESULT_DIR / f"{case_id}_{k}.jpg"
                    if p.is_file():
                        variants[k] = f"results/{case_id}_{k}.jpg"
                doc["clarity_variants"] = variants
                return doc
        except Exception as exc:
            logger.warning("MongoDB get_case_by_id failed: %s", exc)

    return None


def list_cases(
    limit: int = 50,
    offset: int = 0,
    query: str = "",
    threat: str = "",
    current_user: dict[str, Any] | None = None,
    enforce_rls: bool = False,
) -> list[dict[str, Any]]:
    """List cases with optional search query, threat level filtering, and Row-Level Security (RLS)."""
    sql = """
        SELECT c.*, COUNT(e.id) as evidence_count
        FROM cases c
        LEFT JOIN evidence_items e ON c.case_id = e.case_id
        WHERE 1=1
    """
    params: list[Any] = []

    # Row-Level Security (RLS) enforcement
    if enforce_rls and current_user:
        role = current_user.get("role", "")
        # Lead Officers and Admins have global jurisdiction
        if role not in ("Lead Forensic Officer", "Chief", "Admin", "Superintendent"):
            user_id = current_user.get("id", 0)
            unit = current_user.get("unit", "")
            name = current_user.get("name", "")
            sql += " AND (c.user_id = ? OR c.department = ? OR c.investigator = ?)"
            params.extend([user_id, unit, name])

    if query:
        sql += " AND (c.case_id LIKE ? OR c.title LIKE ? OR c.investigator LIKE ? OR c.location LIKE ?)"
        q_wildcard = f"%{query}%"
        params.extend([q_wildcard, q_wildcard, q_wildcard, q_wildcard])

    if threat and threat.upper() != "ALL":
        sql += " AND c.threat_level = ?"
        params.append(threat.upper())

    sql += " GROUP BY c.case_id ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def get_system_stats() -> dict[str, Any]:
    """Compute dashboard analytics for cases and forensic items."""
    with get_db() as conn:
        total_cases = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        total_evidence = conn.execute("SELECT COUNT(*) FROM evidence_items").fetchone()[0]
        critical_threats = conn.execute(
            "SELECT COUNT(*) FROM cases WHERE threat_level = 'CRITICAL'"
        ).fetchone()[0]
        weapons_detected = conn.execute(
            "SELECT COUNT(*) FROM evidence_items WHERE category LIKE '%Firearm%' OR category LIKE '%Weapon%'"
        ).fetchone()[0]

        recent = conn.execute(
            "SELECT case_id, title, threat_level, created_at FROM cases ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

        return {
            "total_cases": total_cases,
            "total_evidence": total_evidence,
            "critical_threats": critical_threats,
            "weapons_detected": weapons_detected,
            "recent_cases": [dict(r) for r in recent],
        }


def delete_case(case_id: str) -> bool:
    """Delete a case and its evidence items from SQLite and MongoDB."""
    deleted_sqlite = False
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
        deleted_sqlite = cursor.rowcount > 0

    mongo_db = get_mongo_db()
    if mongo_db is not None:
        try:
            mongo_db.cases.delete_one({"_id": case_id})
            mongo_db.audit_logs.delete_many({"case_id": case_id})
        except Exception as exc:
            logger.warning("MongoDB delete failed (%s).", exc)

    return deleted_sqlite


def create_user(
    email: str,
    username: str,
    password: str,
    fullname: str,
    badge: str = "",
    unit: str = "Crime Scene Investigation Unit",
    role: str = "Forensic Investigator",
) -> dict[str, Any] | None:
    """Create a new user with securely hashed password."""
    now = datetime.now(timezone.utc).isoformat()
    pwd_hash = generate_password_hash(password, method="scrypt")
    try:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (email, username, password_hash, fullname, badge, unit, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (email.lower().strip(), username.lower().strip(), pwd_hash, fullname.strip(), badge.strip(), unit.strip(), role.strip(), now),
            )
            user_id = cursor.lastrowid
            return {
                "id": user_id,
                "email": email.lower().strip(),
                "username": username.lower().strip(),
                "name": fullname.strip(),
                "fullname": fullname.strip(),
                "badge": badge.strip(),
                "unit": unit.strip(),
                "role": role.strip(),
                "created_at": now,
            }
    except sqlite3.IntegrityError:
        logger.warning("User creation failed: email or username already exists (%s)", email)
        return None


def verify_user_credentials(email_or_username: str, password: str) -> dict[str, Any] | None:
    """Verify user credentials against stored password hash."""
    clean_identifier = email_or_username.lower().strip()
    with get_db() as conn:
        row = conn.execute(
            """
            SELECT id, email, username, password_hash, fullname, badge, unit, role, created_at
            FROM users
            WHERE email = ? OR username = ?
            LIMIT 1
            """,
            (clean_identifier, clean_identifier),
        ).fetchone()

        if not row:
            return None

        if check_password_hash(row["password_hash"], password):
            return {
                "id": row["id"],
                "email": row["email"],
                "username": row["username"],
                "name": row["fullname"],
                "fullname": row["fullname"],
                "badge": row["badge"],
                "unit": row["unit"],
                "role": row["role"],
                "created_at": row["created_at"],
            }
    return None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    """Retrieve user details by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, username, fullname, badge, unit, role, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        res = dict(row)
        res["name"] = res["fullname"]
        return res


def seed_default_user() -> None:
    """Seed default forensic investigator account if table is empty."""
    try:
        with get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count == 0:
                user = create_user(
                    email="officer@forensic.gov",
                    username="officer",
                    password="Password@123",
                    fullname="Lead Forensic Officer",
                    badge="CS-4091",
                    unit="Crime Scene Investigation Unit",
                    role="Forensic Investigator",
                )
                if user:
                    conn.execute("UPDATE users SET email_verified = 1 WHERE email = 'officer@forensic.gov'")
                logger.info("Default investigator account seeded: officer@forensic.gov / Password@123")
    except Exception as exc:
        logger.warning("Default user seeding note: %s", exc)


# ==============================================================================
# Password Reset, Email Verification, Backups, RLS, and Account Management
# ==============================================================================

def create_password_reset_token(email: str) -> str | None:
    """Generate and store a time-limited password reset token for the given email."""
    clean_email = email.lower().strip()
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (clean_email,)).fetchone()
        if not user:
            return None
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        conn.execute(
            "UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?",
            (token, expires, clean_email)
        )
        return token


def verify_password_reset_token(token: str) -> dict[str, Any] | None:
    """Verify that a password reset token exists and has not expired."""
    if not token or len(token) < 16:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, username, fullname, reset_token_expires FROM users WHERE reset_token = ?",
            (token,)
        ).fetchone()
        if not row:
            return None
        expires_str = row["reset_token_expires"]
        if expires_str:
            try:
                expires_dt = datetime.fromisoformat(expires_str)
                if datetime.now(timezone.utc) > expires_dt:
                    return None
            except Exception:
                return None
        return dict(row)


def reset_user_password(token: str, new_password: str) -> bool:
    """Update user password using a valid reset token and clear token."""
    user = verify_password_reset_token(token)
    if not user:
        return False
    pw_hash = generate_password_hash(new_password, method="scrypt")
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, reset_token = '', reset_token_expires = '' WHERE id = ?",
            (pw_hash, user["id"])
        )
    return True


def create_email_verification_token(email: str) -> str | None:
    """Generate and store an email verification token for the user."""
    clean_email = email.lower().strip()
    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?", (clean_email,)).fetchone()
        if not user:
            return None
        token = secrets.token_urlsafe(24)
        conn.execute("UPDATE users SET verification_token = ? WHERE email = ?", (token, clean_email))
        return token


def verify_user_email(token: str) -> dict[str, Any] | None:
    """Mark an investigator's email as verified via the token."""
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, email, username, fullname, badge, unit, role FROM users WHERE verification_token = ?",
            (token,)
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE users SET email_verified = 1, verification_token = '' WHERE id = ?",
            (row["id"],)
        )
        res = dict(row)
        res["name"] = res["fullname"]
        res["email_verified"] = 1
        return res


def is_user_email_verified(user_id_or_email: int | str) -> bool:
    """Check if the given user has verified their official email."""
    with get_db() as conn:
        if isinstance(user_id_or_email, int):
            row = conn.execute("SELECT email_verified FROM users WHERE id = ?", (user_id_or_email,)).fetchone()
        else:
            row = conn.execute("SELECT email_verified FROM users WHERE email = ?", (str(user_id_or_email).lower().strip(),)).fetchone()
        return bool(row and row["email_verified"])


def backup_sqlite_database(max_backups: int = 10) -> dict[str, Any]:
    """Create an atomic snapshot backup of the SQLite database and rotate old backups."""
    from app.config import BASE_DIR
    backup_dir = BASE_DIR / "database" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_filename = f"crime_scene_backup_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    with get_db() as src_conn:
        dest_conn = sqlite3.connect(str(backup_path))
        src_conn.backup(dest_conn)
        dest_conn.close()

    size_kb = round(backup_path.stat().st_size / 1024, 2)

    all_backups = sorted(backup_dir.glob("crime_scene_backup_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(all_backups) > max_backups:
        for old_backup in all_backups[max_backups:]:
            try:
                old_backup.unlink()
            except Exception:
                pass

    return {
        "success": True,
        "backup_file": backup_filename,
        "path": str(backup_path),
        "size_kb": size_kb,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_backups": len(list(backup_dir.glob("crime_scene_backup_*.db")))
    }


def list_database_backups() -> list[dict[str, Any]]:
    """List all available SQLite database backups with sizes and creation times."""
    from app.config import BASE_DIR
    backup_dir = BASE_DIR / "database" / "backups"
    if not backup_dir.is_dir():
        return []

    backups = []
    for p in sorted(backup_dir.glob("crime_scene_backup_*.db"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        backups.append({
            "filename": p.name,
            "size_kb": round(st.st_size / 1024, 2),
            "created_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        })
    return backups


def delete_user_account(user_id: int) -> bool:
    """Permanently delete an officer user account and log to audit logs."""
    with get_db() as conn:
        user = conn.execute("SELECT email, fullname FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return False
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.execute(
            "INSERT INTO audit_logs (case_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            ("AUTH", "USER_ACCOUNT_PURGED", f"User {user['email']} permanently deleted their account", datetime.now(timezone.utc).isoformat())
        )
        return True


def record_analytics_event(event_type: str, event_data: dict[str, Any] | None = None, ip: str | None = None) -> bool:
    """Record a telemetry event into analytics_events table."""
    try:
        ip_hash = hashlib.sha256((ip or "127.0.0.1").encode("utf-8")).hexdigest()[:16]
        data_json = json.dumps(event_data or {})
        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                "INSERT INTO analytics_events (event_type, event_data, ip_hash, timestamp) VALUES (?, ?, ?, ?)",
                (event_type, data_json, ip_hash, now)
            )
        return True
    except Exception as exc:
        logger.debug("Analytics event record error: %s", exc)
        return False


def get_analytics_summary() -> dict[str, Any]:
    """Retrieve summarized platform telemetry and usage metrics."""
    with get_db() as conn:
        total_events = conn.execute("SELECT COUNT(*) FROM analytics_events").fetchone()[0]
        page_views = conn.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'page_view'").fetchone()[0]
        case_scans = conn.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'case_analyzed'").fetchone()[0]
        exports = conn.execute("SELECT COUNT(*) FROM analytics_events WHERE event_type = 'report_exported'").fetchone()[0]
        unique_visitors = conn.execute("SELECT COUNT(DISTINCT ip_hash) FROM analytics_events").fetchone()[0]

        recent_events = conn.execute(
            "SELECT event_type, timestamp FROM analytics_events ORDER BY timestamp DESC LIMIT 8"
        ).fetchall()

        return {
            "total_events": total_events,
            "page_views": page_views,
            "case_scans": case_scans,
            "reports_exported": exports,
            "unique_sessions": unique_visitors or 1,
            "recent_events": [dict(r) for r in recent_events]
        }
