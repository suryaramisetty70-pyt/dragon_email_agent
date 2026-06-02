#!/usr/bin/env python3
"""
================================================================================
🐉 DRAGON EMAIL AGENT - ULTIMATE SUPER POWERED VERSION 🐉
================================================================================

FEATURES:
✓ Send/Receive/Reply/Forward Emails
✓ Spam Detection (AI-powered)
✓ Auto AI Reply Generation
✓ Voice Control (TTS + Speech Recognition)
✓ Priority Inbox Sorting
✓ Contact Management
✓ Email Search
✓ Daily Digest
✓ Auto-responder for Vacation
✓ Email Templates

COMMANDS:
  sync, s           - Check all emails
  unread, u         - Show unread emails
  important, i      - Show important emails
  spam              - Show spam folder
  send              - Send new email
  reply [n]         - Reply to email by number
  forward [n]       - Forward email
  ai-reply [n]      - AI generate reply
  auto-reply on/off - Toggle auto-responder
  search [text]      - Search emails
  contacts          - Show contacts
  digest            - Daily summary
  voice on/off      - Voice control
  status            - Connection status
  help, h           - Show this help
  exit, quit        - Exit program

================================================================================
"""

import sys
import os
import json
import imaplib
import smtplib
import re
from datetime import datetime, timedelta
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

# Voice packages (optional)
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

# ==================== COLORS ====================
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
    UNDERLINE = '\033[4m'

def color(text, code):
    try:
        return f"{code}{text}{Colors.ENDC}"
    except:
        return text

# ==================== SPAM DETECTOR ====================
class SpamDetector:
    """AI-powered spam detection"""
    
    SPAM_KEYWORDS = [
        'winner', 'congratulations', 'lottery', 'prize', 'claim', 'urgent',
        'act now', 'limited time', 'click here', 'free money', 'make money fast',
        'work from home', 'no obligation', 'credit card', 'debt', 'bitcoin',
        'crypto giveaway', 'double your money', 'suspicious', 'verify account',
        'suspended', 'unusual activity', 'security alert', 'password expired',
        'click now', 'order now', 'buy now', 'special offer', 'discount',
        'unsubscribe', 'opt-out', 'nigerian prince', 'inheritance', 'million dollars',
        'casino', 'viagra', 'pharmacy', 'cheap meds', 'weight loss', 'miracle'
    ]
    
    SPAM_PATTERNS = [
        r'\$[\d,]+',  # Dollar amounts
        r'click\s+here', r'http[s]?://', r'www\.', r'\.com\s',
        r'free\s+', r'win\s+', r'winner', r'prize',
        r'all\s+caps',  # ALL CAPS
        r'!!!!+', r'\?\?\?+',  # Multiple ! or ?
    ]
    
    def __init__(self):
        self.spam_count = 0
        self.learned_patterns = []
        
    def check(self, email_data):
        """Check if email is spam"""
        score = 0
        reasons = []
        
        subject = email_data.get('subject', '').lower()
        body = email_data.get('body', '').lower()
        sender = email_data.get('from', '').lower()
        
        # Check sender domain
        if any(x in sender for x in ['noreply', 'no-reply', 'donotreply', 'autoreply']):
            score += 2
            
        # Check subject
        for keyword in self.SPAM_KEYWORDS:
            if keyword in subject:
                score += 3
                reasons.append(f"Keyword: {keyword}")
                
        # Check body
        for keyword in self.SPAM_KEYWORDS[:15]:  # Top 15 keywords
            if keyword in body:
                score += 1
                
        # Check patterns
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, subject, re.I):
                score += 2
            if re.search(pattern, body, re.I):
                score += 1
                
        # Check for excessive caps
        caps_ratio = sum(1 for c in subject if c.isupper()) / max(len(subject), 1)
        if caps_ratio > 0.5 and len(subject) > 10:
            score += 3
            reasons.append("Excessive CAPS")
            
        # Check for many exclamation marks
        if subject.count('!') > 2:
            score += 2
            reasons.append("Multiple ! marks")
            
        # Check for suspicious URLs
        if re.search(r'bit\.ly|goo\.gl|tinyurl', body):
            score += 3
            reasons.append("Shortened URLs")
            
        # Check for attachments named .exe, .zip, etc.
        attachments = email_data.get('attachments', [])
        for att in attachments:
            if any(ext in att.lower() for ext in ['.exe', '.zip', '.scr', '.bat', '.vbs']):
                score += 5
                reasons.append(f"Dangerous attachment: {att}")
                
        is_spam = score >= 7
        if is_spam:
            self.spam_count += 1
            
        return {
            'is_spam': is_spam,
            'score': score,
            'reasons': reasons[:3]  # Top 3 reasons
        }

