# Complete Deployment Strategy — Phase 2

## Overview
- **Backend (FastAPI)** → Railway with Docker
- **Frontend (React)** → Vercel
- **Mobile (Flutter)** → Firebase Hosting + App Stores
- **DeepFace Model** → Runs on backend (Docker pre-loads weights)
- **Database** → PostgreSQL (Railway provided)

---

## 1. BACKEND DEPLOYMENT (Railway + Docker)

### Why Docker?
Railway + Docker ensures:
- DeepFace weights pre-download (~500MB) at build time (prevents timeout)
- Consistent environment across local/production
- All system dependencies (libglib, libsm6, etc.) installed

### Steps:

#### 1a. Update backend/requirements.txt
Add these production dependencies:
```
asyncpg==0.29.0
gunicorn==22.0.0
python-dotenv==1.0.0
```

#### 1b. Create backend/Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for DeepFace
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download DeepFace weights at build time
RUN python -c "from deepface import DeepFace; \
    import numpy as np; \
    DeepFace.represent(np.zeros((224,224,3),dtype=np.uint8), \
    model_name='ArcFace', enforce_detection=False)"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 1c. Create backend/Procfile
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

#### 1d. Create backend/.dockerignore
```
__pycache__
*.pyc
.env
.git
connecting_dots.db
.pytest_cache
```

#### 1e. Update backend/main.py for CORS
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Railway backend URL (update after deployment)
BACKEND_URL = "https://YOUR-APP.up.railway.app"
# Vercel frontend URL (update after deployment)
FRONTEND_URL = "https://YOUR-FRONTEND.vercel.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000"],  # Add mobile IP too
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 1f. Create backend/.env.example
```
DATABASE_URL=postgresql://user:password@localhost:5432/connecting_dots
SECRET_KEY=your-secret-key-here
DEBUG=false
```

#### 1g. Push to GitHub
```bash
cd connecting-the-dots
git add .
git commit -m "Add Dockerfile and production config for Railway"
git push origin main
```

#### 1h. Deploy on Railway
1. Go to **railway.app** → Sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your `connecting-the-dots` repo
4. Railway auto-detects the Dockerfile and deploys
5. After ~5 minutes, you get a URL like `https://connecting-the-dots.up.railway.app`

#### 1i. Add PostgreSQL Database
1. In Railway dashboard → Your project
2. Click **+ Add** → **Database** → **PostgreSQL**
3. Copy the `DATABASE_URL` connection string
4. Go to **Variables** → Add `DATABASE_URL` with the copied value
5. Add other env vars:
   ```
   SECRET_KEY = <generate a random 32-char string>
   DEBUG = false
   ```

**Result:** Backend running at `https://YOUR-APP.up.railway.app`

---

## 2. FRONTEND DEPLOYMENT (Vercel)

### Steps:

#### 2a. Update frontend/.env.production
```
VITE_API_URL=https://YOUR-APP.up.railway.app
```

#### 2b. Update frontend/src (all fetch calls)
```javascript
// Instead of hardcoded URLs:
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Use in all API calls:
fetch(`${API}/api/search`, {...})
```

#### 2c. Verify frontend builds locally
```bash
cd frontend
npm install
npm run build
```

#### 2d. Deploy to Vercel
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

Or use Vercel GitHub integration:
1. Go to **vercel.com** → Sign in with GitHub
2. Click **Add New** → **Project**
3. Select your `connecting-the-dots` repo
4. Vercel auto-detects Vite config
5. Set env variable: `VITE_API_URL = https://YOUR-APP.up.railway.app`
6. Deploy

**Result:** Frontend running at `https://YOUR-FRONTEND.vercel.app`

---

## 3. MOBILE (Flutter) DEPLOYMENT

### Option A: Firebase Hosting (simplest for web)
If you want a mobile web version:
```bash
cd mobile
flutter build web
firebase deploy --only hosting
```

### Option B: App Store Deployment (native mobile)
1. **iOS**: Build `.ipa` → Upload to Apple App Store
2. **Android**: Build `.apk`/`.aab` → Upload to Google Play Store

