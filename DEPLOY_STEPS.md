# Deploy India Trade Dashboard — Free Public Link

Your DB is 300MB+ so we use Supabase (free) + Streamlit Cloud (free).
Total time: ~30-40 minutes. Cost: $0.

---

## STEP 1: Create Free Supabase Database (5 min)

1. Go to: https://supabase.com
2. Click "Start your project" → Sign up (free)
3. Click "New project"
   - Name: india-trade
   - Password: choose a strong password (SAVE IT)
   - Region: choose closest to you
4. Wait ~2 minutes for project to initialize
5. Go to: Settings → Database
6. Copy the "Connection string" URI — looks like:
   postgresql://postgres:YOUR_PASSWORD@db.XXXX.supabase.co:5432/postgres

---

## STEP 2: Install Migration Requirements (1 min)

```
pip install sqlalchemy psycopg2-binary
```

---

## STEP 3: Upload Your Data to Supabase (20-30 min)

```
python migrate_to_supabase.py --url "postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres"
```

This uploads all 1.5M rows to Supabase. Progress is shown.
Your local data is NOT deleted — Supabase gets a copy.

To test connection first:
```
python migrate_to_supabase.py --url "..." --test
```

---

## STEP 4: Push Code to GitHub (5 min)

Create a new repo on github.com (name: india-trade-dashboard)
Then in your project folder:

```
git init
git add dashboard/app_ts.py src/db_cloud.py requirements.txt .streamlit/config.toml
git commit -m "India Trade Intelligence Dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/india-trade-dashboard.git
git push -u origin main
```

NOTE: Do NOT add data/ folder to git (it's 300MB+).
Add a .gitignore file with:
```
data/
*.db
*.xlsx
__pycache__/
*.pyc
```

---

## STEP 5: Deploy on Streamlit Community Cloud (5 min)

1. Go to: https://share.streamlit.io
2. Sign in with your GitHub account
3. Click "New app"
4. Fill in:
   - Repository: YOUR_USERNAME/india-trade-dashboard
   - Branch: main
   - Main file path: dashboard/app_ts.py
5. Click "Advanced settings"
6. Under "Secrets" add:
   ```
   SUPABASE_URL = "postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres"
   ```
7. Click "Deploy!"

Wait 2-3 minutes while it builds.

---

## STEP 6: Share Your Link

Your app is now live at:
  https://YOUR_USERNAME-india-trade-dashboard-appts-XXXXX.streamlit.app

Share this link with anyone — they just open it in a browser.
No login required. Works 24/7 without your PC being on.

---

## ADDING NEW DATA (monthly update process)

When new monthly data is available:
```
# 1. Download new files (e.g. Feb 2026)
python download_2026.py --months Feb

# 2. Process into local SQLite
python main.py --process

# 3. Upload new data to Supabase
python migrate_to_supabase.py --url "..." --table cxc

# 4. Dashboard automatically shows new data (no redeploy needed)
```

---

## TROUBLESHOOTING

"Cannot connect to Supabase":
  - Check your connection string has correct password
  - Check project is not paused (free tier pauses after 1 week inactivity)
  - Go to supabase.com → your project → click "Resume"

"App shows no data on Streamlit Cloud":
  - Check secrets are set correctly in Streamlit Cloud settings
  - Variable name must be exactly: SUPABASE_URL

"Migration is slow":
  - Normal — 300MB takes 20-30 minutes
  - Do not interrupt — let it finish
  - You can migrate one table at a time:
    python migrate_to_supabase.py --url "..." --table cxc
