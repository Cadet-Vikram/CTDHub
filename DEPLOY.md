# Connecting the Dots — Deployment Guide
# Google Cloud Run (Backend) + Vercel (Frontend)

---

## Before you start — what you need

- Google account (free)
- GitHub account (free)
- Your `best.pth` from Phase 3 Colab training (optional — system works without it)
- About 1 hour

---

## PART 1 — One-time Google Cloud Setup

### Step 1 — Create Google Cloud project

1. Go to https://console.cloud.google.com
2. Click project dropdown → New Project
3. Name: `connecting-the-dots` → Create
4. Make sure this project is selected

### Step 2 — Enable APIs (run in terminal)

Install Google Cloud CLI from: https://cloud.google.com/sdk/docs/install

Then run:
```
gcloud init
gcloud config set project connecting-the-dots
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### Step 3 — Free PostgreSQL database on Supabase

1. Go to https://supabase.com → New project
2. Name: `connecting-the-dots`
3. Set a database password — SAVE IT
4. Region: ap-south-1 (Mumbai) for India
5. Wait 2 minutes for provisioning
6. Go to Project Settings → Database → copy the URI:
   `postgresql://postgres:PASSWORD@db.XXXXX.supabase.co:5432/postgres`

---

## PART 2 — Register Your Phase 3 ArcFace Model (Optional)

If you have `best.pth` from Colab:

1. Copy `best.pth` to `backend/checkpoints/arcface_custom.pth`
2. In `backend/models/face_model.py`, inside `EmbeddingExtractor.load()`,
   add this block FIRST (before the deepface try block):

```python
try:
    import torch, sys, os
    ckpt_path = "checkpoints/arcface_custom.pth"
    if os.path.exists(ckpt_path):
        sys.path.insert(0, "ml/training")
        from train_arcface import FaceEmbeddingNet
        ckpt = torch.load(ckpt_path, map_location="cpu")
        self._model = FaceEmbeddingNet("resnet50", 512, pretrained=False)
        self._model.load_state_dict(ckpt.get("model", ckpt))
        self._model.eval()
        self._model_type = "custom_arcface"
        self.EMBEDDING_SIZE = 512
        logger.info("  Custom ArcFace model loaded from best.pth ✅")
        return
except Exception as e:
    logger.warning(f"  Custom model load failed: {e}")
```

3. Add `torch==2.5.1` to requirements.txt

---

## PART 3 — Deploy Backend to Cloud Run

### Step 4 — Push backend to GitHub

```
cd connecting-the-dots/backend
git init
git add .
git commit -m "Phase 2 production deploy"
git branch -M main

# Create a repo on github.com named: ctd-backend
git remote add origin https://github.com/YOUR_USERNAME/ctd-backend.git
git push -u origin main
```

### Step 5 — Deploy to Cloud Run

Run this command (replace the placeholder values):

Windows:
```
gcloud run deploy ctd-backend ^
  --source . ^
  --region asia-south1 ^
  --platform managed ^
  --allow-unauthenticated ^
  --memory 2Gi ^
  --cpu 2 ^
  --timeout 300 ^
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres",SECRET_KEY="make-this-a-long-random-string-32chars",DEBUG="false",ALLOWED_ORIGINS="*"
```

Mac/Linux:
```
gcloud run deploy ctd-backend \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars DATABASE_URL="postgresql+asyncpg://postgres:YOUR_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres",SECRET_KEY="make-this-a-long-random-string-32chars",DEBUG="false",ALLOWED_ORIGINS="*"
```

This takes 10-15 minutes first time (building Docker image with DeepFace).

When done you see:
```
Service URL: https://ctd-backend-XXXXXXXX-el.a.run.app
```

SAVE THIS URL.

### Step 6 — Test backend

Open in browser:
```
https://ctd-backend-XXXXXXXX-el.a.run.app/health
```
Should show: `{"status":"healthy"}`

API docs (Swagger):
```
https://ctd-backend-XXXXXXXX-el.a.run.app/docs
```

---

## PART 4 — Deploy Frontend to Vercel

### Step 7 — Update the API URL

Open `frontend/.env.production` and replace the URL:
```
VITE_API_URL=https://ctd-backend-XXXXXXXX-el.a.run.app
```

### Step 8 — Push frontend to GitHub

```
cd connecting-the-dots/frontend
git init
git add .
git commit -m "Phase 2 production deploy"
git branch -M main

# Create a repo on github.com named: ctd-frontend
git remote add origin https://github.com/YOUR_USERNAME/ctd-frontend.git
git push -u origin main
```

### Step 9 — Deploy on Vercel

1. Go to https://vercel.com → sign in with GitHub
2. Add New Project → import `ctd-frontend`
3. Framework: Vite (auto-detected)
4. Add environment variable:
   - Name:  `VITE_API_URL`
   - Value: `https://ctd-backend-XXXXXXXX-el.a.run.app`
5. Click Deploy

After ~2 minutes you get:
```
https://ctd-frontend.vercel.app
```

### Step 10 — Update CORS to allow your Vercel URL

```
gcloud run services update ctd-backend \
  --region asia-south1 \
  --update-env-vars ALLOWED_ORIGINS="https://ctd-frontend.vercel.app"
```

---

## PART 5 — Flutter Mobile App

### For development (Android emulator):
The app already points to `http://10.0.2.2:8000` by default — works with your local backend.

### For production (real device / APK):
Update `mobile/lib/services/api_service.dart` line 9:
```dart
defaultValue: 'https://ctd-backend-XXXXXXXX-el.a.run.app',
```

Then build APK:
```
cd mobile
flutter build apk --release --dart-define=API_URL=https://ctd-backend-XXXXXXXX-el.a.run.app
```

APK location: `build/app/outputs/flutter-apk/app-release.apk`
Share this file directly — users install it on Android.

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| Build takes 15+ min | Normal — DeepFace is large. Subsequent builds take 3 min. |
| "DeepFace ArcFace loaded" not in logs | Check requirements.txt has deepface==0.0.93 and tf-keras==2.18.0 |
| Database connection refused | Check Supabase URL starts with postgresql+asyncpg:// |
| CORS error in browser | Run Step 10 with your actual Vercel URL |
| Frontend shows blank/errors | Check VITE_API_URL in Vercel matches your Cloud Run URL exactly |
| Cloud Run timeout (60s) | Add --timeout 300 to deploy command |
| "Service unavailable" on first request | Cloud Run cold start — wait 30s and retry |

---

## Cost estimate (free tiers)

| Service | Free limit | Your usage |
|---------|-----------|------------|
| Cloud Run | 2M requests/month, 180K CPU-seconds | ~$0 for prototype |
| Cloud Build | 120 min/day | ~$0 |
| Supabase | 500 MB database, 2 GB transfer | ~$0 |
| Vercel | Unlimited deploys | ~$0 |

Total: **$0/month** for a research/demo project.
