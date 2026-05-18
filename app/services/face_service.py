"""
Face Service - Core AI pipeline
- Face detection using MTCNN
- Feature extraction using FaceNet / ArcFace
- Matching using cosine similarity
- Age-group handling (below 5: skip biometrics)
"""

import numpy as np
import cv2
import logging
from pathlib import Path
from typing import Optional
import base64
import io

logger = logging.getLogger(__name__)

# ── Optional heavy imports (graceful fallback for environments without GPU) ──
try:
    from mtcnn import MTCNN
    MTCNN_AVAILABLE = True
except ImportError:
    MTCNN_AVAILABLE = False
    logger.warning("MTCNN not installed. Install with: pip install mtcnn")

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    logger.warning("DeepFace not installed. Install with: pip install deepface")

try:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


class FaceService:
    """
    Core face recognition pipeline.

    Detection  → MTCNN  (multi-task cascaded CNN)
    Embedding  → ArcFace via DeepFace  (512-dim vector)
    Matching   → Cosine similarity (threshold: 0.40)
    Fallback   → OpenCV Haar cascade
    """

    SIMILARITY_THRESHOLD = 0.40  # Lower = more strict
    FACE_SIZE = (160, 160)       # FaceNet input size

    def __init__(self):
        self.detector = None
        self.model_name = "ArcFace"
        self._init_detector()
        logger.info(f"FaceService initialized | model={self.model_name} | threshold={self.SIMILARITY_THRESHOLD}")

    def _init_detector(self):
        """Initialize face detector with fallback chain"""
        if MTCNN_AVAILABLE:
            try:
                self.detector = MTCNN()
                self.detector_type = "MTCNN"
                logger.info("✅ MTCNN detector loaded")
                return
            except Exception as e:
                logger.warning(f"MTCNN init failed: {e}")

        # Fallback to OpenCV Haar cascade
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(cascade_path)
        self.detector_type = "HaarCascade"
        logger.info("⚠️  Using OpenCV Haar cascade (fallback)")

    # ── Public API ──────────────────────────────────────────────────────────

    def detect_faces(self, image_bytes: bytes) -> list[dict]:
        """
        Detect all faces in an image.
        Returns list of {bbox, confidence, landmarks}
        """
        img = self._bytes_to_cv2(image_bytes)
        if img is None:
            return []

        if self.detector_type == "MTCNN":
            return self._detect_mtcnn(img)
        else:
            return self._detect_haar(img)

    def extract_embedding(self, image_bytes: bytes, age: Optional[int] = None) -> Optional[list[float]]:
        """
        Extract 512-dim face embedding.
        Returns None if:
          - No face detected
          - Child is below 5 (too young for reliable biometrics)
        """
        if age is not None and age < 5:
            logger.info(f"Child is {age} years old — skipping biometric extraction (policy: no biometrics under 5)")
            return None

        img = self._bytes_to_cv2(image_bytes)
        if img is None:
            return None

        if DEEPFACE_AVAILABLE:
            return self._extract_deepface(img)
        else:
            return self._extract_mock_embedding(img)

    def compute_similarity(self, embedding1: list[float], embedding2: list[float]) -> float:
        """Cosine similarity between two embeddings. Returns 0.0–1.0"""
        if not embedding1 or not embedding2:
            return 0.0
        v1 = np.array(embedding1, dtype=np.float32)
        v2 = np.array(embedding2, dtype=np.float32)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    def is_match(self, embedding1: list[float], embedding2: list[float]) -> tuple[bool, float]:
        """Returns (is_match, confidence_score)"""
        sim = self.compute_similarity(embedding1, embedding2)
        return sim >= self.SIMILARITY_THRESHOLD, sim

    def match_against_database(
        self,
        query_embedding: list[float],
        db_records: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Match a query embedding against all database records.

        Args:
            query_embedding: 512-dim embedding from query image
            db_records: list of {id, name, face_embedding, ...}
            top_k: return top-k matches

        Returns:
            Sorted list of {id, name, similarity, is_match, ...}
        """
        results = []
        for record in db_records:
            if not record.get("face_embedding"):
                continue
            sim = self.compute_similarity(query_embedding, record["face_embedding"])
            results.append({
                "child_id": record.get("id"),
                "child_name": record.get("name"),
                "similarity": round(sim * 100, 2),  # percentage
                "is_match": sim >= self.SIMILARITY_THRESHOLD,
                "confidence_label": self._confidence_label(sim),
                "face_image_path": record.get("face_image_path"),
                "age": record.get("age"),
                "last_seen_location": record.get("last_seen_location"),
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def crop_and_align_face(self, image_bytes: bytes) -> Optional[bytes]:
        """Detect, align, and return the largest face crop"""
        img = self._bytes_to_cv2(image_bytes)
        if img is None:
            return None

        faces = self.detect_faces(image_bytes)
        if not faces:
            return None

        # Use largest face
        face = max(faces, key=lambda f: f["bbox"][2] * f["bbox"][3])
        x, y, w, h = face["bbox"]
        # Add 20% padding
        pad = int(0.2 * max(w, h))
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad)
        y2 = min(img.shape[0], y + h + pad)
        crop = img[y1:y2, x1:x2]
        crop = cv2.resize(crop, self.FACE_SIZE)
        _, buf = cv2.imencode(".jpg", crop)
        return buf.tobytes()

    # ── Private helpers ─────────────────────────────────────────────────────

    def _bytes_to_cv2(self, image_bytes: bytes):
        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            logger.error(f"Image decode error: {e}")
            return None

    def _detect_mtcnn(self, img) -> list[dict]:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        detections = self.detector.detect_faces(rgb)
        results = []
        for d in detections:
            results.append({
                "bbox": d["box"],         # [x, y, w, h]
                "confidence": d["confidence"],
                "landmarks": d["keypoints"],
            })
        return results

    def _detect_haar(self, img) -> list[dict]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        return [{"bbox": [x, y, w, h], "confidence": 0.85, "landmarks": None} for (x, y, w, h) in faces]

    def _extract_deepface(self, img) -> Optional[list[float]]:
        try:
            # Save temp image for DeepFace
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                cv2.imwrite(f.name, img)
                temp_path = f.name
            result = DeepFace.represent(img_path=temp_path, model_name=self.model_name, enforce_detection=False)
            os.unlink(temp_path)
            if result:
                return result[0]["embedding"]
        except Exception as e:
            logger.error(f"DeepFace embedding error: {e}")
        return None

    def _extract_mock_embedding(self, img) -> list[float]:
        """
        Mock embedding for testing without GPU/models.
        In production: replace with real ArcFace/FaceNet.
        Produces a deterministic 512-dim vector from image statistics.
        """
        img_resized = cv2.resize(img, (64, 64)).astype(np.float32) / 255.0
        flat = img_resized.flatten()
        # Build 512-dim vector from image statistics
        embedding = []
        chunk_size = len(flat) // 512
        for i in range(512):
            chunk = flat[i * chunk_size: (i + 1) * chunk_size]
            embedding.append(float(np.mean(chunk)))
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = [e / norm for e in embedding]
        return embedding

    def _confidence_label(self, sim: float) -> str:
        if sim >= 0.80:
            return "Very High"
        elif sim >= 0.65:
            return "High"
        elif sim >= 0.50:
            return "Medium"
        elif sim >= 0.40:
            return "Low"
        else:
            return "No Match"