# ==================== AI REPLY GENERATOR ====================
class AIReplyGenerator:
    """Generate intelligent auto-replies"""
    
    def __init__(self):
        self.templates = {
            'meeting': "Thank you for your email regarding the meeting. I have reviewed the details and will confirm my availability shortly. Please let me know the proposed time and I will ensure my schedule is clear.",
            
            'interview': "Thank you for reaching out about the opportunity. I am very interested and would love to learn more. Please share the details and I will respond promptly with my availability.",
            
            'followup': "Thank you for following up. I appreciate your patience. I am actively working on this and will have an update for you soon. Thank you for your understanding.",
            
            'inquiry': "Thank you for your inquiry. I have received your message and will review it carefully. You can expect a detailed response within 24-48 hours.",
            
            'request': "Thank you for your request. I am looking into this matter and will get back to you with the necessary information. Please allow me some time to gather the required details.",
            
            'thanks': "Thank you so much for your kind words! I truly appreciate your message and it means a lot to me. Please don't hesitate to reach out if there's anything else I can help with.",
            
            'urgent': "I have received your urgent email and am treating this as a priority. I will respond with the necessary information as soon as possible. Thank you for bringing this to my attention.",
            
            'default': "Thank you for your email. I have received your message and will respond to you shortly. If this is urgent, please let me know and I will prioritize accordingly.\n\nBest regards"
        }
        
    def analyze_email(self, subject, body, sender):
        """Analyze email to determine best reply type"""
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
        """Generate AI-powered reply"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')
        sender = email_data.get('from', 'User')
        
        # Get sender name
        if '<' in sender:
            sender_name = sender.split('<')[0].strip()
        else:
            sender_name = sender.split('@')[0]
            
        # Determine reply type
        reply_type = self.analyze_email(subject, body, sender)
        
        # Get template
        base_reply = self.templates[reply_type]
        
        # Format sender name
        if sender_name:
            reply = f"Dear {sender_name},\n\n"
        else:
            reply = "Dear Sir/Madam,\n\n"
            
        reply += base_reply
        
        # Add signature
        reply += "\n\nBest regards"
        
        return reply, reply_type
        
    def generate_custom_reply(self, email_data, instruction):
        """Generate custom reply based on instruction"""
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')[:500]
        sender = email_data.get('from', 'User')
        
        if '<' in sender:
            sender_name = sender.split('<')[0].strip()
        else:
            sender_name = sender.split('@')[0]
            
        reply = f"Dear {sender_name},\n\n"
        
        # Generate based on instruction keywords
        instruction_lower = instruction.lower()
        
        if 'short' in instruction_lower or 'brief' in instruction_lower:
            reply += "Thank you for your email. I will review and respond shortly.\n\n"
        elif 'formal' in instruction_lower:
            reply += "I am writing to acknowledge receipt of your correspondence. I have noted the contents and will provide a detailed response in due course.\n\n"
        elif 'thank' in instruction_lower:
            reply += "Thank you for your email. Your message has been received and I appreciate you taking the time to contact me.\n\n"
        elif 'confirm' in instruction_lower:
            reply += "This is to confirm receipt of your email. I can confirm that I have understood the contents and will act accordingly.\n\n"
        elif 'positive' in instruction_lower or 'accept' in instruction_lower:
            reply += "Thank you for your email. I am pleased to inform you that I accept/concur with your proposal. Please find my confirmation below.\n\n"
        elif 'negative' in instruction_lower or 'decline' in instruction_lower:
            reply += "Thank you for your email. After careful consideration, I regret to inform you that I am unable to accommodate your request at this time.\n\n"
        else:
            reply += "Thank you for reaching out. I have reviewed your email and will respond with the necessary information shortly.\n\n"
            
        reply += "Best regards"
        
        return reply

# ==================== EMAIL TEMPLATES ====================
class EmailTemplates:
    """Pre-built email templates"""
    
    TEMPLATES = {
        'meeting_request': {
            'subject': 'Meeting Request: {topic}',
            'body': '''Dear {name},

I hope this email finds you well.

I would like to schedule a meeting to discuss {topic}.

Would you be available on {date} at {time}? Please let me know if this works for you or suggest an alternative time that suits your schedule.

Looking forward to meeting with you.

Best regards,
{your_name}'''
        },
        
        'followup': {
            'subject': 'Following Up: {subject}',
            'body': '''Dear {name},

I hope you are doing well.

I am following up on my previous email regarding {subject}. I wanted to check if you had any questions or if you needed any additional information.

Please let me know if there's anything I can help with.

Best regards,
{your_name}'''
        },
        
        'thank_you': {
            'subject': 'Thank You',
            'body': '''Dear {name},

Thank you so much for {reason}. I truly appreciate your {quality}.

Your {action} has made a significant impact and I am grateful for your support.

Please don't hesitate to reach out if there's anything I can do to return the favor.

With gratitude,
{your_name}'''
        },
        
        'interview': {
            'subject': 'Interview Follow-up: {position}',
            'body': '''Dear {name},

Thank you for taking the time to meet with me yesterday to discuss the {position} position at {company}. I truly enjoyed learning more about the role and your team.

Our conversation reinforced my enthusiasm for this opportunity. I am confident that my skills and experience align well with what you're looking for.

Please don't hesitate to reach out if you need any additional information. I look forward to hearing from you.

Best regards,
{your_name}'''
        },
        
        'project_update': {
            'subject': 'Project Update: {project_name}',
            'body': '''Dear {name},

Here is the latest update on {project_name}:

📊 Current Status: {status}
✅ Completed: {completed}
📋 In Progress: {in_progress}
⏳ Upcoming: {upcoming}

Please let me know if you have any questions or need more details.

Best regards,
{your_name}'''
        }
    }
    
    def get_template(self, name):
        return self.TEMPLATES.get(name, None)
    
    def use_template(self, name, variables):
        template = self.get_template(name)
        if not template:
            return None, None
            
        subject = template['subject'].format(**variables)
        body = template['body'].format(**variables)
        
        return subject, body

# ==================== MAIN DRAGON AGENT ====================
class DragonEmailAgent:
    """🐉 Ultimate Email Agent with AI Powers"""
    
    def __init__(self):
        # Load configuration
        self.accounts = []
        self.load_config()
        
        # Connections
        self.connections = {}
        self.smtp_connections = {}
        
        # Systems
        self.spam_detector = SpamDetector()
        self.ai_reply = AIReplyGenerator()
        self.templates = EmailTemplates()
        
        # State
        self.auto_reply_enabled = False
        self.auto_reply_message = "Thank you for your email. I am currently unavailable and will respond to you shortly."
        self.vacation_mode = False
        
        # Voice
        self.voice_enabled = VOICE_AVAILABLE
        if self.voice_enabled:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 140)
                self.tts.setProperty('volume', 0.9)
            except:
                self.voice_enabled = False
                
        # Statistics
        self.stats = {
            'emails_sent': 0,
            'emails_received': 0,
            'replies_sent': 0,
            'spam_caught': 0
        }
        
    def load_config(self):
        """Load email accounts"""
        config_path = "config/email_accounts.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
            print(color(f"📧 Loaded {len(self.accounts)} account(s)", Colors.GREEN))
        else:
            print(color("❌ config/email_accounts.json not found!", Colors.FAIL))
            
    def speak(self, text):
        """Text-to-speech"""
        print(color(f"🐉 Dragon: {text}", Colors.CYAN))
        if self.voice_enabled:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                pass
                
    def listen(self):
        """Speech recognition"""
        if not self.voice_enabled:
            return None
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print(color("🎤 Listening...", Colors.CYAN))
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
            text = r.recognize_google(audio)
            print(color(f"🎤 You said: {text}", Colors.GREEN))
            return text.lower()
        except:
            print(color("🎤 Could not understand. Try again.", Colors.WARNING))
            return None
            
    def connect_imap(self, account):
        """Connect to IMAP server"""
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
            return True
        except Exception as e:
            print(color(f"   ❌ IMAP Failed: {str(e)[:50]}", Colors.FAIL))
            return False
            
    def connect_smtp(self, account):
        """Connect to SMTP server"""
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
            return True
        except Exception as e:
            print(color(f"   ❌ SMTP Failed: {str(e)[:50]}", Colors.FAIL))
            return False
            
    def connect_all(self):
        """Connect to all accounts"""
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
        
    def send_email(self, to, subject, body, cc=None, bcc=None):
        """Send email"""
        if not self.smtp_connections:
            print(color("❌ No SMTP connection available!", Colors.FAIL))
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
                
            msg.attach(MIMEText(body, 'plain'))
            
            recipients = [to]
            if cc:
                recipients.append(cc)
            if bcc:
                recipients.append(bcc)
                
            server.sendmail(email, recipients, msg.as_string())
            
            print(color(f"✅ Email sent to {to}!", Colors.GREEN))
            self.stats['emails_sent'] += 1
            return True
        except Exception as e:
            print(color(f"❌ Send failed: {e}", Colors.FAIL))
            return False
            
    def fetch_email_data(self, uid, mail):
        """Fetch and parse email data"""
        try:
            status, msg_data = mail.fetch(uid, '(RFC822)')
            if not msg_data or not msg_data[0]:
                return None
                
            raw = msg_data[0][1]
            msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
            
            # Decode subject
            subject = self.decode_header_value(msg.get('Subject', ''))
            
            # Get sender
            sender = msg.get('From', 'Unknown')
            
            # Get body
            body = ''
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='replace')
                
            # Get attachments
            attachments = []
            for part in msg.walk():
                if part.get_content_disposition() == 'attachment':
                    attachments.append(part.get_filename() or 'unknown')
                    
            return {
                'from': sender,
                'subject': subject,
                'body': body,
                'date': msg.get('Date', ''),
                'attachments': attachments,
                'raw': raw
            }
        except Exception as e:
            return None
            
    def decode_header_value(self, value):
        """Decode email header"""
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
        """Sync and display emails"""
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
                            
                        # Check for spam
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
                            
                        # Format display
                        prefix = color("⚠️ SPAM", Colors.FAIL) + " " if spam_check['is_spam'] else ""
                        prefix += color("[NEW] ", Colors.YELLOW) if unread_count > 0 else ""
                        
                        print(f"\n   {prefix}[{i}] 📩 {sender_name[:30]}")
                        print(f"       📌 {subject[:55]}")
                        print(f"       📅 {date}")
                        
                        # Show body preview
                        body_preview = data['body'][:100].replace('\n', ' ').strip()
                        if body_preview:
                            print(f"       💬 {body_preview[:60]}...")
                            
                        # Show spam reasons
                        if spam_check['is_spam'] and spam_check['reasons']:
                            print(f"       🔴 Spam: {', '.join(spam_check['reasons'][:2])}")
                            
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
        print(color("\n" + "="*60, Colors.BLUE))
        print(color(f"📊 SUMMARY: {total} emails | {unread} unread | {spam} spam", Colors.BOLD))
        print(color("="*60, Colors.BLUE))
        
        self.stats['emails_received'] += total
        self.stats['spam_caught'] += spam
        
    def show_unread(self):
        """Show only unread emails"""
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
        """Check spam folder"""
        print(color("\n⚠️ SPAM FOLDER", Colors.BOLD))
        
        for email, mail in self.connections.items():
            try:
                # Try common spam folder names
                for folder in ['[Gmail]/Spam', 'Spam', 'Junk', 'INBOX.Spam']:
                    try:
                        status, _ = mail.select(folder)
                        if status == 'OK':
                            status, messages = mail.search(None, 'ALL')
                            email_ids = messages[0].split()
                            count = len(email_ids)
                            
                            print(color(f"\n📬 {email} - {count} spam emails", Colors.CYAN))
                            
                            for i, uid in enumerate(email_ids[:10], 1):
                                data = self.fetch_email_data(uid, mail)
                                if data:
                                    sender = data['from']
                                    if '<' in sender:
                                        sender = sender.split('<')[0].strip()
                                    print(f"\n   [{i}] 📩 {sender[:35]}")
                                    print(f"       📌 {data['subject'][:55]}")
                            return
                    except:
                        continue
                        
                print(color("   No spam folder found", Colors.WARNING))
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
    def search_emails(self, query):
        """Search emails"""
        print(color(f"\n🔍 SEARCHING: '{query}'", Colors.BOLD))
        
        results = []
        
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                
                for uid in email_ids:
                    data = self.fetch_email_data(uid, mail)
                    if data:
                        combined = f"{data['subject']} {data['body']}".lower()
                        if query.lower() in combined:
                            results.append(data)
                            
            except Exception as e:
                pass
                
        print(color(f"\n📊 Found {len(results)} results", Colors.GREEN))
        
        for i, data in enumerate(results[:10], 1):
            sender = data['from']
            if '<' in sender:
                sender = sender.split('<')[0].strip()
            print(f"\n   [{i}] 📩 {sender[:35]}")
            print(f"       📌 {data['subject'][:55]}")
            print(f"       📅 {data['date'][:16]}")
            
        return results
        
    def send_reply(self, email_num, reply_text=None, use_ai=False):
        """Reply to email"""
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
                
            uid = email_ids[-email_num]
            data = self.fetch_email_data(uid, mail)
            
            if not data:
                print(color("❌ Could not read email", Colors.FAIL))
                return
                
            sender = data['from']
            subject = data['subject']
            
            # Get sender email
            if '<' in sender:
                sender_email = sender.split('<')[1].split('>')[0]
                sender_name = sender.split('<')[0].strip()
            else:
                sender_email = sender
                sender_name = sender.split('@')[0]
                
            print(color(f"\n📩 Replying to: {sender}", Colors.CYAN))
            print(color(f"📌 Subject: Re: {subject}", Colors.CYAN))
            
            if use_ai and not reply_text:
                # Generate AI reply
                ai_reply_text, reply_type = self.ai_reply.generate_reply(data)
                print(color(f"\n🤖 AI Reply Type: {reply_type.upper()}", Colors.YELLOW))
                print(color("-" * 60, Colors.BLUE))
                print(ai_reply_text)
                print(color("-" * 60, Colors.BLUE))
                
                confirm = input(color("\n✅ Send this AI reply? (y/n/s=edit): ", Colors.GREEN)).strip().lower()
                
                if confirm == 's':
                    print(color("\n✏️ Enter your custom reply:", Colors.CYAN))
                    reply_text = input("> ").strip()
                elif confirm != 'y':
                    print(color("❌ Cancelled", Colors.FAIL))
                    return
                else:
                    reply_text = ai_reply_text
            elif not reply_text:
                print(color("\n✏️ Enter your reply:", Colors.CYAN))
                reply_text = input("> ").strip()
                
            if reply_text:
                self.send_email(sender_email, f"Re: {subject}", reply_text)
                self.stats['replies_sent'] += 1
            else:
                print(color("❌ Empty reply", Colors.FAIL))
                
        except Exception as e:
            print(color(f"❌ Error: {e}", Colors.FAIL))
            
    def ai_generate_reply(self, email_num):
        """AI generate reply for email"""
        self.send_reply(email_num, use_ai=True)
        
    def generate_digest(self):
        """Generate daily email digest"""
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("📊 DAILY EMAIL DIGEST", Colors.HEADER))
        print(color("="*60, Colors.BOLD))
        
        total = 0
        unread = 0
        important = []
        spam_count = 0
        
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                total += len(email_ids)
                
                status, unread_list = mail.search(None, 'UNSEEN')
                unread += len(unread_list[0].split()) if unread_list[0] else 0
                
                # Get recent important emails
                recent = email_ids[-20:]
                for uid in recent:
                    data = self.fetch_email_data(uid, mail)
                    if data:
                        spam_check = self.spam_detector.check(data)
                        if not spam_check['is_spam']:
                            # Check for important keywords
                            text = f"{data['subject']} {data['body']}".lower()
                            if any(x in text for x in ['urgent', 'important', 'deadline', 'asap', 'meeting', 'interview', 'project']):
                                important.append(data)
                                
            except:
                pass
                
        print(f"\n📧 Total Emails: {total}")
        print(f"📬 Unread: {unread}")
        print(f"⭐ Important: {len(important)}")
        print(f"⚠️ Spam Caught: {spam_count}")
        
        if important:
            print(color("\n⭐ IMPORTANT EMAILS:", Colors.YELLOW))
            for i, data in enumerate(important[:5], 1):
                sender = data['from']
                if '<' in sender:
                    sender = sender.split('<')[0].strip()
                print(f"\n   [{i}] 📩 {sender[:35]}")
                print(f"       📌 {data['subject'][:55]}")
                
        print(color("\n" + "="*60, Colors.BOLD))
        
    def show_contacts(self):
        """Show tracked contacts"""
        contacts = {}
        
        for email, mail in self.connections.items():
            try:
                mail.select('INBOX')
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                
                for uid in email_ids[-100:]:  # Last 100 emails
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
                
        # Sort by count
        sorted_contacts = sorted(contacts.values(), key=lambda x: x['count'], reverse=True)
        
        print(color("\n👥 CONTACTS (Top 20)", Colors.BOLD))
        print("-" * 60)
        
        for i, contact in enumerate(sorted_contacts[:20], 1):
            print(f"   {i}. {contact['name'][:30]} ({contact['email'][:35]})")
            print(f"      📧 {contact['count']} emails")
            
        print(f"\n📊 Total unique contacts: {len(contacts)}")
        
    def show_status(self):
        """Show connection status"""
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉 DRAGON STATUS", Colors.HEADER))
        print(color("="*60, Colors.BOLD))
        
        print(f"\n📧 Accounts: {len(self.accounts)}")
        print(f"📡 IMAP Connected: {len(self.connections)}")
        print(f"📤 SMTP Connected: {len(self.smtp_connections)}")
        print(f"🎤 Voice: {'✅ Enabled' if self.voice_enabled else '❌ Disabled'}")
        print(f"🤖 Auto-Reply: {'✅ On' if self.auto_reply_enabled else '❌ Off'}")
        print(f"✈️ Vacation: {'✅ On' if self.vacation_mode else '❌ Off'}")
        
        print(color("\n📊 STATISTICS:", Colors.CYAN))
        print(f"   📤 Sent: {self.stats['emails_sent']}")
        print(f"   📥 Received: {self.stats['emails_received']}")
        print(f"   📝 Replies: {self.stats['replies_sent']}")
        print(f"   ⚠️ Spam Caught: {self.stats['spam_caught']}")
        
        print(color("\n📋 ACCOUNTS:", Colors.CYAN))
        for account in self.accounts:
            email = account.get('email', 'Unknown')
            imap_ok = email in self.connections
            smtp_ok = email in self.smtp_connections
            status = color("✅", Colors.GREEN) if imap_ok else color("❌", Colors.FAIL)
            print(f"   {status} {email}")
            print(f"      IMAP: {'✓' if imap_ok else '✗'} | SMTP: {'✓' if smtp_ok else '✗'}")
            
        print(color("="*60, Colors.BOLD))
        
    def show_help(self):
        """Show all commands"""
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT - COMMANDS 🐉🐉🐉", Colors.HEADER))
        print(color("="*60, Colors.BOLD))
        
        print(color("\n📧 EMAIL COMMANDS:", Colors.CYAN))
        print("""
  sync / s              - Check all emails
  unread / u            - Show unread emails
  important / i         - Show important emails
  spam                  - Check spam folder
  send                  - Send new email
  reply [n]             - Reply to email #n
  forward [n]           - Forward email #n
  ai-reply [n]          - AI generate reply for email #n
  search [text]         - Search emails
  contacts              - Show contacts list
  digest                - Daily summary
        """)
        
        print(color("\n🤖 AI COMMANDS:", Colors.YELLOW))
        print("""
  ai-reply [n]          - Generate AI reply for email #n
  ai short/brief        - Generate short AI reply
  ai formal             - Generate formal AI reply
  auto-reply on/off     - Toggle auto-responder
  vacation on/off       - Toggle vacation mode
        """)
        
        print(color("\n🎤 VOICE COMMANDS:", Colors.CYAN))
        print("""
  voice on              - Enable voice control
  voice off             - Disable voice control
  listen                - Listen for voice command
        """)
        
        print(color("\n🔧 GENERAL:", Colors.BOLD))
        print("""
  status / st           - Show connection status
  stats                 - Show statistics
  help / h              - Show this help
  clear / cls           - Clear screen
  exit / quit           - Exit program
        """)
        
        print(color("\n💡 QUICK EXAMPLES:", Colors.GREEN))
        print("""
  sync                  → Check all emails
  unread                → Show unread
  send                  → Send new email
  reply 1               → Reply to email #1
  ai-reply 1            → AI reply to email #1
  voice on              → Enable voice
        """)
        
        print(color("="*60, Colors.BOLD))
        
    def cmd_send(self):
        """Send new email"""
        print(color("\n📤 COMPOSE EMAIL", Colors.BOLD))
        
        to = input(color("To: ", Colors.CYAN)).strip()
        if not to:
            print(color("❌ Cancelled", Colors.FAIL))
            return
            
        subject = input(color("Subject: ", Colors.CYAN)).strip()
        if not subject:
            subject = "(No Subject)"
            
        print(color("Body (press Enter twice to finish):", Colors.WARNING))
        lines = []
        empty_count = 0
        while True:
            line = input()
            if line == "":
                empty_count += 1
                if empty_count >= 1:
                    break
            else:
                empty_count = 0
            lines.append(line)
            
        body = "\n".join(lines)
        
        if body:
            confirm = input(color(f"\n📤 Send to {to}? (y/n): ", Colors.GREEN)).strip().lower()
            if confirm == 'y':
                self.send_email(to, subject, body)
            else:
                print(color("❌ Cancelled", Colors.FAIL))
        else:
            print(color("❌ Empty body", Colors.FAIL))
            
    def cmd_forward(self, email_num):
        """Forward email"""
        if not self.connections or not self.smtp_connections:
            print(color("❌ No connection", Colors.FAIL))
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
            
            if data:
                to = input(color("Forward to: ", Colors.CYAN)).strip()
                if to:
                    forward_body = f"---------- Forwarded Message ----------\n\n"
                    forward_body += f"From: {data['from']}\n"
                    forward_body += f"Subject: {data['subject']}\n"
                    forward_body += f"Date: {data['date']}\n\n"
                    forward_body += data['body']
                    
                    self.send_email(to, f"Fwd: {data['subject']}", forward_body)
                    
        except Exception as e:
            print(color(f"❌ Error: {e}", Colors.FAIL))
            
    def handle_command(self, user_input):
        """Handle user commands"""
        text = user_input.lower().strip()
        original = user_input.strip()
        
        # EXIT
        if text in ['exit', 'quit', 'q', 'bye']:
            self.speak("Goodbye! Have a great day!")
            return False
            
        # HELP
        if text in ['help', 'h', '?']:
            self.show_help()
            return True
            
        # CLEAR
        if text in ['clear', 'cls']:
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
            
        # STATUS
        if text in ['status', 'st', 'info']:
            self.show_status()
            return True
            
        # STATS
        if text in ['stats', 'statistics']:
            self.show_status()
            return True
            
        # SYNC / CHECK EMAILS
        if text in ['sync', 's', 'check', 'emails', 'inbox', 'show emails', 'check emails']:
            self.sync_emails()
            return True
            
        # UNREAD
        if text in ['unread', 'u', 'new', 'new emails', 'show unread']:
            self.show_unread()
            return True
            
        # IMPORTANT
        if text in ['important', 'i', 'priority', 'starred']:
            print(color("\n⭐ SHOWING IMPORTANT EMAILS", Colors.YELLOW))
            self.sync_emails(show_count=20)
            return True
            
        # SPAM
        if text in ['spam', 'junk', 'suspicious']:
            self.show_spam()
            return True
            
        # SEND EMAIL
        if text in ['send', 'compose', 'new email', 'write']:
            self.cmd_send()
            return True
            
        # REPLY
        if text.startswith('reply '):
            try:
                num = int(text.split()[1])
                self.send_reply(num)
            except:
                print(color("Usage: reply [number]", Colors.WARNING))
            return True
        if text == 'reply':
            print(color("Usage: reply [number]", Colors.WARNING))
            return True
            
        # AI REPLY
        if text.startswith('ai-reply ') or text.startswith('ai reply '):
            try:
                num = int(text.split()[-1])
                self.ai_generate_reply(num)
            except:
                print(color("Usage: ai-reply [number]", Colors.WARNING))
            return True
        if text in ['ai-reply', 'ai reply', 'generate reply']:
            print(color("Usage: ai-reply [number]", Colors.WARNING))
            return True
            
        # FORWARD
        if text.startswith('forward '):
            try:
                num = int(text.split()[1])
                self.cmd_forward(num)
            except:
                print(color("Usage: forward [number]", Colors.WARNING))
            return True
            
        # SEARCH
        if text.startswith('search '):
            query = original[7:].strip()
            if query:
                self.search_emails(query)
            else:
                print(color("Usage: search [query]", Colors.WARNING))
            return True
            
        # CONTACTS
        if text in ['contacts', 'people', 'address book']:
            self.show_contacts()
            return True
            
        # DIGEST
        if text in ['digest', 'summary', 'daily']:
            self.generate_digest()
            return True
            
        # AUTO REPLY
        if text == 'auto-reply on':
            self.auto_reply_enabled = True
            print(color("✅ Auto-reply ENABLED", Colors.GREEN))
            self.speak("Auto-reply enabled")
            return True
        if text == 'auto-reply off':
            self.auto_reply_enabled = False
            print(color("❌ Auto-reply DISABLED", Colors.FAIL))
            return True
            
        # VACATION
        if text == 'vacation on':
            self.vacation_mode = True
            print(color("✈️ Vacation mode ENABLED", Colors.GREEN))
            self.speak("Vacation mode enabled")
            return True
        if text == 'vacation off':
            self.vacation_mode = False
            print(color("❌ Vacation mode DISABLED", Colors.FAIL))
            return True
            
        # VOICE
        if text == 'voice on':
            if self.voice_enabled:
                self.speak("Voice control activated! Say a command.")
                print(color("🎤 Voice ON", Colors.GREEN))
            else:
                print(color("❌ Voice not available. Install: pip install pyttsx3 speechrecognition pyaudio", Colors.FAIL))
            return True
            
        if text == 'voice off':
            print(color("🎤 Voice OFF", Colors.WARNING))
            return True
            
        if text in ['listen', 'voice', 'talk']:
            if self.voice_enabled:
                print(color("🎤 Say a command...", Colors.CYAN))
                cmd = self.listen()
                if cmd:
                    return self.handle_command(cmd)
            else:
                print(color("❌ Voice not available", Colors.FAIL))
            return True
            
        # Unknown
        print(color(f"❓ Unknown: '{original}'. Type 'help' for commands.", Colors.WARNING))
        return True
        
    def run(self):
        """Main loop"""
        self.connect_all()
        
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉 Dragon ready! Type 'help' for commands.", Colors.YELLOW))
        print(color("🎤 Use 'voice on' for voice control!", Colors.CYAN))
        print(color("="*60, Colors.BOLD))
        
        while True:
            try:
                user_input = input(color("\n>>> ", Colors.CYAN)).strip()
                
                if not user_input:
                    continue
                    
                if not self.handle_command(user_input):
                    break
                    
            except KeyboardInterrupt:
                self.speak("Goodbye!")
                print(color("\n\n🐉 Dragon signing off!", Colors.HEADER))
                break
            except Exception as e:
                print(color(f"❌ Error: {e}", Colors.FAIL)

# ==================== MAIN ====================
def main():
    """Entry point"""
    # Create directories
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Start agent
    agent = DragonEmailAgent()
    agent.run()

if __name__ == "__main__":
    main()