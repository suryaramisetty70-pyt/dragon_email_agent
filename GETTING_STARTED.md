# =============================================================================
# PROJECT DRAGON - GETTING STARTED GUIDE
# =============================================================================
# Complete guide to set up and run Dragon Email Agent
# =============================================================================

## 📋 Prerequisites

1. **Python 3.10+** installed
2. **Email accounts** you want to connect
3. **App Passwords** (recommended for Gmail/Outlook)

---

## 🚀 QUICK START

### Step 1: Navigate to Project Directory
```bash
cd /workspace/project/dragon_email_agent
```

### Step 2: Run Setup Wizard
```bash
python3 setup_emails.py
```

The wizard will guide you to configure your email accounts.

### Step 3: Start the Agent
```bash
./start.sh
# OR
python3 main.py
```

---

## 📧 EMAIL SETUP

### Your Email Accounts

You mentioned these two emails:
1. **vtu27657@veltec.edu.in** (College/Academic)
2. **suryaramisetty70@gmail.com** (Personal)

### Gmail Setup (Required for suryaramisetty70@gmail.com)

Gmail requires **App Passwords** instead of regular passwords:

1. **Enable 2-Factor Authentication**
   - Go to: https://myaccount.google.com/security
   - Enable "2-Step Verification"

2. **Generate App Password**
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Windows Computer" (or other)
   - Copy the 16-character password

3. **Use the App Password** in the setup wizard instead of your regular password

### College Email Setup (vtu27657@veltec.edu.in)

1. Contact your IT department for IMAP/SMTP settings
2. Or check if they support OAuth/OIDC login
3. Common settings might be:
   - IMAP: imap.veltec.edu.in (port 993)
   - SMTP: smtp.veltec.edu.in (port 587 or 465)

---

## 🎮 HOW TO RUN

### Method 1: Using Start Script
```bash
./start.sh
```

### Method 2: Direct Python
```bash
python3 main.py
```

### Method 3: With Voice Enabled
```bash
python3 main.py --voice
```

### Method 4: API Server Only
```bash
python3 main.py --api
```

---

## 📝 COMMANDS

### Voice Commands (say out loud)
```
"Hey Dragon, read my important emails"
"Hey Dragon, show my unread emails"
"Hey Dragon, reply to Rahul"
"Hey Dragon, summarize my inbox"
"Hey Dragon, what's my inbox status?"
```

### Text Commands (type in terminal)
```
@dragon read important emails
@dragon show unread
@dragon reply to rahul
@dragon summarize inbox
@dragon inbox status
@dragon search internship
@dragon sync emails
@dragon contacts
@dragon analytics
```

### Built-in Commands
```
help, h          - Show help
status           - System status
sync             - Sync emails
briefing         - Daily briefing
emails [filter]  - List emails
contacts         - List contacts
search <query>   - Search emails
analytics        - Productivity stats
voice            - Toggle voice
exit, quit       - Exit agent
```

---

## ⚙️ CONFIGURATION FILES

| File | Purpose |
|------|---------|
| `config/email_accounts.json` | Your email account credentials |
| `config/email_config.yaml` | Email configuration |
| `config/gmail_credentials.json` | Gmail API credentials (if using Gmail API) |
| `.env` | Environment variables (contains passwords) |

---

## 🔧 TROUBLESHOOTING

### "Connection Failed" Error

1. **Check your internet connection**
2. **Verify email/password**
3. **For Gmail: Use App Password, not regular password**
4. **Check if IMAP is enabled** in your email settings:
   - Gmail: https://myaccount.google.com/lesssecureapps

### "Module not found" Error

```bash
pip install -r requirements.txt
```

### Voice Not Working

Install speech recognition packages:
```bash
pip install SpeechRecognition pyttsx3 pyaudio
```

### Want to Use Gmail API Instead of IMAP

1. Create Google Cloud project at https://console.cloud.google.com
2. Enable Gmail API
3. Download credentials as `config/gmail_credentials.json`

---

## 📊 WHAT DRAGON DOES

### Email Management
- ✅ Read emails from all accounts
- ✅ Send emails
- ✅ Reply/Forward emails
- ✅ Organize by priority (P0-P4)
- ✅ Classify into categories (Work, Personal, Finance, etc.)

### Smart Features
- 🔔 Email notifications (new emails, important emails)
- ⏰ Auto follow-up reminders
- 📊 Daily briefing every morning
- 🔍 Semantic search (find emails by meaning, not just keywords)
- 💾 Remember contact history and preferences

### Integrations
- 📧 Gmail, Outlook, IMAP providers
- 🔗 PC Agent, WhatsApp Agent, Other Dragon agents
- 📱 API server for external access

---

## 🔒 SECURITY NOTES

1. **Never share your `.env` file** - it contains passwords
2. **Use App Passwords for Gmail** - they're safer
3. **Credentials are stored locally** - nothing is sent to external servers
4. **For production**: Use encrypted storage for passwords

---

## 📞 SUPPORT

If you need help:
1. Check the logs in `logs/dragon.log`
2. Run `python3 main.py --help` for options
3. Review `README.md` for detailed documentation

---

**Happy emailing with Dragon! 🐉**