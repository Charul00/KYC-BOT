# Deployment Guide

**Architecture:**
- 🚂 **Backend** → Railway (FastAPI + ChromaDB + RAG pipeline)
- ▲ **Frontend** → Vercel (already live at https://kyc-bot.vercel.app)

---

## Files Changed for This Deployment

| File | What Changed |
|---|---|
| `backend/Dockerfile` | NEW — Python 3.11 + Tesseract + all pip deps |
| `backend/railway.json` | NEW — Railway build/healthcheck config |
| `backend/.dockerignore` | NEW — excludes .env, data/, chroma_db/ from image |
| `backend/app/config.py` | FIXED — removed hardcoded API key; added Vercel URL to CORS |
| `frontend/src/App.jsx` | FIXED — API_BASE now reads `VITE_API_URL` env var |

Render files (`render.yaml`, `build.sh`, `Procfile`, `runtime.txt`) — all deleted.

---

## Step 1 — Push Code to GitHub

```bash
cd path/to/kyc-chatbot
git add .
git commit -m "Deploy backend to Railway, frontend stays on Vercel"
git push origin main
```

---

## Step 2 — Deploy Backend on Railway

### 2a. Create the project

1. Go to [railway.app](https://railway.app) → Log in
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository

### 2b. Configure the service

When Railway asks for setup:
- **Root Directory**: `kyc-chatbot/backend`
- **Builder**: Railway will auto-detect your `Dockerfile` ✅
- **Service name**: `kyc-backend`

### 2c. Add a Persistent Volume (CRITICAL)

ChromaDB data must survive redeploys. Without a volume, all indexed documents are wiped every time you deploy.

In `kyc-backend` → **"Volumes"** tab:
- Click **"Add Volume"**
- **Mount Path**: `/data`
- Save

This one volume stores both ChromaDB (`/data/chroma_db`) and uploaded documents (`/data/documents`).

### 2d. Set Environment Variables

In `kyc-backend` → **"Variables"** tab, add:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | `sk-proj-...` (your actual key) |
| `CHROMA_PERSIST_DIR` | `/data/chroma_db` |
| `DOCUMENTS_DIR` | `/data/documents` |
| `MODEL_NAME` | `gpt-4o-mini` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` |
| `CHUNK_SIZE` | `500` |
| `CHUNK_OVERLAP` | `50` |
| `TOP_K_RESULTS` | `4` |
| `TEMPERATURE` | `0` |
| `MAX_TOKENS` | `1024` |
| `MAX_MEMORY_MESSAGES` | `5` |
| `CHROMA_ANONYMIZED_TELEMETRY` | `false` |
| `FRONTEND_URL` | `https://kyc-bot.vercel.app` |

> Railway automatically injects `PORT` — do not set it manually.

Click **"Deploy"**. First build takes 3-5 minutes (installs Tesseract + ML libs).

### 2e. Get your backend URL

After deploy, Railway gives you a public URL like:
```
https://kyc-backend-production.up.railway.app
```
Copy this — you need it for the Vercel step.

**Verify it works:**
```
https://kyc-backend-production.up.railway.app/health
```
Should return: `{"status": "healthy", "version": "1.0.0", ...}`

---

## Step 3 — Update Vercel Frontend

Your frontend is already live at `https://kyc-bot.vercel.app`. You just need to tell it where the new Railway backend is.

### 3a. Add environment variable in Vercel

1. Go to [vercel.com](https://vercel.com) → your `kyc-bot` project
2. **Settings** → **Environment Variables**
3. Add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://kyc-backend-production.up.railway.app/api/v1` |

   - Environment: **Production** (and Preview if you want)
4. Click **Save**

### 3b. Redeploy the frontend

Vercel bakes `VITE_API_URL` into the JS bundle at build time, so you need a fresh deploy:

1. Go to **Deployments** tab in your Vercel project
2. Click the **three-dot menu** on the latest deployment → **"Redeploy"**
3. Wait ~1 minute for build to finish

---

## Step 4 — Verify End-to-End

1. Open `https://kyc-bot.vercel.app`
2. The chatbot should show as **Online**
3. Ask a question — you should get a response from the Railway backend ✅
4. Upload a document — it should persist across redeploys (thanks to the volume) ✅
5. Delete the upload modal and check the background processing badge still tracks progress ✅

---

## Troubleshooting

### CORS error in browser console
Make sure `FRONTEND_URL=https://kyc-bot.vercel.app` is set in Railway backend variables. The `config.py` already has it hardcoded as the default, but it's good practice to also set it explicitly.

### Frontend still calling old API (localhost)
`VITE_API_URL` was not set before the Vercel build. Go to Vercel → Environment Variables → add it → redeploy.

### "Connection refused" from frontend
- Check the Railway backend is actually running (open the `/health` URL directly)
- Verify `VITE_API_URL` does NOT have a trailing slash and ends with `/api/v1`

### Documents lost after redeploy
The Railway volume must be at `/data`. Verify in backend variables: `CHROMA_PERSIST_DIR=/data/chroma_db` and `DOCUMENTS_DIR=/data/documents`.

### Build fails on Railway — out of memory
The ML libraries (chromadb, flashrank, torch) need at least 1 GB RAM to build. Upgrade to Railway **Hobby plan ($5/month)** if on the free tier.

### Tesseract OCR errors
The Dockerfile installs `tesseract-ocr` and `tesseract-ocr-eng`. Check Railway build logs to confirm the apt-get step succeeded.

---

## Railway Plan Note

| Feature | Free Tier | Hobby ($5/month) |
|---|---|---|
| Persistent Volumes | ❌ Not available | ✅ Required for ChromaDB |
| RAM | 512 MB | 8 GB |
| Disk | 500 MB | 100 GB |

You need **Hobby plan** for the persistent volume. Without it, ChromaDB is reset on every deploy.

---

## Final Architecture

```
User Browser
     │
     ▼
▲ Vercel  (https://kyc-bot.vercel.app)
     │  HTTPS API calls to Railway
     ▼
🚂 Railway  (https://kyc-backend-production.up.railway.app)
     │  Reads/writes
     ▼
📁 Railway Volume (/data)
     ├── chroma_db/    ← vector embeddings persist here
     └── documents/    ← uploaded files persist here
```
