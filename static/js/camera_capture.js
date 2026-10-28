/**
 * Field Camera Capture, Drag-and-Drop Intake, and Instant AI Neural Vision Pre-Scan Module
 * Enterprise Forensic Workstation
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Tab Switching Logic
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach((btn) => {
        btn.addEventListener("click", () => {
            tabBtns.forEach((b) => b.classList.remove("active"));
            tabContents.forEach((c) => c.classList.remove("active"));

            btn.classList.add("active");
            const target = document.getElementById(btn.getAttribute("data-tab"));
            if (target) target.classList.add("active");
        });
    });

    // 2. Elements for Dynamic Auto-Tuning (All 6 Form Parameters + Badges)
    const modelSelect = document.getElementById("model");
    const confidenceInput = document.getElementById("confidence");
    const confOutput = document.getElementById("confOutput");
    const investigatorInput = document.getElementById("investigator");
    const locationInput = document.getElementById("location");
    const titleInput = document.getElementById("title");
    const incidentSelect = document.getElementById("incident_type");

    // Dynamic Field Badges
    const modelBadge = document.getElementById("modelBadge");
    const confBadge = document.getElementById("confBadge");
    const investigatorBadge = document.getElementById("investigatorBadge");
    const locationBadge = document.getElementById("locationBadge");
    const titleBadge = document.getElementById("titleBadge");
    const incidentBadge = document.getElementById("incidentBadge");

    // Banner & Buttons
    const autoTuneBanner = document.getElementById("smartAutoTuneBanner");
    const autoTuneIcon = document.getElementById("autoTuneIcon");
    const autoTuneTitle = document.getElementById("autoTuneTitle");
    const autoTuneDetails = document.getElementById("autoTuneDetails");
    const btnResetAutoTune = document.getElementById("btnResetAutoTune");
    const presetChips = document.querySelectorAll(".preset-chip");
    const mainForm = document.getElementById("mainIntakeForm");
    const mainSubmitBtn = document.getElementById("mainSubmitBtn");
    const submitBtnText = document.getElementById("submitBtnText");

    // AI Scanner & Findings Elements
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("fileInput");
    const previewContainer = document.getElementById("previewContainer");
    const previewImage = document.getElementById("previewImage");
    const previewVideo = document.getElementById("previewVideo");
    const aiScanOverlay = document.getElementById("aiScanOverlay");
    const aiScanStatusText = document.getElementById("aiScanStatusText");
    const aiFindingsBar = document.getElementById("aiFindingsBar");
    const aiThreatPill = document.getElementById("aiThreatPill");
    const aiFindingsSummary = document.getElementById("aiFindingsSummary");
    const aiInferenceSpeed = document.getElementById("aiInferenceSpeed");
    const aiTagsList = document.getElementById("aiTagsList");

    const defaultSettings = {
        model: "ensemble",
        confidence: "0.25",
        confText: "25%",
        investigator: "Forensic Investigator",
        location: "Sector 4 Scene Investigation",
        title: "",
        incident: "Armed Assault / Violent Incident"
    };

    function triggerFieldPulse(...elements) {
        elements.forEach((el) => {
            if (!el) return;
            el.classList.remove("field-pulse");
            void el.offsetWidth; // trigger reflow
            el.classList.add("field-pulse");
        });
    }

    function setBadgeClasses(badgeType) {
        const badges = [modelBadge, confBadge, investigatorBadge, locationBadge, titleBadge, incidentBadge];
        badges.forEach((b) => {
            if (!b) return;
            b.classList.remove("badge-video", "badge-weapon", "badge-trace", "badge-homicide");
            if (badgeType) {
                b.classList.add(`badge-${badgeType}`);
            }
        });
    }

    function setActivePresetChip(presetName) {
        presetChips.forEach((chip) => {
            if (chip.getAttribute("data-preset") === presetName) {
                chip.classList.add("active");
            } else {
                chip.classList.remove("active");
            }
        });
    }

    function cleanFilenameForTitle(filename) {
        const stem = filename.substring(0, filename.lastIndexOf('.')) || filename;
        return stem
            .replace(/[-_.]+/g, " ")
            .replace(/\b(jpg|png|webp|mp4|avi|mov|mkv|rf|[a-f0-9]{16,})\b/gi, "")
            .trim()
            .split(" ")
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(" ");
    }

    /**
     * Applies preset manually if clicked by user
     */
    function applyPreset(presetName, customTitle = "") {
        if (presetName === "weapons") {
            if (modelSelect) modelSelect.value = "weapon";
            if (confidenceInput) confidenceInput.value = "0.25";
            if (confOutput) confOutput.value = "25%";
            if (investigatorInput) investigatorInput.value = "Ballistics & Firearms Examiner";
            if (locationInput) locationInput.value = "Primary Armed Incident Scene";
            if (titleInput) titleInput.value = customTitle || "Firearms & Ballistics Evidence Sweep";
            if (incidentSelect) incidentSelect.value = "Armed Assault / Violent Incident";

            if (modelBadge) modelBadge.textContent = "Weapon Specialist";
            if (confBadge) confBadge.textContent = "25% Ballistics";
            if (investigatorBadge) investigatorBadge.textContent = "Ballistics Lead";
            if (locationBadge) locationBadge.textContent = "Armed Scene";
            if (titleBadge) titleBadge.textContent = "Weapons Sweep";
            if (incidentBadge) incidentBadge.textContent = "Armed Incident";
            setBadgeClasses("weapon");
            setActivePresetChip("weapons");

            if (autoTuneBanner) {
                autoTuneBanner.style.display = "flex";
                autoTuneBanner.classList.remove("video-mode");
                if (autoTuneIcon) autoTuneIcon.textContent = "🔫";
                if (autoTuneTitle) autoTuneTitle.textContent = "⚡ Calibrated for Firearms & Weapons";
                if (autoTuneDetails) autoTuneDetails.textContent = "Specialized weapon detector engaged with 25% confidence for guns, rifles, and edged blades.";
            }

        } else if (presetName === "traces") {
            if (modelSelect) modelSelect.value = "forensic";
            if (confidenceInput) confidenceInput.value = "0.15";
            if (confOutput) confOutput.value = "15%";
            if (investigatorInput) investigatorInput.value = "Latent Print & Serology Specialist";
            if (locationInput) locationInput.value = "Crime Scene Surface & Trace Interior";
            if (titleInput) titleInput.value = customTitle || "Latent Biometrics & Biological Evidence Sweep";
            if (incidentSelect) incidentSelect.value = "Biological & Latent Trace Sweep";

            if (modelBadge) modelBadge.textContent = "Trace Specialist";
            if (confBadge) confBadge.textContent = "15% High Sensitivity";
            if (investigatorBadge) investigatorBadge.textContent = "Serology Lead";
            if (locationBadge) locationBadge.textContent = "Trace Interior";
            if (titleBadge) titleBadge.textContent = "Latent Biometrics";
            if (incidentBadge) incidentBadge.textContent = "Trace Sweep";
            setBadgeClasses("trace");
            setActivePresetChip("traces");

            if (autoTuneBanner) {
                autoTuneBanner.style.display = "flex";
                autoTuneBanner.classList.remove("video-mode");
                if (autoTuneIcon) autoTuneIcon.textContent = "🔬";
                if (autoTuneTitle) autoTuneTitle.textContent = "⚡ Calibrated for Biological & Latent Traces";
                if (autoTuneDetails) autoTuneDetails.textContent = "High-sensitivity threshold (15%) enabled to identify faint blood splatters, hair, and latent prints.";
            }

        } else if (presetName === "cctv" || presetName === "video") {
            if (modelSelect) modelSelect.value = "ensemble";
            if (confidenceInput) confidenceInput.value = "0.30";
            if (confOutput) confOutput.value = "30%";
            if (investigatorInput) investigatorInput.value = "Video & Digital Forensics Examiner";
            if (locationInput) locationInput.value = "CCTV Surveillance Node / Perimeter";
            if (titleInput) titleInput.value = customTitle || "Video Surveillance Evidence Audit";
            if (incidentSelect) incidentSelect.value = "CCTV / Video Surveillance Sweep";

            if (modelBadge) modelBadge.textContent = "Surveillance Suite";
            if (confBadge) confBadge.textContent = "30% Noise Filter";
            if (investigatorBadge) investigatorBadge.textContent = "Video Forensics";
            if (locationBadge) locationBadge.textContent = "CCTV Node";
            if (titleBadge) titleBadge.textContent = "Video Audit";
            if (incidentBadge) incidentBadge.textContent = "CCTV Sweep";
            setBadgeClasses("video");
            setActivePresetChip("cctv");

            if (autoTuneBanner) {
                autoTuneBanner.style.display = "flex";
                autoTuneBanner.classList.add("video-mode");
                if (autoTuneIcon) autoTuneIcon.textContent = "📹";
                if (autoTuneTitle) autoTuneTitle.textContent = "⚡ Calibrated for Video Surveillance Footage";
                if (autoTuneDetails) autoTuneDetails.textContent = "Motion-stabilized threshold set to 30% to suppress compression noise and false positives.";
            }

        } else if (presetName === "homicide") {
            if (modelSelect) modelSelect.value = "ensemble";
            if (confidenceInput) confidenceInput.value = "0.20";
            if (confOutput) confOutput.value = "20%";
            if (investigatorInput) investigatorInput.value = "Senior Homicide Investigator & CSI Lead";
            if (locationInput) locationInput.value = "Primary Homicide Scene / Incident Perimeter";
            if (titleInput) titleInput.value = customTitle || "Homicide Investigation Evidence Sweep";
            if (incidentSelect) incidentSelect.value = "Homicide Investigation";

            if (modelBadge) modelBadge.textContent = "Dual Ensemble";
            if (confBadge) confBadge.textContent = "20% Sensitive";
            if (investigatorBadge) investigatorBadge.textContent = "Homicide Division";
            if (locationBadge) locationBadge.textContent = "Homicide Scene";
            if (titleBadge) titleBadge.textContent = "Death Investigation";
            if (incidentBadge) incidentBadge.textContent = "Homicide";
            setBadgeClasses("homicide");
            setActivePresetChip("homicide");

            if (autoTuneBanner) {
                autoTuneBanner.style.display = "flex";
                autoTuneBanner.classList.remove("video-mode");
                if (autoTuneIcon) autoTuneIcon.textContent = "💀";
                if (autoTuneTitle) autoTuneTitle.textContent = "⚡ Calibrated for Homicide Investigation";
                if (autoTuneDetails) autoTuneDetails.textContent = "Dual-ensemble engine engaged with 20% sensitivity for multi-evidence scene sweep.";
            }

        } else {
            if (modelSelect) modelSelect.value = "ensemble";
            if (confidenceInput) confidenceInput.value = "0.25";
            if (confOutput) confOutput.value = "25%";
            if (investigatorInput) investigatorInput.value = "Forensic Crime Scene Investigator";
            if (locationInput) locationInput.value = "Sector 4 Scene Investigation";
            if (titleInput) titleInput.value = customTitle || "Comprehensive Crime Scene Evidence Sweep";
            if (incidentSelect) incidentSelect.value = "Suspicious Scene Audit";

            if (modelBadge) modelBadge.textContent = "Dual Ensemble";
            if (confBadge) confBadge.textContent = "25% Balanced";
            if (investigatorBadge) investigatorBadge.textContent = "Forensic CSI";
            if (locationBadge) locationBadge.textContent = "Scene Location";
            if (titleBadge) titleBadge.textContent = "Evidence Sweep";
            if (incidentBadge) incidentBadge.textContent = "Scene Audit";
            setBadgeClasses("");
            setActivePresetChip("ensemble");

            if (autoTuneBanner) {
                autoTuneBanner.style.display = "flex";
                autoTuneBanner.classList.remove("video-mode");
                if (autoTuneIcon) autoTuneIcon.textContent = "🎯";
                if (autoTuneTitle) autoTuneTitle.textContent = "⚡ General Crime Scene Profile";
                if (autoTuneDetails) autoTuneDetails.textContent = "Dual-Ensemble neural engine engaged with balanced 25% threshold for full sweep.";
            }
        }
        triggerFieldPulse(modelSelect, confidenceInput, confOutput, investigatorInput, locationInput, titleInput, incidentSelect);
    }

    // Preset Chip Click Listeners
    presetChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const preset = chip.getAttribute("data-preset");
            applyPreset(preset);
        });
    });

    if (btnResetAutoTune) {
        btnResetAutoTune.addEventListener("click", () => {
            if (modelSelect) modelSelect.value = defaultSettings.model;
            if (confidenceInput) confidenceInput.value = defaultSettings.confidence;
            if (confOutput) confOutput.value = defaultSettings.confText;
            if (investigatorInput) investigatorInput.value = defaultSettings.investigator;
            if (locationInput) locationInput.value = defaultSettings.location;
            if (titleInput) titleInput.value = defaultSettings.title;
            if (incidentSelect) incidentSelect.value = defaultSettings.incident;
            if (autoTuneBanner) autoTuneBanner.style.display = "none";
            if (aiFindingsBar) aiFindingsBar.style.display = "none";

            if (modelBadge) modelBadge.textContent = "Dual-Ensemble";
            if (confBadge) confBadge.textContent = "25% Balanced";
            if (investigatorBadge) investigatorBadge.textContent = "CSI Officer";
            if (locationBadge) locationBadge.textContent = "Scene Location";
            if (titleBadge) titleBadge.textContent = "Case Title";
            if (incidentBadge) incidentBadge.textContent = "Violent Incident";
            setBadgeClasses("");

            if (mainSubmitBtn) {
                mainSubmitBtn.style.background = "";
                if (submitBtnText) submitBtnText.textContent = "Execute Forensic Evidence Sweep";
            }
            if (mainForm) mainForm.action = "/predict";
            if (fileInput) fileInput.name = "image";

            setActivePresetChip("ensemble");
            triggerFieldPulse(modelSelect, confidenceInput, confOutput, investigatorInput, locationInput, titleInput, incidentSelect);
        });
    }

    /**
     * CORE AI VISION PRE-SCAN:
     * Immediately analyzes the uploaded media file pixels using AI computer vision,
     * detecting objects in real time and configuring ALL 6 parameters automatically!
     */
    async function autoDetectWithAI(file) {
        if (!file) return;

        const name = (file.name || "").toLowerCase();
        const isVideo = file.type.startsWith("video/") || /\.(mp4|avi|mov|mkv|webm)$/i.test(name);
        const cleanTitle = cleanFilenameForTitle(file.name);

        // 1. Show interactive media preview
        if (previewContainer) previewContainer.style.display = "block";
        if (aiScanOverlay) {
            aiScanOverlay.style.display = "flex";
            if (aiScanStatusText) {
                aiScanStatusText.textContent = isVideo
                    ? "AI Video Pre-Scan: Inspecting Frame Dynamics & Evidentiary Objects..."
                    : "AI Neural Vision Pre-Scan: Scanning Pixels For Weapons, Traces & Scene Context...";
            }
        }

        if (isVideo) {
            if (previewImage) previewImage.style.display = "none";
            if (previewVideo) {
                previewVideo.src = URL.createObjectURL(file);
                previewVideo.style.display = "block";
                previewVideo.load();
            }
        } else {
            if (previewVideo) {
                previewVideo.style.display = "none";
                previewVideo.pause();
            }
            const reader = new FileReader();
            reader.onload = (e) => {
                if (previewImage) {
                    previewImage.src = e.target.result;
                    previewImage.style.display = "block";
                }
            };
            reader.readAsDataURL(file);
        }

        // 2. Transmit to AI auto-detection endpoint
        const formData = new FormData();
        formData.append("file", file);
        formData.append("filename", file.name);
        formData.append("is_video", isVideo ? "true" : "false");

        try {
            const response = await fetch("/api/v1/auto_detect_metadata", {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            // Hide scanner overlay after analysis
            if (aiScanOverlay) aiScanOverlay.style.display = "none";

            if (data && data.success) {
                // AUTO-POPULATE ALL 6 FIELDS BY AI:
                if (modelSelect) modelSelect.value = data.fields.model;
                if (confidenceInput) confidenceInput.value = data.fields.confidence;
                if (confOutput) confOutput.value = data.fields.confidence_pct;
                if (investigatorInput) investigatorInput.value = data.fields.investigator;
                if (locationInput) locationInput.value = data.fields.location;
                if (titleInput) titleInput.value = data.fields.title;
                if (incidentSelect) incidentSelect.value = data.fields.incident_type;

                // Update Badges
                if (modelBadge) modelBadge.textContent = data.badges.engine;
                if (confBadge) confBadge.textContent = data.badges.confidence;
                if (investigatorBadge) investigatorBadge.textContent = data.badges.investigator;
                if (locationBadge) locationBadge.textContent = data.badges.location;
                if (titleBadge) titleBadge.textContent = data.badges.title;
                if (incidentBadge) incidentBadge.textContent = data.badges.incident;
                setBadgeClasses(data.badges.style);

                // Set Preset Chip
                if (data.is_video) {
                    setActivePresetChip("cctv");
                } else if (data.badges.style === "weapon") {
                    setActivePresetChip("weapons");
                } else if (data.badges.style === "trace") {
                    setActivePresetChip("traces");
                } else if (data.badges.style === "homicide") {
                    setActivePresetChip("homicide");
                } else {
                    setActivePresetChip("ensemble");
                }

                // Trigger glowing animation on all 6 fields to show they were set by AI!
                triggerFieldPulse(modelSelect, confidenceInput, confOutput, investigatorInput, locationInput, titleInput, incidentSelect);

                // Show AI Findings Bar
                if (aiFindingsBar) {
                    aiFindingsBar.style.display = "flex";
                    if (aiThreatPill) {
                        aiThreatPill.textContent = `${data.threat_level} (${data.threat_score}/100)`;
                        aiThreatPill.className = `threat-pill threat-${data.threat_level}`;
                    }
                    if (aiInferenceSpeed) {
                        aiInferenceSpeed.textContent = `AI Pre-Scan Latency: ${data.latency_ms}ms`;
                    }
                    if (aiFindingsSummary) {
                        if (data.detected_items && data.detected_items.length > 0) {
                            aiFindingsSummary.textContent = `AI Identified: ${data.detected_items.join(", ")} (${data.evidence_count} evidence targets)`;
                        } else {
                            aiFindingsSummary.textContent = `AI Pre-Scan Complete: Clean Evidentiary Baseline`;
                        }
                    }
                    if (aiTagsList) {
                        aiTagsList.innerHTML = "";
                        if (data.detected_items && data.detected_items.length > 0) {
                            data.detected_items.forEach((item) => {
                                const tag = document.createElement("span");
                                tag.className = `ai-evidence-tag tag-${data.badges.style || 'default'}`;
                                tag.innerHTML = `<span>🎯</span> <strong>${item}</strong>`;
                                aiTagsList.appendChild(tag);
                            });
                        } else {
                            const tag = document.createElement("span");
                            tag.className = "ai-evidence-tag";
                            tag.innerHTML = `<span>🔍</span> Scene Sweep Ready`;
                            aiTagsList.appendChild(tag);
                        }
                    }
                }

                // Show Banner with AI Explanation
                if (autoTuneBanner) {
                    autoTuneBanner.style.display = "flex";
                    if (data.is_video) {
                        autoTuneBanner.classList.add("video-mode");
                    } else {
                        autoTuneBanner.classList.remove("video-mode");
                    }
                    if (autoTuneIcon) {
                        autoTuneIcon.textContent = data.is_video ? "📹" : (data.badges.style === "weapon" ? "🔫" : (data.badges.style === "trace" ? "🔬" : "🎯"));
                    }
                    if (autoTuneTitle) {
                        autoTuneTitle.textContent = `⚡ AI Detected: ${data.detected_items.length > 0 ? data.detected_items.join(", ") : (data.is_video ? 'Video Stream' : 'Scene Content')} · All 6 Parameters Auto-Filled`;
                    }
                    if (autoTuneDetails) {
                        autoTuneDetails.textContent = data.explanation;
                    }
                }

                // Form Routing
                if (data.is_video) {
                    if (mainForm) mainForm.action = "/predict_video";
                    if (fileInput) fileInput.name = "video";
                    if (mainSubmitBtn) {
                        mainSubmitBtn.style.background = "linear-gradient(135deg, #d97706, #f59e0b)";
                        if (submitBtnText) submitBtnText.textContent = "Execute Video Surveillance Sweep (MP4 Timeline)";
                    }
                } else {
                    if (mainForm) mainForm.action = "/predict";
                    if (fileInput) fileInput.name = "image";
                    if (mainSubmitBtn) {
                        mainSubmitBtn.style.background = "";
                        if (submitBtnText) submitBtnText.textContent = "Execute Forensic Evidence Sweep";
                    }
                }
            }

        } catch (err) {
            console.error("AI pre-scan network error:", err);
            if (aiScanOverlay) aiScanOverlay.style.display = "none";
            // Fallback heuristic if offline
            if (isVideo) {
                applyPreset("cctv", `Video Evidence - ${cleanTitle || 'Surveillance Audit'}`);
            } else {
                applyPreset("ensemble", `Crime Scene - ${cleanTitle || 'Evidence Sweep'}`);
            }
        }
    }

    // 3. File Input & Dropzone Event Bindings
    if (dropzone && fileInput) {
        dropzone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        });

        dropzone.addEventListener("dragleave", () => {
            dropzone.classList.remove("dragover");
        });

        dropzone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                autoDetectWithAI(fileInput.files[0]);
            }
        });

        fileInput.addEventListener("change", () => {
            if (fileInput.files && fileInput.files[0]) {
                autoDetectWithAI(fileInput.files[0]);
            }
        });
    }

    // Video Tab Dropzone
    const videoFileInput = document.getElementById("videoFileInput");
    if (videoFileInput) {
        videoFileInput.addEventListener("change", () => {
            if (videoFileInput.files && videoFileInput.files[0]) {
                const f = videoFileInput.files[0];
                const clean = cleanFilenameForTitle(f.name);
                const vidTitle = document.getElementById("vid_title");
                if (vidTitle) {
                    vidTitle.value = `CCTV Video - ${clean || 'Surveillance Audit'}`;
                    triggerFieldPulse(vidTitle);
                }
            }
        });
    }

    // 4. Live Field Camera Capture
    const video = document.getElementById("cameraVideo");
    const startCamBtn = document.getElementById("startCameraBtn");
    const captureBtn = document.getElementById("capturePhotoBtn");
    const cameraForm = document.getElementById("cameraForm");
    let stream = null;

    if (startCamBtn && video) {
        startCamBtn.addEventListener("click", async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
                });
                video.srcObject = stream;
                video.play();
                startCamBtn.style.display = "none";
                if (captureBtn) captureBtn.style.display = "inline-flex";
            } catch (err) {
                alert("Camera access denied or unavailable: " + err.message);
            }
        });
    }

    if (captureBtn && video && cameraForm) {
        captureBtn.addEventListener("click", () => {
            const canvas = document.createElement("canvas");
            canvas.width = video.videoWidth || 640;
            canvas.height = video.videoHeight || 480;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

            canvas.toBlob((blob) => {
                const capturedFile = new File([blob], "camera_snapshot.jpg", { type: "image/jpeg" });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(capturedFile);

                const camFileInput = document.getElementById("cameraFileInput");
                if (camFileInput) {
                    camFileInput.files = dataTransfer.files;
                    if (stream) {
                        stream.getTracks().forEach((track) => track.stop());
                    }
                    cameraForm.submit();
                }
            }, "image/jpeg", 0.95);
        });
    }

    // 5. Preloaded Scenario 1-Click Card Handlers with AI Auto-Pre-Scan
    const sampleCards = document.querySelectorAll(".btn-load-sample");
    const sampleInput = document.getElementById("sampleImageInput");

    sampleCards.forEach((btn) => {
        btn.addEventListener("click", async (e) => {
            e.preventDefault();
            const filename = btn.getAttribute("data-filename") || "";
            if (sampleInput && mainForm && filename) {
                sampleInput.value = filename;

                // Pre-scan the sample using AI to configure the 6 parameters
                try {
                    const fd = new FormData();
                    fd.append("sample", filename);
                    const res = await fetch("/api/v1/auto_detect_metadata", { method: "POST", body: fd });
                    const data = await res.json();
                    if (data && data.success) {
                        if (modelSelect) modelSelect.value = data.fields.model;
                        if (confidenceInput) confidenceInput.value = data.fields.confidence;
                        if (investigatorInput) investigatorInput.value = data.fields.investigator;
                        if (locationInput) locationInput.value = data.fields.location;
                        if (titleInput) titleInput.value = data.fields.title;
                        if (incidentSelect) incidentSelect.value = data.fields.incident_type;
                    }
                } catch (err) {
                    console.warn("Sample AI pre-scan:", err);
                }
                mainForm.submit();
            }
        });
    });
});
