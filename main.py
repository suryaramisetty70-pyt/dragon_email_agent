#!/usr/bin/env python3
"""
🐉 DRAGON EMAIL AGENT - ULTIMATE VERSION
Features: Send, Receive, Reply, Voice Control, AI Assistant

Dependencies:
pip install loguru pyttsx3 speechrecognition pyaudio
"""

import sys
import os
import json
import imaplib
import smtplib
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Voice packages (optional - will work without them)
try:
    import pyttsx3
    import speech_recognition as sr
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def color(text, code):
    try:
        return f"{code}{text}{Colors.ENDC}"
    except:
        return text

class DragonEmailAgent:
    def __init__(self):
        self.accounts = []
        self.load_config()
        self.connections = {}
        self.smtp_connections = {}
        
        # Initialize voice if available
        self.voice_enabled = VOICE_AVAILABLE
        if self.voice_enabled:
            try:
                self.tts = pyttsx3.init()
                self.tts.setProperty('rate', 150)
            except:
                self.voice_enabled = False
        
    def load_config(self):
        config_path = "config/email_accounts.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
                print(color(f"📧 Loaded {len(self.accounts)} accounts", Colors.GREEN))
        else:
            print(color("❌ config/email_accounts.json not found!", Colors.FAIL))
            
    def speak(self, text):
        """Speak text using TTS"""
        if self.voice_enabled:
            print(color(f"🐉 Dragon: {text}", Colors.CYAN))
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except:
                pass
        else:
            print(color(f"🐉 Dragon: {text}", Colors.CYAN))
            
    def listen(self):
        """Listen for voice command"""
        if not self.voice_enabled:
            print(color("🎤 Voice not available. Install: pip install pyttsx3 speechrecognition pyaudio", Colors.WARNING))
            return None
            
        try:
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print(color("🎤 Listening...", Colors.CYAN))
                audio = r.listen(source, timeout=5)
            
            text = r.recognize_google(audio)
            print(color(f"🎤 You said: {text}", Colors.GREEN))
            return text.lower()
        except Exception as e:
            print(color(f"🎤 Could not understand: {e}", Colors.WARNING))
            return None
            
    def connect_imap(self, account):
        """Connect to IMAP (receiving emails)"""
        email = account.get('email', '')
        password = account.get('password', '')
        imap_host = account.get('imap_host', '')
        imap_port = account.get('imap_port', 993)
        
        print(color(f"\n📡 Connecting to IMAP: {email}", Colors.CYAN))
        
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=20)
            mail.login(email, password)
            self.connections[email] = mail
            print(color(f"✅ IMAP Connected!", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"❌ IMAP Failed: {e}", Colors.FAIL))
            return False
            
    def connect_smtp(self, account):
        """Connect to SMTP (sending emails)"""
        email = account.get('email', '')
        password = account.get('password', '')
        smtp_host = account.get('smtp_host', '')
        smtp_port = account.get('smtp_port', 587)
        
        print(color(f"📤 Connecting to SMTP: {email}", Colors.CYAN))
        
        try:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()
            server.login(email, password)
            self.smtp_connections[email] = server
            print(color(f"✅ SMTP Connected!", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"❌ SMTP Failed: {e}", Colors.FAIL))
            return False
            
    def connect_all(self):
        """Connect to all accounts (IMAP + SMTP)"""
        print(color("\n" + "="*50, Colors.BOLD))
        print(color("🐉 DRAGON EMAIL AGENT - CONNECTING", Colors.HEADER))
        print(color("="*50, Colors.BOLD))
        
        connected = 0
        for account in self.accounts:
            if account.get('is_active', True):
                imap_ok = self.connect_imap(account)
                smtp_ok = self.connect_smtp(account)
                if imap_ok or smtp_ok:
                    connected += 1
                    
        print(color(f"\n✅ Connected: {connected}/{len(self.accounts)} accounts", Colors.GREEN))
        
    def send_email(self, to, subject, body, cc=None):
        """Send an email"""
        if not self.smtp_connections:
            print(color("❌ No SMTP connection available!", Colors.FAIL))
            return False
            
        # Use first available SMTP connection
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
            
            server.sendmail(email, [to] + ([cc] if cc else []), msg.as_string())
            print(color(f"✅ Email sent to {to}!", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"❌ Send failed: {e}", Colors.FAIL))
            return False
            
    def send_reply(self, original_email, reply_text):
        """Reply to an email"""
        # Get sender from original email
        from_email = original_email.get('from', '')
        # Extract email address
        if '<' in from_email:
            sender_email = from_email.split('<')[1].split('>')[0]
        else:
            sender_email = from_email
            
        subject = original_email.get('subject', '')
        if not subject.startswith('Re:'):
            subject = f"Re: {subject}"
            
        return self.send_email(sender_email, subject, reply_text)
        
    def generate_reply(self, email_data, user_instruction):
        """AI-generated reply based on instruction"""
        sender = email_data.get('from', 'Unknown')
        subject = email_data.get('subject', '')
        body = email_data.get('body', '')[:500]  # First 500 chars
        
        # Simple AI-style response generation
        reply = f"Dear {sender.split('<')[0].strip() if '<' in sender else sender},\n\n"
        
        if 'meeting' in user_instruction.lower():
            reply += "Thank you for your email regarding the meeting. I will review the details and get back to you shortly.\n\n"
        elif 'follow up' in user_instruction.lower():
            reply += "Following up on our previous conversation. I wanted to check if you need any additional information.\n\n"
        elif 'thanks' in user_instruction.lower() or 'thank' in user_instruction.lower():
            reply += "Thank you for your email. I appreciate your message and will respond accordingly.\n\n"
        else:
            reply += "Thank you for reaching out. I have received your email and will respond shortly.\n\n"
        
        reply += f"Original Subject: {subject}\n\n"
        reply += "Best regards,\n[Your Name]"
        
        return reply
        
    def sync_emails(self, show_count=10):
        """Show emails from all accounts"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("📧 SYNCING EMAILS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        total_emails = 0
        total_unread = 0
        
        for email, mail in self.connections.items():
            try:
                print(color(f"\n📬 {email}", Colors.CYAN))
                mail.select('INBOX')
                
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                count = len(email_ids)
                
                status, unread_data = mail.search(None, 'UNSEEN')
                unread_count = len(unread_data[0].split()) if unread_data[0] else 0
                
                print(color(f"   📊 Total: {count} | Unread: {unread_count}", Colors.WARNING))
                total_emails += count
                total_unread += unread_count
                
                if count > 0:
                    recent = email_ids[-show_count:]
                    print(color("\n   📬 Recent emails:", Colors.GREEN))
                    print("-" * 50)
                    
                    for i, uid in enumerate(recent, 1):
                        try:
                            status, msg_data = mail.fetch(uid, '(RFC822)')
                            if msg_data and msg_data[0]:
                                raw = msg_data[0][1]
                                msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
                                
                                sender = msg.get('From', 'Unknown')
                                subject = msg.get('Subject', '(No Subject)') or '(No Subject)'
                                date = msg.get('Date', '')[:16]
                                body_preview = msg.get_body().get_content()[:100] if msg.get_body() else ''
                                
                                if '<' in sender:
                                    sender = sender.split('<')[0].strip()
                                    
                                print(f"\n   [{i}] 📩 {sender[:30]}")
                                print(f"       📌 {subject[:50]}")
                                print(f"       📅 {date}")
                                print(f"       💬 {body_preview[:80]}...")
                                
                        except Exception as e:
                            pass
                            
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
        print(color("\n" + "="*50, Colors.BLUE))
        print(color(f"📊 TOTAL: {total_emails} emails | {total_unread} unread", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
    def show_unread(self):
        """Show only unread emails"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("📬 UNREAD EMAILS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        for email, mail in self.connections.items():
            try:
                print(color(f"\n📬 {email}", Colors.CYAN))
                mail.select('INBOX')
                
                status, messages = mail.search(None, 'UNSEEN')
                email_ids = messages[0].split()
                count = len(email_ids)
                
                if count == 0:
                    print(color("   ✅ No unread emails!", Colors.GREEN))
                else:
                    print(color(f"   📊 Unread: {count}", Colors.WARNING))
                    
                    for i, uid in enumerate(email_ids[:15], 1):
                        try:
                            status, msg_data = mail.fetch(uid, '(RFC822)')
                            if msg_data and msg_data[0]:
                                raw = msg_data[0][1]
                                msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
                                
                                sender = msg.get('From', 'Unknown')
                                subject = msg.get('Subject', '(No Subject)') or '(No Subject)'
                                date = msg.get('Date', '')[:16]
                                
                                if '<' in sender:
                                    sender = sender.split('<')[0].strip()
                                    
                                print(f"\n   [{i}] 📩 {sender[:30]}")
                                print(f"       📌 {subject[:50]}")
                                print(f"       📅 {date}")
                                
                        except:
                            pass
                            
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
        print(color("\n" + "="*50, Colors.BLUE))
        
    def show_status(self):
        """Show connection status"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 STATUS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        print(f"📧 Accounts: {len(self.accounts)}")
        print(f"📡 IMAP Connected: {len(self.connections)}")
        print(f"📤 SMTP Connected: {len(self.smtp_connections)}")
        print(f"🎤 Voice: {'Enabled' if self.voice_enabled else 'Disabled'}")
        
        for account in self.accounts:
            email = account.get('email', 'Unknown')
            imap_ok = email in self.connections
            smtp_ok = email in self.smtp_connections
            status = color("✅", Colors.GREEN) if imap_ok else color("❌", Colors.FAIL)
            print(f"   {status} {email} (IMAP: {'✓' if imap_ok else '✗'}, SMTP: {'✓' if smtp_ok else '✗'})")
            
        print(color("="*50, Colors.BLUE))
        
    def show_help(self):
        """Show all commands"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT - COMMANDS 🐉🐉🐉", Colors.HEADER))
        print(color("="*50, Colors.BLUE))
        print(color("\n📧 EMAIL COMMANDS:", Colors.BOLD))
        print("""
  sync / s         - Check all emails
  unread / u       - Show unread emails
  send             - Send new email
  reply [n]        - Reply to email (by number)
  forward [n]      - Forward email (by number)
  status / st      - Show connection status
        """)
        print(color("\n🎤 VOICE COMMANDS:", Colors.BOLD))
        print("""
  voice on         - Enable voice control
  voice off        - Disable voice control
  listen           - Listen for voice command
        """)
        print(color("\n🔧 GENERAL:", Colors.BOLD))
        print("""
  help / h         - Show this help
  clear / cls      - Clear screen
  exit / quit      - Exit program
        """)
        print(color("\n💡 EXAMPLES:", Colors.BOLD))
        print("""
  send              - Send new email
  reply 1           - Reply to email #1
  sync              - Check emails
  voice on          - Enable voice
        """)
        print(color("="*50, Colors.BLUE))
        
    def cmd_send(self):
        """Send new email"""
        print(color("\n📤 SEND EMAIL", Colors.BOLD))
        
        to = input("To: ").strip()
        if not to:
            print(color("❌ Cancelled", Colors.FAIL))
            return
            
        subject = input("Subject: ").strip()
        if not subject:
            subject = "(No Subject)"
            
        print("Body (type and press Enter twice to finish):")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        body = "\n".join(lines)
        
        if not body:
            print(color("❌ Empty body", Colors.FAIL))
            return
            
        confirm = input(f"\n📤 Send to {to}? (y/n): ").strip().lower()
        if confirm == 'y':
            self.send_email(to, subject, body)
        else:
            print(color("❌ Cancelled", Colors.FAIL))
            
    def cmd_reply(self, email_num=None):
        """Reply to an email"""
        if email_num is None:
            email_num = input("Reply to email #: ").strip()
            if not email_num.isdigit():
                print(color("❌ Invalid number", Colors.FAIL))
                return
            email_num = int(email_num)
        
        # Get email from first account
        if not self.connections:
            print(color("❌ No email account connected", Colors.FAIL))
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
            status, msg_data = mail.fetch(uid, '(RFC822)')
            
            if msg_data and msg_data[0]:
                raw = msg_data[0][1]
                msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
                
                sender = msg.get('From', 'Unknown')
                subject = msg.get('Subject', '') or '(No Subject)'
                body = msg.get_body().get_content()[:500] if msg.get_body() else ''
                
                print(color(f"\n📩 Replying to: {sender}", Colors.CYAN))
                print(color(f"📌 Subject: Re: {subject}", Colors.CYAN))
                print(color("-" * 50, Colors.BLUE))
                print(body[:300] + "...")
                print(color("-" * 50, Colors.BLUE))
                
                # Generate reply suggestion
                print(color("\n💡 Type your reply or say 'help' for options", Colors.WARNING))
                
                reply_text = input("\n📝 Your reply: ").strip()
                if not reply_text:
                    print(color("❌ Empty reply", Colors.FAIL))
                    return
                    
                # Get sender email
                if '<' in sender:
                    sender_email = sender.split('<')[1].split('>')[0]
                else:
                    sender_email = sender
                    
                self.send_email(sender_email, f"Re: {subject}", reply_text)
                
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
        if text in ['status', 'st', 'accounts']:
            self.show_status()
            return True
            
        # SYNC / CHECK EMAILS
        if text in ['sync', 's', 'check', 'emails', 'inbox', 'show emails']:
            self.sync_emails(10)
            return True
            
        # UNREAD
        if text in ['unread', 'u', 'new', 'new emails']:
            self.show_unread()
            return True
            
        # SEND EMAIL
        if text in ['send', 'compose', 'new email', 'write']:
            self.cmd_send()
            return True
            
        # REPLY
        if text.startswith('reply '):
            try:
                num = int(text.split()[1])
                self.cmd_reply(num)
            except:
                self.cmd_reply()
            return True
        if text == 'reply':
            self.cmd_reply()
            return True
            
        # VOICE
        if text == 'voice on':
            if self.voice_enabled:
                self.speak("Voice activated! Say 'help' for commands.")
                print(color("🎤 Voice ON", Colors.GREEN))
            else:
                print(color("❌ Voice not available. Install: pip install pyttsx3 speechrecognition pyaudio", Colors.FAIL))
            return True
            
        if text == 'voice off':
            print(color("🎤 Voice OFF", Colors.WARNING))
            return True
            
        if text == 'listen' or text == 'voice':
            if self.voice_enabled:
                command = self.listen()
                if command:
                    return self.handle_command(command)
            else:
                print(color("❌ Voice not available", Colors.FAIL))
            return True
            
        # Unknown
        print(color(f"❓ Unknown: '{original}'. Type 'help'", Colors.WARNING))
        return True
        
    def run(self):
        """Main loop"""
        print(color("\n" + "="*60, Colors.BOLD))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT - ULTIMATE 🐉🐉🐉", Colors.HEADER))
        print(color("Your AI Email Assistant with Voice Control", Colors.CYAN))
        print(color("="*60, Colors.BOLD))
        
        self.connect_all()
        
        self.speak("Dragon Email Agent ready! Type 'help' for commands.")
        
        print(color("\nType 'help' for commands. Use 'voice on' for voice control!", Colors.WARNING))
        
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
                
def main():
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    agent = DragonEmailAgent()
    agent.run()

if __name__ == "__main__":
    main()