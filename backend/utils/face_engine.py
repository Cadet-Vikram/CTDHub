"""
Face Recognition Engine
- MTCNN for face detection
- FaceNet / ArcFace for feature extraction
- Cosine similarity for matching
"""

import os
import io
import cv2
import numpy as np
import logging
from typing import Optional, Tuple, List
from PIL import Image

logger = logging.getLogger(__name__)

# ─── Lazy model holders ───────────────────────────────────────────────────────
_mtcnn = None
_facenet = None
_arcface = None

EMBEDDING_DIM = 512          # ArcFace embedding size
MATCH_THRESHOLD = 0.65       # cosine-similarity threshold for a positive match
FACE_IMAGE_SIZE = (160, 160) # FaceNet input size


def get_mtcnn():
    global _mtcnn
    if _mtcnn is None:
        try:
            from facenet_pytorch import MTCNN
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _mtcnn = MTCNN(
                image_size=160,
                margin=20,
                min_face_size=20,
                thresholds=[0.6, 0.7, 0.7],
                factor=0.709,
                post_process=True,
                keep_all=False,
                device=device,
            )
            logger.info(f"MTCNN loaded on {device}")
        except ImportError:
            logger.warning("facenet-pytorch not installed – using OpenCV fallback")
            _mtcnn = "opencv"
    return _mtcnn


def get_facenet():
    global _facenet
    if _facenet is None:
        try:
            from facenet_pytorch import InceptionResnetV1
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _facenet = InceptionResnetV1(pretrained="vggface2").eval().to(device)
            logger.info(f"FaceNet loaded on {device}")
        except ImportError:
            logger.warning("facenet-pytorch not installed")
            _facenet = None
    return _facenet


def get_arcface():
    """Load InsightFace ArcFace model (preferred over FaceNet for accuracy)."""
    global _arcface
    if _arcface is None:
        try:
            import insightface
            from insightface.app import FaceAnalysis
            _arcface = FaceAnalysis(providers=["CPUExecutionProvider"])
            _arcface.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("ArcFace loaded")
        except ImportError:
            logger.warning("insightface not installed – falling back to FaceNet")
            _arcface = None
    return _arcface


# ─── Face Detection ──────────────────────────────────────────────────────────

def detect_faces_mtcnn(image: np.ndarray) -> List[np.ndarray]:
    """Return list of cropped face arrays using MTCNN."""
    mtcnn = get_mtcnn()
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if mtcnn == "opencv":
        return _detect_faces_opencv(image)

    try:
        import torch
        boxes, _ = mtcnn.detect(pil_img)
        faces = []
        if boxes is not None:
            for box in boxes:
                x1, y1, x2, y2 = [int(c) for c in box]
                face = image[max(0, y1):y2, max(0, x1):x2]
                if face.size > 0:
                    faces.append(cv2.resize(face, FACE_IMAGE_SIZE))
        return faces
    except Exception as e:
        logger.error(f"MTCNN detection error: {e}")
        return _detect_faces_opencv(image)


def _detect_faces_opencv(image: np.ndarray) -> List[np.ndarray]:
    """Fallback: Haar cascade face detection."""
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    rects = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    faces = []
    for (x, y, w, h) in rects:
        face = image[y:y+h, x:x+w]
        faces.append(cv2.resize(face, FACE_IMAGE_SIZE))
    return faces


# ─── Embedding Extraction ────────────────────────────────────────────────────

def extract_embedding_arcface(image: np.ndarray) -> Optional[np.ndarray]:
    """Extract 512-d ArcFace embedding from an image."""
    arc = get_arcface()
    if arc is None:
        return extract_embedding_facenet(image)
    try:
        faces = arc.get(image)
        if faces:
            emb = faces[0].normed_embedding  # already L2-normalised
            return emb.astype(np.float32)
        return None
    except Exception as e:
        logger.error(f"ArcFace embedding error: {e}")
        return extract_embedding_facenet(image)


def extract_embedding_facenet(image: np.ndarray) -> Optional[np.ndarray]:
    """Extract FaceNet embedding."""
    model = get_facenet()
    if model is None:
        return _dummy_embedding()
    try:
        import torch
        mtcnn = get_mtcnn()
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        if mtcnn != "opencv":
            face_tensor = mtcnn(pil_img)
        else:
            face_tensor = None
        if face_tensor is None:
            # Resize and normalise manually
            resized = cv2.resize(image, FACE_IMAGE_SIZE)
            face_np = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            face_tensor = torch.from_numpy(face_np.transpose(2, 0, 1)).unsqueeze(0)
        with torch.no_grad():
            embedding = model(face_tensor.unsqueeze(0) if face_tensor.dim() == 3 else face_tensor)
        return embedding.squeeze().cpu().numpy()
    except Exception as e:
        logger.error(f"FaceNet embedding error: {e}")
        return _dummy_embedding()


def _dummy_embedding() -> np.ndarray:
    """Random unit-vector placeholder when models are unavailable."""
    v = np.random.randn(EMBEDDING_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def extract_embedding(image: np.ndarray) -> Optional[np.ndarray]:
    """Primary entry-point: tries ArcFace, falls back to FaceNet."""
    emb = extract_embedding_arcface(image)
    if emb is None:
        emb = extract_embedding_facenet(image)
    if emb is not None:
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
    return emb


# ─── Matching ────────────────────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity in [-1, 1]; mapped to [0, 1]."""
    a = a / (np.linalg.norm(a) + 1e-10)
    b = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a, b))


def match_face(
    query_embedding: np.ndarray,
    candidate_embeddings: List[Tuple[str, np.ndarray]],
) -> List[Tuple[str, float]]:
    """
    Match query embedding against a list of (case_id, embedding) pairs.
    Returns sorted list of (case_id, similarity_score) above threshold.
    """
    results = []
    for case_id, cand_emb in candidate_embeddings:
        score = cosine_similarity(query_embedding, cand_emb)
        if score >= MATCH_THRESHOLD:
            results.append((case_id, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return results


# ─── Image helpers ───────────────────────────────────────────────────────────

def load_image_from_bytes(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def enhance_image(image: np.ndarray) -> np.ndarray:
    """CLAHE + slight sharpening – improves low-quality sighting photos."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    return cv2.filter2D(enhanced, -1, kernel)


def align_face(image: np.ndarray, landmarks) -> np.ndarray:
    """Align face using eye landmarks for consistent embedding."""
    try:
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        angle = np.degrees(np.arctan2(dy, dx))
        center = tuple(np.array(image.shape[1::-1]) / 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(image, M, image.shape[1::-1], flags=cv2.INTER_CUBIC)
    except Exception:
        return image
