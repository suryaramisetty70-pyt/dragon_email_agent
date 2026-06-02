# =============================================================================
# DATABASE MODULE - SQLite & PostgreSQL Support
# =============================================================================

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from contextlib import contextmanager
import threading
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, Boolean,
    Float, ForeignKey, Enum as SQLEnum, CLOB, JSON, Index, UniqueConstraint,
    func, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

Base = declarative_base()

# Local imports (delayed to avoid circular dependencies)
# from ..security.encryption import EncryptionService  # Will be imported lazily when needed


class EmailCategory(Enum):
    """Email classification categories"""
    EMERGENCY = "emergency"
    CRITICAL = "critical"
    IMPORTANT = "important"
    WORK = "work"
    PERSONAL = "personal"
    FINANCE = "finance"
    COLLEGE = "college"
    SPAM = "spam"
    NEWSLETTER = "newsletter"
    PROMOTIONS = "promotions"
    NORMAL = "normal"
    LOW_PRIORITY = "low_priority"


class EmailPriority(Enum):
    """Email priority levels"""
    P0_EMERGENCY = 0
    P1_CRITICAL = 1
    P2_IMPORTANT = 2
    P3_NORMAL = 3
    P4_LOW = 4


class EmailDirection(Enum):
    """Email direction"""
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    DRAFT = "draft"


# =============================================================================
# DATABASE MODELS
# =============================================================================

class Contact(Base):
    """Contact model"""
    __tablename__ = "contacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    category = Column(String(50), default="general")  # family, friend, faculty, client, team
    importance_level = Column(Integer, default=50)  # 0-100
    relationship_type = Column(String(50), default="general")
    organization = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    preferences = Column(JSON, default=dict)  # preferred_response_time, communication_style
    meta_data = Column(JSON, default=dict)
    first_contact_at = Column(DateTime, default=datetime.utcnow)
    last_contact_at = Column(DateTime, default=datetime.utcnow)
    total_emails = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)
    is_vip = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_contact_email_name", "email", "name"),
        Index("idx_contact_vip", "is_vip"),
        Index("idx_contact_category", "category"),
    )


class Email(Base):
    """Email message model"""
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    thread_id = Column(String(500), nullable=True, index=True)
    
    # Sender & Recipients
    sender_email = Column(String(255), nullable=False, index=True)
    sender_name = Column(String(255), nullable=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    cc_list = Column(JSON, default=list)
    bcc_list = Column(JSON, default=list)
    
    # Email Content
    subject = Column(Text, nullable=False)
    body_plain = Column(Text, nullable=True)
    body_html = Column(Text, nullable=True)
    snippet = Column(Text, nullable=True)
    
    # Metadata
    date_sent = Column(DateTime, nullable=False, index=True)
    date_received = Column(DateTime, default=datetime.utcnow, index=True)
    date_created = Column(DateTime, default=datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Classification
    category = Column(SQLEnum(EmailCategory), default=EmailCategory.NORMAL, index=True)
    priority = Column(SQLEnum(EmailPriority), default=EmailPriority.P3_NORMAL, index=True)
    importance_score = Column(Float, default=50.0, index=True)  # 0-100
    direction = Column(SQLEnum(EmailDirection), default=EmailDirection.INCOMING)
    
    # Processing
    is_read = Column(Boolean, default=False, index=True)
    is_starred = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False, index=True)
    is_pinned = Column(Boolean, default=False, index=True)
    is_draft = Column(Boolean, default=False, index=True)
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    
    # NLP & AI
    summary = Column(Text, nullable=True)
    sentiment = Column(String(20), nullable=True)  # positive, negative, neutral
    keywords = Column(JSON, default=list)
    detected_intents = Column(JSON, default=list)  # meeting_request, invoice, etc.
    is_replied = Column(Boolean, default=False, index=True)
    is_forwarded = Column(Boolean, default=False)
    
    # Interaction
    action_required = Column(Boolean, default=False)
    action_deadline = Column(DateTime, nullable=True)
    action_type = Column(String(100), nullable=True)  # reply, follow_up, schedule, etc.
    follow_up_date = Column(DateTime, nullable=True)
    follow_up_reminded = Column(Boolean, default=False)
    
    # Source
    source_account = Column(String(100), nullable=False)  # gmail, outlook, imap
    source_labels = Column(JSON, default=list)
    gmail_labels = Column(JSON, default=list)
    
    # Embedding Reference
    embedding_id = Column(String(255), nullable=True, index=True)
    
    # Contact relationship
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    
    attachments = relationship("Attachment", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_email_priority_score", "priority", "importance_score"),
        Index("idx_email_date_priority", "date_sent", "priority"),
        Index("idx_email_unread_pinned", "is_read", "is_pinned"),
        Index("idx_email_contact_action", "contact_id", "action_required"),
    )


class Attachment(Base):
    """Email attachment model"""
    __tablename__ = "attachments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, default=0)
    storage_path = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)
    is_inline = Column(Boolean, default=False)
    extraction_status = Column(String(50), default="pending")  # pending, processed, failed
    extracted_text = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_attachment_email", "email_id"),
        Index("idx_attachment_type", "content_type"),
    )


