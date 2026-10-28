"""Configuration module for AI Crime Scene Detection System."""

from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
APP_DIR = BASE_DIR / "app"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_DIR = BASE_DIR / "templates"

UPLOAD_DIR = STATIC_DIR / "uploads"
RESULT_DIR = STATIC_DIR / "results"
CROPS_DIR = STATIC_DIR / "crops"
SAMPLES_DIR = STATIC_DIR / "samples"
DATABASE_DIR = BASE_DIR / "database"
REPORTS_DIR = BASE_DIR / "reports"
MODELS_DIR = BASE_DIR / "models"

DATABASE_PATH = DATABASE_DIR / "forensics.db"

# MongoDB Atlas Configuration
MONGO_URI = os.getenv("MONGO_URI", "").strip()
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "forensic_ai").strip()


def is_mongo_configured() -> bool:
    """Check if a valid MongoDB URI is provided without unresolved placeholders."""
    if not MONGO_URI:
        return False
    if "<db_username>" in MONGO_URI or "<db_password>" in MONGO_URI:
        return False
    return MONGO_URI.startswith("mongodb://") or MONGO_URI.startswith("mongodb+srv://")


# Firebase Cloud Configuration
FIREBASE_CREDENTIALS_PATH = BASE_DIR / "firebase_credentials.json"
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "crime-scene-detection")


def is_firebase_configured() -> bool:
    """Check if Firebase service account credential file is available."""
    return FIREBASE_CREDENTIALS_PATH.is_file()


# Model Checkpoints
WEAPON_MODEL_PATH = MODELS_DIR / "pretrained_weapon_detector.pt"
FORENSIC_MODEL_PATH = MODELS_DIR / "best.pt"
GENERAL_MODEL_PATH = BASE_DIR / "yolo11n.pt"

# Create directories if they do not exist
for folder in [UPLOAD_DIR, RESULT_DIR, CROPS_DIR, SAMPLES_DIR, DATABASE_DIR, REPORTS_DIR, MODELS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "bmp"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100 MiB
DEFAULT_CONFIDENCE = 0.25
DEFAULT_IOU = 0.45
VIDEO_FRAME_STRIDE = 2  # Process every 2nd frame for real-time efficiency

# Forensic Classification Mapping
FORENSIC_CATEGORIES = {
    # Firearms & Explosives (Critical)
    "gun": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "pistol": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "handgun": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "rifle": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "shotgun": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "shotgun-weapon": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "submachine-gun": {"category": "Firearms & Ballistics", "severity": "CRITICAL", "color": "#ef4444"},
    "grenade": {"category": "Explosive Munitions", "severity": "CRITICAL", "color": "#ef4444"},
    "rocket": {"category": "Heavy Munitions", "severity": "CRITICAL", "color": "#ef4444"},

    # Edged & Blunt Weapons (High)
    "knife": {"category": "Edged Weapons", "severity": "HIGH", "color": "#f59e0b"},
    "hammer": {"category": "Blunt / Impact Tools", "severity": "HIGH", "color": "#f59e0b"},
    "blunt-object": {"category": "Blunt Instruments", "severity": "HIGH", "color": "#f59e0b"},

    # Biological & Victim Evidence (High)
    "blood": {"category": "Biological Evidence", "severity": "HIGH", "color": "#dc2626"},
    "victim": {"category": "Victim / Casualty", "severity": "CRITICAL", "color": "#e11d48"},
    "human-body": {"category": "Human Remains / Presence", "severity": "HIGH", "color": "#f97316"},
    "human-hair": {"category": "Trace Biological", "severity": "MEDIUM", "color": "#06b6d4"},
    "human-hand": {"category": "Biological Presence", "severity": "MEDIUM", "color": "#06b6d4"},

    # Physical Traces & Scene Markers (Medium)
    "finger-print": {"category": "Latent Prints & Biometrics", "severity": "MEDIUM", "color": "#38bdf8"},
    "shoe-print": {"category": "Impression Evidence", "severity": "MEDIUM", "color": "#38bdf8"},
    "rope": {"category": "Restraints / Ligatures", "severity": "HIGH", "color": "#eab308"},
    "glass": {"category": "Physical Trace / Glass", "severity": "LOW", "color": "#94a3b8"},
    "fire": {"category": "Arson / Thermal Marker", "severity": "HIGH", "color": "#f97316"},

    # Subjects, Persons & Witnesses (High Priority)
    "person": {"category": "Subjects & Persons of Interest", "severity": "HIGH", "color": "#f97316"},
    "suspect": {"category": "Suspect / Perpetrator", "severity": "CRITICAL", "color": "#ef4444"},

    # Vehicular Evidence
    "car": {"category": "Vehicular Evidence", "severity": "MEDIUM", "color": "#38bdf8"},
    "motorcycle": {"category": "Vehicular Evidence", "severity": "MEDIUM", "color": "#38bdf8"},
    "truck": {"category": "Vehicular Evidence", "severity": "MEDIUM", "color": "#38bdf8"},
    "bus": {"category": "Vehicular Evidence", "severity": "MEDIUM", "color": "#38bdf8"},
    "bicycle": {"category": "Vehicular Evidence", "severity": "MEDIUM", "color": "#38bdf8"},

    # Stolen Property, Bags & Evidence Containers
    "backpack": {"category": "Physical Property / Containers", "severity": "MEDIUM", "color": "#eab308"},
    "handbag": {"category": "Physical Property / Containers", "severity": "MEDIUM", "color": "#eab308"},
    "suitcase": {"category": "Physical Property / Containers", "severity": "MEDIUM", "color": "#eab308"},

    # Digital Forensics
    "cell phone": {"category": "Digital Evidence Device", "severity": "HIGH", "color": "#a855f7"},
    "laptop": {"category": "Digital Evidence Device", "severity": "HIGH", "color": "#a855f7"},

    # Improvised Weapons & Tools
    "baseball bat": {"category": "Blunt Impact Weapon", "severity": "HIGH", "color": "#f59e0b"},
    "scissors": {"category": "Edged Weapon / Tool", "severity": "HIGH", "color": "#f59e0b"},
    "bottle": {"category": "Trace / Chemical Container", "severity": "MEDIUM", "color": "#06b6d4"},
}

DEFAULT_CATEGORY = {"category": "Unclassified Evidence", "severity": "LOW", "color": "#94a3b8"}


def get_evidence_metadata(class_name: str) -> dict[str, str]:
    """Retrieve category, severity, and color for a detected class."""
    key = class_name.strip().lower()
    return FORENSIC_CATEGORIES.get(key, DEFAULT_CATEGORY)
