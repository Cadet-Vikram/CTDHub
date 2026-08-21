#!/bin/bash
set -e
echo "============================================"
echo " Connecting the Dots — Backend Setup"
echo "============================================"

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install fastapi==0.115.5 "uvicorn[standard]==0.32.1" python-multipart==0.0.12
pip install "sqlalchemy[asyncio]==2.0.36" aiosqlite==0.20.0
pip install pyjwt==2.10.0 "passlib[bcrypt]==1.7.4" "python-jose[cryptography]==3.3.0"
pip install numpy==1.26.4 opencv-python-headless==4.10.0.84 Pillow==11.0.0
pip install pydantic==2.10.3 pydantic-settings==2.6.1 python-dotenv==1.0.1
pip install websockets==13.1 httpx==0.28.0

uvicorn main:app --reload --port 8000
