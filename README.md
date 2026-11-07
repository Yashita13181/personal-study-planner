# 📜 The Scholar's Ledger: Personal Study Planner & Progress Tracker

> *"Nulla dies sine linea" — No day without a line.*

A complete, production-ready Python study planner and progress journal built in the aesthetic of a classic academic ledger. **The Scholar's Ledger** operates both as an old-world **terminal journal (CLI / TUI)** powered by the `rich` library and as an online **web application** ready for cloud deployment on **Render**, **Railway**, or **PythonAnywhere**.

---

## ✦ Key Highlights & Visual Theme

- **Classic Academic Ledger Aesthetic:**
  - Styled with a deep charcoal background, parchment-gold/amber accents (`#D4AF37`, `#E6C280`), laurel greens (`#5B8A62`), and scholarly crimson (`#C85A5A`).
  - Double-bordered ledger entries, bookkeeper columns, academic laurels, and Latin scholar mottos.
- **Dual Interface (CLI + Web Portal):**
  - **Terminal Mode:** Fast, keyboard-driven interface with Rich tables, status badges, and Pomodoro hourglass.
  - **Web Portal Mode:** Modern responsive web application with interactive dashboards, visual progress bars, and one-click JSON backup/sync.
- **Intelligent Study Planner & Scheduling:**
  - Inscribe, update, categorize, and complete assignments, readings, and study tasks.
  - Flexible natural language date parsing (`today`, `tomorrow`, `yesterday`, `+3d`, `+2w`, or `YYYY-MM-DD`).
  - Categorization by discipline and priority (**High ▲**, **Medium ■**, **Low ▽**).
  - Dedicated **Daily Journal** and **Weekly Curriculum Schedule** (Monday to Sunday grid).
- **Progress & Streak Analytics:**
  - Live **Scholarly Streak Counter** (consecutive days studied) and record tracking.
  - Unicode visual progress bars for syllabus task completion % and weekly study hours vs target goals.
  - Lifetime study volume and daily study velocity breakdown per subject.
- **Scholar's Focus Hourglass (Timer):**
  - Interactive terminal & web focus countdown (default 25-minute Pomodoro) with auto-logging to your persistent ledger.
- **Robust Persistence & Cloud Portability:**
  - Local **SQLite database** (`tracker.db`) with Write-Ahead Logging (WAL) and configurable `DATABASE_PATH` for cloud persistent disks.
  - Zero-data-loss export and import to **JSON** (`study_data.json`) for backups or sync across environments.

---

## 🏛 Architecture & Project Structure

The project maintains strict modular separation of concerns and PEP 8 guidelines:

```
personal_study_planner/
├── app.py               # Production Flask web server (Gunicorn entry point)
├── main.py              # CLI entry point, interactive TUI menu loop & subcommand dispatcher
├── models.py            # Dataclasses & Enums (Task, Subject, StudyLog, Milestone, Priority, Status)
├── storage.py           # SQLite database engine, queries, streak calculations & JSON interchange
├── planner.py           # Business services, natural date parser, daily/weekly view aggregators
├── ui.py                # Rich terminal UI components, ledger tables, progress bars & hourglass timer
├── sample_data.py       # Curated academic seed dataset (CS, Math, Systems, Philosophy)
├── templates/           # Web portal templates styled in the classic academic ledger aesthetic
│   ├── base.html        # Shared layout, Latin mottos & custom CSS palette
│   ├── dashboard.html   # Main dashboard (streak flame, progress bars, active ledger)
│   ├── tasks.html       # Full task ledger with status & overdue filters
│   ├── task_edit.html   # Task amendment form
│   ├── daily.html       # Daily agenda & logged study sessions
│   ├── weekly.html      # Monday-to-Sunday weekly curriculum grid
│   ├── analytics.html   # Comprehensive progress & streak statistics
│   ├── milestones.html  # Academic laurels & syllabus milestone tracking
│   ├── timer.html       # Focus Hourglass countdown timer with auto-logging
│   └── backup.html      # JSON export/import and sample data seeding
├── test_planner.py      # Unit tests covering domain models, SQLite persistence, and streaks
├── test_web_app.py      # Web route integration tests
├── requirements.txt     # Python package requirements (rich, Flask, gunicorn)
├── Procfile             # Web process declaration for Render / Railway / Heroku
├── render.yaml          # Render Blueprint configuration file
├── .gitignore           # Git ignore rules for virtualenvs, caches, and databases
└── README.md            # Comprehensive documentation & deployment guide
```

---

## 🚀 Local Installation & Running

### 1. Prerequisites
- Python **3.8 or higher**

### 2. Setup
```bash
cd C:\Users\yashii\.gemini\antigravity\scratch\personal_study_planner
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Running Locally

#### Option A: Run the Web Portal
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your web browser.

#### Option B: Run the Terminal CLI
```bash
python main.py
```

---

## ☁️ How to Deploy Online (Render Free Tier)

**Render** is the recommended free hosting platform for this application.

### Step-by-Step Deployment:

1. **Initialize Git & Push to GitHub:**
   ```bash
   cd C:\Users\yashii\.gemini\antigravity\scratch\personal_study_planner
   git init
   git add .
   git commit -m "feat: complete personal study planner with web and CLI interfaces"
   git branch -M main
   # Create a new repository on github.com, then:
   git remote add origin https://github.com/<your-username>/personal-study-planner.git
   git push -u origin main
   ```

2. **Deploy on Render:**
   - Sign up / Log in to [render.com](https://render.com).
   - Click **New +** &rarr; **Web Service**.
   - Connect your GitHub repository.
   - Configure the following settings:
     - **Name:** `personal-study-planner`
     - **Runtime:** `Python 3`
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
     - **Instance Type:** `Free`
   - Under **Advanced / Environment Variables**, add:
     - `PYTHON_VERSION`: `3.11.8`
     - `SECRET_KEY`: *(Generate any random string, e.g. `scholar-secret-2026`)*
   - Click **Create Web Service**.

3. **Enjoy your live application:**
   Render will build and deploy your application. You will receive a free public URL such as:
   `https://personal-study-planner.onrender.com`

> [!NOTE]
> **Database Persistence on Render Free Tier:**
> On the Render free tier, web instances enter sleep mode after 15 minutes of inactivity, and the file system resets across deploys.
> To ensure your study data is always preserved:
> 1. Use the built-in **Backup & Sync** tab in the web app to download `study_data.json` at any time.
> 2. You can restore your data with one click on any newly started instance.
> 3. If you upgrade to a persistent disk on Render, set `DATABASE_PATH=/var/data/tracker.db` in your environment variables.

---

## 🧪 Running Automated Tests

Run the CLI unit tests:
```bash
python test_planner.py
```

Run the web portal integration tests:
```bash
python test_web_app.py
```
Or run all tests together:
```bash
python -m unittest discover -s . -p "test_*.py"
```
