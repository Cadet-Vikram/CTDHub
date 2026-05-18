"""
Age Progression Service using a conditional GAN (CAAE-style).
Generates age-progressed photos of missing children for more accurate matching.

Architecture: Encoder → Age-conditioned Generator → Discriminator
Training: See training/train_age_gan.py
"""
import io
import logging
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Optional

logger = logging.getLogger(__name__)

# Target ages to generate (years). We generate multiple for search.
AGE_BUCKETS = [5, 10, 15, 18]


class AgeProgressionService:
    """
    Wraps a trained Keras/TF age-progression generator model.
    Falls back to a simple face-morph heuristic if model not available.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._model = None
            cls._instance._loaded = False
        return cls._instance

    def load_model(self, model_path: str):
        try:
            import tensorflow as tf
            self._model = tf.keras.models.load_model(model_path)
            self._loaded = True
            logger.info(f"Age-progression model loaded from {model_path}")
        except Exception as e:
            logger.warning(f"Could not load age-progression model: {e}. Fallback active.")
            self._loaded = False

    def preprocess(self, image: Image.Image, target_size=(128, 128)) -> np.ndarray:
        img = image.convert("RGB").resize(target_size)
        arr = np.array(img, dtype=np.float32) / 127.5 - 1.0   # [-1, 1]
        return arr[np.newaxis, ...]                              # (1, H, W, 3)

    def postprocess(self, arr: np.ndarray) -> Image.Image:
        img = (arr.squeeze() + 1.0) * 127.5
        img = np.clip(img, 0, 255).astype(np.uint8)
        return Image.fromarray(img)

    def age_condition_vector(self, target_age: int, num_classes: int = 8) -> np.ndarray:
        """
        One-hot encode age bucket: [0-5, 5-10, 10-15, 15-20, 20-30, 30-40, 40-50, 50+]
        """
        buckets = [5, 10, 15, 20, 30, 40, 50, 200]
        idx = next((i for i, b in enumerate(buckets) if target_age <= b), num_classes - 1)
        vec = np.zeros((1, num_classes), dtype=np.float32)
        vec[0, idx] = 1.0
        return vec

    def progress_age(
        self,
        image: Image.Image,
        current_age: float,
        target_age: int,
    ) -> Optional[Image.Image]:
        """
        Generate an age-progressed version of the child's photo.
        Returns None if ages are too close or model unavailable.
        """
        if abs(target_age - current_age) < 2:
            return None                     # Not worth progressing

        if self._loaded and self._model is not None:
            try:
                img_arr = self.preprocess(image)
                age_vec = self.age_condition_vector(target_age)
                generated = self._model.predict([img_arr, age_vec], verbose=0)
                return self.postprocess(generated)
            except Exception as e:
                logger.error(f"GAN inference failed: {e}")

        # ── Fallback: simple heuristic aging via OpenCV ──────────────────────
        return self._heuristic_age(image, current_age, target_age)

    def _heuristic_age(
        self, image: Image.Image, current_age: float, target_age: int
    ) -> Image.Image:
        """
        Naive fallback that adjusts skin tone & sharpness to simulate aging.
        Not a real GAN output — only for demo/prototype purposes.
        """
        import cv2
        img = np.array(image.convert("RGB"))
        age_delta = target_age - current_age

        # Slightly increase contrast + warm tone for aging
        factor = min(1.0 + age_delta * 0.01, 1.25)
        img = cv2.convertScaleAbs(img, alpha=factor, beta=-age_delta * 0.3)

        # Add very subtle wrinkle texture via noise for older ages
        if target_age > 15:
            noise = np.random.normal(0, age_delta * 0.15, img.shape).astype(np.int16)
            img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        return Image.fromarray(img)

    def generate_all_progressions(
        self, image: Image.Image, current_age: float
    ) -> dict[int, Image.Image]:
        """Generate age progressions for all future age buckets."""
        results = {}
        for target_age in AGE_BUCKETS:
            if target_age > current_age:
                result = self.progress_age(image, current_age, target_age)
                if result:
                    results[target_age] = result
        return results

    def to_bytes(self, image: Image.Image, fmt: str = "JPEG") -> bytes:
        buf = io.BytesIO()
        image.save(buf, format=fmt, quality=85)
        return buf.getvalue()
