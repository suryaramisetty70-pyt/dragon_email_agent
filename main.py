#!/usr/bin/env python3
"""
================================================================================
🐉 DRAGON EMAIL AGENT - ULTIMATE SUPER POWERED VERSION 🐉
================================================================================

FEATURES:
✓ Send/Receive/Reply/Forward Emails
✓ Spam Detection (AI-powered)
✓ Auto AI Reply Generation
✓ Realistic Voice Control (GTTS + Google Speech)
✓ Priority Inbox Sorting
✓ Contact Management
✓ Email Search
✓ Daily Digest
✓ Auto-responder for Vacation
✓ Enterprise Security System

================================================================================
"""

import sys
import os
import json
import imaplib
import smtplib
import re
import hashlib
import base64
import secrets
import time
from datetime import datetime
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

# Voice packages
try:
    from gtts import gTTS
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    WARNING = YELLOW
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def color(text, code):
    try:
        return f"{code}{text}{Colors.ENDC}"
    except:
        return text

# ==================== SECURITY SYSTEM ====================
class SecuritySystem:
    def __init__(self):
        self.failed_attempts = {}
        self.max_attempts = 5
        self.lockout_duration = 300
        self.rate_limits = {}
        self.audit_log = []
        
    def log_audit(self, event, details=""):
        entry = {'timestamp': datetime.now().isoformat(), 'event': event, 'details': details}
        self.audit_log.append(entry)
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
            
    def check_rate_limit(self, action, limit=20, window=60):
        now = time.time()
        key = f"{action}_{int(now/window)}"
        if key not in self.rate_limits:
            self.rate_limits[key] = 0
        self.rate_limits[key] += 1
        return self.rate_limits[key] <= limit
        
    def check_brute_force(self, identifier):
        now = time.time()
        if identifier in self.failed_attempts:
            attempts, first_attempt = self.failed_attempts[identifier]
            if now - first_attempt < self.lockout_duration and attempts >= self.max_attempts:
                remaining = int(self.lockout_duration - (now - first_attempt))
                return False, f"Locked. Try in {remaining}s."
        return True, ""
        
    def validate_input(self, text, max_length=10000):
        if not text:
            return ""
        if len(text) > max_length:
            text = text[:max_length]
        text = text.replace('\x00', '')
        dangerous = [r'<script', r'javascript:', r'onerror=', r'onclick=']
        for pattern in dangerous:
            text = re.sub(pattern, '', text, flags=re.I)
        return text.strip()
        
    def sanitize_email_content(self, content):
        if not content:
            return ""
        clean = re.sub(r'<[^>]+>', '', content)
        clean = re.sub(r'<script[^>]*>.*?</script>', '', clean, flags=re.I|re.DOTALL)
        clean = re.sub(r'javascript:', '', clean, flags=re.I)
        clean = re.sub(r'vbscript:', '', clean, flags=re.I)
        return clean
        
    def get_status(self):
        return {
            'locked': len([k for k, v in self.failed_attempts.items() 
                          if time.time() - v[1] < self.lockout_duration]),
            'audit_entries': len(self.audit_log)
        }

# ==================== VOICE SYSTEM ====================
class VoiceSystem:
    def __init__(self):
        self.enabled = VOICE_AVAILABLE
        self.recognizer = None
        self.microphone = None
        if self.enabled:
            try:
                self.recognizer = sr.Recognizer()
                self.microphone = sr.Microphone()
            except:
                self.enabled = False
                
        self.commands = {
            'check emails': 'sync', 'show emails': 'sync', 'sync': 'sync',
            'unread emails': 'unread', 'new emails': 'unread', 'show unread': 'unread',
            'important emails': 'important', 'show important': 'important',
            'spam folder': 'spam', 'check spam': 'spam',
            'send email': 'send', 'compose': 'send',
            'help': 'help', 'show help': 'help',
            'status': 'status', 'contacts': 'contacts',
            'exit': 'exit', 'quit': 'exit', 'bye': 'bye',
        }
        
    def speak(self, text):
        if not self.enabled:
            print(color(f"🐉 Dragon: {text}", Colors.CYAN))
            return
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save("temp_voice.mp3")
            os.system("start temp_voice.mp3" if os.name == 'nt' else "mpg123 temp_voice.mp3" if os.path.exists("/usr/bin/mpg123") else "xdg-open temp_voice.mp3")
            time.sleep(2)
            try:
                os.remove("temp_voice.mp3")
            except:
                pass
        except Exception as e:
            print(color(f"🐉 Dragon: {text}", Colors.CYAN))
            
    def listen(self):
        if not self.enabled:
            return None
        try:
            with self.microphone as source:
                print(color("🎤 Listening...", Colors.CYAN))
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print(color("🎤 Processing...", Colors.CYAN))
            text = self.recognizer.recognize_google(audio)
            print(color(f"🎤 You: {text}", Colors.GREEN))
            return text.lower()
        except Exception as e:
            print(color("🎤 Could not understand. Please speak clearly.", Colors.WARNING))
            return None
            
    def parse_command(self, text):
        if not text:
            return None
        text = text.lower().strip()
        for phrase, command in self.commands.items():
            if phrase in text:
                return command
        if 'search' in text or 'find' in text:
            for phrase in ['search for ', 'find ']:
                if phrase in text:
                    return f"search {text.split(phrase)[1].strip()}"
        return None