class Thread(Base):
    """Email thread model"""
    __tablename__ = "threads"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(500), unique=True, nullable=False, index=True)
    subject = Column(Text, nullable=False)
    participant_emails = Column(JSON, default=list)
    participant_count = Column(Integer, default=0)
    message_count = Column(Integer, default=0)
    last_message_date = Column(DateTime, nullable=True, index=True)
    last_sender = Column(String(255), nullable=True)
    is_read = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    category = Column(SQLEnum(EmailCategory), default=EmailCategory.NORMAL)
    priority = Column(SQLEnum(EmailPriority), default=EmailPriority.P3_NORMAL)
    max_priority = Column(SQLEnum(EmailPriority), default=EmailPriority.P3_NORMAL)
    max_importance_score = Column(Float, default=50.0)
    sentiment = Column(String(20), nullable=True)
    action_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_thread_priority", "priority", "last_message_date"),
        Index("idx_thread_participants", "participant_emails"),
    )


class Escalation(Base):
    """Escalation tracking model"""
    __tablename__ = "escalations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    escalation_level = Column(Integer, nullable=False)  # 1-5
    reason = Column(Text, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    notification_sent = Column(Boolean, default=False)
    notification_type = Column(String(50), nullable=True)  # desktop, voice, fullscreen, dragon, calling
    notes = Column(Text, nullable=True)
    
    __table_args__ = (
        Index("idx_escalation_email", "email_id"),
        Index("idx_escalation_level", "escalation_level"),
    )


class FollowUp(Base):
    """Follow-up tracking model"""
    __tablename__ = "follow_ups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    scheduled_date = Column(DateTime, nullable=False, index=True)
    reminder_date = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    reminder_sent = Column(Boolean, default=False)
    reminder_type = Column(String(50), default="notification")  # notification, desktop, voice, dragon
    status = Column(String(50), default="pending")  # pending, sent, completed, skipped
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_followup_scheduled", "scheduled_date"),
        Index("idx_followup_contact", "contact_id"),
        Index("idx_followup_status", "status"),
    )


class Rule(Base):
    """Automation rule model"""
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # keyword, sender, category, priority, schedule
    trigger_conditions = Column(JSON, default=dict)
    actions = Column(JSON, default=list)  # [{action_type, params}]
    priority = Column(Integer, default=50)  # Higher = higher priority
    is_enabled = Column(Boolean, default=True, index=True)
    is_system = Column(Boolean, default=False)  # System rules cannot be deleted
    execution_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    last_triggered_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_rule_enabled_priority", "is_enabled", "priority"),
    )


class ScheduledEmail(Base):
    """Scheduled email model"""
    __tablename__ = "scheduled_emails"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_data = Column(JSON, nullable=False)  # Serialized email data
    scheduled_at = Column(DateTime, nullable=False, index=True)
    sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    failed = Column(Boolean, default=False)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_scheduled_pending", "scheduled_at", "sent"),
    )


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # email, contact, rule, etc.
    entity_id = Column(Integer, nullable=True)
    user = Column(String(255), nullable=True)
    ip_address = Column(String(50), nullable=True)
    details = Column(JSON, default=dict)
    status = Column(String(50), default="success")  # success, failed, partial
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_created", "created_at"),
    )


