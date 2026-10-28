# CSI Forensic AI: Crime Scene Evidence Detection & Intelligence Workstation

An enterprise-grade, computer-vision powered forensic workstation designed for crime-scene investigators, forensic analysts, and law-enforcement laboratories. The system detects lethal weapons, ballistic markers, biological traces, and physical impression evidence using specialized YOLO neural networks, delivering threat assessments, chain-of-custody logging, interactive evidence inspection, and official PDF investigation reports.

---

## Key Capabilities

- **Multi-Model Intelligence**:
  - **Specialized Weapons & Ballistics Detector** (`pretrained_weapon_detector.pt`): Detects firearms, handguns, rifles, shotguns, knives, and grenades with high confidence.
  - **Forensic Traces & Remains Detector** (`best.pt`): Detects fingerprints, shoe prints, blood, hair, ropes/ligatures, glass, and victims.
  - **Dual-Ensemble Engine**: Concurrently executes both specialized neural models and applies IoU-based Non-Maximum Suppression (NMS) to merge detections into a unified forensic evidence map.
- **Forensic Threat Assessment**:
  - Automatically assesses scene danger levels (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and computes a 0–100 **Scene Threat Index**.
  - Categorizes evidence into *Firearms & Ballistics*, *Edged & Blunt Weapons*, *Biological Traces*, and *Physical Impression Evidence*.
- **Interactive Evidence Workstation**:
  - **Tactical Canvas**: Hover-synced bounding boxes, corner reticles, and confidence pills.
  - **Evidence Crop Gallery**: Automatically extracts and saves high-resolution crops of every detected item with pixel dimensions.
  - **Tri-View Display**: Switch instantly between *AI Annotated View*, *Interactive Canvas*, and *Original Clean Image*.
- **Official PDF Forensic Report Generation**:
  - Automatically creates publication-quality investigation reports (`ReportLab`) featuring official department crest headers, case metadata, annotated scene photos, tabulated evidence registers, crop cutouts, and legal chain-of-custody signature blocks.
- **Case Registry & Chain of Custody**:
  - Persistent SQLite database indexing cases (`CRIME-YYYYMMDD-XXXXXX`), lead officers, incident types, scene locations, timestamps, and audit logs.
  - Filter by threat level, search by keyword, and inspect historical case files.
- **Multi-Modal Evidence Intake**:
  - **Drag & Drop Upload**: High-resolution file upload with live preview (up to 32 MB).
  - **Live Field Camera**: In-browser camera capture for on-scene tablet or laptop operation.
  - **Batch Evidence Scanner**: Upload multiple scene photos simultaneously to generate unified case logs.
  - **1-Click Forensic Scenarios**: 4 preloaded authentic crime scene scenarios for instant demonstration and testing.
- **Enterprise REST API (v1)**:
  - Full programmatic interface (`/api/v1/detect`, `/api/v1/cases`, `/api/v1/health`) for integration with police CAD (Computer-Aided Dispatch) and RMS systems.

---

## System Architecture

```
AI Crime Scene Detection/
├── app/
│   ├── __init__.py               # Flask application factory
│   ├── config.py                 # Central configuration & forensic mappings
│   ├── database.py               # SQLite ORM for cases, evidence & audit trails
│   ├── services/
│   │   ├── detector.py           # Multi-model YOLO inference & ensemble merger
│   │   ├── analyzer.py           # Threat scoring, category mapping & crop extraction
│   │   └── report_generator.py   # Publication-ready PDF report builder (ReportLab)
│   ├── routes/
│   │   ├── web.py                # Dashboard, workstation, case registry, batch
│   │   └── api.py                # Enterprise REST API v1 endpoints
│   └── app.py                    # Backwards-compatible application entrypoint
├── database/
│   └── forensics.db              # SQLite case & evidence database
├── models/
│   ├── best.pt                   # 10-class forensic trace & body weights
│   ├── pretrained_weapon_detector.pt # 6-class weapon & ballistics weights
│   └── model_metadata.json       # Dynamic checkpoint registry
├── static/
│   ├── css/forensic.css          # Modern dark HUD command-center design system
│   ├── js/evidence_viewer.js     # Interactive canvas reticles & hover synchronization
│   ├── js/camera_capture.js      # Field camera video streaming & snapshot capture
│   ├── samples/                  # Preloaded authentic crime-scene test scenarios
│   ├── uploads/                  # Secure evidentiary image intake
│   ├── results/                  # Annotated forensic renders
│   └── crops/                    # Isolated high-resolution evidence cutouts
├── templates/
│   ├── base.html                 # Master forensic layout with navigation HUD
│   ├── index.html                # Intake hub (Upload, Camera, 1-Click Samples)
│   ├── result.html               # Evidence workstation & threat dashboard
│   ├── cases.html                # Searchable case registry & chain of custody
│   ├── batch.html                # Batch evidence processor
│   └── api_docs.html             # Interactive REST API documentation sandbox
├── tests/
│   └── test_forensic_system.py   # Automated unit and integration test suite
├── run.py                        # Clean CLI application launcher
└── README.md                     # Technical documentation
```

---

## Quick Start

### 1. Launch the Application
Run the launcher using the virtual environment Python:
```powershell
.\venv\Scripts\python.exe run.py
```
The workstation will be live at:
```
http://127.0.0.1:5000
```

### 2. Run Automated Verification Tests
Execute the comprehensive test suite covering models, database, PDF generation, and APIs:
```powershell
.\venv\Scripts\python.exe -m unittest discover tests
```

---

## REST API Reference

### 1. System Health & Neural Engine Status
```http
GET /api/v1/health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "AI Crime Scene Detection Engine",
  "version": "2.0.0",
  "cuda_available": false,
  "device": "CPU",
  "models": {
    "weapon_detector": {"available": true, "path": "pretrained_weapon_detector.pt"},
    "forensic_detector": {"available": true, "path": "best.pt"},
    "general_detector": {"available": true, "path": "yolo11n.pt"}
  }
}
```

### 2. Run Evidence Detection
```http
POST /api/v1/detect
Content-Type: multipart/form-data
```
**Parameters:**
- `image` (File, Required): Image file (`.jpg`, `.png`, `.webp`)
- `model` (String, Optional): `ensemble` (default), `weapon`, or `forensic`
- `confidence` (Float, Optional): Minimum confidence threshold (0.10 to 0.90, default `0.25`)

**cURL Example:**
```bash
curl -X POST http://127.0.0.1:5000/api/v1/detect \
  -F "image=@crime.jpg" \
  -F "model=ensemble" \
  -F "confidence=0.25"
```

### 3. Query Case Registry
```http
GET /api/v1/cases?q=Robbery&threat=CRITICAL&limit=10
```

---

## Forensic Classification & Severity Reference

| Class Name | Category | Threat Severity | Description |
| :--- | :--- | :--- | :--- |
| **Gun / Pistol / Handgun** | Firearms & Ballistics | **CRITICAL** | Lethal firearms capable of immediate projectile discharge. |
| **Rifle / Shotgun / SMG** | Firearms & Ballistics | **CRITICAL** | Long guns, tactical rifles, and automatic weapons. |
| **Grenade / Rocket** | Explosive Munitions | **CRITICAL** | High-explosive ordnance requiring bomb squad protocol. |
| **Knife** | Edged Weapons | **HIGH** | Bladed weapons capable of puncture or laceration trauma. |
| **Hammer / Blunt Object** | Blunt / Impact Tools | **HIGH** | Impact instruments associated with blunt force trauma. |
| **Blood** | Biological Evidence | **HIGH** | Splatter or pools requiring serology/DNA analysis. |
| **Victim / Human-body** | Casualty / Remains | **CRITICAL** | Decedents or injured individuals at incident scene. |
| **Finger-print** | Latent Biometrics | **MEDIUM** | Latent friction ridge impressions for suspect identification. |
| **Shoe-print** | Impression Evidence | **MEDIUM** | Footwear pattern analysis for movement tracking. |
| **Rope** | Restraints / Ligatures | **HIGH** | Binding or asphyxiation evidence. |
| **Glass** | Physical Trace | **LOW** | Shattered structural or vehicular trace evidence. |

---

## Training & Model Updates

To retrain the 20-class unified dataset model on a CUDA GPU machine:
```powershell
.\venv\Scripts\python.exe scripts\train_yolo.py --epochs 100 --batch 16
```
Upon completion, the script verifies accuracy and automatically deploys the validated checkpoint to `models/best.pt`.
