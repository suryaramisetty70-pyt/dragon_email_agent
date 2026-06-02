# =============================================================================
# EMAIL CONNECTION STATUS
# =============================================================================

## College Email: vtu27657@veltech.edu.in
**Status**: ❌ Connection Timeout
**Issue**: The mail server `mail.veltech.edu.in` is not responding on standard IMAP ports.

**Possible Solutions**:
1. College may only provide webmail access (no IMAP)
2. Contact IT department for correct IMAP settings
3. Check if you need VPN to access college mail remotely
4. May need to use a different mail server address

**What you can do**:
- Login to webmail directly at mail.veltech.edu.in or veltech.edu.in
- Check with college IT for IMAP/SMTP settings
- Some colleges use Microsoft 365 - try `outlook.office365.com`

---

## Gmail: suryaramisetty70@gmail.com
**Status**: ⚠️ Needs App Password
**Issue**: Gmail requires an App Password, not your regular password.

**To Fix**:

### Step 1: Enable 2-Factor Authentication
1. Go to: https://myaccount.google.com/security
2. Find "2-Step Verification" and turn it ON
3. Complete the setup process

### Step 2: Generate App Password
1. Go to: https://myaccount.google.com/apppasswords
2. You may need to sign in again
3. Select app: "Mail"
4. Select device: "Windows Computer" (or any)
5. Click "Generate"
6. **Copy the 16-character password** (example: `abcd efgh ijkl mnop`)

### Step 3: Update Config
```bash
cd /workspace/project/dragon_email_agent

# Edit the config file
nano config/email_accounts.json
```

Change the Gmail password from `jayasurya_ram91821` to your **App Password**.

Example:
```json
{
  "email": "suryaramisetty70@gmail.com",
  "password": "abcd efgh ijkl mnop",  <-- Your App Password here
  ...
}
```

### Step 4: Test
```bash
python3 main.py
```

Then type: `sync`

---

## Quick Test Command

Test if Gmail works:
```bash
cd /workspace/project/dragon_email_agent
python3 -c "
import imaplib
print('Testing Gmail connection...')
print('Enter your App Password when prompted')
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    mail.login('suryaramisetty70@gmail.com', 'YOUR_APP_PASSWORD')
    print('✓ Gmail connected!')
    mail.logout()
except Exception as e:
    print(f'✗ Failed: {e}')
"
```

---

## Summary

| Email | Status | Action Needed |
|-------|--------|---------------|
| vtu27657@veltech.edu.in | ❌ Timeout | Contact IT or use webmail |
| suryaramisetty70@gmail.com | ⚠️ App Password | Get App Password from Google |

---

**Once Gmail is configured, Dragon will start syncing emails!**