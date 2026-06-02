# =============================================================================
# HOW TO SAVE AND RUN DRAGON EMAIL AGENT
# =============================================================================

## 📁 Project Location

The project is located at:
```
/workspace/project/dragon_email_agent
```

---

## 📋 FILES YOU NEED TO KEEP

### Main Files
```
dragon_email_agent/
├── main.py              # Main program - RUN THIS
├── sync_emails.py       # Quick email sync script
├── start.sh             # Start script
├── setup_emails.py      # Email setup wizard
├── requirements.txt     # Python dependencies
├── setup.py             # Package setup
├── pyproject.toml       # Package config
│
├── config/
│   └── email_accounts.json    # YOUR EMAIL CREDENTIALS (KEEP THIS!)
│
├── core/                # Core system
├── database/            # Database
├── email_engine/        # Email engine
├── voice/               # Voice system
├── memory/              # Memory system
├── rag/                # Search system
├── security/           # Security
├── automation/          # Automation
├── analytics/          # Analytics
├── integrations/       # Email integrations
├── api/                # API server
├── utils/              # Utilities
│
├── data/                # Database files (created automatically)
├── logs/                # Log files (created automatically)
│
└── README.md           # Documentation
```

---

## 🚀 HOW TO RUN IN YOUR TERMINAL

### Step 1: Navigate to Project Folder

```bash
cd /workspace/project/dragon_email_agent
```

### Step 2: Run the Main Program

```bash
python3 main.py
```

That's it! The agent will start and you can type commands.

---

## 📝 COMMANDS TO USE

When the agent is running, type these commands:

| Command | What it does |
|---------|-------------|
| `help` | Show all commands |
| `sync` | Sync all emails |
| `status` | Check inbox status |
| `@dragon show unread` | Show unread emails |
| `@dragon read important` | Read important emails |
| `exit` | Quit the agent |

---

## 🔄 QUICK SYNC (Separate Script)

If you just want to quickly see your emails without the full agent:

```bash
python3 sync_emails.py
```

---

## 📦 INSTALL DEPENDENCIES (If needed)

```bash
pip install loguru pydantic pydantic-settings sqlalchemy fastapi uvicorn python-dateutil beautifulsoup4 apscheduler pyyaml
```

---

## ⚠️ IMPORTANT - SAVE YOUR CONFIG

Your email credentials are stored in:
```
config/email_accounts.json
```

**DO NOT delete this file!** It contains your email passwords.

---

## 🎯 STEP-BY-STEP TO RUN

Open your terminal and run these commands:

```bash
# 1. Go to project folder
cd /workspace/project/dragon_email_agent

# 2. Run the agent
python3 main.py

# 3. When running, type:
help       # To see commands
sync       # To sync emails
status     # To check inbox
exit       # To quit
```

---

## 🔧 If You Get Errors

### "Module not found" error:
```bash
pip install -r requirements.txt
```

### "Database error":
Delete the old database and restart:
```bash
rm data/dragon_email.db
python3 main.py
```

---

## 📂 To Copy Project to Another Location

```bash
# Create a zip file
zip -r dragon_email_agent.zip /workspace/project/dragon_email_agent

# Or copy the folder
cp -r /workspace/project/dragon_email_agent ~/dragon_email_agent
```

Then on your new computer:
```bash
cd ~/dragon_email_agent
pip install -r requirements.txt
python3 main.py
```

---

## ✅ CHECKLIST BEFORE RUNNING

- [ ] Navigate to project folder: `cd /workspace/project/dragon_email_agent`
- [ ] Check email config exists: `cat config/email_accounts.json`
- [ ] Run: `python3 main.py`

---

## 🎉 That's It!

You're ready to use Dragon Email Agent!

**Start now:**
```bash
python3 main.py
```