Update `lib/main.dart` to point to backend:
```dart
const String API_URL = "https://YOUR-APP.up.railway.app";

// In HTTP calls:
final response = await http.get(Uri.parse('$API_URL/api/search'));
```

---

## 4. DEEPFACE MODEL DEPLOYMENT

### ❌ NOT a separate deployment
DeepFace runs **inside the backend FastAPI app**, not separately.

### How it works:
1. **Build phase** (Railway builds your Docker image):
   - Dockerfile runs: `python -c "from deepface import DeepFace; DeepFace.represent(...)"`
   - Downloads ArcFace weights (~500MB) and bakes them into the image
   - Image now has all weights preloaded

2. **Runtime** (Railway runs the container):
   - Your API calls `DeepFace.represent()` 
   - Weights are already loaded → instant response
   - No external API call needed

### Cost implication:
- **Build time**: ~10-15 min (Railway builds with Dockerfile)
- **Deploy size**: ~800MB (Docker image with weights)
- **No extra costs**: DeepFace runs on Railway container

---

## 5. ENVIRONMENT VARIABLES CHECKLIST

### Railway Backend
```
DATABASE_URL = postgresql://...
SECRET_KEY = [long-random-string]
DEBUG = false
```

### Vercel Frontend
```
VITE_API_URL = https://YOUR-APP.up.railway.app
```

### Flutter Mobile
```dart
const String API_URL = "https://YOUR-APP.up.railway.app";
```

---

## 6. DEPLOYMENT ORDER

1. **Backend first** → Get Railway URL
2. **Update frontend** → Point to Railway URL
3. **Deploy frontend** → Get Vercel URL
4. **Update backend CORS** → Allow Vercel domain
5. **Test end-to-end**
6. **Deploy mobile** → Point to backend + frontend

---

## 7. DEPLOYMENT CHECKLIST

- [ ] Backend Dockerfile created and tested locally
- [ ] backend/requirements.txt updated with production deps
- [ ] backend/Procfile created
- [ ] GitHub repo pushed with all changes
- [ ] Railway project created and repo connected
- [ ] PostgreSQL database added to Railway
- [ ] Railway env vars set (DATABASE_URL, SECRET_KEY, DEBUG)
- [ ] Backend URL generated (e.g., https://connecting-the-dots.up.railway.app)
- [ ] Backend tested at public URL (check `/docs`)
- [ ] Frontend .env.production updated with correct backend URL
- [ ] Frontend env vars used in all API calls
- [ ] Frontend builds locally without errors
- [ ] Vercel project created and repo connected
- [ ] Frontend deployed and accessible
- [ ] Backend CORS updated to allow Vercel domain
- [ ] Test: register user → upload face → search → get result
- [ ] Mobile app updated with backend URL
- [ ] Mobile built and tested

---

## 8. ESTIMATED COSTS & LIMITS

| Component | Service | Free Tier | Limit |
|-----------|---------|-----------|-------|
| Backend | Railway | 500 hrs/mo | ~20 days continuous |
| Database | Railway PostgreSQL | 1 GB | Enough for 10k+ records |
| Frontend | Vercel | Unlimited | No limits for static |
| Mobile | Firebase | 1 GB storage | Enough for most apps |

**Total Monthly Cost (free tier):** $0

---

## 9. TROUBLESHOOTING

### DeepFace timeout on Railway
**Problem:** Build fails with "timeout downloading model"
**Solution:** The Dockerfile pre-download step handles this. If it still times out:
- Increase Railway build timeout (Settings → Build Timeout)
- Or use a lighter model: `model_name='VGGFace2'` (faster, less accurate)

### API calls return CORS error
**Problem:** Frontend can't reach backend
**Solution:** 
1. Check backend CORS allows your Vercel domain
2. Check frontend is using correct API URL
3. Check Railway backend is actually running

### DeepFace weights not found at runtime
**Problem:** API returns "Model not found"
**Solution:**
1. Check Docker build completed successfully
2. Check Railway logs for build errors
3. Add verbose logging to backend main.py

---

## NEXT STEPS

1. Run the **Backend Setup** commands (1a-1g)
2. Deploy to Railway (1h-1i)
3. Update and deploy frontend (2a-2d)
4. Test end-to-end
5. Deploy mobile app
