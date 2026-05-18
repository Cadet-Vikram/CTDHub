"""
Face Recognition Service
Handles: MTCNN detection, FaceNet/ArcFace embedding, cosine similarity matching.
Supports age-progression fallback for children under 5.
"""
import io
import pickle
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from facenet_pytorch import MTCNN, InceptionResnetV1
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MATCH_THRESHOLD = 0.55          # cosine similarity; tune per evaluation
UNDER_5_THRESHOLD = 0.45        # looser threshold for toddlers (fewer facial landmarks)
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class FaceRecognitionService:
    """
    Singleton service that wraps MTCNN + FaceNet (InceptionResnetV1).

    Usage:
        svc = FaceRecognitionService()
        embedding = svc.get_embedding(pil_image)
        results  = svc.match_against_database(embedding, db_embeddings)
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        logger.info(f"Loading face models on {DEVICE}...")
        # MTCNN for face detection + alignment
        self.mtcnn = MTCNN(
            image_size=160,
            margin=20,
            min_face_size=20,
            thresholds=[0.6, 0.7, 0.7],
            factor=0.709,
            post_process=True,
            keep_all=False,         # return only the largest face
            device=DEVICE,
        )
        # FaceNet pretrained on VGGFace2 — produces 512-d embeddings
        self.resnet = InceptionResnetV1(pretrained="vggface2").eval().to(DEVICE)
        self._initialized = True
        logger.info("Face models loaded.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def detect_and_embed(self, image: Image.Image) -> Optional[np.ndarray]:
        """
        Detect the primary face in a PIL image and return a 512-d L2-normalised
        embedding vector, or None if no face is found.
        """
        img_rgb = image.convert("RGB")
        try:
            face_tensor = self.mtcnn(img_rgb)           # (3, 160, 160) or None
        except Exception as e:
            logger.warning(f"MTCNN failed: {e}")
            return None

        if face_tensor is None:
            return None

        face_tensor = face_tensor.unsqueeze(0).to(DEVICE)  # (1, 3, 160, 160)
        with torch.no_grad():
            embedding = self.resnet(face_tensor)            # (1, 512)
            embedding = F.normalize(embedding, p=2, dim=1)

        return embedding.squeeze(0).cpu().numpy()

    def get_embedding_from_bytes(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Convenience wrapper that accepts raw image bytes."""
        image = Image.open(io.BytesIO(image_bytes))
        return self.detect_and_embed(image)

    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Returns similarity in [0, 1]; higher = more similar."""
        return float(1 - cosine(emb1, emb2))

    def match_against_database(
        self,
        query_embedding: np.ndarray,
        db_embeddings: list[dict],          # [{case_id, embedding_bytes, age_at_missing}, …]
        top_k: int = 5,
    ) -> list[dict]:
        """
        Compare query embedding against all stored embeddings.
        Returns top_k matches sorted by similarity descending.

        Each db entry must have:
            case_id (int), embedding_bytes (bytes), age_at_missing (float)
        """
        results = []
        for entry in db_embeddings:
            try:
                stored_emb = pickle.loads(entry["embedding_bytes"])
            except Exception:
                continue

            sim = self.cosine_similarity(query_embedding, stored_emb)

            # Apply age-appropriate threshold
            threshold = UNDER_5_THRESHOLD if entry.get("age_at_missing", 99) < 5 else MATCH_THRESHOLD
            results.append({
                "case_id": entry["case_id"],
                "similarity": round(sim, 4),
                "is_match": sim >= threshold,
                "threshold_used": threshold,
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def serialize_embedding(self, embedding: np.ndarray) -> bytes:
        return pickle.dumps(embedding)

    def deserialize_embedding(self, data: bytes) -> np.ndarray:
        return pickle.loads(data)

    def draw_faces(self, image: Image.Image) -> Image.Image:
        """Return image with bounding boxes drawn (useful for debug/UI preview)."""
        img_rgb = np.array(image.convert("RGB"))
        boxes, probs = self.mtcnn.detect(image)
        if boxes is not None:
            for box, prob in zip(boxes, probs):
                if prob < 0.9:
                    continue
                x1, y1, x2, y2 = [int(c) for c in box]
                cv2.rectangle(img_rgb, (x1, y1), (x2, y2), (0, 220, 100), 2)
                cv2.putText(
                    img_rgb, f"{prob:.2f}", (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 100), 1
                )
        return Image.fromarray(img_rgb)
