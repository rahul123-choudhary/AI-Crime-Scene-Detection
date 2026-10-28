/**
 * Real-Time Forensic Live Camera Stream & AI Tactical HUD
 */

document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("liveVideo");
    const overlay = document.getElementById("liveOverlay");
    const startBtn = document.getElementById("btnStartStream");
    const stopBtn = document.getElementById("btnStopStream");
    const recordBtn = document.getElementById("btnRecordClip");
    const audioToggle = document.getElementById("toggleAudioAlert");
    const threatBadge = document.getElementById("liveThreatBadge");
    const threatScoreEl = document.getElementById("liveThreatScore");
    const threatBar = document.getElementById("liveThreatBar");
    const countBadge = document.getElementById("liveObjectCount");
    const latencyEl = document.getElementById("liveLatency");
    const tickerList = document.getElementById("liveEvidenceTicker");

    if (!video || !overlay) return;

    const ctx = overlay.getContext("2d");
    let stream = null;
    let isStreaming = false;
    let isProcessingFrame = false;
    let animationFrameId = null;
    let mediaRecorder = null;
    let recordedChunks = [];
    let isRecording = false;

    // Web Audio API for Tactical Alerts
    let audioCtx = null;
    function playTacticalChime(severity) {
        if (!audioToggle || !audioToggle.checked) return;
        try {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);

            if (severity === "CRITICAL") {
                osc.type = "sawtooth";
                osc.frequency.setValueAtTime(880, audioCtx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.2, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.2);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.2);
            } else if (severity === "HIGH") {
                osc.type = "sine";
                osc.frequency.setValueAtTime(587, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.15);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.15);
            }
        } catch (e) {
            console.warn("Audio alert failed", e);
        }
    }

    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: "environment"
                },
                audio: false
            });

            video.srcObject = stream;
            await video.play();

            overlay.width = video.videoWidth || 640;
            overlay.height = video.videoHeight || 480;

            isStreaming = true;
            if (startBtn) startBtn.style.display = "none";
            if (stopBtn) stopBtn.style.display = "inline-flex";
            if (recordBtn) recordBtn.style.display = "inline-flex";

            streamLoop();
        } catch (err) {
            alert("Could not access camera: " + err.message + "\nEnsure camera permissions are allowed.");
        }
    }

    function stopCamera() {
        isStreaming = false;
        if (animationFrameId) cancelAnimationFrame(animationFrameId);
        if (stream) {
            stream.getTracks().forEach((track) => track.stop());
            stream = null;
        }
        video.srcObject = null;
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        if (startBtn) startBtn.style.display = "inline-flex";
        if (stopBtn) stopBtn.style.display = "none";
        if (recordBtn) recordBtn.style.display = "none";
    }

    // High-speed frame extraction and transmission
    async function processLiveFrame() {
        if (!isStreaming || isProcessingFrame || video.paused || video.ended) return;
        isProcessingFrame = true;

        const offCanvas = document.createElement("canvas");
        const scale = Math.min(1.0, 640 / (video.videoWidth || 640));
        offCanvas.width = (video.videoWidth || 640) * scale;
        offCanvas.height = (video.videoHeight || 480) * scale;
        const offCtx = offCanvas.getContext("2d");
        offCtx.drawImage(video, 0, 0, offCanvas.width, offCanvas.height);

        const frameB64 = offCanvas.toDataURL("image/jpeg", 0.65);
        const modelSelect = document.getElementById("liveModelSelect");
        const modelChoice = modelSelect ? modelSelect.value : "ensemble";

        try {
            const res = await fetch("/api/v1/detect_frame", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    frame_base64: frameB64,
                    model: modelChoice,
                    confidence: 0.25
                })
            });

            if (res.ok) {
                const data = await res.json();
                renderTacticalOverlay(data);
                updateLiveHUD(data);
            }
        } catch (err) {
            console.warn("Frame detection loop error:", err);
        } finally {
            isProcessingFrame = false;
        }
    }

    function renderTacticalOverlay(data) {
        ctx.clearRect(0, 0, overlay.width, overlay.height);

        if (overlay.width !== video.videoWidth || overlay.height !== video.videoHeight) {
            overlay.width = video.videoWidth;
            overlay.height = video.videoHeight;
        }

        const detections = data.detections || [];
        detections.forEach((item) => {
            const norm = item.norm_box;
            if (!norm || norm.length < 4) return;

            const x1 = Math.round(norm[0] * overlay.width);
            const y1 = Math.round(norm[1] * overlay.height);
            const x2 = Math.round(norm[2] * overlay.width);
            const y2 = Math.round(norm[3] * overlay.height);
            const w = x2 - x1;
            const h = y2 - y1;

            const isCritical = (item.severity === "CRITICAL");
            const color = isCritical ? "#ef4444" : (item.color || "#38bdf8");

            // Tactical Box
            ctx.save();
            ctx.lineWidth = isCritical ? 3 : 2;
            ctx.strokeStyle = color;
            ctx.shadowColor = color;
            ctx.shadowBlur = 12;
            ctx.strokeRect(x1, y1, w, h);

            // Tactical corner brackets
            const corner = Math.min(18, Math.max(6, Math.round(w * 0.18)));
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(x1, y1 + corner); ctx.lineTo(x1, y1); ctx.lineTo(x1 + corner, y1);
            ctx.moveTo(x2 - corner, y1); ctx.lineTo(x2, y1); ctx.lineTo(x2, y1 + corner);
            ctx.moveTo(x1, y2 - corner); ctx.lineTo(x1, y2); ctx.lineTo(x1 + corner, y2);
            ctx.moveTo(x2 - corner, y2); ctx.lineTo(x2, y2); ctx.lineTo(x2, y2 - corner);
            ctx.stroke();

            // Label Pill
            const label = `[${item.class.toUpperCase()}] ${Math.round(item.confidence)}%`;
            ctx.font = "bold 13px 'JetBrains Mono', monospace";
            const textW = ctx.measureText(label).width;

            ctx.fillStyle = "rgba(4, 16, 30, 0.92)";
            ctx.fillRect(x1, Math.max(0, y1 - 22), textW + 12, 22);
            ctx.strokeStyle = color;
            ctx.lineWidth = 1;
            ctx.strokeRect(x1, Math.max(0, y1 - 22), textW + 12, 22);

            ctx.fillStyle = color;
            ctx.fillText(label, x1 + 6, Math.max(16, y1 - 6));
            ctx.restore();
        });
    }

    let lastAlertSecond = 0;
    function updateLiveHUD(data) {
        if (threatBadge) {
            threatBadge.textContent = `${data.threat_level} THREAT`;
            threatBadge.className = `badge-threat ${data.threat_level.toLowerCase().split(' ')[0]}`;
        }
        if (threatScoreEl) threatScoreEl.textContent = `${data.threat_score} / 100`;
        if (threatBar) {
            threatBar.style.width = `${data.threat_score}%`;
            threatBar.className = `gauge-fill ${data.threat_level.toLowerCase().split(' ')[0]}`;
        }
        if (countBadge) countBadge.textContent = `${data.count} DETECTED`;
        if (latencyEl) latencyEl.textContent = `${data.latency_ms} ms`;

        // Audio Alert on Critical Weapons
        if (data.threat_level === "CRITICAL" || data.threat_level === "HIGH") {
            const nowSec = Math.floor(Date.now() / 1000);
            if (nowSec - lastAlertSecond >= 2) {
                lastAlertSecond = nowSec;
                playTacticalChime(data.threat_level);
            }
        }

        // Update live evidence ticker
        if (tickerList && data.detections && data.detections.length > 0) {
            const timeStr = new Date().toLocaleTimeString();
            data.detections.forEach((d) => {
                const li = document.createElement("li");
                li.style.cssText = "padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; font-size: 0.82rem;";
                li.innerHTML = `<span><strong style="color: ${d.color};">${d.class}</strong> (${d.confidence.toFixed(1)}%)</span><span style="color: var(--text-muted); font-family: var(--font-mono);">${timeStr}</span>`;
                tickerList.insertBefore(li, tickerList.firstChild);
                if (tickerList.children.length > 25) {
                    tickerList.removeChild(tickerList.lastChild);
                }
            });
        }
    }

    function streamLoop() {
        if (!isStreaming) return;
        processLiveFrame();
        setTimeout(streamLoop, 120); // ~8 FPS detection loop
    }

    if (startBtn) startBtn.addEventListener("click", startCamera);
    if (stopBtn) stopBtn.addEventListener("click", stopCamera);

    // MediaRecorder for recording live crime scene clip
    if (recordBtn && video) {
        recordBtn.addEventListener("click", () => {
            if (!stream) return;
            if (!isRecording) {
                // Start Recording
                recordedChunks = [];
                try {
                    mediaRecorder = new MediaRecorder(stream, { mimeType: "video/webm" });
                } catch (e) {
                    mediaRecorder = new MediaRecorder(stream);
                }

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) recordedChunks.push(e.data);
                };

                mediaRecorder.onstop = () => {
                    const blob = new Blob(recordedChunks, { type: "video/webm" });
                    const file = new File([blob], "live_recorded_scene.webm", { type: "video/webm" });
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);

                    // Submit to /predict_video
                    const form = document.createElement("form");
                    form.method = "POST";
                    form.action = "/predict_video";
                    form.enctype = "multipart/form-data";

                    const fileIn = document.createElement("input");
                    fileIn.type = "file";
                    fileIn.name = "video";
                    fileIn.files = dataTransfer.files;
                    form.appendChild(fileIn);

                    const titleIn = document.createElement("input");
                    titleIn.name = "title";
                    titleIn.value = "Live Camera Incident Recording";
                    form.appendChild(titleIn);

                    document.body.appendChild(form);
                    form.submit();
                };

                mediaRecorder.start();
                isRecording = true;
                recordBtn.innerHTML = `<span class="status-pulse" style="background: red;"></span> Stop & Archive Clip`;
                recordBtn.style.background = "#ef4444";
                recordBtn.style.color = "#fff";
            } else {
                // Stop Recording
                mediaRecorder.stop();
                isRecording = false;
                recordBtn.innerHTML = `Start Scene Clip Recording`;
                recordBtn.style.background = "";
                recordBtn.style.color = "";
            }
        });
    }
});
