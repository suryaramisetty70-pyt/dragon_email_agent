#!/usr/bin/env python3
"""
Dragon Email Agent - Quick Email Sync
Fetches and displays emails from configured accounts
"""

import imaplib
import json
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def sync_gmail():
    """Sync Gmail emails"""
    print("\n" + "="*60)
    print("📧 DRAGON EMAIL SYNC")
    print("="*60)
    
    # Load config
    with open('config/email_accounts.json') as f:
        config = json.load(f)
    
    total_emails = 0
    
    for account in config['accounts']:
        email = account['email']
        password = account['password']
        imap_host = account['imap_host']
        
        print(f"\n📬 Connecting to: {email}")
        print(f"   Server: {imap_host}")
        
        try:
            # Connect
            mail = imaplib.IMAP4_SSL(imap_host, 993, timeout=20)
            mail.login(email, password)
            print(f"   ✅ Connected!")
            
            # Get inbox stats
            mail.select('INBOX')
            status, messages = mail.search(None, 'ALL')
            email_ids = messages[0].split()
            inbox_count = len(email_ids)
            
            # Get unread count
            status, unread = mail.search(None, 'UNSEEN')
            unread_count = len(unread[0].split()) if unread[0] else 0
            
            print(f"   📧 Total emails: {inbox_count}")
            print(f"   📬 Unread: {unread_count}")
            
            total_emails += inbox_count
            
            # Show recent emails
            if inbox_count > 0:
                recent = email_ids[-10:]  # Last 10
                print(f"\n   📬 Recent emails:")
                print("   " + "-"*50)
                
                for uid in recent:
                    status, msg_data = mail.fetch(uid, '(RFC822)')
                    raw = msg_data[0][1]
                    
                    # Parse email
                    from email import parser
                    msg = parser.Parser().parsestr(raw.decode('utf-8', errors='replace'))
                    
                    sender = msg.get('From', 'Unknown')
                    subject = msg.get('Subject', '(No Subject)')
                    date = msg.get('Date', '')[:16]
                    
                    # Clean up sender
                    if '<' in sender:
                        sender = sender.split('<')[0].strip()
                    
                    print(f"   📩 {sender[:30]}")
                    print(f"      {subject[:45] if subject else '(No subject)'}")
                    print(f"      📅 {date}")
                    print()
            
            mail.logout()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("="*60)
    print(f"✅ Total emails across all accounts: {total_emails}")
    print("="*60)

def sync_all():
    """Sync from all accounts"""
    sync_gmail()

if __name__ == "__main__":
    sync_all()