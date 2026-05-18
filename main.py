"""
Connecting the Dots — Backend API
Run:  uvicorn main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

os.makedirs("uploads/children", exist_ok=True)
os.makedirs("uploads/searches", exist_ok=True)
os.makedirs("uploads/progressed", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Database init ──────────────────────────────────────────────────────
    from models.database import init_db
    await init_db()
    logger.info("✅ Database ready")

    # ── Face model (loads lazily — skips gracefully if torch/mtcnn absent) ─
    from models.face_model import FaceRecognitionModel
    app.state.face_model = FaceRecognitionModel()
    await app.state.face_model.load()
    logger.info("✅ Face model ready (mock mode if ML libs not installed)")

    yield
    logger.info("🛑 Shutting down")


app = FastAPI(
    title="Connecting the Dots API",
    description="AI-powered missing children identification system",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Configuration (Production-safe) ────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

cors_origins = [
    FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

if DEBUG:
    cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from api.routes import children, search, alerts, auth, reports
from api.websocket import ws_router

app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(children.router, prefix="/api/children", tags=["Children"])
app.include_router(search.router,   prefix="/api/search",   tags=["Search"])
app.include_router(alerts.router,   prefix="/api/alerts",   tags=["Alerts"])
app.include_router(reports.router,  prefix="/api/reports",  tags=["Reports"])
app.include_router(ws_router,       prefix="/ws",           tags=["WebSocket"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "service": "Connecting the Dots", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
