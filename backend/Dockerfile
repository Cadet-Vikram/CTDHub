# ── Stage 1: Build + download model weights ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download DeepFace ArcFace weights so container starts instantly
RUN python -c "\
from deepface import DeepFace; \
import numpy as np; \
img = np.zeros((224,224,3), dtype=np.uint8); \
DeepFace.represent(img, model_name='ArcFace', enforce_detection=False); \
print('ArcFace weights downloaded')"

# ── Stage 2: Lean runtime image ───────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy packages + pre-downloaded weights from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.deepface /root/.deepface

# Copy app code (excluding dev/training files)
COPY . .

RUN mkdir -p uploads/children uploads/searches uploads/progressed

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8080

CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1 --timeout-keep-alive 75
