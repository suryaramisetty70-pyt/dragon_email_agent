# =============================================================================
# EMAIL CONNECTION ISSUES - SOLUTIONS
# =============================================================================

## ❌ Issues Found

### 1. College Email: vtu27657@veltech.edu.in
**Error**: "Name or service not known"
**Problem**: IMAP server `imap.veltech.edu.in` doesn't exist

### 2. Gmail: suryaramisetty70@gmail.com
**Error**: "Application-specific password required"
**Problem**: Gmail requires an App Password, not your regular password

---

## 🔧 SOLUTIONS

### For Gmail (Fix Now!)

Gmail blocks regular passwords. You need an **App Password**:

1. **Enable 2-Factor Authentication**:
   - Go to: https://myaccount.google.com/security
   - Find "2-Step Verification" and enable it

2. **Generate App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select app: "Mail"
   - Select device: "Windows" or "Other"
   - Click "Generate"
   - Copy the 16-character password (looks like: xxxx xxxx xxxx xxxx)

3. **Update config**:
   ```bash
   nano config/email_accounts.json
   ```
   Replace `jayasurya_ram91821` with your new App Password

---

### For College Email

The domain `veltech.edu.in` might have a different mail server. Try these:

**Common patterns**:
- `mail.veltech.edu.in`
- `smtp.veltech.edu.in`
- `webmail.veltech.edu.in`
- `outlook.office.com` (if using Microsoft 365)

**Or check**:
1. Login to your college webmail
2. Look for settings or help about IMAP/SMTP
3. Or contact IT department

---

## ⚡ QUICK FIX FOR GMAIL

Run this to update your Gmail password to use App Password:

```bash
# After you get your App Password from Google, run:
cd /workspace/project/dragon_email_agent
python3 -c "
import json
with open('config/email_accounts.json', 'r') as f:
    config = json.load(f)

# Update Gmail password (replace YOUR_APP_PASSWORD with actual App Password)
for acc in config['accounts']:
    if 'gmail.com' in acc['email']:
        acc['password'] = 'YOUR_APP_PASSWORD_HERE'

with open('config/email_accounts.json', 'w') as f:
    json.dump(config, f, indent=2)
print('Updated! Now run: python3 main.py')
"
```

---

## 🔍 Test Connections

After fixing, test with:

```bash
cd /workspace/project/dragon_email_agent
python3 -c "
import imaplib

# Test Gmail
print('Testing Gmail...')
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    mail.login('suryaramisetty70@gmail.com', 'YOUR_APP_PASSWORD')
    print('✓ Gmail works!')
    mail.logout()
except Exception as e:
    print(f'✗ Gmail failed: {e}')
"
```

---

## 📞 Need Help?

1. **For Gmail**: Follow steps in "For Gmail (Fix Now!)" above
2. **For College**: Contact IT or check college website for mail settings

---

## ✅ Expected Result

Once both accounts are configured:
- Gmail: "Connected! Folders: X"
- College: "Connected! Folders: X"