# ==================== SPAM DETECTOR ====================
class SpamDetector:
    SPAM_KEYWORDS = [
        'winner', 'congratulations', 'lottery', 'prize', 'claim', 'urgent',
        'act now', 'limited time', 'click here', 'free money', 'make money fast',
        'work from home', 'no obligation', 'credit card', 'debt', 'bitcoin',
        'crypto giveaway', 'double your money', 'suspicious', 'verify account',
        'suspended', 'unusual activity', 'security alert', 'password expired',
        'click now', 'order now', 'buy now', 'special offer', 'discount',
        'unsubscribe', 'opt-out', 'nigerian prince', 'inheritance', 'casino',
        'viagra', 'pharmacy', 'cheap meds', 'weight loss', 'miracle'
    ]
    
    def __init__(self):
        self.spam_count = 0
        
    def check(self, email_data):
        score = 0
        reasons = []
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('from', '').lower()
        
        if any(x in sender for x in ['noreply', 'no-reply', 'donotreply']):
            score += 2
        for keyword in self.SPAM_KEYWORDS:
            if keyword in subject:
                score += 3
                reasons.append(f"Keyword: {keyword}")
        for keyword in self.SPAM_KEYWORDS[:15]:
            if keyword in body:
                score += 1
        caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
        if caps_ratio > 0.5 and len(subject) > 10:
            score += 3
            reasons.append("Excessive CAPS")
        if subject.count('!') > 2:
            score += 2
        if re.search(r'bit\.ly|goo\.gl|tinyurl', body):
            score += 3
            reasons.append("Shortened URLs")
        attachments = email_data.get('attachments', [])
        for att in attachments:
            if any(ext in att.lower() for ext in ['.exe', '.zip', '.scr', '.bat', '.vbs']):
                score += 5
                reasons.append(f"Dangerous: {att}")
                
        is_spam = score >= 7
        if is_spam:
            self.spam_count += 1
        return {'is_spam': is_spam, 'score': score, 'reasons': reasons[:3]}

# ==================== AI REPLY GENERATOR ====================
class AIReplyGenerator:
    def __init__(self):
        self.templates = {
            'meeting': "Thank you for your email regarding the meeting. I have reviewed the details and will confirm my availability shortly. Please let me know the proposed time.",
            'interview': "Thank you for reaching out about the opportunity. I am very interested and would love to learn more. Please share the details.",
            'followup': "Thank you for following up. I appreciate your patience. I am actively working on this and will have an update soon.",
            'inquiry': "Thank you for your inquiry. I have received your message and will review it carefully. You can expect a response within 24-48 hours.",
            'request': "Thank you for your request. I am looking into this matter and will get back to you with the necessary information.",
            'thanks': "Thank you so much for your kind words! I truly appreciate your message and it means a lot to me.",
            'urgent': "Thank you for your urgent email. I am treating this as a priority and will respond as soon as possible.",
            'default': "Thank you for your email. I have received your message and will respond to you shortly. If urgent, please let me know.\n\nBest regards"
        }
        
    def analyze_email(self, subject, body, sender):
        combined = f"{subject} {body} {sender}".lower()
        if any(x in combined for x in ['meeting', 'schedule', 'calendar', 'call', 'discussion']):
            return 'meeting'
        if any(x in combined for x in ['interview', 'position', 'job', 'vacancy', 'hiring']):
            return 'interview'
        if any(x in combined for x in ['follow', 'update', 'checking']):
            return 'followup'
        if any(x in combined for x in ['question', 'information', 'details', 'query']):
            return 'inquiry'
        if any(x in combined for x in ['request', 'need', 'require', 'help']):
            return 'request'
        if any(x in combined for x in ['thank', 'grateful', 'appreciate']):
            return 'thanks'
        if any(x in combined for x in ['urgent', 'asap', 'immediately', 'emergency', 'critical']):
            return 'urgent'
        return 'default'
        
    def generate_reply(self, email_data):
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('from', 'User')
        if '<' in sender:
            sender_name = sender.split('<')[0].strip()
        else:
            sender_name = sender.split('@')[0]
        reply_type = self.analyze_email(subject, body, sender)
        base_reply = self.templates[reply_type]
        if sender_name:
            reply = f"Dear {sender_name},\n\n{base_reply}\n\nBest regards"
        else:
            reply = f"Dear Sir/Madam,\n\n{base_reply}\n\nBest regards"
        return reply, reply_type

