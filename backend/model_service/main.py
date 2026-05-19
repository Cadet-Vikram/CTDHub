"""Standalone face model service for Cloud Run."""

import io
import logging
import os
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _decode_image(content: bytes):
    try:
        import cv2

        arr = np.frombuffer(content, np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content)).convert("RGB")
            return np.array(img)[:, :, ::-1]
        except Exception:
            return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    from face_model import FaceRecognitionModel

    app.state.face_model = FaceRecognitionModel()
    load_real_model = os.getenv("LOAD_REAL_FACE_MODEL", "true").lower() == "true"
    strict_real_model = os.getenv("FACE_MODEL_STRICT", "true").lower() == "true"
    app.state.load_real_model = load_real_model
    app.state.strict_real_model = strict_real_model
    if load_real_model:
        logger.info("LOAD_REAL_FACE_MODEL=true")
        logger.info("FACE_MODEL_STRICT=%s", strict_real_model)
        await app.state.face_model.load()
        logger.info("Face model ready")
    else:
        logger.info("LOAD_REAL_FACE_MODEL=false")
        logger.info("Face model running in lightweight mock mode")

    yield
    logger.info("Shutting down")


app = FastAPI(title="CTD Model Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mode": "real" if getattr(app.state, "load_real_model", False) else "mock",
        "strict": getattr(app.state, "strict_real_model", True),
    }


@app.post("/embed")
async def embed(photo: UploadFile = File(...)):
    content = await photo.read()
    image = _decode_image(content)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image file")

    face_model = getattr(app.state, "face_model", None)
    if face_model is None:
        raise HTTPException(status_code=503, detail="Face model not ready")

    embedding, faces = face_model.process_image(image)
    if embedding is None:
        return {
            "embedding": None,
            "face_count": len(faces),
            "message": "No face detected in the provided image",
        }

    return {
        "embedding": embedding.tolist(),
        "face_count": len(faces),
        "message": "Embedding extracted",
    }
