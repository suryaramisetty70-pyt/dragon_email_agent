# =============================================================================
# INTEGRATIONS MODULE - Gmail API, IMAP, SMTP, Outlook
# =============================================================================

import os
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

# Optional Google API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    Credentials = None  # type: ignore
    InstalledAppFlow = None  # type: ignore
    build = None  # type: ignore
    HttpError = None  # type: ignore
    GOOGLE_API_AVAILABLE = False

from database import Email, EmailDirection, EmailPriority, EmailCategory, get_db_manager
from core import Config, DragonModule, logger, events
from email_engine import EmailMessage, EmailParser


@dataclass
class GmailAccount:
    """Gmail account configuration"""
    email: str
    credentials_path: str
    labels: List[str]
    is_active: bool = True


class GmailAPI:
    """Gmail API integration"""
    
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
    ]
    
    def __init__(self, config: Config):
        self.config = config
        self.service = None
        self.credentials = None
        self._parser = EmailParser()
        
    def authenticate(self, credentials_path: Optional[str] = None) -> bool:
        """Authenticate with Gmail API"""
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API not available. Install: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
            return False
            
        path = credentials_path or self.config.gmail_credentials_path
        
        if not path or not os.path.exists(path):
            logger.error(f"Gmail credentials file not found: {path}")
            return False
            
        try:
            flow = InstalledAppFlow.from_client_secrets_file(path, self.SCOPES)
            
            # For headless auth, use port 0 and handle manually
            self.credentials = flow.run_local_server(port=0, prompt="consent")
            self.service = build("gmail", "v1", credentials=self.credentials)
            
            logger.info("Gmail authentication successful")
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
            
    def authenticate_with_token(self, token_data: Dict[str, Any]) -> bool:
        """Authenticate with stored token"""
        if not GOOGLE_API_AVAILABLE:
            logger.error("Google API not available")
            return False
            
        try:
            self.credentials = Credentials.from_authorized_user_info(token_data)
            self.service = build("gmail", "v1", credentials=self.credentials)
            return True
        except Exception as e:
            logger.error(f"Token authentication failed: {e}")
            return False
            
    def list_messages(
        self, 
        label: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List messages from Gmail"""
        if not self.service:
            return []
            
        try:
            results = []
            request = self.service.users().messages().list(
                userId="me",
                labelIds=[label] if label else None,
                q=query,
                maxResults=max_results
            )
            
            while request:
                response = request.execute()
                messages = response.get("messages", [])
                
                for message in messages:
                    msg = self.service.users().messages().get(
                        userId="me",
                        id=message["id"],
                        format="full"
                    ).execute()
                    results.append(msg)
                    
                request = self.service.users().messages().list_next(request, response)
                
            return results
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []
            
    def get_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message"""
        if not self.service:
            return None
            
        try:
            return self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None
            
    def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Send email via Gmail API"""
        if not self.service:
            return None
            
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from base64 import urlsafe_b64encode
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["To"] = ", ".join(to)
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
                
            # Add body
            msg.attach(MIMEText(body, "plain"))
            
            # Encode
            raw = urlsafe_b64encode(msg.as_bytes()).decode()
            
            # Send
            sent = self.service.users().messages().send(
                userId="me",
                body={"raw": raw, "threadId": thread_id}
            ).execute()
            
            return sent["id"]
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None
            
    def modify_labels(
        self,
        message_ids: List[str],
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None
    ) -> bool:
        """Modify message labels"""
        if not self.service or not message_ids:
            return False
            
        try:
            for msg_id in message_ids:
                self.service.users().messages().modify(
                    userId="me",
                    id=msg_id,
                    body={
                        "addLabelIds": add_labels or [],
                        "removeLabelIds": remove_labels or []
                    }
                ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to modify labels: {e}")
            return False
            
    def get_labels(self) -> List[Dict[str, Any]]:
        """Get all labels"""
        if not self.service:
            return []
            
        try:
            labels = self.service.users().labels().list(userId="me").execute()
            return labels.get("labels", [])
        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return []
            
    def parse_gmail_message(self, msg_data: Dict[str, Any]) -> EmailMessage:
        """Parse Gmail API message to EmailMessage"""
        email_msg = EmailMessage()
        
        payload = msg_data.get("payload", {})
        headers = payload.get("headers", [])
        
        # Extract headers
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            
            if name == "from":
                email_msg.sender = self._parse_address(value)
            elif name == "to":
                email_msg.recipients = [self._parse_address(a) for a in value.split(",")]
            elif name == "cc":
                email_msg.cc = [self._parse_address(a) for a in value.split(",")]
            elif name == "subject":
                email_msg.subject = value
            elif name == "date":
                email_msg.date_sent = self._parse_date(value)
            elif name == "message-id":
                email_msg.message_id = value.strip("<>")
                
        # Get thread ID
        email_msg.thread_id = msg_data.get("threadId", "")
        
        # Get body
        body = self._get_message_body(payload)
        email_msg.body_html = body.get("html", "")
        email_msg.body_plain = body.get("plain", "")
        
        # Get attachments
        email_msg.attachments = self._get_attachments(payload)
        email_msg.has_attachments = len(email_msg.attachments) > 0
        
        # Get labels
        email_msg.labels = msg_data.get("labelIds", [])
        
        return email_msg
        
    def _parse_address(self, address_str: str) -> Any:
        """Parse email address"""
        from email_engine import EmailAddress
        import re
        
        match = re.search(r'"?([^"<]*)"?\s*<([^>]+)>', address_str)
        if match:
            return EmailAddress(match.group(2).strip(), match.group(1).strip())
            
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', address_str)
        if email_match:
            return EmailAddress(email_match.group(0).lower(), "")
            
        return EmailAddress("", "")
        
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from header"""
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            return datetime.utcnow()
            
    def _get_message_body(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Extract message body"""
        body = {"html": "", "plain": ""}
        
        if "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                data = part.get("body", {}).get("data", "")
                
                if data:
                    import base64
                    try:
                        decoded = base64.urlsafe_b64decode(data.encode()).decode()
                    except:
                        decoded = data
                        
                    if mime_type == "text/plain":
                        body["plain"] = decoded
                    elif mime_type == "text/html":
                        body["html"] = decoded
        else:
            data = payload.get("body", {}).get("data", "")
            if data:
                import base64
                try:
                    decoded = base64.urlsafe_b64decode(data.encode()).decode()
                except:
                    decoded = data
                body["plain"] = decoded
                
        return body
        
    def _get_attachments(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachments"""
        attachments = []
        
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    att = {
                        "filename": part.get("filename", "unknown"),
                        "content_type": part.get("mimeType", "application/octet-stream"),
                        "attachment_id": part.get("body", {}).get("attachmentId", ""),
                    }
                    attachments.append(att)
                    
        return attachments


class IMAPIntegration:
    """IMAP integration for multiple providers"""
    
    def __init__(self, config: Config):
        self.config = config
        self.connections: Dict[str, Any] = {}
        self._parser = EmailParser()
        
    def connect(
        self,
        account_name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True
    ) -> bool:
        """Connect to IMAP server"""
        try:
            import imaplib
            
            if use_ssl:
                conn = imaplib.IMAP4_SSL(host, port)
            else:
                conn = imaplib.IMAP4(host, port)
                
            conn.login(username, password)
            self.connections[account_name] = conn
            
            logger.info(f"IMAP connected: {account_name}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
            
    def disconnect(self, account_name: str) -> None:
        """Disconnect from IMAP server"""
        if account_name in self.connections:
            try:
                self.connections[account_name].logout()
            except:
                pass
            del self.connections[account_name]
            
    def list_folders(self, account_name: str) -> List[str]:
        """List folders on IMAP server"""
        if account_name not in self.connections:
            return []
            
        try:
            _, folders = self.connections[account_name].list()
            return [f.decode().split('"."')[-1].strip('"') for f in folders]
        except Exception as e:
            logger.error(f"List folders failed: {e}")
            return []
            
    def fetch_emails(
        self,
        account_name: str,
        folder: str = "INBOX",
        since_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[EmailMessage]:
        """Fetch emails from IMAP server"""
        if account_name not in self.connections:
            return []
            
        emails = []
        conn = self.connections[account_name]
        
        try:
            conn.select(folder)
            
            criteria = "ALL"
            if since_date:
                criteria = f'SINCE {since_date.strftime("%d-%b-%Y")}'
                
            _, message_ids = conn.search(None, criteria)
            
            ids = message_ids[0].split()
            to_fetch = ids[-limit:] if len(ids) > limit else ids
            
            for msg_id in to_fetch:
                try:
                    _, data = conn.fetch(msg_id, "(RFC822)")
                    if data and data[0]:
                        raw = data[0][1]
                        email_msg = self._parser.parse(raw.decode("utf-8", errors="replace"))
                        emails.append(email_msg)
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg_id}: {e}")
                    
        except Exception as e:
            logger.error(f"IMAP fetch failed: {e}")
            
        return emails
        
    def move_email(self, account_name: str, message_ids: List[str], target_folder: str) -> bool:
        """Move email to folder"""
        if account_name not in self.connections:
            return False
            
        try:
            conn = self.connections[account_name]
            for msg_id in message_ids:
                conn.copy(msg_id, target_folder)
                conn.store(msg_id, "+FLAGS", "\\Deleted")
            conn.expunge()
            return True
        except Exception as e:
            logger.error(f"Move email failed: {e}")
            return False
            
    def delete_emails(self, account_name: str, message_ids: List[str]) -> bool:
        """Delete emails"""
        if account_name not in self.connections:
            return False
            
        try:
            conn = self.connections[account_name]
            for msg_id in message_ids:
                conn.store(msg_id, "+FLAGS", "\\Deleted")
            conn.expunge()
            return True
        except Exception as e:
            logger.error(f"Delete emails failed: {e}")
            return False


class SMTPIntegration:
    """SMTP integration for sending emails"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def send(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        use_tls: bool = True,
        use_ssl: bool = False
    ) -> bool:
        """Send email via SMTP"""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        try:
            if use_ssl:
                server = smtplib.SMTP_SSL(host, port)
            else:
                server = smtplib.SMTP(host, port)
                if use_tls:
                    server.starttls()
                    
            server.login(username, password)
            
            msg = MIMEMultipart("alternative")
            msg["From"] = username
            msg["To"] = ", ".join(to)
            msg["Subject"] = subject
            
            if cc:
                msg["Cc"] = ", ".join(cc)
                to = to + cc
                
            msg.attach(MIMEText(body, "plain"))
            
            server.sendmail(username, to, msg.as_string())
            server.quit()
            
            logger.info(f"SMTP email sent to {to}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return False


class OutlookIntegration:
    """Microsoft Outlook integration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.service = None
        
    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph API"""
        try:
            import msal
            
            app_id = self.config.get("outlook_app_id")
            app_secret = self.config.get("outlook_app_secret")
            
            if not app_id or not app_secret:
                logger.error("Outlook credentials not configured")
                return False
                
            # MSAL authentication
            app = msal.ConfidentialClientApplication(
                app_id,
                authority="https://login.microsoftonline.com/common",
                client_credential=app_secret
            )
            
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                import requests
                
                self.graph_url = "https://graph.microsoft.com/v1.0"
                self.headers = {
                    "Authorization": f"Bearer {result['access_token']}",
                    "Content-Type": "application/json"
                }
                return True
                
            return False
            
        except ImportError:
            logger.warning("MSAL not installed, Outlook integration unavailable")
            return False
        except Exception as e:
            logger.error(f"Outlook authentication failed: {e}")
            return False
            
    def list_messages(self, folder: str = "Inbox", top: int = 50) -> List[Dict[str, Any]]:
        """List messages from Outlook"""
        if not hasattr(self, 'headers'):
            return []
            
        try:
            import requests
            
            response = requests.get(
                f"{self.graph_url}/me/mailFolders/{folder}/messages",
                headers=self.headers,
                params={"$top": top, "$orderby": "receivedDateTime desc"}
            )
            
            if response.status_code == 200:
                return response.json().get("value", [])
            return []
            
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []
            
    def send_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None
    ) -> bool:
        """Send email via Outlook Graph API"""
        if not hasattr(self, 'headers'):
            return False
            
        try:
            import requests
            
            message = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "Text", "content": body},
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in to]
                },
                "saveToSentItems": True
            }
            
            if cc:
                message["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in cc
                ]
                
            response = requests.post(
                f"{self.graph_url}/me/sendMail",
                headers=self.headers,
                json=message
            )
            
            return response.status_code == 202
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False


class IntegrationManager(DragonModule):
    """Manage all email integrations"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.gmail = GmailAPI(config)
        self.imap = IMAPIntegration(config)
        self.smtp = SMTPIntegration(config)
        self.outlook = OutlookIntegration(config)
        self._active_accounts: Dict[str, str] = {}  # name -> provider
        self._account_configs: List[Dict[str, Any]] = []
        
    def initialize(self) -> None:
        """Initialize integration manager"""
        super().initialize()
        
        # Load email accounts from config
        self._load_email_accounts()
        
        logger.info("Integration Manager initialized")
        
    def _load_email_accounts(self) -> None:
        """Load email accounts from config file"""
        config_path = Path("config/email_accounts.json")
        
        if not config_path.exists():
            logger.warning("No email accounts configured. Run setup_emails.py first.")
            return
            
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                
            accounts = config_data.get("accounts", [])
            
            for acc in accounts:
                if not acc.get("is_active", True):
                    continue
                    
                self._account_configs.append(acc)
                
                # Try to connect based on account type
                email = acc.get("email", "")
                
                if "@gmail.com" in email.lower() and acc.get("use_gmail_api"):
                    # Try Gmail API first
                    creds_path = acc.get("gmail_credentials_path", "config/gmail_credentials.json")
                    if Path(creds_path).exists():
                        if self.gmail.authenticate(creds_path):
                            self._active_accounts[email] = "gmail"
                            logger.info(f"Connected to Gmail: {email}")
                    else:
                        # Fall back to IMAP
                        self._connect_imap_account(acc)
                else:
                    # Use IMAP
                    self._connect_imap_account(acc)
                    
        except Exception as e:
            logger.error(f"Failed to load email accounts: {e}")
            
    def _connect_imap_account(self, acc: Dict[str, Any]) -> bool:
        """Connect an IMAP account"""
        try:
            name = acc.get("email", "unknown")
            host = acc.get("imap_host", "")
            port = acc.get("imap_port", 993)
            username = acc.get("email", "")
            password = acc.get("password", "")
            
            if not host or not password or password == "YOUR_PASSWORD_HERE" or password == "YOUR_APP_PASSWORD_HERE":
                logger.warning(f"Account {name} not configured with real credentials")
                return False
                
            if self.imap.connect(name, host, port, username, password):
                self._active_accounts[name] = "imap"
                logger.info(f"Connected to IMAP: {name} ({host})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to connect IMAP account {acc.get('email')}: {e}")
            return False
        
    def setup_gmail(self, credentials_path: str) -> bool:
        """Setup Gmail integration"""
        return self.gmail.authenticate(credentials_path)
        
    def setup_smtp(
        self,
        host: str,
        port: int,
        username: str,
        password: str
    ) -> bool:
        """Setup SMTP connection"""
        # Test SMTP connection
        test_result = self.smtp.send(
            host, port, username, password,
            to=[username],  # Send to self
            subject="Connection Test",
            body="Dragon Email Agent SMTP Test"
        )
        
        if test_result:
            self.config.smtp_host = host
            self.config.smtp_port = port
            self.config.smtp_username = username
            self.config.smtp_password = password
            
        return test_result
        
    def add_imap_account(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str
    ) -> bool:
        """Add IMAP account"""
        if self.imap.connect(name, host, port, username, password):
            self._active_accounts[name] = "imap"
            return True
        return False
        
    def get_active_providers(self) -> List[str]:
        """Get list of active providers"""
        providers = []
        
        if hasattr(self.gmail, 'service') and self.gmail.service:
            providers.append("gmail")
            
        if hasattr(self.outlook, 'service') and self.outlook.service:
            providers.append("outlook")
            
        if self._active_accounts:
            providers.extend(self._active_accounts.keys())
            
        return providers
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        # Close all IMAP connections
        for account_name in list(self.imap.connections.keys()):
            self.imap.disconnect(account_name)
            
        logger.info("Integration Manager shutdown complete")
