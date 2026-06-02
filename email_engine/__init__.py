# =============================================================================
# EMAIL ENGINE - Core Email Processing
# =============================================================================

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from email.parser import Parser
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
import hashlib
import json
import re
from bs4 import BeautifulSoup
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

try:
    import html2text
    HTML2TEXT_AVAILABLE = True
except ImportError:
    HTML2TEXT_AVAILABLE = False

# Handle imports for both package and direct execution
try:
    from database import (
        Email, Attachment, Thread, Contact, EmailCategory, EmailPriority,
        EmailDirection, get_db_manager, DatabaseManager
    )
    from core import Config, DragonModule, logger, events, format_email_preview
except ImportError:
    from database import (
        Email, Attachment, Thread, Contact, EmailCategory, EmailPriority,
        EmailDirection, get_db_manager, DatabaseManager
    )
    from core import Config, DragonModule, logger, events, format_email_preview


class EmailAddress:
    """Email address with name"""
    def __init__(self, email: str, name: Optional[str] = None):
        self.email = email
        self.name = name or ""
        
    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailMessage:
    """Parsed email message"""
    def __init__(self):
        self.message_id = ""
        self.thread_id = ""
        self.subject = ""
        self.sender = EmailAddress("", "")
        self.recipients: List[EmailAddress] = []
        self.cc: List[EmailAddress] = []
        self.bcc: List[EmailAddress] = []
        self.date_sent = datetime.utcnow()
        self.date_received = datetime.utcnow()
        self.body_plain = ""
        self.body_html = ""
        self.snippet = ""
        self.has_attachments = False
        self.attachments: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}
        self.labels: List[str] = []
        self.is_html = False


class EmailClassifier:
    """AI-powered email classification"""
    
    def __init__(self, config: Config):
        self.config = config
        self.keyword_weights = {
            "emergency": 50,
            "urgent": 40,
            "critical": 40,
            "asap": 35,
            "deadline": 30,
            "client": 25,
            "interview": 25,
            "offer": 25,
            "faculty": 20,
            "professor": 20,
            "internship": 30,
            "job": 25,
            "invoice": 30,
            "payment": 25,
            "meeting": 15,
            "project": 15,
            "update": 10,
            "newsletter": 5,
            "promo": 5,
            "unsubscribe": 8,
        }
        
    def classify(self, email: EmailMessage, contact: Optional[Contact] = None) -> Tuple[EmailCategory, EmailPriority]:
        """Classify email into category and priority"""
        text = f"{email.subject} {email.body_plain}".lower()
        
        category = self._classify_category(text, email.sender.email if email.sender else "")
        priority = self._classify_priority(
            text, 
            email.sender.email if email.sender else "",
            contact
        )
        
        return category, priority
        
    def _classify_category(self, text: str, sender: str) -> EmailCategory:
        """Classify into category"""
        # Emergency
        emergency_keywords = self.config.emergency_keywords
        if any(kw in text for kw in emergency_keywords):
            return EmailCategory.EMERGENCY
            
        # Finance
        finance_keywords = ["invoice", "payment", "receipt", "transaction", "bank", "gst", "tds", "tax"]
        if any(kw in text for kw in finance_keywords):
            return EmailCategory.FINANCE
            
        # Spam
        spam_keywords = ["unsubscribe", "spam", "click here", "act now", "limited time", "winner"]
        if sum(1 for kw in spam_keywords if kw in text) >= 2:
            return EmailCategory.SPAM
            
        # Promotions
        promo_keywords = ["offer", "discount", "deal", "sale", "promo", "coupon", "free"]
        if sum(1 for kw in promo_keywords if kw in text) >= 2:
            return EmailCategory.PROMOTIONS
            
        # Newsletter
        newsletter_keywords = ["newsletter", "weekly", "digest", "subscribe", "update"]
        if any(kw in text for kw in newsletter_keywords):
            return EmailCategory.NEWSLETTER
            
        # Critical
        critical_keywords = self.config.critical_keywords
        if any(kw in text for kw in critical_keywords):
            return EmailCategory.CRITICAL
            
        # Important
        important_keywords = self.config.important_keywords
        if any(kw in text for kw in important_keywords):
            return EmailCategory.IMPORTANT
            
        # Personal vs Work
        personal_keywords = ["family", "friend", "birthday", "personal", "home"]
        work_keywords = ["work", "office", "business", "client", "project", "report"]
        
        personal_score = sum(1 for kw in personal_keywords if kw in text)
        work_score = sum(1 for kw in work_keywords if kw in text)
        
        if personal_score > work_score:
            return EmailCategory.PERSONAL
        elif work_score > 0:
            return EmailCategory.WORK
            
        # College detection
        domains = [".edu", ".ac.in"]
        if any(d in sender.lower() for d in domains):
            return EmailCategory.COLLEGE
            
        return EmailCategory.NORMAL
        
    def _classify_priority(
        self, 
        text: str, 
        sender: str,
        contact: Optional[Contact] = None
    ) -> EmailPriority:
        """Classify priority level"""
        # Emergency
        emergency_keywords = ["emergency", "urgent", "immediate", "police", "ambulance", "fire"]
        if any(kw in text for kw in emergency_keywords):
            return EmailPriority.P0_EMERGENCY
            
        # VIP contacts always high priority
        if contact and contact.is_vip:
            return EmailPriority.P1_CRITICAL
            
        # Critical
        critical_keywords = ["deadline", "client", "offer", "interview", "faculty", "professor"]
        if any(kw in text for kw in critical_keywords):
            return EmailPriority.P1_CRITICAL
            
        # Important
        important_keywords = ["meeting", "project", "important", "review", "decision"]
        if any(kw in text for kw in important_keywords):
            return EmailPriority.P2_IMPORTANT
            
        return EmailPriority.P3_NORMAL


