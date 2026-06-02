# =============================================================================
# PROJECT DRAGON - QUICK START GUIDE
# =============================================================================

## 📧 YOUR EMAIL ACCOUNTS

You have two emails to configure:
1. **vtu27657@veltec.edu.in** (College)
2. **suryaramisetty70@gmail.com** (Personal)

---

## 🚀 STEP-BY-STEP SETUP

### Step 1: Edit Email Configuration

Open `config/email_accounts.json` and replace your passwords:

```json
{
  "accounts": [
    {
      "email": "vtu27657@veltec.edu.in",
      "password": "YOUR_COLLEGE_PASSWORD_HERE",
      "imap_host": "imap.veltec.edu.in",
      "imap_port": 993,
      "smtp_host": "smtp.veltec.edu.in",
      "smtp_port": 587,
      "is_active": true,
      "account_type": "college",
      "display_name": "College Email"
    },
    {
      "email": "suryaramisetty70@gmail.com",
      "password": "YOUR_GMAIL_APP_PASSWORD",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "is_active": true,
      "account_type": "personal",
      "display_name": "Personal Email"
    }
  ]
}
```

### Step 2: For Gmail - Get App Password

Gmail requires an **App Password**, not your regular password:

1. Go to: https://myaccount.google.com/security
2. Enable "2-Step Verification" if not enabled
3. Go to: https://myaccount.google.com/apppasswords
4. Create a new App Password for "Mail"
5. Copy the 16-character password (spaces don't matter)
6. Use this as your password in `config/email_accounts.json`

### Step 3: Run the Agent

```bash
cd /workspace/project/dragon_email_agent
python3 main.py
```

---

## 📝 COMMANDS TO USE

Once the agent is running, you can use these commands:

### Text Commands
```
@dragon sync emails          - Sync all email accounts
@dragon show unread          - Show unread emails
@dragon read important      - Show important emails
@dragon inbox status         - Show inbox status
@dragon search [query]       - Search emails
@dragon contacts             - List contacts
@dragon analytics            - Show productivity stats
```

### Built-in Commands
```
help                        - Show help
status                      - System status
sync                        - Sync emails
briefing                    - Daily briefing
emails [filter]             - List emails
contacts                    - List contacts
search <query>              - Search emails
exit                        - Exit agent
```

---

## 🔧 IF CONNECTION FAILS

### For College Email (vtu27657@veltec.edu.in)

Contact your IT department to get:
- IMAP server address (usually imap.yourcollege.edu)
- SMTP server address
- Your email password or app-specific password

### For Gmail (suryaramisetty70@gmail.com)

1. Make sure 2-Step Verification is ON
2. Create an App Password at: https://myaccount.google.com/apppasswords
3. Use that 16-character password

---

## 🎯 LIVE DEMO

To run with your emails:

1. Edit `config/email_accounts.json` with real passwords
2. Run: `python3 main.py`
3. Type: `sync` to fetch emails
4. Type: `@dragon show unread` to see emails
5. Type: `exit` to quit

---

## 📊 WHAT YOU'LL SEE

When emails sync successfully, you'll see:
- Email count per account
- Unread count
- Important emails highlighted
- Contact list
- Productivity metrics

---

**Need help?** Check `GETTING_STARTED.md` for detailed instructions.