class Conversation(Base):
    """Conversation memory model"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String(500), nullable=True)
    subject = Column(Text, nullable=True)
    participant_emails = Column(JSON, default=list)
    message_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    key_points = Column(JSON, default=list)
    decisions = Column(JSON, default=list)
    action_items = Column(JSON, default=list)
    sentiment_trend = Column(String(20), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    embedding_id = Column(String(255), nullable=True, index=True)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_conversation_thread", "thread_id"),
    )


class QuickAction(Base):
    """Quick action template model"""
    __tablename__ = "quick_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    command = Column(String(255), nullable=False, unique=True)  # voice command trigger
    action_type = Column(String(50), nullable=False)  # reply, forward, archive, etc.
    template_data = Column(JSON, default=dict)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyBriefing(Base):
    """Daily briefing cache model"""
    __tablename__ = "daily_briefings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    summary = Column(JSON, default=dict)
    important_emails = Column(JSON, default=list)
    unread_count = Column(Integer, default=0)
    pending_replies = Column(Integer, default=0)
    deadlines = Column(JSON, default=list)
    meetings = Column(JSON, default=list)
    productivity_metrics = Column(JSON, default=dict)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("date", name="uq_daily_briefing_date"),
    )


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path: str = "data/dragon_email.db", use_sqlite: bool = True):
        self.db_path = db_path
        self.use_sqlite = use_sqlite
        self.engine = None
        self.session_factory = None
        self._lock = threading.Lock()
        self._initialized = False
        
    def initialize(self) -> None:
        """Initialize database connection"""
        if self._initialized:
            return
            
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        if self.use_sqlite:
            # SQLite with WAL mode for better concurrency
            connection_string = f"sqlite:///{self.db_path}"
            self.engine = create_engine(
                connection_string,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,
                },
                pool_pre_ping=True,
                echo=False,
            )
        else:
            # PostgreSQL for production
            connection_string = os.getenv(
                "DATABASE_URL", 
                "postgresql://user:password@localhost/dragon_email"
            )
            self.engine = create_engine(
                connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
            )
        
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
        )
        
        # Create all tables
        Base.metadata.create_all(self.engine)
        self._initialized = True
        
        # Setup default rules
        self._setup_default_rules()
        
    def _setup_default_rules(self) -> None:
        """Setup default automation rules"""
        default_rules = [
            {
                "name": "Tax/Invoice Forwarding",
                "trigger_type": "keyword",
                "trigger_conditions": {
                    "keywords": ["invoice", "tax", "gst", "tds", "receipt"]
                },
                "actions": [
                    {"action_type": "highlight", "params": {"color": "red"}},
                    {"action_type": "forward_to", "params": {"agent": "ca"}},
                ],
                "priority": 100,
                "is_system": True,
                "description": "Auto-detect and forward financial documents"
            },
            {
                "name": "Internship Opportunity Alert",
                "trigger_type": "keyword",
                "trigger_conditions": {
                    "keywords": ["internship", "intern", "job", "position", "vacancy", "opening"]
                },
                "actions": [
                    {"action_type": "highlight", "params": {"color": "blue"}},
                    {"action_type": "set_priority", "params": {"priority": "P1"}},
                ],
                "priority": 90,
                "is_system": True,
                "description": "Priority alert for career opportunities"
            },
            {
                "name": "Faculty Communication",
                "trigger_type": "sender",
                "trigger_conditions": {
                    "domains": [".edu", ".ac.in", "university"]
                },
                "actions": [
                    {"action_type": "highlight", "params": {"color": "purple"}},
                    {"action_type": "set_category", "params": {"category": "COLLEGE"}},
                ],
                "priority": 95,
                "is_system": True,
                "description": "Highlight emails from educational institutions"
            },
            {
                "name": "Emergency Detection",
                "trigger_type": "keyword",
                "trigger_conditions": {
                    "keywords": ["emergency", "urgent", "immediate", "critical", "asap", "help", "police", "ambulance"]
                },
                "actions": [
                    {"action_type": "set_priority", "params": {"priority": "P0"}},
                    {"action_type": "escalate", "params": {"level": 5}},
                    {"action_type": "voice_alert", "params": {"message": "Emergency email detected"}},
                ],
                "priority": 100,
                "is_system": True,
                "description": "Emergency escalation for critical situations"
            },
            {
                "name": "Client Follow-up",
                "trigger_type": "category",
                "trigger_conditions": {
                    "category": "WORK",
                    "is_replied": False,
                    "hours_since_sent": 6
                },
                "actions": [
                    {"action_type": "create_follow_up", "params": {"reminder": "2 hours"}},
                    {"action_type": "escalate", "params": {"level": 3}},
                ],
                "priority": 80,
                "is_system": True,
                "description": "Auto-escalate unanswered client emails"
            },
        ]
        
        for rule_data in default_rules:
            with self.get_session() as session:
                existing = session.query(Rule).filter(
                    Rule.name == rule_data["name"]
                ).first()
                if not existing:
                    rule = Rule(**rule_data)
                    session.add(rule)
        
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager"""
        if not self._initialized:
            self.initialize()
            
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            
    def get_raw_connection(self):
        """Get raw connection for complex queries"""
        if not self._initialized:
            self.initialize()
        return self.engine.raw_connection()
        
    def vacuum(self):
        """Optimize database"""
        if self.use_sqlite:
            with self.get_raw_connection() as conn:
                conn.execute("VACUUM")
                
    def backup(self, backup_path: str) -> None:
        """Create database backup"""
        if self.use_sqlite:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()


# =============================================================================
# QUERY HELPERS
# =============================================================================