class ImportanceScorer:
    """Score email importance (0-100)"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def score(self, email: EmailMessage, contact: Optional[Contact] = None) -> float:
        """Calculate importance score"""
        score = 50.0  # Base score
        
        text = f"{email.subject} {email.body_plain}".lower()
        
        # Contact importance (up to +-25)
        if contact:
            score += (contact.importance_level - 50)
            if contact.is_vip:
                score += 20
                
        # Keyword scoring
        keyword_scores = {
            "deadline": 15,
            "urgent": 20,
            "asap": 20,
            "emergency": 30,
            "critical": 25,
            "important": 10,
            "client": 15,
            "project": 10,
            "meeting": 8,
            "interview": 15,
            "offer": 20,
            "internship": 15,
            "job": 12,
            "faculty": 12,
            "professor": 12,
            "invoice": 20,
            "payment": 15,
        }
        for keyword, weight in keyword_scores.items():
            if keyword in text:
                score += weight
                
        # Deadline detection (up to +20)
        if self._has_deadline(text):
            score += 20
            
        # Reply expectation (up to +10)
        if self._has_reply_question(text):
            score += 10
            
        # Attachment bonus (up to +8)
        if email.has_attachments:
            score += 8
            # Verify document type for additional score
            for att in email.attachments:
                doc_types = ["pdf", "doc", "docx", "xls", "xlsx"]
                if any(att.get("type", "").lower().startswith(dt) for dt in doc_types):
                    score += 5
                    break
                    
        # Time sensitivity (up to +10)
        if self._is_time_sensitive(text):
            score += 10
            
        # Cap at 100
        return min(100.0, max(0.0, score))
        
    def _has_deadline(self, text: str) -> bool:
        """Detect deadline mentions"""
        deadline_patterns = [
            r"deadline[:\s]+\w+",
            r"by\s+\w+\s+\d{1,2}",
            r"due\s+(?:date|on|in)",
            r"before\s+\w+",
            r"within\s+\d+\s*(?:hours?|days?|weeks?)",
            r"by\s+end\s+of\s+(?:day|week|month)",
            r"today",
            r"tonight",
            r"\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
        ]
        return any(re.search(p, text) for p in deadline_patterns)
        
    def _has_reply_question(self, text: str) -> bool:
        """Detect reply expectation"""
        question_patterns = [
            r"\?",
            r"please\s+(?:let\s+me\s+know|confirm|reply)",
            r"could\s+you",
            r"would\s+you",
            r"let\s+me\s+know",
            r"waiting\s+for",
            r"期待.*回复",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in question_patterns)
        
    def _is_time_sensitive(self, text: str) -> bool:
        """Detect time sensitivity"""
        time_keywords = ["today", "tomorrow", "asap", "urgent", "immediate", "quickly", "hurry"]
        return any(kw in text for kw in time_keywords)


class IntentDetector:
    """Detect email intents"""
    
    INTENT_PATTERNS = {
        "meeting_request": [
            r"schedule", r"meeting", r"calendar", r"available", r"call.*\?",
            r"安排.*会议", r"meeting.*\?"
        ],
        "document_request": [
            r"send.*(?:document|file|report|resume|cv)",
            r"attach", r"document", r"report"
        ],
        "approval_request": [
            r"approve", r"approval", r"authorize", r"permission",
            r"批准|审批"
        ],
        "payment_request": [
            r"payment", r"invoice", r"fee", r"charge", r"amount",
            r"付款|账单"
        ],
        "information_request": [
            r"tell\s+(?:me\s+)?(?:about|us)", r"information", r"details",
            r"query", r"question"
        ],
        "feedback_request": [
            r"feedback", r"review", r"comment", r"suggestion", r"opinion"
        ],
        "follow_up": [
            r"follow[\s_-]?up", r"just.*checking", r"any.*update",
            r"追", r"followup"
        ],
        "rsvp": [
            r"rsvp", r"(?:will\s+)?(?:you\s+)?attend", r"confirm.*attendance",
            r"请.*回复", r"(?:是否)?参加"
        ],
    }
    
    def detect(self, text: str) -> List[str]:
        """Detect intents from text"""
        intents = []
        text_lower = text.lower()
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    intents.append(intent)
                    break
                    
        return intents


class EmailParser:
    """Parse raw email into structured format"""
    
    def __init__(self):
        if HTML2TEXT_AVAILABLE:
            self.html_converter = html2text.HTML2Text()
            self.html_converter.ignore_links = False
            self.html_converter.ignore_images = True
        else:
            self.html_converter = None
        
    def parse(self, raw_email: str) -> EmailMessage:
        """Parse raw email message"""
        msg = email.message_from_string(raw_email)
        email_msg = EmailMessage()
        
        # Message ID
        email_msg.message_id = msg.get("Message-ID", "") or msg.get("Message-Id", "") or ""
        email_msg.message_id = email_msg.message_id.strip("<>")
        
        # Thread ID
        email_msg.thread_id = msg.get("Thread-Index", "") or msg.get("References", "").split()[-1] if msg.get("References") else ""
        
        # Subject
        subject = self._decode_header(msg.get("Subject", ""))
        email_msg.subject = subject
        
        # Sender
        from_addr = msg.get("From", "")
        sender_email, sender_name = self._parse_address(from_addr)
        email_msg.sender = EmailAddress(sender_email, sender_name)
        
        # Recipients
        to_addr = msg.get("To", "")
        for addr in to_addr.split(","):
            addr = addr.strip()
            if addr:
                email_addr, name = self._parse_address(addr)
                if email_addr:
                    email_msg.recipients.append(EmailAddress(email_addr, name))
                    
        # CC
        cc_addr = msg.get("Cc", "")
        for addr in cc_addr.split(","):
            addr = addr.strip()
            if addr:
                email_addr, name = self._parse_address(addr)
                if email_addr:
                    email_msg.cc.append(EmailAddress(email_addr, name))
                    
        # Date
        date_str = msg.get("Date", "")
        email_msg.date_sent = self._parse_date(date_str) or datetime.utcnow()
        
        # Body
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain" and not email_msg.body_plain:
                    email_msg.body_plain = self._get_payload(part)
                elif content_type == "text/html" and not email_msg.body_html:
                    email_msg.body_html = self._get_payload(part)
        else:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                email_msg.body_html = msg.get_payload()
            else:
                email_msg.body_plain = str(msg.get_payload())
                
        # Convert HTML to plain text
        if email_msg.body_html and not email_msg.body_plain:
            try:
                if self.html_converter:
                    email_msg.body_plain = self.html_converter.handle(email_msg.body_html)
                else:
                    # Simple HTML stripping fallback
                    soup = BeautifulSoup(email_msg.body_html, "html.parser")
                    email_msg.body_plain = soup.get_text(separator=" ", strip=True)
            except:
                email_msg.body_plain = email_msg.body_html
                
        # Snippet
        email_msg.snippet = format_email_preview(email_msg.body_plain)
        
        # Attachments
        self._parse_attachments(msg, email_msg)
        
        # Headers
        for key, value in msg.items():
            email_msg.headers[key] = value
            
        return email_msg
        
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        decoded_parts = decode_header(header)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or "utf-8", errors="replace"))
                except:
                    result.append(part.decode("utf-8", errors="replace"))
            else:
                result.append(part)
        return " ".join(result)
        
    DELEM_REGEX = re.compile(r'[<>/;,\s]+')

    def _parse_address(self, address: str) -> Tuple[str, str]:
        """Parse email address with optional name"""
        if not address:
            return "", ""
            
        # Try to extract email and name
        match = re.search(r'"?([^"<]*)"?\s*<([^>]+)>', address)
        if match:
            return match.group(2).strip(), match.group(1).strip()
            
        # Just email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', address)
        if email_match:
            return email_match.group(0).lower(), ""
            
        return "", ""
        
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date"""
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except:
            try:
                return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            except:
                return None
                
    def _get_payload(self, part) -> str:
        """Get decoded payload"""
        try:
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload()
            if isinstance(payload, bytes):
                return payload.decode(charset, errors="replace")
            return str(payload)
        except:
            return ""
            
    def _parse_attachments(self, msg, email_msg: EmailMessage) -> None:
        """Parse attachments"""
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition", ""))
            
            if "attachment" in content_disposition or part.get_filename():
                filename = part.get_filename() or "unknown"
                filename = self._decode_header(filename)
                content_type = part.get_content_type()
                
                try:
                    payload = part.get_payload(decode=True)
                    size = len(payload) if payload else 0
                    
                    email_msg.attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": size,
                        "data": payload,
                        "is_inline": "inline" in content_disposition,
                    })
                    email_msg.has_attachments = True
                except:
                    pass


