"""Forensic Image Enhancement and Clarification Service.

Provides scientific image enhancement algorithms:
- Contrast Limited Adaptive Histogram Equalization (CLAHE) in LAB space
- Unsharp Masking & Detail Sharpening for edge recovery
- Low-Light / Night-Vision Gamma Amplification
- Bilateral Denoising with Edge Preservation
- Objective Clarity & Sharpness Metrics (Laplacian variance, contrast, SNR)
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def measure_image_clarity(img: np.ndarray) -> dict[str, float]:
    """Calculate objective forensic clarity and quality metrics for an image."""
    if img is None or img.size == 0:
        return {"sharpness": 0.0, "contrast": 0.0, "brightness": 0.0, "quality_score": 0.0}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # 1. Sharpness via variance of the Laplacian (standard in computer vision)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 2. Contrast via standard deviation of pixel intensities
    contrast = float(np.std(gray))

    # 3. Brightness via mean luminance
    brightness = float(np.mean(gray))

    # 4. Composite forensic quality score (0 - 100)
    # Higher sharpness (>150) and good contrast (>50) yield higher quality
    sharpness_norm = min(100.0, (laplacian_var / 350.0) * 100.0)
    contrast_norm = min(100.0, (contrast / 65.0) * 100.0)
    quality_score = round(0.6 * sharpness_norm + 0.4 * contrast_norm, 1)

    return {
        "sharpness": round(laplacian_var, 2),
        "laplacian_variance": round(laplacian_var, 2),
        "contrast": round(contrast, 2),
        "brightness": round(brightness, 2),
        "quality_score": quality_score,
    }


def apply_clahe_enhancement(
    img: np.ndarray,
    clip_limit: float = 3.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) in LAB color space.

    Enhances subtle forensic details (e.g. latent blood, fingerprints, faint
    weapon silhouettes) without washing out colors or introducing severe noise.
    """
    if len(img.shape) == 2:
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        return clahe.apply(img)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced_l = clahe.apply(l_channel)

    merged_lab = cv2.merge((enhanced_l, a_channel, b_channel))
    return cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)


def apply_unsharp_mask(
    img: np.ndarray,
    strength: float = 1.6,
    sigma: float = 1.8,
) -> np.ndarray:
    """Sharpen contours, edges, and fine forensic details using Unsharp Masking.

    Ideal for de-blurring weapon edges, serial numbers, cartridge markings, and
    textile fibers.
    """
    gaussian = cv2.GaussianBlur(img, (0, 0), sigma)
    # unsharp formula: original + strength * (original - blurred)
    sharpened = cv2.addWeighted(img, 1.0 + strength, gaussian, -strength, 0)
    return np.clip(sharpened, 0, 255).astype(np.uint8)


def apply_low_light_boost(
    img: np.ndarray,
    gamma: float = 0.65,
    brightness_offset: int = 15,
) -> np.ndarray:
    """Brighten dark crime scenes and night-time CCTV surveillance footage using

    adaptive gamma transformation.
    """
    inv_gamma = 1.0 / max(0.1, gamma)
    table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype("uint8")
    adjusted = cv2.LUT(img, table)

    if brightness_offset != 0:
        adjusted = cv2.convertScaleAbs(adjusted, alpha=1.05, beta=brightness_offset)

    return adjusted


def apply_forensic_denoise(img: np.ndarray) -> np.ndarray:
    """Bilateral filter smoothing sensor noise while strictly preserving critical

    forensic edges.
    """
    return cv2.bilateralFilter(img, d=7, sigmaColor=50, sigmaSpace=50)


def enhance_forensic_image(
    img: np.ndarray,
    mode: str = "full_forensic",
) -> dict[str, Any]:
    """Execute complete forensic clarification and enhancement on an image.

    Modes:
    - 'full_forensic': Multi-stage (denoise -> low-light gamma -> CLAHE -> unsharp mask).
    - 'clahe': Contrast-limited adaptive histogram equalization.
    - 'sharpen': Edge sharpening & de-blurring.
    - 'low_light': Night-vision and low-light amplification.
    - 'denoise': Sensor noise suppression.
    """
    if img is None:
        raise ValueError("Cannot enhance empty image.")

    initial_metrics = measure_image_clarity(img)
    mode = mode.lower().strip()

    if mode == "clahe":
        enhanced = apply_clahe_enhancement(img, clip_limit=3.5)
    elif mode == "sharpen":
        enhanced = apply_unsharp_mask(img, strength=1.8, sigma=1.5)
    elif mode == "low_light":
        enhanced = apply_low_light_boost(img, gamma=0.55, brightness_offset=20)
        enhanced = apply_clahe_enhancement(enhanced, clip_limit=2.5)
    elif mode == "denoise":
        enhanced = apply_forensic_denoise(img)
    else:
        # Full Forensic Clarity (State of the art multi-stage pipeline)
        # Stage 1: Edge-preserving noise suppression
        step1 = apply_forensic_denoise(img)

        # Stage 2: Low-light compensation if scene is dark (mean brightness < 110)
        mean_b = np.mean(step1)
        if mean_b < 115:
            step2 = apply_low_light_boost(step1, gamma=0.68, brightness_offset=15)
        else:
            step2 = step1

        # Stage 3: CLAHE detail extraction
        step3 = apply_clahe_enhancement(step2, clip_limit=3.0)

        # Stage 4: High-precision edge recovery
        enhanced = apply_unsharp_mask(step3, strength=1.4, sigma=1.5)

    final_metrics = measure_image_clarity(enhanced)

    sharpness_gain_pct = 0.0
    if initial_metrics["sharpness"] > 0:
        sharpness_gain_pct = round(
            ((final_metrics["sharpness"] - initial_metrics["sharpness"]) / initial_metrics["sharpness"]) * 100.0,
            1,
        )

    contrast_gain_pct = 0.0
    if initial_metrics["contrast"] > 0:
        contrast_gain_pct = round(
            ((final_metrics["contrast"] - initial_metrics["contrast"]) / initial_metrics["contrast"]) * 100.0,
            1,
        )

    return {
        "enhanced_image": enhanced,
        "mode": mode,
        "initial_metrics": initial_metrics,
        "final_metrics": final_metrics,
        "sharpness_gain_pct": sharpness_gain_pct,
        "contrast_gain_pct": contrast_gain_pct,
        "quality_score": final_metrics["quality_score"],
    }


def generate_and_save_clarity_suite(
    img: np.ndarray,
    output_dir: Path,
    file_prefix: str,
) -> dict[str, str]:
    """Generate all 4 forensic enhancement layers (Full Enhanced, CLAHE,

    Sharpened, Night Vision) and save them to disk for instant interactive UI
    toggling.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = {
        "full_enhanced": enhance_forensic_image(img, mode="full_forensic")["enhanced_image"],
        "clahe": enhance_forensic_image(img, mode="clahe")["enhanced_image"],
        "sharpened": enhance_forensic_image(img, mode="sharpen")["enhanced_image"],
        "night_vision": enhance_forensic_image(img, mode="low_light")["enhanced_image"],
    }

    saved_paths: dict[str, str] = {}
    for key, v_img in variants.items():
        filename = f"{file_prefix}_{key}.jpg"
        filepath = output_dir / filename
        cv2.imwrite(str(filepath), v_img, [cv2.IMWRITE_JPEG_QUALITY, 96])
        saved_paths[key] = str(filepath.relative_to(output_dir.parent)).replace("\\", "/")

    return saved_paths