class EmailQueryHelper:
    """Helper for common email queries"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    def get_unread_emails(self, limit: int = 100, offset: int = 0) -> List[Email]:
        """Get unread emails"""
        with self.db.get_session() as session:
            return session.query(Email).filter(
                Email.is_read == False,
                Email.is_deleted == False,
                Email.direction == EmailDirection.INCOMING
            ).order_by(
                Email.priority.asc(),
                Email.importance_score.desc(),
                Email.date_received.desc()
            ).limit(limit).offset(offset).all()
            
    def get_important_emails(self, min_score: float = 70.0, limit: int = 50) -> List[Email]:
        """Get important emails by score"""
        with self.db.get_session() as session:
            return session.query(Email).filter(
                Email.importance_score >= min_score,
                Email.is_deleted == False,
                Email.direction == EmailDirection.INCOMING
            ).order_by(
                Email.importance_score.desc(),
                Email.date_received.desc()
            ).limit(limit).all()
            
    def get_pending_replies(self, limit: int = 50) -> List[Email]:
        """Get emails that need replies"""
        with self.db.get_session() as session:
            return session.query(Email).filter(
                Email.action_required == True,
                Email.is_replied == False,
                Email.is_deleted == False,
                Email.direction == EmailDirection.INCOMING
            ).order_by(
                Email.action_deadline.asc(),
                Email.priority.asc()
            ).limit(limit).all()
            
    def get_emails_by_contact(
        self, 
        email: str, 
        limit: int = 100, 
        offset: int = 0,
        direction: Optional[EmailDirection] = None
    ) -> List[Email]:
        """Get emails by contact"""
        with self.db.get_session() as session:
            query = session.query(Email).filter(
                Email.sender_email == email,
                Email.is_deleted == False
            )
            if direction:
                query = query.filter(Email.direction == direction)
            return query.order_by(
                Email.date_received.desc()
            ).limit(limit).offset(offset).all()
            
    def get_emails_by_category(
        self, 
        category: EmailCategory, 
        limit: int = 100,
        unread_only: bool = False
    ) -> List[Email]:
        """Get emails by category"""
        with self.db.get_session() as session:
            query = session.query(Email).filter(
                Email.category == category,
                Email.is_deleted == False
            )
            if unread_only:
                query = query.filter(Email.is_read == False)
            return query.order_by(
                Email.date_received.desc()
            ).limit(limit).all()
            
    def get_emails_by_priority(
        self, 
        priority: EmailPriority, 
        limit: int = 100
    ) -> List[Email]:
        """Get emails by priority"""
        with self.db.get_session() as session:
            return session.query(Email).filter(
                Email.priority == priority,
                Email.is_deleted == False
            ).order_by(
                Email.importance_score.desc(),
                Email.date_received.desc()
            ).limit(limit).all()
            
    def search_emails(
        self,
        query: str,
        limit: int = 100,
        category: Optional[EmailCategory] = None,
        priority: Optional[EmailPriority] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> List[Email]:
        """Search emails by keyword"""
        with self.db.get_session() as session:
            search_pattern = f"%{query}%"
            q = session.query(Email).filter(
                Email.is_deleted == False
            ).filter(
                (Email.subject.ilike(search_pattern)) |
                (Email.body_plain.ilike(search_pattern)) |
                (Email.sender_name.ilike(search_pattern)) |
                (Email.sender_email.ilike(search_pattern))
            )
            
            if category:
                q = q.filter(Email.category == category)
            if priority:
                q = q.filter(Email.priority == priority)
            if date_from:
                q = q.filter(Email.date_received >= date_from)
            if date_to:
                q = q.filter(Email.date_received <= date_to)
                
            return q.order_by(
                Email.importance_score.desc(),
                Email.date_received.desc()
            ).limit(limit).all()
            
    def get_email_counts(self) -> Dict[str, int]:
        """Get email counts by category"""
        with self.db.get_session() as session:
            results = session.query(
                Email.category,
                func.count(Email.id).label("count")
            ).filter(
                Email.is_deleted == False
            ).group_by(Email.category).all()
            
            return {str(row[0]): row[1] for row in results}
            
    def get_recent_threads(self, limit: int = 50) -> List[Thread]:
        """Get recent threads"""
        with self.db.get_session() as session:
            return session.query(Thread).filter(
                Thread.last_message_date.isnot(None)
            ).order_by(
                Thread.last_message_date.desc()
            ).limit(limit).all()


# Singleton instance
_db_manager = None

def get_db_manager(db_path: str = "data/dragon_email.db") -> DatabaseManager:
    """Get or create database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path=db_path)
        _db_manager.initialize()
    return _db_manager
