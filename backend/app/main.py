"""
Connecting the Dots - Missing Children AI System
Main FastAPI Application
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
import logging

from app.api import children, search, alerts, sos, auth
from app.services.face_service import FaceService
from app.services.alert_service import AlertService
from app.database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    logger.info("🚀 Starting Connecting the Dots API...")
    await init_db()
    app.state.face_service = FaceService()
    app.state.alert_service = AlertService()
    logger.info("✅ All services initialized")
    yield
    logger.info("🛑 Shutting down...")


app = FastAPI(
    title="Connecting the Dots API",
    description="AI-powered missing children identification system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(children.router, prefix="/api/v1/children", tags=["Children"])
app.include_router(search.router, prefix="/api/v1/search", tags=["Search & Match"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(sos.router, prefix="/api/v1/sos", tags=["SOS Emergency"])


@app.get("/")
async def root():
    return {
        "message": "Connecting the Dots API",
        "status": "operational",
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": ["face_detection", "matching", "alerts"]}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
