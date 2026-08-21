# Connecting the Dots — Deployment Guide (Phase 2)
## Make it usable by others right now

---

## What "deployed" means at Phase 2

- Backend runs on a server with a public URL
- Anyone with the URL can use the web dashboard
- Face search uses real DeepFace ArcFace embeddings (no NVIDIA needed)
- Data stored in a real database (not just your laptop)

---

## Option 1 — Railway (Easiest, Free tier, 15 minutes)

Railway hosts your FastAPI backend for free. No credit card needed for the free tier.

### Step 1 — Push your code to GitHub

```
1. Go to github.com → New repository → Name: connecting-the-dots → Create
2. On your computer, open a terminal in the backend folder:

   cd connecting-the-dots/backend
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/connecting-the-dots.git
   git push -u origin main
```

### Step 2 — Deploy on Railway

```
1. Go to railway.app → Login with GitHub
2. New Project → Deploy from GitHub repo → select your repo
3. Railway auto-detects Python and runs: uvicorn main:app
4. Wait ~3 minutes → you get a URL like: https://connecting-the-dots.up.railway.app
```

### Step 3 — Set environment variables on Railway

In Railway dashboard → your project → Variables → Add:
```
DATABASE_URL    = postgresql://... (Railway gives you a free Postgres — add it below)
SECRET_KEY      = any-long-random-string-here
DEBUG           = false
```

To add free Postgres: Railway project → + Add → Database → PostgreSQL
Copy the DATABASE_URL it gives you and paste it as an env variable.

### Step 4 — Update requirements.txt for Railway

Add these lines to backend/requirements.txt:
```
asyncpg==0.29.0
gunicorn==22.0.0
```

And add a Procfile in the backend folder:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Push to GitHub → Railway auto-redeploys.

### Step 5 — Update frontend to point to Railway URL

In frontend/src/App.jsx and all pages, replace:
```js
// Old (local)
fetch("http://localhost:8000/api/...")

// New (deployed)
fetch("https://YOUR-APP.up.railway.app/api/...")
```

Or better — use an environment variable in vite.config.js:
```js
// In all fetch calls, use:
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
fetch(`${API}/api/...`)
```

Then create frontend/.env.production:
```
VITE_API_URL=https://YOUR-APP.up.railway.app
```

---

## Option 2 — Render (Also free, similar to Railway)

```
1. render.com → New → Web Service → Connect GitHub repo
2. Build Command:  pip install -r requirements.txt
3. Start Command:  uvicorn main:app --host 0.0.0.0 --port $PORT
4. Add environment variables same as Railway
5. Add a free PostgreSQL database from Render dashboard
```

---

## Option 3 — Deploy frontend on Vercel (free static hosting)

After Railway/Render has the backend running:

```bash
cd frontend
npm install
npm run build          # creates dist/ folder

# Install Vercel CLI
npm install -g vercel
vercel                 # follow prompts, connect GitHub

# Set env variable in Vercel dashboard:
# VITE_API_URL = https://your-backend.up.railway.app
```

This gives you a URL like: https://connecting-the-dots.vercel.app

---

## Database switch from SQLite → PostgreSQL

The backend uses SQLite by default (a local file). For production with multiple users, switch to PostgreSQL.

In backend/main.py and models/database.py, the DATABASE_URL env variable controls this.
Railway/Render give you a PostgreSQL URL like:
```
postgresql+asyncpg://user:password@host:5432/dbname
```

Set that as DATABASE_URL in your deployment environment variables — no code changes needed.

Also add to requirements.txt:
```
asyncpg==0.29.0
```

---

## DeepFace on the server (Phase 2 face recognition)

On the server, DeepFace downloads model weights on first startup (~500 MB).
This can cause a timeout on Railway's free tier.

Fix — pre-download in Dockerfile:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libglib2.0-0 libsm6 libxext6 libxrender-dev
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

---

## Final deployment checklist

- [ ] Backend deployed on Railway/Render with public URL
- [ ] PostgreSQL database connected
- [ ] DeepFace installed and working (check logs for "DeepFace ArcFace loaded")
- [ ] Frontend deployed on Vercel with correct API URL
- [ ] CORS updated in backend main.py to allow your Vercel domain:
      allow_origins=["https://your-app.vercel.app"]
- [ ] SECRET_KEY set to a long random string (not the default)
- [ ] Test: register a child → search by face → get a result
- [ ] Share the Vercel URL with your users

---

## Estimated costs (free tier limits)

| Service | Free tier | Limit before paid |
|---------|-----------|-------------------|
| Railway | 500 hours/month | ~20 days continuous |
| Render  | 750 hours/month | ~31 days (sleeps after 15 min idle) |
| Vercel  | Unlimited static | No limit for frontend |
| PostgreSQL | 1 GB | Enough for thousands of records |

For a demo or research project, the free tiers are more than enough.
For 24/7 production with real users, Railway Hobby plan is $5/month.

