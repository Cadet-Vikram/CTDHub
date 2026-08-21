"""
Age Progression Engine using GANs
- CACD / FFHQ-Aging pretrained model
- Fallback: simple morphological aging simulation
"""

import cv2
import numpy as np
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_age_model = None
MODEL_PATH = "models/age_progression_model.onnx"


def get_age_model():
    global _age_model
    if _age_model is not None:
        return _age_model
    # Try loading ONNX model (e.g. SAM / FRAN / IPCGAN exported)
    if os.path.exists(MODEL_PATH):
        try:
            import onnxruntime as ort
            _age_model = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
            logger.info("Age progression ONNX model loaded")
            return _age_model
        except Exception as e:
            logger.warning(f"ONNX model load failed: {e}")
    # Try PyTorch FRAN / SAM if available
    try:
        from age_gan import AgeProgressionGAN  # your custom module
        _age_model = AgeProgressionGAN.load("models/age_gan.pt")
        logger.info("PyTorch age GAN loaded")
        return _age_model
    except ImportError:
        pass
    logger.warning("No age GAN model found – using algorithmic simulation")
    return None


def progress_age(
    image: np.ndarray,
    current_age: int,
    target_age: int,
) -> Tuple[np.ndarray, float]:
    """
    Produce an age-progressed version of the face.
    Returns (progressed_image, confidence_score).
    """
    years = target_age - current_age
    if years <= 0:
        return image, 1.0

    model = get_age_model()

    if model is not None:
        result = _run_gan(model, image, current_age, target_age)
        if result is not None:
            return result, 0.82
    # Algorithmic fallback
    return _algorithmic_aging(image, years), 0.55


def _run_gan(model, image: np.ndarray, current_age: int, target_age: int) -> Optional[np.ndarray]:
    try:
        import onnxruntime as ort
        inp = cv2.resize(image, (256, 256)).astype(np.float32) / 127.5 - 1.0
        inp = inp.transpose(2, 0, 1)[np.newaxis]  # NCHW
        age_norm = np.array([[target_age / 100.0]], dtype=np.float32)
        input_name = model.get_inputs()[0].name
        age_name = model.get_inputs()[1].name if len(model.get_inputs()) > 1 else None
        if age_name:
            outputs = model.run(None, {input_name: inp, age_name: age_norm})
        else:
            outputs = model.run(None, {input_name: inp})
        out = outputs[0].squeeze().transpose(1, 2, 0)
        out = ((out + 1) * 127.5).clip(0, 255).astype(np.uint8)
        out = cv2.resize(out, (image.shape[1], image.shape[0]))
        return cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"GAN inference failed: {e}")
        return None


def _algorithmic_aging(image: np.ndarray, years: int) -> np.ndarray:
    """
    Simulation-based aging:
    - Adds subtle wrinkles via texture overlay
    - Adjusts skin tone
    - Slight facial structure dilation
    """
    result = image.copy().astype(np.float32)

    # Slight skin-tone desaturation (aging reduces colour vibrancy)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    saturation_factor = max(0.6, 1.0 - years * 0.008)
    hsv[:, :, 1] *= saturation_factor
    hsv = np.clip(hsv, 0, 255).astype(np.uint8)
    result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.float32)

    # Wrinkle texture (high-freq noise blended at low opacity)
    if years >= 5:
        noise = np.random.randn(*image.shape[:2]).astype(np.float32) * (years * 0.3)
        noise_3ch = cv2.merge([noise, noise, noise])
        # Apply only to high-texture (skin) regions
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        skin_mask = cv2.GaussianBlur((gray > 60).astype(np.float32), (15, 15), 0)
        skin_mask_3ch = cv2.merge([skin_mask, skin_mask, skin_mask])
        result += noise_3ch * skin_mask_3ch * 0.04

    # Slight morphological expansion for older look (face broadens)
    if years >= 10:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        expanded = cv2.dilate(result.astype(np.uint8), kernel, iterations=1).astype(np.float32)
        result = cv2.addWeighted(result, 0.7, expanded, 0.3, 0)

    # Subtle brightness reduction
    result *= max(0.85, 1.0 - years * 0.003)

    return np.clip(result, 0, 255).astype(np.uint8)


def generate_age_series(
    image: np.ndarray,
    current_age: int,
    max_age: int = 25,
    step: int = 5,
) -> list:
    """Generate a sequence of age-progressed images."""
    series = []
    for target_age in range(current_age + step, max_age + 1, step):
        progressed, confidence = progress_age(image, current_age, target_age)
        series.append({
            "age": target_age,
            "years_progressed": target_age - current_age,
            "confidence": confidence,
            "image": progressed,
        })
    return series