class EmailSender:
    """Send emails via SMTP"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def send(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_html: bool = False,
    ) -> bool:
        """Send email"""
        if not self.config.smtp_username or not self.config.smtp_password:
            logger.error("SMTP credentials not configured")
            return False
            
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.smtp_username
            
            # To recipients
            to_str = ", ".join(to) if isinstance(to, list) else to
            msg["To"] = to_str
            
            # CC
            if cc:
                msg["Cc"] = ", ".join(cc)
                to = to + cc
                
            # Body
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
                
            # Attachments
            if attachments:
                for att in attachments:
                    self._add_attachment(msg, att)
                    
            # Send
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_use_tls:
                    server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.sendmail(self.config.smtp_username, to, msg.as_string())
                
            logger.info(f"Email sent to {to_str}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
            
    def _add_attachment(self, msg, attachment: Dict[str, Any]) -> None:
        """Add attachment to message"""
        filename = attachment.get("filename", "attachment")
        data = attachment.get("data", b"")
        
        part = MIMEBase("application", "octet-stream")
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)


class IMAPClient:
    """IMAP email client"""
    
    def __init__(self, config: Config):
        self.config = config
        self.connection = None
        
    def connect(self, username: str, password: str) -> bool:
        """Connect to IMAP server"""
        try:
            if self.config.imap_use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.config.imap_host, self.config.imap_port)
            else:
                self.connection = imaplib.IMAP4(self.config.imap_host, self.config.imap_port)
                
            self.connection.login(username, password)
            logger.info(f"Connected to IMAP: {self.config.imap_host}")
            return True
            
        except Exception as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
            
    def disconnect(self) -> None:
        """Disconnect from IMAP"""
        if self.connection:
            try:
                self.connection.logout()
            except:
                pass
            self.connection = None
            
    def list_folders(self) -> List[str]:
        """List available folders"""
        if not self.connection:
            return []
            
        try:
            _, folders = self.connection.list()
            return [f.decode().split('"."')[-1].strip('"') for f in folders]
        except Exception as e:
            logger.error(f"Failed to list folders: {e}")
            return []
            
    def fetch_emails(
        self, 
        folder: str = "INBOX",
        limit: int = 100,
        since_date: Optional[datetime] = None
    ) -> List[Tuple[str, EmailMessage]]:
        """Fetch emails from folder"""
        if not self.connection:
            return []
            
        emails = []
        
        try:
            self.connection.select(folder)
            
            # Build search criteria
            criteria = "ALL"
            if since_date:
                criteria = f'SINCE {since_date.strftime("%d-%b-%Y")}'
                
            _, message_ids = self.connection.search(None, criteria)
            
            # Fetch last N emails
            ids = message_ids[0].split()
            to_fetch = ids[-limit:] if len(ids) > limit else ids
            
            parser = EmailParser()
            
            for msg_id in to_fetch:
                try:
                    _, data = self.connection.fetch(msg_id, "(RFC822)")
                    if data and data[0]:
                        raw = data[0][1]
                        email_msg = parser.parse(raw.decode("utf-8", errors="replace"))
                        emails.append((msg_id.decode(), email_msg))
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            
        return emails
        
    def mark_read(self, message_ids: List[str], folder: str = "INBOX") -> None:
        """Mark emails as read"""
        if not self.connection or not message_ids:
            return
            
        try:
            self.connection.select(folder)
            for msg_id in message_ids:
                self.connection.store(msg_id, "+FLAGS", "\\Seen")
        except Exception as e:
            logger.error(f"Failed to mark emails as read: {e}")
            
    def delete_emails(self, message_ids: List[str], folder: str = "INBOX") -> None:
        """Delete emails"""
        if not self.connection or not message_ids:
            return
            
        try:
            self.connection.select(folder)
            for msg_id in message_ids:
                self.connection.store(msg_id, "+FLAGS", "\\Deleted")
            self.connection.expunge()
        except Exception as e:
            logger.error(f"Failed to delete emails: {e}")


class EmailEngine(DragonModule):
    """Main email processing engine"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.classifier = EmailClassifier(config)
        self.scorer = ImportanceScorer(config)
        self.intent_detector = IntentDetector()
        self.sender = EmailSender(config)
        self.imap = None  # Will be set when integrations are available
        self.integration_manager = None  # Will be set from main
        self.parser = EmailParser()
        self._sync_active = False
        
        # Register event handlers
        events.on("email_new", self._on_new_email)
        events.on("email_reply_sent", self._on_reply_sent)
        
    def set_integration_manager(self, im: 'IntegrationManager') -> None:
        """Set integration manager for email sync"""
        self.integration_manager = im
        self.imap = im.imap
        
    def initialize(self) -> None:
        """Initialize email engine"""
        super().initialize()
        logger.info("Email Engine initialized")
        
    def sync_all_accounts(self) -> Dict[str, Any]:
        """Sync emails from all configured accounts"""
        results = {}
        
        if not self.integration_manager:
            logger.warning("No integration manager set - cannot sync emails")
            return results
            
        for email, provider in self.integration_manager._active_accounts.items():
            self.logger.info(f"Syncing {email} via {provider}")
            try:
                results[email] = self.sync_email(email)
            except Exception as e:
                self.logger.error(f"Sync failed for {email}: {e}")
                results[email] = {"error": str(e)}
                
        return results
        
    def sync_email(self, account: str = "primary") -> Dict[str, Any]:
        """Sync emails from account"""
        status = {
            "synced": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
        }
        
        self.logger.info(f"Starting email sync for {account}")
        
        try:
            # This would integrate with Gmail API or IMAP
            # For now, we'll use IMAP as example
            emails = self.imap.fetch_emails(limit=self.config.batch_size)
            
            for msg_id, email_msg in emails:
                try:
                    with self.db.get_session() as session:
                        existing = session.query(Email).filter(
                            Email.message_id == email_msg.message_id
                        ).first()
                    
                    if not existing:
                        self._process_and_store_email(email_msg, account)
                        status["new"] += 1
                    else:
                        status["updated"] += 1
                        
                    status["synced"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process email: {e}")
                    status["errors"] += 1
                    
            # Cleanup old emails
            self._cleanup_old_emails()
            
        except Exception as e:
            logger.error(f"Email sync failed: {e}")
            
        return status
        
    def _process_and_store_email(
        self, 
        email_msg: EmailMessage,
        account: str
    ) -> Email:
        """Process and store email"""
        # Get or create contact
        contact = self._get_or_create_contact(email_msg.sender)
        
        # Classify
        category, priority = self.classifier.classify(email_msg, contact)
        
        # Score
        importance_score = self.scorer.score(email_msg, contact)
        
        # Detect intents
        text = f"{email_msg.subject} {email_msg.body_plain}"
        intents = self.intent_detector.detect(text)
        
        # Create email record
        db_email = Email(
            message_id=email_msg.message_id,
            thread_id=email_msg.thread_id,
            sender_email=email_msg.sender.email,
            sender_name=email_msg.sender.name,
            recipient_email=email_msg.recipients[0].email if email_msg.recipients else account,
            subject=email_msg.subject,
            body_plain=email_msg.body_plain[:10000],  # Limit body size
            body_html=email_msg.body_html[:20000],
            snippet=email_msg.snippet,
            date_sent=email_msg.date_sent,
            date_received=datetime.utcnow(),
            category=category,
            priority=priority,
            importance_score=importance_score,
            direction=EmailDirection.INCOMING,
            has_attachments=email_msg.has_attachments,
            attachment_count=len(email_msg.attachments),
            keywords=intents,
            detected_intents=intents,
            source_account=account,
            contact_id=contact.id if contact else None,
        )
        
        with self.db.get_session() as session:
            session.add(db_email)
            session.flush()
            
            # Handle attachments
            for att in email_msg.attachments:
                attachment = Attachment(
                    email_id=db_email.id,
                    filename=att.get("filename", "unknown"),
                    content_type=att.get("content_type", "application/octet-stream"),
                    size_bytes=att.get("size", 0),
                    is_inline=att.get("is_inline", False),
                )
                session.add(attachment)
                
            # Update contact
            if contact:
                contact.total_emails += 1
                contact.last_contact_at = datetime.utcnow()
                
        # Process automation rules
        self._process_rules(db_email)
        
        # Emit new email event
        events.emit("email_new", email=db_email)
        
        return db_email
        
    def _get_or_create_contact(self, sender: EmailAddress) -> Optional[Contact]:
        """Get or create contact"""
        with self.db.get_session() as session:
            existing = session.query(Contact).filter(
                Contact.email == sender.email
            ).first()
            
            if existing:
                return existing
                
            # Create new contact
            contact = Contact(
                email=sender.email,
                name=sender.name,
                display_name=sender.name or sender.email.split("@")[0],
                importance_level=50,
            )
            session.add(contact)
            session.flush()
            return contact
            
    def _process_rules(self, db_email: Email) -> None:
        """Process automation rules"""
        # Rule processing is handled by the automation engine
        # This placeholder is replaced at runtime
        pass
            
    def _cleanup_old_emails(self) -> None:
        """Clean up old emails based on retention policy"""
        cutoff_date = datetime.utcnow() - timedelta(days=self.config.max_email_age_days)
        
        with self.db.get_session() as session:
            session.query(Email).filter(
                Email.date_received < cutoff_date,
                Email.is_deleted == True
            ).delete()
            
    def _on_new_email(self, email: Email) -> None:
        """Handle new email event"""
        self.logger.info(f"New email: {email.subject[:50]}")
        
        # Generate high-priority alert if P0
        if email.priority == EmailPriority.P0_EMERGENCY:
            events.emit("escalation_trigger", email=email, level=5)
            
    def _on_reply_sent(self, original_email: Email) -> None:
        """Handle reply sent event"""
        with self.db.get_session() as session:
            email = session.query(Email).filter(Email.id == original_email.id).first()
            if email:
                email.is_replied = True
                email.action_required = False
                
    def draft_reply(
        self,
        original_email: Email,
        body: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        is_draft: bool = True,
    ) -> bool:
        """Draft or send reply"""
        subject = original_email.subject
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"
            
        if self.sender.send(
            to=[original_email.sender_email],
            subject=subject,
            body=body,
            cc=cc,
            attachments=attachments,
        ):
            original_email.is_replied = True
            events.emit("email_reply_sent", email=original_email)
            return True
            
        return False
        
    def draft_forward(
        self,
        original_email: Email,
        to: List[str],
        body: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """Forward email"""
        forward_body = body or ""
        forward_body += f"\n\n--- Forwarded message ---\nFrom: {original_email.sender_name or original_email.sender_email}\nDate: {original_email.date_sent}\nSubject: {original_email.subject}\n\n{original_email.body_plain}"
        
        return self.sender.send(
            to=to,
            subject=f"Fwd: {original_email.subject}",
            body=forward_body,
            attachments=attachments,
        )
        
    def get_daily_summary(self) -> Dict[str, Any]:
        """Generate daily email summary"""
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        with self.db.get_session() as session:
            all_emails = session.query(Email).filter(
                Email.date_received >= start_of_day,
                Email.direction == EmailDirection.INCOMING
            ).all()
            
            unread = session.query(Email).filter(
                Email.date_received >= start_of_day,
                Email.is_read == False,
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            important = [e for e in all_emails if e.importance_score >= 70]
            
            breakdown = {}
            for email in all_emails:
                cat = email.category.value
                breakdown[cat] = breakdown.get(cat, 0) + 1
                
            return {
                "date": today.isoformat(),
                "total_received": len(all_emails),
                "unread": unread,
                "important_emails": [
                    {
                        "id": e.id,
                        "subject": e.subject,
                        "from": e.sender_name or e.sender_email,
                        "score": e.importance_score,
                        "priority": e.priority.value,
                    }
                    for e in sorted(important, key=lambda x: x.importance_score, reverse=True)[:10]
                ],
                "breakdown": breakdown,
                "pending_replies": session.query(Email).filter(
                    Email.action_required == True,
                    Email.is_replied == False
                ).count(),
            }
            
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        self.imap.disconnect()
        logger.info("Email Engine shutdown complete")
