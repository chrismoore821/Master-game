# Game Pulse - Deployment Guide

Your Flask game website is now ready for production deployment!

## Files Added for Deployment

- **requirements.txt** - Python dependencies
- **config.py** - Production/development configuration
- **Procfile** - For Heroku, Render, Railway hosting
- **.env.example** - Environment variables template

## Quick Start

### 1. First, create your .env file locally:
```bash
cp .env.example .env
```

Then edit `.env` and add your secure values:
```
FLASK_ENV=production
SECRET_KEY=your-very-secure-random-key-here
DATABASE_URL=sqlite:///database.db
```

### 2. Test locally before deploying:
```bash
pip install -r requirements.txt
FLASK_ENV=development python app.py
```

---

## Deployment Options

### Option A: Render (Recommended - Easiest)

1. **Push to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy on Render:**
   - Go to https://render.com
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Set Environment:
     - **Runtime:** Python 3.11
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
   - Add Environment Variables:
     - `FLASK_ENV`: `production`
     - `SECRET_KEY`: Generate a secure key (keep it secret!)
   - Click "Deploy"

3. **After deployment:**
   - Your site will be live at `https://your-app-name.onrender.com`
   - Free tier goes to sleep after 15 min of inactivity (paid tier keeps it live)

---

### Option B: Railway (Very Easy)

1. **Push to GitHub** (same as Render)

2. **Deploy on Railway:**
   - Go to https://railway.app
   - Click "New Project" → "Deploy from GitHub"
   - Select your repository
   - Railway auto-detects the Procfile
   - Add Environment Variables:
     - `FLASK_ENV`: `production`
     - `SECRET_KEY`: Your secure key
   - Done! Your app deploys automatically

3. **Your site:** `https://your-project-name.up.railway.app`

---

### Option C: Heroku (Free tier discontinued, but still reliable)

1. **Install Heroku CLI:** https://devcenter.heroku.com/articles/heroku-cli

2. **Deploy:**
   ```bash
   heroku login
   heroku create your-app-name
   heroku config:set FLASK_ENV=production
   heroku config:set SECRET_KEY=your-secure-key
   git push heroku main
   ```

3. **View your site:** `https://your-app-name.herokuapp.com`

---

### Option D: PythonAnywhere (Python-specific)

1. **Sign up:** https://www.pythonanywhere.com

2. **Upload your code:**
   - Via git: `git clone your-repo`
   - Or upload via web interface

3. **Configure:**
   - Click "Web" tab → Create new web app
   - Choose Python 3.11 and Flask
   - Edit WSGI configuration:
     ```python
     import sys
     sys.path.insert(0, '/home/yourusername/mysite')
     from app import app as application
     ```
   - Set environment variables in `.bash_profile`

4. **Reload and visit:** `https://yourusername.pythonanywhere.com`

---

### Option E: DigitalOcean App Platform

1. **Push to GitHub**

2. **Create App on DigitalOcean:**
   - Go to https://cloud.digitalocean.com/apps
   - Click "Create App" → Connect GitHub
   - Select your repo
   - DigitalOcean auto-detects Procfile
   - Add environment variables
   - Deploy!

3. **Your site:** `https://your-app-name-xxxxx.ondigitalocean.app`

---

## Before Deploying - IMPORTANT CHECKLIST

- [ ] Change the hardcoded password in `app.py` (line with `if password == 'Nanayaw1@2008'`)
  - Better: Use environment variable
  ```python
  admin_password = os.getenv('ADMIN_PASSWORD', 'change-me')
  if password == admin_password:
  ```

- [ ] Generate a secure SECRET_KEY:
  ```python
  from secrets import token_hex
  print(token_hex(32))
  ```
  Use this value in your `.env` and production environment

- [ ] Create a `.gitignore`:
  ```
  .env
  .venv
  __pycache__/
  instance/
  *.pyc
  .DS_Store
  ```

- [ ] Test in production mode locally:
  ```bash
  FLASK_ENV=production python app.py
  ```

---

## Database Considerations

Your app uses **SQLite (database.db)** by default.

**For production:**
- ✅ SQLite works for small-to-medium traffic
- ⚠️ SQLite is NOT ideal for multiple simultaneous users (locking issues)
- 🚀 Better options: PostgreSQL, MySQL

**To use PostgreSQL:**
1. Create database on host (all platforms offer free tier)
2. Set `DATABASE_URL` environment variable
3. Example: `postgresql://user:pass@host:5432/dbname`
4. No code changes needed - SQLAlchemy handles it!

---

## Monitoring & Troubleshooting

### Check logs:
- **Render:** Logs tab in dashboard
- **Railway:** Logs tab in deployment
- **Heroku:** `heroku logs --tail`
- **PythonAnywhere:** Error log in Web tab

### Common Issues:

**502 Bad Gateway:**
- Your app is crashing
- Check logs for errors
- Ensure all dependencies in `requirements.txt`

**Database locked:**
- Multiple users accessing SQLite at once
- Solution: Switch to PostgreSQL

**Static files not loading:**
- Ensure CSS/JS files are in `static/` folder
- In production, run: `flask --app app collect-static`

---

## Updating Your App

After deployment:
1. Make changes locally
2. Test with `FLASK_ENV=development python app.py`
3. Commit and push to GitHub
4. Platform auto-redeploys! (Most platforms)

For manual deployment:
```bash
git push heroku main  # Heroku
git push origin main  # Render/Railway auto-deploy from GitHub
```

---

## Security Tips

1. **Never commit `.env`** - Keep secrets out of version control
2. **Use strong SECRET_KEY** - At least 32 random characters
3. **Update admin password** - Use environment variable
4. **Enable HTTPS** - All modern platforms do this automatically
5. **Set FLASK_DEBUG=False** - Never use debug in production

---

## Getting Help

- **Render Support:** https://render.com/docs
- **Railway Docs:** https://docs.railway.app
- **Heroku Docs:** https://devcenter.heroku.com
- **Flask Docs:** https://flask.palletsprojects.com
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org

---

## Next Steps

1. Choose a platform (Render or Railway recommended for easiest setup)
2. Follow the platform-specific steps above
3. Test your deployed app
4. Share the link with your audience!

Good luck! 🚀
