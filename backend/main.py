"""
Connecting the Dots — Backend API
Production-ready for Google Cloud Run
"""

import logging, os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

for d in ["uploads/children", "uploads/searches", "uploads/progressed"]:
    os.makedirs(d, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from models.database import init_db
    await init_db()
    logger.info("✅ Database ready")

    from models.face_model import FaceRecognitionModel
    app.state.face_model = FaceRecognitionModel()
    await app.state.face_model.load()
    logger.info("✅ Face model ready")

    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Connecting the Dots API",
    description="AI-powered missing children identification system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: reads comma-separated origins from env var, defaults to * for dev
_origins = os.getenv("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import children, search, alerts, auth, reports
from api.websocket import ws_router

app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(children.router, prefix="/api/children", tags=["Children"])
app.include_router(search.router,   prefix="/api/search",   tags=["Search"])
app.include_router(alerts.router,   prefix="/api/alerts",   tags=["Alerts"])
app.include_router(reports.router,  prefix="/api/reports",  tags=["Reports"])
app.include_router(ws_router,       prefix="/ws",           tags=["WebSocket"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    return {"status": "online", "service": "Connecting the Dots", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