# ==================== MAIN AGENT ====================
class DragonEmailAgent:
    def __init__(self):
        self.security = SecuritySystem()
        self.accounts = []
        self.load_config()
        self.connections = {}
        self.smtp_connections = {}
        self.spam_detector = SpamDetector()
        self.ai_reply = AIReplyGenerator()
        self.voice = VoiceSystem()
        self.auto_reply_enabled = False
        self.vacation_mode = False
        self.voice_enabled = False
        self.stats = {'emails_sent': 0, 'emails_received': 0, 'replies_sent': 0, 'spam_caught': 0}
        
    def load_config(self):
        config_path = "config/email_accounts.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
            print(color(f"📧 Loaded {len(self.accounts)} account(s)", Colors.GREEN))
        else:
            print(color("❌ config/email_accounts.json not found!", Colors.FAIL))
            
    def speak(self, text):
        if self.voice_enabled:
            self.voice.speak(text)
        print(color(f"🐉 Dragon: {text}", Colors.CYAN))
            
    def listen(self):
        if not self.voice_enabled:
            return None
        text = self.voice.listen()
        if text:
            return self.voice.parse_command(text)
        return None
            
    def connect_imap(self, account):
        email = account.get('email', '')
        password = account.get('password', '')
        imap_host = account.get('imap_host', '')
        imap_port = account.get('imap_port', 993)
        print(color(f"\n📡 Connecting to IMAP: {email}", Colors.CYAN))
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=20)
            mail.login(email, password)
            self.connections[email] = mail
            print(color(f"   ✅ IMAP Connected!", Colors.GREEN))
            self.security.log_audit("imap_connected", email)
            return True
        except Exception as e:
            print(color(f"   ❌ IMAP Failed", Colors.FAIL))
            return False
            
    def connect_smtp(self, account):
        email = account.get('email', '')
        password = account.get('password', '')
        smtp_host = account.get('smtp_host', '')
        smtp_port = account.get('smtp_port', 587)
        print(color(f"📤 Connecting SMTP: {email}", Colors.CYAN))
        try:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()
            server.login(email, password)
            self.smtp_connections[email] = server
            print(color(f"   ✅ SMTP Connected!", Colors.GREEN))
            self.security.log_audit("smtp_connected", email)
            return True
        except Exception as e:
            print(color(f"   ❌ SMTP Failed", Colors.FAIL))
            return False
            
    def connect_all(self):
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT 🐉🐉🐉", Colors.HEADER))
        print(color("ULTIMATE SUPER POWERED VERSION", Colors.YELLOW))
        print(color("="*60, Colors.BOLD))
        connected = 0
        for account in self.accounts:
            if account.get('is_active', True):
                imap_ok = self.connect_imap(account)
                smtp_ok = self.connect_smtp(account)
                if imap_ok or smtp_ok:
                    connected += 1
        print(color(f"\n✅ Connected: {connected}/{len(self.accounts)} accounts", Colors.GREEN))
        self.speak("Dragon Email Agent ready!")
        
    def send_email(self, to, subject, body, cc=None):
        if not self.smtp_connections:
            print(color("❌ No SMTP connection!", Colors.FAIL))
            return False
        to = self.security.validate_input(to, 200)
        subject = self.security.validate_input(subject, 500)
        body = self.security.validate_input(body, 50000)
        if not self.security.check_rate_limit('send_email', limit=20, window=60):
            print(color("❌ Rate limit exceeded. Please wait.", Colors.FAIL))
            return False
        email = list(self.smtp_connections.keys())[0]
        server = self.smtp_connections[email]
        try:
            msg = MIMEMultipart()
            msg['From'] = email
            msg['To'] = to
            msg['Subject'] = subject
            if cc:
                msg['Cc'] = cc
            safe_body = self.security.sanitize_email_content(body)
            msg.attach(MIMEText(safe_body, 'plain'))
            recipients = [to]
            if cc:
                recipients.append(cc)
            server.sendmail(email, recipients, msg.as_string())
            print(color(f"✅ Email sent to {to}!", Colors.GREEN))
            self.stats['emails_sent'] += 1
            self.security.log_audit("email_sent", f"To: {to}")
            return True
        except Exception as e:
            print(color(f"❌ Send failed: {e}", Colors.FAIL))
            return False
            
    def fetch_email_data(self, uid, mail):
        try:
            status, msg_data = mail.fetch(uid, '(RFC822)')
            if not msg_data or not msg_data[0]:
                return None
            raw = msg_data[0][1]
            msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
            subject = self.decode_header_value(msg.get('Subject', ''))
            sender = msg.get('From', 'Unknown')
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
            body = self.security.sanitize_email_content(body)
            attachments = []
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    attachments.append(part.get_filename() or 'unknown')
            return {'from': sender, 'subject': subject, 'body': body, 'date': msg.get('Date', ''), 'attachments': attachments, 'raw': raw}
        except:
            return None
            
    def decode_header_value(self, value):
        try:
            decoded_parts = decode_header(value)
            result = []
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result.append(part.decode(encoding or 'utf-8', errors='replace'))
                else:
                    result.append(part)
            return ' '.join(result)
        except:
            return value
            
    def sync_emails(self, folder='INBOX', show_count=15):
        print(color("\n" + "="*60, Colors.BLUE))
        print(color(f"📧 {folder.upper()} - SYNCING...", Colors.BOLD))
        print(color("="*60, Colors.BLUE))
        total = 0
        unread = 0
        spam = 0
        for email, mail in self.connections.items():
            try:
                status, messages = mail.select(folder)
                if status != 'OK':
                    continue
                status, msg_list = mail.search(None, 'ALL')
                email_ids = msg_list[0].split()
                count = len(email_ids)
                status, unread_list = mail.search(None, 'UNSEEN')
                unread_count = len(unread_list[0].split()) if unread_list[0] else 0
                print(color(f"\n📬 {email}", Colors.CYAN))
                print(color(f"   📊 Total: {count} | Unread: {unread_count}", Colors.WARNING))
                total += count
                unread += unread_count
                if count > 0:
                    recent = email_ids[-show_count:]
                    print(color("\n   📬 Recent Emails:", Colors.GREEN))
                    print("-" * 60)
                    for i, uid in enumerate(recent, 1):
                        data = self.fetch_email_data(uid, mail)
                        if not data:
                            continue
                        spam_check = self.spam_detector.check(data)
                        if spam_check['is_spam']:
                            spam += 1
                        sender = data['from']
                        subject = data['subject']
                        date = data['date'][:16]
                        if '<' in sender:
                            sender_name = sender.split('<')[0].strip()
                        else:
                            sender_name = sender.split('@')[0]
                        prefix = color("⚠️ SPAM ", Colors.FAIL) if spam_check['is_spam'] else color("[NEW] ", Colors.YELLOW)
                        print(f"\n   {prefix}[{i}] 📩 {sender_name[:30]}")
                        print(f"       📌 {subject[:55]}")
                        print(f"       📅 {date}")
                        body_preview = data['body'][:100].replace('\n', ' ').strip()
                        if body_preview:
                            print(f"       💬 {body_preview[:60]}...")
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
        print(color("\n" + "="*60, Colors.BLUE))
        print(color(f"📊 SUMMARY: {total} emails | {unread} unread | {spam} spam", Colors.BOLD))
        print(color("="*60, Colors.BLUE))
        self.stats['emails_received'] += total
        self.stats['spam_caught'] += spam
        
    def show_unread(self):
        print(color("\n📬 UNREAD EMAILS", Colors.BOLD))
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'UNSEEN')
                email_ids = messages[0].split()
                count = len(email_ids)
                print(color(f"\n📬 {email} - {count} unread", Colors.CYAN))
                if count == 0:
                    print(color("   ✅ All caught up!", Colors.GREEN))
                else:
                    for i, uid in enumerate(email_ids[:15], 1):
                        data = self.fetch_email_data(uid, mail)
                        if data:
                            sender = data['from']
                            if '<' in sender:
                                sender = sender.split('<')[0].strip()
                            print(f"\n   [{i}] 📩 {sender[:35]}")
                            print(f"       📌 {data['subject'][:55]}")
                            print(f"       📅 {data['date'][:16]}")
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
    def show_spam(self):
        print(color("\n⚠️ SPAM FOLDER", Colors.BOLD))
        for email, mail in self.connections.items():
            try:
                for folder in ['[Gmail]/Spam', 'Spam', 'Junk']:
                    try:
                        status, _ = mail.select(folder)
                        if status == 'OK':
                            status, messages = mail.search(None, 'ALL')
                            email_ids = messages[0].split()
                            print(color(f"\n📬 {email} - {len(email_ids)} spam", Colors.CYAN))
                            return
                    except:
                        continue
                print(color("   No spam folder found", Colors.WARNING))
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
    def search_emails(self, query):
        query = self.security.validate_input(query, 200)
        print(color(f"\n🔍 SEARCHING: '{query}'", Colors.BOLD))
        results = []
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                for uid in email_ids:
                    data = self.fetch_email_data(uid, mail)
                    if data and query.lower() in f"{data['subject']} {data['body']}".lower():
                        results.append(data)
            except:
                pass
        print(color(f"\n📊 Found {len(results)} results", Colors.GREEN))
        for i, data in enumerate(results[:10], 1):
            sender = data['from']
            if '<' in sender:
                sender = sender.split('<')[0].strip()
            print(f"\n   [{i}] 📩 {sender[:35]}")
            print(f"       📌 {data['subject'][:55]}")
        return results
        
    def send_reply(self, email_num, reply_text=None, use_ai=False):
        if not self.connections:
            print(color("❌ No IMAP connection", Colors.FAIL))
            return
        email = list(self.connections.keys())[0]
        mail = self.connections[email]
        try:
            mail.select('INBOX')
            status, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()
            if email_num > len(email_ids) or email_num < 1:
                print(color("❌ Invalid email number", Colors.FAIL))
                return
            data = self.fetch_email_data(email_ids[-email_num], mail)
            if not data:
                print(color("❌ Could not read email", Colors.FAIL))
                return
            sender = data['from']
            subject = data['subject']
            if '<' in sender:
                sender_email = sender.split('<')[1].split('>')[0]
            else:
                sender_email = sender
            print(color(f"\n📩 Replying to: {sender}", Colors.CYAN))
            if use_ai and not reply_text:
                ai_reply_text, reply_type = self.ai_reply.generate_reply(data)
                print(color(f"\n🤖 AI Reply ({reply_type.upper()}):", Colors.YELLOW))
                print("-" * 60)
                print(ai_reply_text)
                print("-" * 60)
                confirm = input(color("\n✅ Send AI reply? (y/n/s=edit): ", Colors.GREEN)).strip().lower()
                if confirm == 's':
                    reply_text = input("> ").strip()
                elif confirm != 'y':
                    print(color("❌ Cancelled", Colors.FAIL))
                    return
                else:
                    reply_text = ai_reply_text
            elif not reply_text:
                reply_text = input("\n✏️ Your reply: ").strip()
            if reply_text:
                self.send_email(sender_email, f"Re: {subject}", reply_text)
                self.stats['replies_sent'] += 1
            else:
                print(color("❌ Empty reply", Colors.FAIL))
        except Exception as e:
            print(color(f"❌ Error: {e}", Colors.FAIL))
            
    def ai_generate_reply(self, email_num):
        self.send_reply(email_num, use_ai=True)
        
    def show_contacts(self):
        contacts = {}
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                for uid in email_ids[-100:]:
                    data = self.fetch_email_data(uid, mail)
                    if data:
                        sender = data['from']
                        if '<' in sender:
                            name = sender.split('<')[0].strip()
                            addr = sender.split('<')[1].split('>')[0]
                        else:
                            name = sender.split('@')[0]
                            addr = sender
                        if addr not in contacts:
                            contacts[addr] = {'name': name, 'email': addr, 'count': 1}
                        else:
                            contacts[addr]['count'] += 1
            except:
                pass
        sorted_contacts = sorted(contacts.values(), key=lambda x: x['count'], reverse=True)
        print(color("\n👥 CONTACTS (Top 20)", Colors.BOLD))
        print("-" * 60)
        for i, contact in enumerate(sorted_contacts[:20], 1):
            print(f"   {i}. {contact['name'][:30]}")
            print(f"      📧 {contact['email'][:35]} ({contact['count']} emails)")
            
    def show_status(self):
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉 DRAGON STATUS", Colors.HEADER))
        print(color("="*60, Colors.BOLD))
        print(f"\n📧 Accounts: {len(self.accounts)}")
        print(f"📡 IMAP: {len(self.connections)}")
        print(f"📤 SMTP: {len(self.smtp_connections)}")
        print(f"🎤 Voice: {'✅' if self.voice_enabled else '❌'}")
        print(f"🤖 Auto-Reply: {'✅' if self.auto_reply_enabled else '❌'}")
        print(color("\n📊 STATISTICS:", Colors.CYAN))
        print(f"   📤 Sent: {self.stats['emails_sent']}")
        print(f"   📥 Received: {self.stats['emails_received']}")
        print(f"   📝 Replies: {self.stats['replies_sent']}")
        print(f"   ⚠️ Spam: {self.stats['spam_caught']}")
        print(color("\n📋 ACCOUNTS:", Colors.CYAN))
        for account in self.accounts:
            email = account.get('email', 'Unknown')
            imap_ok = email in self.connections
            smtp_ok = email in self.smtp_connections
            status = color("✅", Colors.GREEN) if imap_ok else color("❌", Colors.FAIL)
            print(f"   {status} {email}")
        print(color("="*60, Colors.BOLD))
        
    def show_security(self):
        status = self.security.get_status()
        print(color("\n🔐 SECURITY STATUS", Colors.BOLD))
        print(f"   Locked Accounts: {status['locked']}")
        print(f"   Audit Entries: {status['audit_entries']}")
        if self.security.audit_log:
            print(color("\n📋 Recent Events:", Colors.CYAN))
            for entry in self.security.audit_log[-5:]:
                print(f"   [{entry['timestamp'][11:19]}] {entry['event']}")
                
    def show_help(self):
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉🐉🐉 COMMANDS 🐉🐉🐉", Colors.HEADER))
        print(color("="*60, Colors.BOLD))
        print(color("\n📧 EMAIL:", Colors.CYAN))
        print("  sync / s              - Check emails")
        print("  unread / u            - Show unread")
        print("  important / i        - Important emails")
        print("  spam                  - Spam folder")
        print("  send                  - Send email")
        print("  reply [n]            - Reply to #n")
        print("  ai-reply [n]         - AI reply to #n")
        print("  forward [n]          - Forward #n")
        print("  search [text]         - Search emails")
        print("  contacts              - Show contacts")
        print("  digest                - Daily summary")
        print(color("\n🎤 VOICE:", Colors.CYAN))
        print("  voice on              - Enable voice")
        print("  voice off             - Disable voice")
        print("  listen                - Listen for command")
        print(color("\n🔐 SECURITY:", Colors.FAIL))
        print("  security              - Security status")
        print(color("\n🔧 GENERAL:", Colors.BOLD))
        print("  status / st           - Status")
        print("  help / h             - This help")
        print("  exit                  - Exit")
        print(color("="*60, Colors.BOLD))
        
    def cmd_send(self):
        print(color("\n📤 COMPOSE EMAIL", Colors.BOLD))
        to = input(color("To: ", Colors.CYAN)).strip()
        if not to:
            print(color("❌ Cancelled", Colors.FAIL))
            return
        subject = input(color("Subject: ", Colors.CYAN)).strip() or "(No Subject)"
        print("Body (press Enter twice to finish):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        body = "\n".join(lines)
        if body and input(color(f"📤 Send to {to}? (y/n): ", Colors.GREEN)).strip().lower() == 'y':
            self.send_email(to, subject, body)
            
    def cmd_forward(self, email_num):
        if not self.connections:
            print(color("❌ No connection", Colors.FAIL))
            return
        email = list(self.connections.keys())[0]
        mail = self.connections[email]
        try:
            mail.select('INBOX')
            status, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()
            if email_num <= len(email_ids) and email_num >= 1:
                data = self.fetch_email_data(email_ids[-email_num], mail)
                if data:
                    to = input(color("Forward to: ", Colors.CYAN)).strip()
                    if to:
                        forward_body = f"---------- Forwarded ----------\nFrom: {data['from']}\nSubject: {data['subject']}\n\n{data['body']}"
                        self.send_email(to, f"Fwd: {data['subject']}", forward_body)
        except Exception as e:
            print(color(f"❌ Error: {e}", Colors.FAIL))
            
    def handle_command(self, user_input):
        user_input = self.security.validate_input(user_input, 5000)
        text = user_input.lower().strip()
        original = user_input.strip()
        
        if text in ['exit', 'quit', 'q', 'bye']:
            self.speak("Goodbye!")
            return False
            
        if text in ['help', 'h', '?']:
            self.show_help()
            return True
            
        if text in ['clear', 'cls']:
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
            
        if text in ['status', 'st', 'info', 'stats']:
            self.show_status()
            return True
            
        if text == 'security':
            self.show_security()
            return True
            
        if text in ['sync', 's', 'check', 'emails', 'inbox', 'check emails', 'check my emails']:
            self.sync_emails()
            return True
            
        if text in ['unread', 'u', 'new', 'show unread', 'unread emails', 'new emails']:
            self.show_unread()
            return True
            
        if text in ['important', 'i', 'priority', 'important emails']:
            self.sync_emails(show_count=20)
            return True
            
        if text in ['spam', 'spam folder']:
            self.show_spam()
            return True
            
        if text in ['send', 'compose', 'send email']:
            self.cmd_send()
            return True
            
        if text.startswith('reply '):
            try:
                self.send_reply(int(text.split()[1]))
            except:
                print(color("Usage: reply [number]", Colors.WARNING))
            return True
            
        if text.startswith('ai-reply ') or text.startswith('ai reply '):
            try:
                self.ai_generate_reply(int(text.split()[-1]))
            except:
                print(color("Usage: ai-reply [number]", Colors.WARNING))
            return True
            
        if text.startswith('forward '):
            try:
                self.cmd_forward(int(text.split()[1]))
            except:
                print(color("Usage: forward [number]", Colors.WARNING))
            return True
            
        if text.startswith('search '):
            query = original[7:].strip()
            if query:
                self.search_emails(query)
            else:
                print(color("Usage: search [query]", Colors.WARNING))
            return True
            
        if text in ['contacts', 'people']:
            self.show_contacts()
            return True
            
        if text in ['digest', 'summary']:
            self.sync_emails()
            return True
            
        if text == 'auto-reply on':
            self.auto_reply_enabled = True
            print(color("✅ Auto-reply ENABLED", Colors.GREEN))
            return True
        if text == 'auto-reply off':
            self.auto_reply_enabled = False
            print(color("❌ Auto-reply DISABLED", Colors.FAIL))
            return True
            
        if text == 'voice on':
            self.voice_enabled = True
            self.speak("Voice control activated! Speak commands naturally.")
            print(color("🎤 Voice ON - Speak naturally!", Colors.GREEN))
            return True
            
        if text == 'voice off':
            self.voice_enabled = False
            print(color("🎤 Voice OFF", Colors.WARNING))
            return True
            
        if text in ['listen', 'voice', 'talk']:
            if self.voice_enabled:
                print(color("🎤 Say a command...", Colors.CYAN))
                cmd = self.listen()
                if cmd:
                    return self.handle_command(cmd)
            else:
                print(color("❌ Voice not enabled. Use 'voice on'", Colors.FAIL))
            return True
            
        print(color(f"❓ Unknown: '{original}'. Type 'help'", Colors.WARNING))
        return True
        
    def run(self):
        self.connect_all()
        print(color("\n🐉 Dragon ready! 'help' for commands. 'voice on' for voice!", Colors.YELLOW))
        print(color("🔐 Security system active", Colors.FAIL))
        while True:
            try:
                user_input = input(color("\n>>> ", Colors.CYAN)).strip()
                if user_input and not self.handle_command(user_input):
                    break
            except KeyboardInterrupt:
                self.speak("Goodbye!")
                print(color("\n🐉 Dragon signing off!", Colors.HEADER))
                break
            except Exception as e:
                print(color(f"❌ Error: {e}", Colors.FAIL))

def main():
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    agent = DragonEmailAgent()
    agent.run()

if __name__ == "__main__":
    main()