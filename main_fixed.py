#!/usr/bin/env python3
"""
🐉 DRAGON EMAIL AGENT - MAIN PROGRAM
Simple, working email agent
"""

import sys
import os
import json
import imaplib
from datetime import datetime

# Colors for Windows
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
        """Load email accounts from config file"""
        config_path = "config/email_accounts.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.accounts = data.get('accounts', [])
                print(color(f"Loaded {len(self.accounts)} email accounts", Colors.GREEN))
        else:
            print(color("ERROR: config/email_accounts.json not found!", Colors.FAIL))
            
    def connect_account(self, account):
        """Connect to an email account"""
        email = account.get('email', '')
        password = account.get('password', '')
        imap_host = account.get('imap_host', '')
        imap_port = account.get('imap_port', 993)
        
        print(color(f"\nConnecting to: {email}", Colors.CYAN))
        print(f"Server: {imap_host}:{imap_port}")
        
        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port, timeout=30)
            mail.login(email, password)
            self.connections[email] = mail
            print(color(f"✅ Connected successfully!", Colors.GREEN))
            return True
        except Exception as e:
            print(color(f"❌ Connection failed: {e}", Colors.FAIL))
            return False
            
    def connect_all(self):
        """Connect to all configured accounts"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 DRAGON EMAIL AGENT - CONNECTING", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        connected = 0
        for account in self.accounts:
            if account.get('is_active', True):
                if self.connect_account(account):
                    connected += 1
                    
        print(color(f"\n✅ Connected to {connected}/{len(self.accounts)} accounts", Colors.GREEN))
        return connected
        
    def sync_emails(self):
        """Sync emails from all connected accounts"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("📧 SYNCING EMAILS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        total_emails = 0
        total_unread = 0
        
        for email, mail in self.connections.items():
            try:
                print(color(f"\n📬 {email}", Colors.CYAN))
                
                # Select inbox
                mail.select('INBOX')
                
                # Get all emails
                status, messages = mail.search(None, 'ALL')
                email_ids = messages[0].split()
                inbox_count = len(email_ids)
                
                # Get unread emails
                status, unread = mail.search(None, 'UNSEEN')
                unread_ids = unread[0].split() if unread[0] else []
                unread_count = len(unread_ids)
                
                print(color(f"   Total: {inbox_count} | Unread: {unread_count}", Colors.WARNING))
                
                total_emails += inbox_count
                total_unread += unread_count
                
                # Show recent emails
                if inbox_count > 0:
                    recent = email_ids[-5:]  # Last 5
                    print(color("   Recent emails:", Colors.GREEN))
                    
                    for uid in recent:
                        try:
                            status, msg_data = mail.fetch(uid, '(RFC822)')
                            raw = msg_data[0][1]
                            from email import parser
                            msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
                            
                            sender = msg.get('From', 'Unknown')
                            subject = msg.get('Subject', '(No Subject)')
                            date = msg.get('Date', '')[:16]
                            
                            # Clean sender
                            if '<' in sender:
                                sender = sender.split('<')[0].strip()
                            
                            print(f"   📩 {sender[:30]}")
                            print(f"      {subject[:45] if subject else '(No subject)'}")
                            print(f"      📅 {date}")
                        except:
                            pass
                            
            except Exception as e:
                print(color(f"   ❌ Error: {e}", Colors.FAIL))
                
        print(color("\n" + "="*50, Colors.BLUE))
        print(color(f"📊 TOTAL: {total_emails} emails | {total_unread} unread", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
    def show_status(self):
        """Show connection status"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 DRAGON EMAIL AGENT - STATUS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        
        print(f"\n📧 Configured accounts: {len(self.accounts)}")
        print(f"🔗 Connected accounts: {len(self.connections)}")
        
        print(color("\n📋 Account Details:", Colors.CYAN))
        for account in self.accounts:
            email = account.get('email', 'Unknown')
            display = account.get('display_name', email)
            connected = email in self.connections
            status = color("✅ Connected", Colors.GREEN) if connected else color("❌ Not connected", Colors.FAIL)
            print(f"   • {display} ({email}) - {status}")
            
        print(color("\n" + "="*50, Colors.BLUE))
        
    def show_help(self):
        """Show available commands"""
        print(color("\n" + "="*50, Colors.BLUE))
        print(color("🐉 DRAGON EMAIL AGENT - COMMANDS", Colors.BOLD))
        print(color("="*50, Colors.BLUE))
        print("""
  help, h      - Show this help message
  sync, s      - Sync emails from all accounts
  status, st   - Show connection status
  inbox        - Show inbox summary
  search [text] - Search emails
  exit, quit   - Exit the program
  
  @dragon commands:
  @dragon read important  - Show important emails
  @dragon show unread     - Show unread emails
  @dragon inbox status    - Check inbox
        """)
        print(color("="*50, Colors.BLUE))
        
    def run(self):
        """Main loop"""
        print(color("\n" + "="*50, Colors.BOLD))
        print(color("🐉🐉🐉 DRAGON EMAIL AGENT 🐉🐉🐉", Colors.HEADER))
        print(color("="*50, Colors.BOLD))
        print(color("Your AI Email Assistant", Colors.CYAN))
        print(color("="*50, Colors.BOLD))
        
        # Connect to accounts
        self.connect_all()
        
        print(color("\nType 'help' for commands, 'exit' to quit", Colors.WARNING))
        
        while True:
            try:
                user_input = input(color("\nDragon> ", Colors.CYAN)).strip()
                
                if not user_input:
                    continue
                    
                cmd = user_input.lower().split()[0] if user_input else ''
                
                if cmd in ['exit', 'quit', 'q']:
                    print(color("\n🐉 Goodbye! Dragon signing off...", Colors.HEADER))
                    break
                    
                elif cmd in ['help', 'h', '?']:
                    self.show_help()
                    
                elif cmd in ['sync', 's']:
                    self.sync_emails()
                    
                elif cmd in ['status', 'st']:
                    self.show_status()
                    
                elif cmd in ['inbox', 'ib']:
                    self.sync_emails()
                    
                elif cmd.startswith('@dragon'):
                    # Handle dragon commands
                    if 'unread' in user_input.lower():
                        self.sync_emails()
                    elif 'important' in user_input.lower():
                        self.sync_emails()
                    else:
                        print(color("Try: @dragon show unread, @dragon read important", Colors.WARNING))
                        
                elif cmd == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                else:
                    print(color(f"Unknown command: {cmd}. Type 'help' for commands.", Colors.WARNING))
                    
            except KeyboardInterrupt:
                print(color("\n\n🐉 Goodbye! Dragon signing off...", Colors.HEADER))
                break
            except Exception as e:
                print(color(f"Error: {e}", Colors.FAIL)

def main():
    """Entry point"""
    # Create necessary directories
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Run the agent
    agent = DragonEmailAgent()
    agent.run()

if __name__ == "__main__":
    main()