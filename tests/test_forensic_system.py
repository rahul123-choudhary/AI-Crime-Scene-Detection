"""Automated test suite for AI Crime Scene Detection Workstation."""

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.config import BASE_DIR, DATABASE_PATH, REPORTS_DIR
from app.database import get_case_by_id, get_system_stats, init_db, insert_case, list_cases
from app.services.analyzer import process_scene_analysis
from app.services.detector import detect_evidence
from app.services.report_generator import generate_forensic_pdf_report


class TestForensicSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app({"TESTING": True})
        cls.client = cls.app.test_client()
        cls.test_image_path = BASE_DIR / "crime.jpg"

    def test_01_database_operations(self):
        """Test database initialization, insertion, and retrieval."""
        import uuid
        init_db()
        test_case_id = f"TEST-CASE-{uuid.uuid4().hex[:8]}"
        case_data = {
            "case_id": test_case_id,
            "title": "Unit Test Scene Analysis",
            "investigator": "Test Officer",
            "department": "Test Unit",
            "location": "Test Lab",
            "incident_type": "Simulation",
            "notes": "Testing db persistence",
            "threat_level": "CRITICAL",
            "threat_score": 85,
            "model_used": "Ensemble",
            "image_path": "uploads/test.jpg",
            "annotated_path": "results/test_annotated.jpg",
        }
        evidence_items = [
            {
                "class": "Gun",
                "category": "Firearms & Ballistics",
                "severity": "CRITICAL",
                "confidence": 92.5,
                "box": [10, 20, 100, 200],
                "crop_path": "crops/test_crop.jpg",
            }
        ]

        inserted_id = insert_case(case_data, evidence_items)
        self.assertEqual(inserted_id, test_case_id)

        case = get_case_by_id(test_case_id)
        self.assertIsNotNone(case)
        self.assertEqual(case["title"], "Unit Test Scene Analysis")
        self.assertEqual(len(case["evidence_items"]), 1)
        self.assertEqual(case["evidence_items"][0]["class_name"], "Gun")

        stats = get_system_stats()
        self.assertGreaterEqual(stats["total_cases"], 1)

    def test_02_detection_pipeline(self):
        """Test YOLO multi-model detection on crime.jpg."""
        self.assertTrue(self.test_image_path.is_file())
        result = detect_evidence(self.test_image_path, model_choice="ensemble", confidence=0.20)
        self.assertIn("detections", result)
        self.assertIn("inference_ms", result)
        self.assertGreater(result["image_width"], 0)
        self.assertGreater(result["image_height"], 0)

    def test_03_forensic_analyzer_and_crops(self):
        """Test forensic threat analysis and crop generation."""
        det_result = detect_evidence(self.test_image_path, model_choice="ensemble", confidence=0.20)
        raw_img = det_result["raw_image"]
        analysis = process_scene_analysis(raw_img, det_result["detections"], "TEST-ANALYZER")

        self.assertIn(analysis["threat_level"], ["CRITICAL", "HIGH", "MEDIUM", "LOW", "CLEAR / UNVERIFIED"])
        self.assertGreaterEqual(analysis["threat_score"], 0)
        self.assertTrue((BASE_DIR / "static" / analysis["annotated_rel_path"]).is_file())

    def test_04_pdf_report_generator(self):
        """Test ReportLab PDF report generation."""
        import uuid
        case_data = {
            "case_id": f"TEST-PDF-{uuid.uuid4().hex[:8]}",
            "title": "PDF Generation Test Case",
            "investigator": "Officer J. Doe",
            "department": "Forensic Bureau",
            "location": "Downtown Incident",
            "threat_level": "HIGH",
            "threat_score": 65,
            "model_used": "Dual Ensemble",
            "annotated_path": "results/TEST-ANALYZER_annotated.jpg",
        }
        evidence_items = [
            {
                "class": "Knife",
                "category": "Edged Weapons",
                "severity": "HIGH",
                "confidence": 88.0,
                "box": [50, 60, 150, 200],
            }
        ]

        pdf_path = generate_forensic_pdf_report(case_data, evidence_items)
        self.assertTrue(pdf_path.is_file())
        self.assertGreater(pdf_path.stat().st_size, 1000)

    def test_05_api_health_endpoint(self):
        """Test /api/v1/health response."""
        res = self.client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("models", data)

    def test_06_api_detect_endpoint(self):
        """Test /api/v1/detect with image payload."""
        with open(self.test_image_path, "rb") as f:
            data = {
                "image": (io.BytesIO(f.read()), "test_crime.jpg"),
                "model": "ensemble",
                "confidence": "0.25",
            }
            res = self.client.post("/api/v1/detect", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            res_data = res.get_json()
            self.assertIn("case_id", res_data)
            self.assertIn("threat_level", res_data)
            self.assertIn("detections", res_data)

    def test_07_web_pages(self):
        """Test key HTML routes render without exceptions."""
        for path in ["/", "/cases", "/batch", "/api-docs", "/live"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Failed for {path}")

    def test_08_live_frame_detection_api(self):
        """Test ultra-low-latency /api/v1/detect_frame endpoint."""
        with open(self.test_image_path, "rb") as f:
            data = {"frame": (io.BytesIO(f.read()), "frame.jpg"), "model": "ensemble"}
            res = self.client.post("/api/v1/detect_frame", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("detections", data)
            self.assertIn("threat_level", data)
            self.assertIn("latency_ms", data)

    def test_09_video_case_pdf_generation(self):
        """Test ReportLab PDF generation for a video surveillance case."""
        import uuid
        case_data = {
            "case_id": f"TEST-VID-{uuid.uuid4().hex[:8]}",
            "title": "Video Surveillance Test Case",
            "investigator": "Officer J. Doe",
            "department": "Video Forensics",
            "location": "CCTV Hub",
            "threat_level": "CRITICAL",
            "threat_score": 90,
            "model_used": "Ensemble",
            "annotated_path": "results/test_annotated.mp4",
            "media_type": "video",
            "video_duration": 12.5,
        }
        evidence_items = [
            {
                "class": "Gun",
                "category": "Firearms & Ballistics",
                "severity": "CRITICAL",
                "confidence": 95.0,
                "box": [100, 100, 200, 250],
                "video_timestamp": 4.2,
            }
        ]
        pdf_path = generate_forensic_pdf_report(case_data, evidence_items)
        self.assertTrue(pdf_path.is_file())
        self.assertGreater(pdf_path.stat().st_size, 1000)


    def test_10_video_cross_route_in_predict(self):
        """Test submitting a video sample to /predict automatically routes to predict_video."""
        res = self.client.post(
            "/predict",
            data={
                "sample_image": "sample_cctv_footage.mp4",
                "investigator": "Auto-Route Detective",
                "location": "North Entrance CCTV",
                "model": "ensemble",
            },
        )
        self.assertEqual(res.status_code, 302)
        self.assertIn("/result/CRIME-VID-", res.headers.get("Location", ""))

    def test_11_auto_detect_metadata_api(self):
        """Test AI auto-detection endpoint configuring all 6 parameters."""
        with open(self.test_image_path, "rb") as f:
            data = {"file": (io.BytesIO(f.read()), "unnamed_evidence.jpg")}
            res = self.client.post("/api/v1/auto_detect_metadata", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            json_data = res.get_json()
            self.assertTrue(json_data["success"])
            self.assertIn("fields", json_data)
            fields = json_data["fields"]
            self.assertIn("model", fields)
            self.assertIn("confidence", fields)
            self.assertIn("investigator", fields)
            self.assertIn("location", fields)
            self.assertIn("title", fields)
            self.assertIn("incident_type", fields)
    def test_12_forensic_enhancement_pipeline_and_api(self):
        """Test forensic clarity measurement, enhancement pipeline, and /api/v1/enhance endpoint."""
        from app.services.enhancer import enhance_forensic_image, measure_image_clarity
        import cv2

        raw_img = cv2.imread(str(self.test_image_path))
        self.assertIsNotNone(raw_img)

        # 1. Clarity metrics computation
        clarity_info = measure_image_clarity(raw_img)
        self.assertIn("laplacian_variance", clarity_info)
        self.assertIn("quality_score", clarity_info)
        self.assertGreater(clarity_info["laplacian_variance"], 0)

        # 2. Pipeline enhancement
        enhanced_res = enhance_forensic_image(raw_img, mode="full_forensic")
        self.assertIn("enhanced_image", enhanced_res)
        self.assertIn("sharpness_gain_pct", enhanced_res)
        self.assertGreater(enhanced_res["sharpness_gain_pct"], 0)

        # 3. API endpoint test with image payload
        with open(self.test_image_path, "rb") as f:
            data = {"image": (io.BytesIO(f.read()), "scene_test.jpg"), "mode": "all"}
            res = self.client.post("/api/v1/enhance", data=data, content_type="multipart/form-data")
            self.assertEqual(res.status_code, 200)
            json_data = res.get_json()
            self.assertTrue(json_data["success"])
            self.assertIn("before_metrics", json_data)
            self.assertIn("after_metrics", json_data)
            self.assertIn("variants", json_data)
            self.assertIn("full_enhanced", json_data["variants"])
            self.assertIn("clahe", json_data["variants"])
            self.assertIn("sharpened", json_data["variants"])
            self.assertIn("night_vision", json_data["variants"])


if __name__ == "__main__":
    unittest.main()

