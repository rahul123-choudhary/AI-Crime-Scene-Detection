"""Migration script: Migrate local SQLite forensic cases & evidence to MongoDB Atlas."""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

try:
    from pymongo import MongoClient
except ImportError:
    print("[ERROR] pymongo is not installed. Run: pip install pymongo dnspython")
    sys.exit(1)

from app.config import DATABASE_PATH, MONGO_DB_NAME, MONGO_URI


def test_mongo_connection(uri: str) -> bool:
    """Test if MongoDB can be reached with given URI."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        print("[SUCCESS] MongoDB connection verified successfully!")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to connect to MongoDB: {exc}")
        return False


def migrate(uri: str, db_name: str) -> None:
    """Read all cases & evidence from SQLite and push to MongoDB."""
    if "<db_username>" in uri or "<db_password>" in uri:
        print("\n[ATTENTION REQUIRED]")
        print("Your MongoDB URI still contains '<db_username>' or '<db_password>' placeholders!")
        print("Please update your .env file with your real username & password, or run:")
        print('python scripts/migrate_to_mongo.py --uri "mongodb+srv://YOUR_USER:YOUR_PASS@cluster0.6mfce4a.mongodb.net/?appName=Cluster0"\n')
        sys.exit(1)

    print(f"[*] Connecting to MongoDB Atlas ({db_name})...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[db_name]
    except Exception as exc:
        print(f"[ERROR] Connection failed: {exc}")
        sys.exit(1)

    if not DATABASE_PATH.is_file():
        print(f"[ERROR] SQLite database not found at {DATABASE_PATH}")
        sys.exit(1)

    print(f"[*] Reading SQLite database from {DATABASE_PATH}...")
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row

    cases = conn.execute("SELECT * FROM cases").fetchall()
    print(f"[*] Found {len(cases)} cases in SQLite database.")

    migrated_cases = 0
    total_evidence = 0

    for c in cases:
        case_dict = dict(c)
        case_id = case_dict["case_id"]

        evidence_rows = conn.execute(
            "SELECT * FROM evidence_items WHERE case_id = ? ORDER BY confidence DESC",
            (case_id,),
        ).fetchall()

        evidence_items = []
        for e in evidence_rows:
            ed = dict(e)
            evidence_items.append({
                "class_name": ed.get("class_name", "Evidence"),
                "category": ed.get("category", "General Evidence"),
                "severity": ed.get("severity", "LOW"),
                "confidence": float(ed.get("confidence", 0.0)),
                "bbox": [
                    float(ed.get("bbox_x1", 0.0)),
                    float(ed.get("bbox_y1", 0.0)),
                    float(ed.get("bbox_x2", 0.0)),
                    float(ed.get("bbox_y2", 0.0)),
                ],
                "crop_path": ed.get("crop_path", ""),
                "video_timestamp": float(ed.get("video_timestamp", 0.0)),
            })

        total_evidence += len(evidence_items)

        mongo_doc = {
            "_id": case_id,
            "case_id": case_id,
            "title": case_dict.get("title", ""),
            "investigator": case_dict.get("investigator", ""),
            "department": case_dict.get("department", ""),
            "location": case_dict.get("location", ""),
            "incident_type": case_dict.get("incident_type", ""),
            "notes": case_dict.get("notes", ""),
            "threat_level": case_dict.get("threat_level", "LOW"),
            "threat_score": int(case_dict.get("threat_score", 0)),
            "model_used": case_dict.get("model_used", ""),
            "image_path": case_dict.get("image_path", ""),
            "annotated_path": case_dict.get("annotated_path", ""),
            "media_type": case_dict.get("media_type", "image"),
            "video_duration": float(case_dict.get("video_duration", 0.0)),
            "clarity_score": float(case_dict.get("clarity_score", 0.0)),
            "enhanced_path": case_dict.get("enhanced_path", ""),
            "created_at": case_dict.get("created_at", ""),
            "evidence_items": evidence_items,
            "evidence_count": len(evidence_items),
        }

        db.cases.update_one({"_id": case_id}, {"$set": mongo_doc}, upsert=True)
        migrated_cases += 1

    # Migrate audit logs
    audit_rows = conn.execute("SELECT * FROM audit_logs").fetchall()
    for a in audit_rows:
        ad = dict(a)
        db.audit_logs.insert_one({
            "case_id": ad.get("case_id"),
            "action": ad.get("action", ""),
            "details": ad.get("details", ""),
            "timestamp": ad.get("timestamp", ""),
        })

    # Create Indexes
    db.cases.create_index([("created_at", -1)])
    db.cases.create_index([("threat_level", 1)])
    db.cases.create_index([("case_id", 1)], unique=True)
    db.audit_logs.create_index([("timestamp", -1)])

    conn.close()

    print("\n" + "=" * 55)
    print("      MONGODB ATLAS MIGRATION COMPLETE")
    print("=" * 55)
    print(f" [OK] Successfully migrated {migrated_cases} cases")
    print(f" [OK] Successfully migrated {total_evidence} evidence items")
    print(f" [OK] Successfully migrated {len(audit_rows)} audit logs")
    print(f" [OK] Target Database: {db_name}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Forensic SQLite records to MongoDB Atlas")
    parser.add_argument("--uri", default="", help="MongoDB connection URI")
    parser.add_argument("--db", default="", help="Target MongoDB database name")
    parser.add_argument("--ping", action="store_true", help="Test MongoDB connection only")

    args = parser.parse_args()

    uri = (args.uri or MONGO_URI).strip()
    db_name = (args.db or MONGO_DB_NAME or "crime_scene_forensics").strip()

    if not uri:
        print("[ERROR] No MongoDB URI provided in .env or via --uri.")
        sys.exit(1)

    if args.ping:
        test_mongo_connection(uri)
    else:
        migrate(uri, db_name)
