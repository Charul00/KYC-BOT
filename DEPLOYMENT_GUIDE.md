# Deployment Guide - eClerx KYC Chatbot

## Architecture
- **Backend (FastAPI)** → Render (Free tier)
- **Frontend (React)** → Vercel (Free tier)

---

## Step 1: Push to GitHub

First, create a GitHub repository and push the code:

```bash
cd kyc-chatbot
git init
git add .
git commit -m "Initial commit - eClerx KYC Chatbot"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/kyc-chatbot.git
git branch -M main
git push -u origin main
```

IMPORTANT: Make sure `.env` is in `.gitignore` — never commit your OpenAI API key!

---

## Step 2: Deploy Backend on Render (Free)

1. Go to https://render.com and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `kyc-chatbot-api`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

5. Add **Environment Variables** (click "Advanced"):
   - `OPENAI_API_KEY` = your OpenAI key (keep this secret!)
   - `CHROMA_PERSIST_DIR` = `/tmp/kyc_chroma_db`
   - `DOCUMENTS_DIR` = `./data/documents`
   - `MODEL_NAME` = `gpt-4o`
   - `EMBEDDING_MODEL` = `text-embedding-3-small`
   - `CHUNK_SIZE` = `500`
   - `CHUNK_OVERLAP` = `50`
   - `TOP_K_RESULTS` = `4`
   - `TEMPERATURE` = `0`
   - `MAX_MEMORY_MESSAGES` = `5`

6. Click **"Create Web Service"**
7. Wait for deploy (2-5 minutes)
8. Note your backend URL: `https://kyc-chatbot-api.onrender.com`
9. Test: Visit `https://kyc-chatbot-api.onrender.com/health`

---

## Step 3: Deploy Frontend on Vercel (Free)

1. Go to https://vercel.com and sign up (free, use GitHub login)
2. Click **"Add New Project"**
3. Import your GitHub repo
4. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

5. Add **Environment Variable**:
   - `VITE_API_URL` = `https://kyc-chatbot-api.onrender.com/api/v1`
   (Replace with YOUR actual Render URL from Step 2)

6. Click **"Deploy"**
7. Wait for deploy (1-2 minutes)
8. Note your frontend URL: `https://kyc-chatbot-xxx.vercel.app`

---

## Step 4: Update Backend CORS

After getting your Vercel URL, add it to Render:

1. Go to Render dashboard → your service → Environment
2. Add new env var:
   - `FRONTEND_URL` = `https://kyc-chatbot-xxx.vercel.app`
3. This allows your Vercel frontend to talk to the Render backend

---

## Step 5: Verify

1. Open your Vercel URL in browser
2. You should see the eClerx KYC Assistant
3. Try asking: "What does eClerx do?"
4. Try uploading a document

---

## Important Notes

### Render Free Tier Limitations
- Server spins down after 15 min of inactivity
- First request after spin-down takes ~30 seconds (cold start)
- 750 free hours/month
- ChromaDB data in /tmp is ephemeral (resets on redeploy)
  - Documents in `data/documents/` folder are persistent (part of your repo)
  - Uploaded documents via the UI will be lost on redeploy

### Vercel Free Tier
- Unlimited deployments
- Custom domain support
- Automatic HTTPS
- No limitations for this use case

### To use a custom domain
- Vercel: Settings → Domains → Add your domain
- Update Render FRONTEND_URL env var to match
