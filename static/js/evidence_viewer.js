/**
 * Interactive Forensic Evidence Canvas & Inspection Viewer
 */

document.addEventListener("DOMContentLoaded", () => {
    const canvas = document.getElementById("evidenceCanvas");
    const container = document.getElementById("canvasContainer");
    const baseImg = document.getElementById("baseEvidenceImage");

    if (!canvas || !baseImg) return;

    const ctx = canvas.getContext("2d");
    let activeBoxIndex = -1;
    let detectionsData = [];

    // Parse detections embedded in data attribute
    try {
        const raw = canvas.getAttribute("data-detections");
        detectionsData = raw ? JSON.parse(raw) : [];
    } catch (e) {
        console.error("Error reading detections payload", e);
    }

    function initCanvas() {
        if (!baseImg.complete) {
            baseImg.onload = initCanvas;
            return;
        }

        canvas.width = baseImg.naturalWidth;
        canvas.height = baseImg.naturalHeight;
        drawOverlay();
    }

    function drawOverlay() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw image onto canvas
        ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height);

        detectionsData.forEach((item, index) => {
            const box = item.box || [item.bbox_x1, item.bbox_y1, item.bbox_x2, item.bbox_y2];
            if (!box || box.length < 4) return;

            const [x1, y1, x2, y2] = box.map(Math.round);
            const w = x2 - x1;
            const h = y2 - y1;
            const isHovered = (index === activeBoxIndex);

            // Bounding box styling
            ctx.save();
            ctx.lineWidth = isHovered ? 4 : 2;
            ctx.strokeStyle = isHovered ? "#38bdf8" : (item.color || "#0284c7");
            if (isHovered) {
                ctx.shadowColor = "#38bdf8";
                ctx.shadowBlur = 15;
            }

            // Draw rectangle
            ctx.strokeRect(x1, y1, w, h);

            // Corner reticles
            const corner = Math.min(16, Math.max(6, Math.round(w * 0.15)));
            ctx.lineWidth = 3;
            // Top-left
            ctx.beginPath();
            ctx.moveTo(x1, y1 + corner); ctx.lineTo(x1, y1); ctx.lineTo(x1 + corner, y1);
            // Top-right
            ctx.moveTo(x2 - corner, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + corner);
            // Bottom-left
            ctx.beginPath();
            ctx.moveTo(x1, y2 - corner); ctx.lineTo(x1, y2); ctx.lineTo(x1 + corner, y2);
            // Bottom-right
            ctx.moveTo(x2 - corner, y2); ctx.lineTo(x2, y2); ctx.lineTo(x2, y2 - corner);
            ctx.stroke();

            // Label pill
            const label = `${item.class || item.class_name} ${Math.round(item.confidence)}%`;
            ctx.font = "bold 13px 'JetBrains Mono', monospace";
            const textWidth = ctx.measureText(label).width;

            ctx.fillStyle = isHovered ? "rgba(56, 189, 248, 0.95)" : "rgba(10, 18, 30, 0.9)";
            ctx.fillRect(x1, Math.max(0, y1 - 22), textWidth + 12, 22);

            ctx.fillStyle = isHovered ? "#04101e" : "#f8fafc";
            ctx.fillText(label, x1 + 6, Math.max(16, y1 - 6));

            ctx.restore();
        });
    }

    // Canvas Mouse Interaction
    canvas.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const mouseX = (e.clientX - rect.left) * scaleX;
        const mouseY = (e.clientY - rect.top) * scaleY;

        let foundIndex = -1;
        for (let i = 0; i < detectionsData.length; i++) {
            const b = detectionsData[i].box || [
                detectionsData[i].bbox_x1,
                detectionsData[i].bbox_y1,
                detectionsData[i].bbox_x2,
                detectionsData[i].bbox_y2
            ];
            if (mouseX >= b[0] && mouseX <= b[2] && mouseY >= b[1] && mouseY <= b[3]) {
                foundIndex = i;
                break;
            }
        }

        if (foundIndex !== activeBoxIndex) {
            activeBoxIndex = foundIndex;
            drawOverlay();
            highlightTableRow(activeBoxIndex);
        }
    });

    canvas.addEventListener("mouseleave", () => {
        if (activeBoxIndex !== -1) {
            activeBoxIndex = -1;
            drawOverlay();
            highlightTableRow(-1);
        }
    });

    // Synchronize Table Row Hover with Canvas
    document.querySelectorAll(".evidence-row").forEach((row) => {
        const idx = parseInt(row.getAttribute("data-index"), 10);

        row.addEventListener("mouseenter", () => {
            activeBoxIndex = idx;
            drawOverlay();
            row.style.background = "rgba(56, 189, 248, 0.12)";
        });

        row.addEventListener("mouseleave", () => {
            activeBoxIndex = -1;
            drawOverlay();
            row.style.background = "";
        });
    });

    function highlightTableRow(idx) {
        document.querySelectorAll(".evidence-row").forEach((row) => {
            const rIdx = parseInt(row.getAttribute("data-index"), 10);
            if (rIdx === idx) {
                row.style.background = "rgba(56, 189, 248, 0.15)";
            } else {
                row.style.background = "";
            }
        });
    }

    // View toggle handler (Annotated / Interactive Canvas / Original / Clarity Suite / Split Slider)
    const clarityButtons = document.querySelectorAll(".btn-clarity, .btn-view-mode");
    const viewMap = {
        annotated: document.getElementById("annotatedView"),
        original: document.getElementById("originalView"),
        enhanced: document.getElementById("enhancedView"),
        clahe: document.getElementById("claheView"),
        sharpened: document.getElementById("sharpenedView"),
        night_vision: document.getElementById("nightVisionView"),
        split_compare: document.getElementById("splitCompareView"),
        interactive: document.getElementById("canvasView"),
    };

    clarityButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            clarityButtons.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");

            const mode = btn.getAttribute("data-mode");

            // Hide all views
            Object.values(viewMap).forEach((el) => {
                if (el) el.style.display = "none";
            });

            // Show selected view
            if (viewMap[mode]) {
                viewMap[mode].style.display = "block";
            }

            if (mode === "interactive") {
                initCanvas();
            } else if (mode === "split_compare") {
                initSplitSlider();
            }
        });
    });

    // Split Before/After Slider Interaction
    const splitWrap = document.getElementById("splitCompareView");
    const splitLayerAfter = document.getElementById("splitLayerAfter");
    const splitDivider = document.getElementById("splitDivider");
    const splitImgBefore = document.getElementById("splitImgBefore");
    const splitImgAfter = document.getElementById("splitImgAfter");

    let isSliding = false;

    function initSplitSlider() {
        if (!splitWrap || !splitImgBefore || !splitImgAfter) return;
        const updateWidth = () => {
            const w = splitWrap.offsetWidth;
            if (w > 0) {
                splitImgAfter.style.width = w + "px";
            }
        };
        updateWidth();
        window.addEventListener("resize", updateWidth);
    }

    function setSplitPosition(x) {
        if (!splitWrap || !splitLayerAfter || !splitDivider) return;
        const rect = splitWrap.getBoundingClientRect();
        let pos = (x - rect.left) / rect.width;
        pos = Math.max(0.02, Math.min(0.98, pos));
        const pct = (pos * 100).toFixed(2) + "%";
        splitLayerAfter.style.width = pct;
        splitDivider.style.left = pct;
    }

    if (splitWrap) {
        splitWrap.addEventListener("mousedown", (e) => {
            isSliding = true;
            setSplitPosition(e.clientX);
        });

        window.addEventListener("mousemove", (e) => {
            if (!isSliding) return;
            setSplitPosition(e.clientX);
        });

        window.addEventListener("mouseup", () => {
            isSliding = false;
        });

        // Touch support for mobile / touchpads
        splitWrap.addEventListener("touchstart", (e) => {
            if (e.touches.length > 0) {
                isSliding = true;
                setSplitPosition(e.touches[0].clientX);
            }
        });

        window.addEventListener("touchmove", (e) => {
            if (!isSliding || e.touches.length === 0) return;
            setSplitPosition(e.touches[0].clientX);
        });

        window.addEventListener("touchend", () => {
            isSliding = false;
        });
    }

    // Live Re-Enhancement via /api/v1/enhance
    const btnLiveReEnhance = document.getElementById("btnLiveReEnhance");
    if (btnLiveReEnhance) {
        btnLiveReEnhance.addEventListener("click", async () => {
            const caseId = btnLiveReEnhance.getAttribute("data-caseid");
            const sharpen = parseFloat(document.getElementById("paramSharpen")?.value || "1.5");
            const clahe = parseFloat(document.getElementById("paramClahe")?.value || "3.0");

            const origText = btnLiveReEnhance.innerHTML;
            btnLiveReEnhance.disabled = true;
            btnLiveReEnhance.innerHTML = `<span>⏳ Clarifying Evidence...</span>`;

            try {
                const res = await fetch("/api/v1/enhance", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        case_id: caseId,
                        mode: "full",
                        sharpen_strength: sharpen,
                        clahe_clip: clahe,
                    }),
                });
                const data = await res.json();
                if (data.success && data.enhanced_url) {
                    const cacheBust = data.enhanced_url + "?t=" + Date.now();
                    const enhImg = document.getElementById("enhancedView");
                    if (enhImg) enhImg.src = cacheBust;
                    if (splitImgAfter) splitImgAfter.src = cacheBust;
                    if (baseImg) {
                        baseImg.src = cacheBust;
                        baseImg.onload = initCanvas;
                    }

                    // Update UI labels
                    const scoreEl = document.getElementById("displayClarityScore");
                    if (scoreEl && data.after_metrics) {
                        scoreEl.innerText = data.after_metrics.quality_score.toFixed(1);
                    }
                    const gainEl = document.getElementById("displayGainPct");
                    if (gainEl && data.sharpness_gain_pct !== undefined) {
                        gainEl.innerText = (data.sharpness_gain_pct >= 0 ? "+" : "") + data.sharpness_gain_pct + "% Sharper";
                    }

                    // Switch view to Enhanced
                    const btnEnh = document.querySelector('[data-mode="enhanced"]');
                    if (btnEnh) btnEnh.click();
                } else {
                    alert("Enhancement failed: " + (data.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Re-enhancement error:", err);
                alert("Network error while clarifying image: " + err.message);
            } finally {
                btnLiveReEnhance.disabled = false;
                btnLiveReEnhance.innerHTML = origText;
            }
        });
    }

    initCanvas();
});

