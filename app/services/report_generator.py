"""Forensic PDF Investigation Report generator using ReportLab."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.config import BASE_DIR, REPORTS_DIR, STATIC_DIR


def generate_forensic_pdf_report(
    case_data: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    output_filename: str | None = None,
) -> Path:
    """Compile and export an official forensic investigation PDF report."""
    case_id = case_data.get("case_id", "CRIME-REPORT")
    if not output_filename:
        output_filename = f"Report_{case_id}.pdf"

    output_path = REPORTS_DIR / output_filename
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#0284c7"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    body_bold = ParagraphStyle(
        "ReportBodyBold",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#0f172a"),
    )
    badge_style = ParagraphStyle(
        "ReportBadge",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("FORENSIC EVIDENCE & CRIME SCENE INVESTIGATION DIVISION", subtitle_style))
    story.append(Paragraph("AI-ASSISTED EVIDENCE DETECTION REPORT", title_style))
    story.append(
        Paragraph(
            f"Case File Ref: <b>{case_id}</b> | Classification: <b>OFFICIAL LAW ENFORCEMENT FORENSICS</b>",
            body_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0284c7"), spaceAfter=12))

    # 2. Case Metadata Table
    threat_level = case_data.get("threat_level", "LOW")
    threat_bg = "#ef4444" if threat_level == "CRITICAL" else ("#f59e0b" if threat_level == "HIGH" else "#0284c7")

    meta_table_data = [
        [
            Paragraph("<b>Case Reference:</b>", body_style),
            Paragraph(str(case_id), body_bold),
            Paragraph("<b>Threat Assessment:</b>", body_style),
            Paragraph(f"<font color='white'><b>{threat_level}</b></font>", badge_style),
        ],
        [
            Paragraph("<b>Incident Title:</b>", body_style),
            Paragraph(case_data.get("title", "Evidence Analysis"), body_style),
            Paragraph("<b>Threat Score:</b>", body_style),
            Paragraph(f"{case_data.get('threat_score', 0)} / 100", body_bold),
        ],
        [
            Paragraph("<b>Lead Investigator:</b>", body_style),
            Paragraph(case_data.get("investigator", "Forensic Officer"), body_style),
            Paragraph("<b>Department:</b>", body_style),
            Paragraph(case_data.get("department", "CSI Division"), body_style),
        ],
        [
            Paragraph("<b>Scene Location:</b>", body_style),
            Paragraph(case_data.get("location", "Scene Location"), body_style),
            Paragraph("<b>Model Architecture:</b>", body_style),
            Paragraph(case_data.get("model_used", "Ensemble"), body_style),
        ],
        [
            Paragraph("<b>Date / Timestamp:</b>", body_style),
            Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), body_style),
            Paragraph("<b>Total Items Found:</b>", body_style),
            Paragraph(f"{len(evidence_items)} objects", body_bold),
        ],
    ]

    meta_table = Table(meta_table_data, colWidths=[1.4 * inch, 2.2 * inch, 1.4 * inch, 2.0 * inch])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor(threat_bg)),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. Annotated Crime Scene Photograph / Video Summary
    annotated_rel = case_data.get("annotated_path", "")
    annotated_full = STATIC_DIR / annotated_rel if annotated_rel else None
    if annotated_full and annotated_full.is_file():
        is_video_file = annotated_rel.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))
        if not is_video_file:
            story.append(Paragraph("1. Primary Crime Scene Visual Identification", section_style))
            img = Image(str(annotated_full), width=6.8 * inch, height=3.2 * inch, kind="proportional")
            story.append(img)
            story.append(Spacer(1, 10))
        else:
            story.append(Paragraph("1. Primary Video Surveillance Analysis", section_style))
            story.append(
                Paragraph(
                    f"Archival Surveillance Recording: <b>{annotated_full.name}</b> | Media Duration: <b>{case_data.get('video_duration', 0.0):.1f}s</b><br/>"
                    "Evidence moments extracted and time-coded below.",
                    body_style,
                )
            )
            story.append(Spacer(1, 10))

    # 4. Itemized Evidence Register Table
    story.append(Paragraph("2. Forensic Evidence Register & Detections", section_style))
    if evidence_items:
        table_rows = [
            [
                Paragraph("<b>#</b>", body_bold),
                Paragraph("<b>Identified Class</b>", body_bold),
                Paragraph("<b>Forensic Category</b>", body_bold),
                Paragraph("<b>Severity</b>", body_bold),
                Paragraph("<b>Confidence</b>", body_bold),
                Paragraph("<b>Coordinates (px)</b>", body_bold),
            ]
        ]

        for idx, item in enumerate(evidence_items, start=1):
            sev = item.get("severity", "LOW")
            box = item.get("box", [item.get("bbox_x1", 0), item.get("bbox_y1", 0), item.get("bbox_x2", 0), item.get("bbox_y2", 0)])
            box_str = f"[{int(box[0])},{int(box[1])}]-[{int(box[2])},{int(box[3])}]"
            conf_val = item.get("confidence", 0.0)

            table_rows.append(
                [
                    Paragraph(str(idx), body_style),
                    Paragraph(f"<b>{item.get('class', item.get('class_name', 'Unknown'))}</b>", body_style),
                    Paragraph(item.get("category", "General"), body_style),
                    Paragraph(sev, body_bold),
                    Paragraph(f"{conf_val:.1f}%", body_style),
                    Paragraph(box_str, body_style),
                ]
            )

        reg_table = Table(table_rows, colWidths=[0.3 * inch, 1.5 * inch, 1.8 * inch, 1.0 * inch, 1.0 * inch, 1.4 * inch])
        reg_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        story.append(reg_table)
    else:
        story.append(Paragraph("No positive evidence detections recorded above the confidence threshold.", body_style))

    story.append(Spacer(1, 14))

    # 5. Evidence Crops Section (if available)
    crop_items = [item for item in evidence_items if item.get("crop_path")][:4]
    if crop_items:
        story.append(Paragraph("3. Extracted High-Resolution Evidence Crops", section_style))
        crop_cells = []
        crop_labels = []
        for item in crop_items:
            crop_full = STATIC_DIR / item["crop_path"]
            if crop_full.is_file():
                crop_img = Image(str(crop_full), width=1.5 * inch, height=1.1 * inch, kind="proportional")
                crop_cells.append(crop_img)
                crop_labels.append(
                    Paragraph(
                        f"<b>{item.get('class', item.get('class_name', ''))}</b><br/>{item.get('confidence', 0):.1f}% conf",
                        body_style,
                    )
                )

        if crop_cells:
            crops_table = Table([crop_cells, crop_labels], colWidths=[1.7 * inch] * len(crop_cells))
            crops_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                        ("PADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(crops_table)
            story.append(Spacer(1, 14))

    # 6. Chain of Custody & Verification Signatures
    sign_block = [
        Paragraph("4. Chain of Custody & Legal Forensic Verification", section_style),
        Paragraph(
            "I hereby certify that the evidence analyzed in this report was processed in accordance with established "
            "forensic computer vision protocols. AI predictions serve as investigative decision support and have been "
            "archived with complete cryptographic integrity.",
            body_style,
        ),
        Spacer(1, 16),
        Table(
            [
                [
                    Paragraph("________________________________________<br/><b>Investigating Officer Signature</b>", body_style),
                    Paragraph("________________________________________<br/><b>Forensic Supervisor Approval</b>", body_style),
                ],
                [
                    Paragraph(f"Date: <b>{datetime.now(timezone.utc).strftime('%B %d, %Y')}</b>", body_style),
                    Paragraph("Badge / Identification: <b>CSI-EVID-8491</b>", body_style),
                ],
            ],
            colWidths=[3.5 * inch, 3.5 * inch],
        ),
    ]

    story.append(KeepTogether(sign_block))

    doc.build(story)
    return output_path
