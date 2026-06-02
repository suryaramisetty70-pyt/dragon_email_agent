#!/usr/bin/env python3
"""
🐉 DRAGON EMAIL AGENT - MAIN PROGRAM
Simple, working email agent with natural language support
"""

import sys
import os
import json
import imaplib
from email import parser

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
    return f"{code}{text}{Colors.ENDC}"

class DragonEmailAgent:
    def __init__(self):
        self.accounts = []
        self.load_config()
        self.connections = {}
        
    def load_config(self):
        config_path = "config/email_accounts.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
                print(color(f"Loaded {len(self.accounts)} email accounts", Colors.GREEN))
        else:
            print(color("ERROR: config/email_accounts.json not found!", Colors.FAIL))
            
    def connect_account(self, account):
        email = account.get('email', '')
        password = account.get('password', '')
        imap_host = account.get('imap_host', '')
        imap_port = account.get('imap_port', 993)
        
        print(color(f"\nConnecting to: {email}", Colors.CYAN))
        print(f"Server: {imap_host}:{imap_port}")
        
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=15)
            mail.login(email, password)
            self.connections[email] = mail
            print(color(f"✅ Connected successfully!", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"❌ Connection failed", Colors.FAIL))
            return False
            
    def connect_all(self):
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 DRAGON EMAIL AGENT", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        connected = 0
        for account in self.accounts:
            if account.get('is_active', True):
                if self.connect_account(account):
                    connected += 1
                    
        print(color(f"\n✅ Connected: {connected} accounts", Colors.GREEN))
        return connected
        
    def sync_emails(self, filter_type="all"):
        """Sync emails with optional filter"""
        print(color("\n" + "="*50, Colors.BLUE))
        
        total_emails = 0
        total_unread = 0
        
        for email, mail in self.connections.items():
            try:
                print(color(f"\n📬 {email}", Colors.CYAN))
                mail.select('INBOX')
                
                search_criteria = 'ALL' if filter_type == "all" else 'UNSEEN'
                status, messages = mail.search(None, search_criteria)
                email_ids = messages[0].split()
                count = len(email_ids)
                
                status, unread_data = mail.search(None, 'UNSEEN')
                unread_count = len(unread_data[0].split()) if unread_data[0] else 0
                
                print(color(f"   Total: {count} | Unread: {unread_count}", Colors.WARNING))
                total_emails += count
                total_unread += unread_count
                
                if count > 0:
                    recent = email_ids[-10:]
                    print(color("   Recent:", Colors.GREEN))
                    
                    for uid in recent:
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
                                
                                print(f"   📩 {sender[:35]}")
                                print(f"      📌 {subject[:50]}")
                                print(f"      📅 {date}")
                                print()
                        except:
                            pass
                            
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
        print(color("="*50, Colors.BLUE))
        print(color(f"📊 TOTAL: {total_emails} emails | {total_unread} unread", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
    def show_status(self):
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 STATUS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        print(f"\n📧 Accounts: {len(self.accounts)}")
        print(f"🔗 Connected: {len(self.connections)}")
        
        for account in self.accounts:
            email = account.get('email', 'Unknown')
            connected = email in self.connections
            status = color("✅", Colors.GREEN) if connected else color("❌", Colors.FAIL)
            print(f"   {status} {email}")
            
        print(color("="*50, Colors.BLUE))
        
    def show_help(self):
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 COMMANDS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        print("""
  sync / s         - Check all emails
  unread           - Show unread emails
  important        - Show important emails
  status / st      - Show connection status
  help             - Show this help
  exit / quit      - Exit program
        """)
        print(color("="*50, Colors.BLUE))
        
    def handle_command(self, user_input):
        """Handle natural language commands"""
        text = user_input.lower().strip()
        
        if text in ['exit', 'quit', 'q', 'bye']:
            print(color("\n🐉 Goodbye!", Colors.HEADER))
            return False
            
        if text in ['help', 'h', '?']:
            self.show_help()
            return True
            
        if text in ['sync', 's', 'check', 'emails', 'inbox', 'all emails', 'show emails', 'read emails']:
            self.sync_emails("all")
            return True
            
        if any(x in text for x in ['unread', 'new emails', 'new messages', 'show unread']):
            self.sync_emails("unread")
            return True
            
        if any(x in text for x in ['important', 'priority', 'starred', 'read important']):
            self.sync_emails("all")
            print(color("\n📌 Tip: Star emails in Gmail to mark as important!", Colors.WARNING))
            return True
            
        if text in ['status', 'st', 'accounts', 'inbox status']:
            self.show_status()
            return True
            
        if text.startswith('search '):
            print(color("\n🔍 Search feature coming soon!", Colors.WARNING))
            return True
            
        if text in ['clear', 'cls']:
            os.system('cls' if os.name == 'nt' else 'clear')
            return True
            
        print(color(f"❓ Type 'help' for commands. You typed: '{user_input}'", Colors.WARNING))
        return True
        
    def run(self):
        print(color("\n" + "="*50, Colors.BOLD))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT 🐉🐉🐉", Colors.HEADER))
        print(color("Your AI Email Assistant", Colors.CYAN))
        print(color("="*50, Colors.BOLD))
        
        self.connect_all()
        
        print(color("\nType 'help' for commands", Colors.WARNING))
        
        while True:
            try:
                user_input = input(color("\n>>> ", Colors.CYAN)).strip()
                
                if not user_input:
                    continue
                    
                if not self.handle_command(user_input):
                    break
                    
            except KeyboardInterrupt:
                print(color("\n\n🐉 Goodbye!", Colors.HEADER))
                break
            except Exception as e:
                print(color(f"Error: {e}", Colors.FAIL)

def main():
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    agent = DragonEmailAgent()
    agent.run()

if __name__ == "__main__":
    main()