#!/usr/bin/env python3
# =============================================================================
# PROJECT DRAGON - EMAIL SETUP SCRIPT
# =============================================================================
# This script helps configure email accounts for Dragon Email Agent
# =============================================================================

import os
import sys
import json
import yaml
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_step(step, text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[{step}]{Colors.END} {text}")

def print_success(text):
    print(f"{Colors.GREEN}✓{Colors.END} {text}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠{Colors.END} {text}")

def print_error(text):
    print(f"{Colors.RED}✗{Colors.END} {text}")

def get_email_config():
    """Get email configuration from user"""
    print(f"\n{Colors.BOLD}📧 EMAIL ACCOUNT CONFIGURATION{Colors.END}\n")
    
    accounts = []
    
    # Account 1
    print(f"\n{Colors.CYAN}--- Account 1 ---{Colors.END}")
    email1 = input("Enter email address (e.g., vtu27657@veltec.edu.in): ").strip()
    if not email1:
        print_warning("No email entered, skipping account 1")
    else:
        password1 = input("Enter password or App Password: ").strip()
        imap_host = input("IMAP Host (press Enter for auto-detect): ").strip()
        smtp_host = input("SMTP Host (press Enter for auto-detect): ").strip()
        
        # Auto-detect hosts
        if "@gmail.com" in email1.lower():
            imap_host = imap_host or "imap.gmail.com"
            smtp_host = smtp_host or "smtp.gmail.com"
        elif "@outlook.com" in email1.lower() or "@hotmail.com" in email1.lower():
            imap_host = imap_host or "outlook.office365.com"
            smtp_host = smtp_host or "smtp.office365.com"
        elif not imap_host:
            imap_host = input("IMAP Host (required): ").strip()
        if not smtp_host:
            smtp_host = input("SMTP Host (required): ").strip()
            
        accounts.append({
            "email": email1,
            "password": password1,
            "imap_host": imap_host,
            "imap_port": 993,
            "smtp_host": smtp_host,
            "smtp_port": 587,
            "is_active": True,
            "account_type": "college" if "edu" in email1 else "personal",
            "display_name": email1.split("@")[0].title()
        })
    
    # Account 2
    print(f"\n{Colors.CYAN}--- Account 2 ---{Colors.END}")
    email2 = input("Enter email address (e.g., suryaramisetty70@gmail.com): ").strip()
    if not email2:
        print_warning("No second email entered, you can add more later")
    else:
        password2 = input("Enter password or App Password: ").strip()
        imap_host = input("IMAP Host (press Enter for auto-detect): ").strip()
        smtp_host = input("SMTP Host (press Enter for auto-detect): ").strip()
        
        # Auto-detect hosts
        if "@gmail.com" in email2.lower():
            imap_host = imap_host or "imap.gmail.com"
            smtp_host = smtp_host or "smtp.gmail.com"
        elif "@outlook.com" in email2.lower() or "@hotmail.com" in email2.lower():
            imap_host = imap_host or "outlook.office365.com"
            smtp_host = smtp_host or "smtp.office365.com"
        elif not imap_host:
            imap_host = input("IMAP Host (required): ").strip()
        if not smtp_host:
            smtp_host = input("SMTP Host (required): ").strip()
            
        accounts.append({
            "email": email2,
            "password": password2,
            "imap_host": imap_host,
            "imap_port": 993,
            "smtp_host": smtp_host,
            "smtp_port": 587,
            "is_active": True,
            "account_type": "personal",
            "display_name": email2.split("@")[0].title()
        })
    
    return accounts

def save_config(accounts):
    """Save email configuration to file"""
    config_path = Path("config/email_accounts.json")
    config_path.parent.mkdir(exist_ok=True)
    
    # Convert to JSON-safe format (in production, encrypt the passwords)
    config_data = {
        "accounts": accounts,
        "sync_interval_minutes": 5,
        "sync_on_startup": True,
        "notifications_enabled": True
    }
    
    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)
    
    # Also save as YAML
    yaml_path = Path("config/email_config.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    print_success(f"Configuration saved to {config_path}")
    print_success(f"Configuration saved to {yaml_path}")

def create_env_file(accounts):
    """Create .env file for sensitive data"""
    env_path = Path(".env")
    
    env_content = "# Dragon Email Agent - Environment Variables\n"
    env_content += "# ⚠️ DO NOT SHARE THIS FILE - Contains sensitive credentials\n\n"
    
    for i, acc in enumerate(accounts, 1):
        email_key = acc["email"].replace("@", "_").replace(".", "_")
        env_content += f"# Account {i}: {acc['email']}\n"
        env_content += f"EMAIL_{email_key}_PASSWORD={acc['password']}\n"
        env_content += f"EMAIL_{email_key}_IMAP={acc['imap_host']}\n"
        env_content += f"EMAIL_{email_key}_SMTP={acc['smtp_host']}\n\n"
    
    with open(env_path, "w") as f:
        f.write(env_content)
    
    print_success(f"Environment variables saved to {env_path}")

def test_imap_connection(email, password, imap_host):
    """Test IMAP connection"""
    try:
        import imaplib
        print(f"\n{Colors.CYAN}Testing IMAP connection to {imap_host}...{Colors.END}")
        mail = imaplib.IMAP4_SSL(imap_host, 993)
        mail.login(email, password)
        mail.logout()
        return True
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False

def generate_gmail_credentials_guide():
    """Generate guide for Gmail API setup"""
    guide = """
    
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                    GMAIL API SETUP GUIDE                             ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║                                                                      ║
    ║  For @gmail.com accounts, you need to create a Google API project:   ║
    ║                                                                      ║
    ║  1. Go to: https://console.cloud.google.com/apis/credentials          ║
    ║                                                                      ║
    ║  2. Create a new project or select existing one                      ║
    ║                                                                      ║
    ║  3. Enable "Gmail API" from the library                              ║
    ║                                                                      ║
    ║  4. Create OAuth 2.0 credentials:                                    ║
    ║     - Application type: Desktop app                                 ║
    ║     - Name: "Dragon Email Agent"                                    ║
    ║                                                                      ║
    ║  5. Download the JSON file and save as:                              ║
    ║     config/gmail_credentials.json                                    ║
    ║                                                                      ║
    ║  6. For @gmail.com accounts, we recommend using Gmail API instead   ║
    ║     of IMAP for better reliability.                                 ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """
    print(guide)

def main():
    print(f"""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║         🐉 PROJECT DRAGON - EMAIL SETUP WIZARD                       ║
    ║                                                                      ║
    ║         Configure your email accounts to get started                ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    print_step("1", "Getting email configurations...")
    accounts = get_email_config()
    
    if not accounts:
        print_error("No accounts configured. Exiting.")
        sys.exit(1)
    
    print_step("2", "Testing connections...")
    for acc in accounts:
        if "@gmail.com" not in acc["email"].lower():
            if test_imap_connection(acc["email"], acc["password"], acc["imap_host"]):
                print_success(f"✓ {acc['email']} - Connection successful")
            else:
                print_warning(f"⚠ {acc['email']} - Connection failed, please check credentials")
    
    print_step("3", "Saving configuration...")
    save_config(accounts)
    
    print_step("4", "Creating environment file...")
    create_env_file(accounts)
    
    print_step("5", "Gmail API Setup (if applicable)...")
    gmail_accounts = [a for a in accounts if "@gmail.com" in a["email"].lower()]
    if gmail_accounts:
        generate_gmail_credentials_guide()
    
    print(f"""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                        SETUP COMPLETE!                               ║
    ╠══════════════════════════════════════════════════════════════════════╣
    ║                                                                      ║
    ║  Configured Accounts:                                                ║""")
    
    for i, acc in enumerate(accounts, 1):
        print(f"║    {i}. {acc['email']:<45} ║")
    
    print(f"""║                                                                      ║
    ║  Next Steps:                                                         ║
    ║                                                                      ║
    ║    1. For Gmail accounts, complete Gmail API setup (see guide above)║
    ║                                                                      ║
    ║    2. Run: python3 main.py                                           ║
    ║                                                                      ║
    ║    3. Use @dragon commands or voice to manage emails                ║
    ║                                                                      ║
    ║    Example: @dragon sync emails                                      ║
    ║              @dragon show unread                                    ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)

if __name__ == "__main__":
    main()