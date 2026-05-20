"""
Face Recognition Pipeline
MTCNN (detect) -> ArcFace/FaceNet (embed) -> Cosine Similarity (match)
Falls back to mock mode if ML libraries are not installed.
"""

import asyncio
import json
import logging
import os
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)
STRICT_REAL_FACE_MODEL = os.getenv("FACE_MODEL_STRICT", "true").lower() == "true"


class FaceDetector:
    """MTCNN face detector with graceful fallback"""

    def __init__(self):
        self._model = None

    def load(self):
        try:
            from mtcnn import MTCNN

            self._model = MTCNN()
            logger.info("MTCNN loaded (real detection)")
        except Exception as e:
            if STRICT_REAL_FACE_MODEL:
                raise RuntimeError(f"MTCNN failed to load: {e}") from e
            logger.warning("MTCNN not available (%s) - using mock detector", e)
            self._model = None

    def detect(self, image: np.ndarray) -> List[dict]:
        if self._model is None:
            h, w = image.shape[:2]
            return [
                {
                    "box": [w // 4, h // 4, w // 2, h // 2],
                    "confidence": 0.99,
                    "keypoints": {
                        "left_eye": (w // 3, h // 3),
                        "right_eye": (2 * w // 3, h // 3),
                        "nose": (w // 2, h // 2),
                        "mouth_left": (w // 3, 2 * h // 3),
                        "mouth_right": (2 * w // 3, 2 * h // 3),
                    },
                }
            ]
        return self._model.detect_faces(image)

    def crop(self, image: np.ndarray, box: list, margin: int = 20) -> np.ndarray:
        x, y, w, h = box
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(image.shape[1], x + w + margin)
        y2 = min(image.shape[0], y + h + margin)
        if x2 <= x1 or y2 <= y1:
            return image[0:0, 0:0]
        return image[y1:y2, x1:x2]


class EmbeddingExtractor:
    """ArcFace / FaceNet extractor with mock fallback"""

    EMBEDDING_SIZE = 512

    def __init__(self):
        self._model = None
        self._type = None

    def load(self):
        deepface_error = None
        try:
            from deepface import DeepFace

            dummy = np.zeros((224, 224, 3), dtype=np.uint8)
            DeepFace.represent(dummy, model_name="ArcFace", enforce_detection=False)
            self._model = "deepface"
            self.EMBEDDING_SIZE = 512
            logger.info("DeepFace ArcFace loaded")
            return
        except Exception as e:
            deepface_error = e
            logger.warning("DeepFace not available: %s", e)

        try:
            from keras_facenet import FaceNet

            self._model = FaceNet()
            self._type = "facenet"
            self.EMBEDDING_SIZE = 128
            logger.info("FaceNet loaded (real embedding)")
            return
        except Exception as e:
            if STRICT_REAL_FACE_MODEL:
                raise RuntimeError(
                    f"FaceNet failed to load: {e}. DeepFace error was: {deepface_error}"
                ) from e

        logger.warning("No ML embedding library found - using deterministic mock embeddings")

    @staticmethod
    def _prepare_for_facenet(face_image: np.ndarray) -> np.ndarray:
        try:
            import cv2

            face_image = cv2.resize(face_image, (160, 160))
            return cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
        except Exception:
            return face_image

    def extract(self, face_image: np.ndarray) -> np.ndarray:
        if self._model == "deepface":
            try:
                from deepface import DeepFace

                result = DeepFace.represent(
                    face_image,
                    model_name="ArcFace",
                    enforce_detection=True,
                    detector_backend="opencv",
                )
                emb = np.array(result[0]["embedding"], dtype=np.float32)
                return emb / (np.linalg.norm(emb) + 1e-10)
            except Exception as e:
                logger.warning("DeepFace extract failed: %s", e)

        if self._type == "facenet" and self._model is not None:
            try:
                prepared = self._prepare_for_facenet(face_image)
                embeddings = self._model.embeddings([prepared])
                emb = np.array(embeddings[0], dtype=np.float32)
                return emb / (np.linalg.norm(emb) + 1e-10)
            except Exception as e:
                logger.warning("FaceNet extract failed: %s", e)

        seed = int(np.sum(face_image.astype(np.float32)) % (2**31))
        rng = np.random.RandomState(seed)
        v = rng.randn(self.EMBEDDING_SIZE).astype(np.float32)
        return v / (np.linalg.norm(v) + 1e-10)


class SimilarityMatcher:
    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom < 1e-10:
            return 0.0
        return float(np.dot(a, b) / denom)

    def search(
        self,
        query: np.ndarray,
        database: List[Tuple[str, np.ndarray]],
        threshold: float = 0.60,
        top_k: int = 5,
    ) -> List[dict]:
        scores = [
            {
                "child_id": cid,
                "similarity": self.cosine(query, emb),
                "confidence": self.cosine(query, emb) * 100,
            }
            for cid, emb in database
        ]
        scores.sort(key=lambda x: x["similarity"], reverse=True)
        return [s for s in scores[:top_k] if s["similarity"] >= threshold]


class FaceRecognitionModel:
    def __init__(self):
        self.detector = FaceDetector()
        self.extractor = EmbeddingExtractor()
        self.matcher = SimilarityMatcher()

    async def load(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_sync)

    def _load_sync(self):
        self.detector.load()
        self.extractor.load()

    def process_image(
        self, image: np.ndarray
    ) -> Tuple[Optional[np.ndarray], List[dict]]:
        faces = self.detector.detect(image)
        if not faces:
            return None, []
        best = max(faces, key=lambda f: f["confidence"])
        crop = self.detector.crop(image, best["box"])
        if crop.size == 0:
            logger.warning("Detected face crop was empty")
            return None, faces
        embedding = self.extractor.extract(crop)
        return embedding, faces

    @staticmethod
    def to_json(embedding: np.ndarray) -> str:
        return json.dumps(embedding.tolist())

    @staticmethod
    def from_json(s: str) -> np.ndarray:
        return np.array(json.loads(s), dtype=np.float32)

    def search(
        self,
        query: np.ndarray,
        database: List[Tuple[str, np.ndarray]],
        threshold: float = 0.60,
    ) -> List[dict]:
        return self.matcher.search(query, database, threshold)
