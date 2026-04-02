# Keep Render Backend Alive — Free Solutions

Render free tier sleeps after **15 minutes of no traffic**, causing a 30–60 second cold start.
Use **any one** of these free methods to keep it awake 24/7.

---

## ✅ Method 1: GitHub Actions (Already Set Up!)

The file `.github/workflows/keep-alive.yml` is already in this repo.

**Steps to activate:**
1. Push this repo to GitHub (if not already done)
2. Go to your GitHub repo → **Actions** tab
3. You will see "🔔 Keep Render Alive" workflow
4. It automatically runs every 14 minutes — no setup needed

**Why it works:** GitHub Actions runs on GitHub's servers for free (2,000 minutes/month on free plan — pinging uses ~2 min/day, well within limits).

---

## ✅ Method 2: UptimeRobot (Easiest — No Code)

**Steps:**
1. Go to https://uptimerobot.com → Sign up free
2. Click **+ Add New Monitor**
3. Set:
   - Monitor Type: **HTTP(s)**
   - Friendly Name: `eClerx KYC Backend`
   - URL: `https://kyc-chatbot-api.onrender.com/health`
   - Monitoring Interval: **5 minutes**
4. Click **Create Monitor**

Done. UptimeRobot pings your backend every 5 minutes forever, for free.
Free plan: 50 monitors, 5-minute intervals, email alerts if it goes down.

---

## ✅ Method 3: cron-job.org (No Sign-up for basic)

**Steps:**
1. Go to https://cron-job.org → Sign up free
2. Click **Create Cronjob**
3. Set:
   - URL: `https://kyc-chatbot-api.onrender.com/health`
   - Schedule: Every **10 minutes**
4. Save

---

## 🎯 Recommendation

Use **both** Method 1 (GitHub Actions) + Method 2 (UptimeRobot) together.
- GitHub Actions = primary pinger
- UptimeRobot = backup + alerts if backend goes down

With both running, your chatbot will **always** respond instantly — no cold start.

---

## Health Endpoint

Your backend health check URL:
```
GET https://kyc-chatbot-api.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "documents_loaded": 36,
  "vector_store_ready": true
}
```
