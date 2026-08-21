"""
Age Progression Model
Uses simulation by default. Replace _simulate() with real GAN inference
once SAM / HRFAE weights are downloaded.
"""

import numpy as np
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class AgeProgressionModel:
    def __init__(self):
        self._model = None

    def load(self):
        try:
            import torch  # noqa: F401
            logger.info("PyTorch available — GAN weights can be loaded")
            # self._model = _load_sam_weights("pretrained_models/sam_ffhq_aging.pt")
        except ImportError:
            logger.warning("PyTorch not installed — age progression uses simulation")

    def progress(self, image: np.ndarray, current_age: int, target_age: int) -> np.ndarray:
        if self._model is not None:
            return self._gan(image, current_age, target_age)
        return self._simulate(image, current_age, target_age)

    # ── Simulation ──────────────────────────────────────────────────────────

    def _simulate(self, image: np.ndarray, current_age: int, target_age: int) -> np.ndarray:
        years = target_age - current_age
        if years <= 0:
            return image.copy()

        result = image.copy().astype(np.float32)

        # 1. Slight desaturation (skin becomes less vibrant)
        try:
            import cv2
            hsv = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] - min(years * 1.5, 25), 0, 255)
            result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
        except Exception:
            pass

        # 2. Subtle texture noise (simulates fine lines)
        noise = np.random.normal(0, min(years * 0.4, 7), result.shape).astype(np.float32)
        result = np.clip(result + noise * 0.12, 0, 255)

        # 3. Slight darkening around eye region
        if target_age > 18:
            h, w = result.shape[:2]
            y1, y2 = h // 5, h // 3
            x1, x2 = w // 5, 4 * w // 5
            result[y1:y2, x1:x2] = np.clip(result[y1:y2, x1:x2] * 0.93, 0, 255)

        return result.astype(np.uint8)

    # ── GAN placeholder ─────────────────────────────────────────────────────

    def _gan(self, image, current_age, target_age):
        """Wire real SAM model here"""
        return self._simulate(image, current_age, target_age)

    def progress_and_save(
        self,
        image: np.ndarray,
        child_id: str,
        current_age: int,
        target_age: int,
        output_dir: str = "uploads/progressed",
    ) -> Optional[str]:
        os.makedirs(output_dir, exist_ok=True)
        result = self.progress(image, current_age, target_age)
        path = os.path.join(output_dir, f"{child_id}_age_{target_age}.jpg").replace("\\", "/")
        try:
            import cv2
            cv2.imwrite(path, result)
        except Exception:
            from PIL import Image
            Image.fromarray(result[:, :, ::-1]).save(path)
        return path
