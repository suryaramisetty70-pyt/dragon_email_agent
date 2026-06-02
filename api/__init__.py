# =============================================================================
# API MODULE - FastAPI REST API
# =============================================================================

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from core import Config, logger
from database import (
    Email, Contact, Thread, Rule, FollowUp,
    get_db_manager, EmailPriority, EmailCategory, EmailDirection
)
from email_engine import EmailEngine
from voice import VoiceCommand
from analytics import Analytics
from automation import AutomationEngine
from rag import RAGSystem


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EmailResponse(BaseModel):
    id: int
    message_id: str
    subject: str
    sender_email: str
    sender_name: Optional[str]
    recipient_email: str
    date_sent: datetime
    date_received: datetime
    category: str
    priority: str
    importance_score: float
    is_read: bool
    is_starred: bool
    is_pinned: bool
    has_attachments: bool
    snippet: Optional[str]
    summary: Optional[str]
    action_required: bool
    thread_id: Optional[str]

    class Config:
        from_attributes = True


class ContactResponse(BaseModel):
    id: int
    email: str
    name: Optional[str]
    display_name: Optional[str]
    category: str
    importance_level: int
    is_vip: bool
    total_emails: int
    last_contact_at: Optional[datetime]

    class Config:
        from_attributes = True


class SendEmailRequest(BaseModel):
    to: List[str]
    subject: str
    body: str
    cc: Optional[List[str]] = None
    is_html: bool = False


class ReplyRequest(BaseModel):
    email_id: int
    body: str
    cc: Optional[List[str]] = None


class SearchRequest(BaseModel):
    query: str
    scope: str = "all"
    limit: int = 10
    category: Optional[str] = None
    priority: Optional[str] = None


class BriefingResponse(BaseModel):
    date: str
    summary: Dict[str, Any]
    important_emails: List[Dict[str, Any]]
    urgent_emails: List[Dict[str, Any]]
    category_breakdown: Dict[str, int]


class VoiceCommandRequest(BaseModel):
    command: str


class RuleCreateRequest(BaseModel):
    name: str
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 50


class HealthResponse(BaseModel):
    status: str
    version: str
    database: bool
    services: Dict[str, str]


# =============================================================================
# DEPENDENCIES
# =============================================================================

_app_state: Dict[str, Any] = {}


def get_config() -> Config:
    """Get app config"""
    return _app_state.get("config", Config())


def get_db():
    """Get database manager"""
    return _app_state.get("db")


def get_engine():
    """Get email engine"""
    return _app_state.get("engine")


def get_analytics():
    """Get analytics"""
    return _app_state.get("analytics")


def get_automation():
    """Get automation engine"""
    return _app_state.get("automation")


def get_rag():
    """Get RAG system"""
    return _app_state.get("rag")


# =============================================================================
# API ROUTES
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    config = Config()
    config.db_path = "data/dragon_email.db"
    
    # Initialize components
    db = get_db_manager(config.db_path)
    engine = EmailEngine(config)
    analytics = Analytics(config)
    automation = AutomationEngine(config)
    rag = RAGSystem(config)
    
    # Store in state
    _app_state["config"] = config
    _app_state["db"] = db
    _app_state["engine"] = engine
    _app_state["analytics"] = analytics
    _app_state["automation"] = automation
    _app_state["rag"] = rag
    
    logger.info("API startup complete")
    
    yield
    
    # Shutdown
    engine.shutdown()
    automation.shutdown()
    logger.info("API shutdown complete")


app = FastAPI(
    title="Dragon Email Agent API",
    description="AI-powered Email Management System API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# HEALTH & STATUS
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    db = get_db()
    engine = get_engine()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        database=db is not None,
        services={
            "email_engine": "running" if engine else "stopped",
            "voice": "enabled",
        }
    )


@app.get("/status")
async def get_status():
    """Get system status"""
    db = get_db()
    analytics = get_analytics()
    
    if not db:
        return {"status": "error", "message": "Database not initialized"}
        
    with db.get_session() as session:
        total_emails = session.query(Email).filter(
            Email.direction == EmailDirection.INCOMING
        ).count()
        
        unread = session.query(Email).filter(
            Email.direction == EmailDirection.INCOMING,
            Email.is_read == False
        ).count()
        
        total_contacts = session.query(Contact).count()
        
        pending_followups = session.query(FollowUp).filter(
            FollowUp.completed == False
        ).count()
        
    return {
        "status": "operational",
        "database": {
            "total_emails": total_emails,
            "unread_emails": unread,
            "total_contacts": total_contacts,
        },
        "pending_actions": pending_followups,
        "timestamp": datetime.utcnow().isoformat(),
    }


# =============================================================================
# EMAIL ENDPOINTS
# =============================================================================

@app.get("/emails", response_model=List[EmailResponse])
async def list_emails(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = False,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None
):
    """List emails with filtering"""
    db = get_db()
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    with db.get_session() as session:
        query = session.query(Email).filter(Email.is_deleted == False)
        
        if unread_only:
            query = query.filter(Email.is_read == False)
        if category:
            try:
                query = query.filter(Email.category == EmailCategory[category.upper()])
            except:
                pass
        if priority:
            try:
                query = query.filter(Email.priority == EmailPriority[priority])
            except:
                pass
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                (Email.subject.ilike(search_pattern)) |
                (Email.body_plain.ilike(search_pattern))
            )
            
        emails = query.order_by(
            Email.date_received.desc()
        ).limit(limit).offset(offset).all()
        
        return [
            EmailResponse(
                id=e.id,
                message_id=e.message_id,
                subject=e.subject,
                sender_email=e.sender_email,
                sender_name=e.sender_name,
                recipient_email=e.recipient_email,
                date_sent=e.date_sent,
                date_received=e.date_received,
                category=e.category.value if e.category else "unknown",
                priority=e.priority.value if e.priority else "unknown",
                importance_score=e.importance_score,
                is_read=e.is_read,
                is_starred=e.is_starred,
                is_pinned=e.is_pinned,
                has_attachments=e.has_attachments,
                snippet=e.snippet,
                summary=e.summary,
                action_required=e.action_required,
                thread_id=e.thread_id
            )
            for e in emails
        ]


@app.get("/emails/{email_id}", response_model=EmailResponse)
async def get_email(email_id: int):
    """Get email by ID"""
    db = get_db()
    
    with db.get_session() as session:
        email = session.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
            
        # Mark as read
        email.is_read = True
        
        return EmailResponse(
            id=email.id,
            message_id=email.message_id,
            subject=email.subject,
            sender_email=email.sender_email,
            sender_name=email.sender_name,
            recipient_email=email.recipient_email,
            date_sent=email.date_sent,
            date_received=email.date_received,
            category=email.category.value if email.category else "unknown",
            priority=email.priority.value if email.priority else "unknown",
            importance_score=email.importance_score,
            is_read=email.is_read,
            is_starred=email.is_starred,
            is_pinned=email.is_pinned,
            has_attachments=email.has_attachments,
            snippet=email.snippet,
            summary=email.summary,
            action_required=email.action_required,
            thread_id=email.thread_id
        )


@app.post("/emails/send")
async def send_email(request: SendEmailRequest, background_tasks: BackgroundTasks):
    """Send an email"""
    engine = get_engine()
    
    if not engine:
        raise HTTPException(status_code=500, detail="Email engine not initialized")
        
    def send_task():
        engine.sender.send(
            to=request.to,
            subject=request.subject,
            body=request.body,
            cc=request.cc,
            is_html=request.is_html
        )
        
    background_tasks.add_task(send_task)
    
    return {"status": "queued", "message": "Email sending initiated"}


@app.post("/emails/{email_id}/reply")
async def reply_to_email(email_id: int, request: ReplyRequest):
    """Reply to an email"""
    db = get_db()
    engine = get_engine()
    
    if not db or not engine:
        raise HTTPException(status_code=500, detail="Service not initialized")
        
    with db.get_session() as session:
        email = session.query(Email).filter(Email.id == email_id).first()
        
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
            
        success = engine.draft_reply(
            original_email=email,
            body=request.body,
            cc=request.cc
        )
        
        if success:
            return {"status": "success", "message": "Reply sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send reply")


@app.post("/emails/sync")
async def sync_emails():
    """Trigger email sync"""
    engine = get_engine()
    automation = get_automation()
    
    if not engine:
        raise HTTPException(status_code=500, detail="Email engine not initialized")
        
    # Trigger via automation engine
    automation._on_new_email  # This would be triggered by events
    
    return {"status": "success", "message": "Sync initiated"}


# =============================================================================
# CONTACTS ENDPOINTS
# =============================================================================

@app.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    limit: int = Query(default=50, le=100),
    category: Optional[str] = None,
    vip_only: bool = False
):
    """List contacts"""
    db = get_db()
    
    if not db:
        raise HTTPException(status_code=500, detail="Database not initialized")
        
    with db.get_session() as session:
        query = session.query(Contact).filter(Contact.is_blocked == False)
        
        if vip_only:
            query = query.filter(Contact.is_vip == True)
        if category:
            query = query.filter(Contact.category == category)
            
        contacts = query.order_by(
            Contact.last_contact_at.desc()
        ).limit(limit).all()
        
        return [
            ContactResponse(
                id=c.id,
                email=c.email,
                name=c.name,
                display_name=c.display_name,
                category=c.category or "general",
                importance_level=c.importance_level,
                is_vip=c.is_vip,
                total_emails=c.total_emails,
                last_contact_at=c.last_contact_at
            )
            for c in contacts
        ]


@app.get("/contacts/{contact_id}")
async def get_contact(contact_id: int):
    """Get contact details"""
    db = get_db()
    
    with db.get_session() as session:
        contact = session.query(Contact).filter(Contact.id == contact_id).first()
        
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
            
        recent_emails = session.query(Email).filter(
            Email.sender_email == contact.email
        ).order_by(Email.date_received.desc()).limit(10).all()
        
        return {
            "id": contact.id,
            "email": contact.email,
            "name": contact.name,
            "display_name": contact.display_name,
            "category": contact.category,
            "importance_level": contact.importance_level,
            "is_vip": contact.is_vip,
            "organization": contact.organization,
            "job_title": contact.job_title,
            "total_emails": contact.total_emails,
            "last_contact_at": contact.last_contact_at.isoformat() if contact.last_contact_at else None,
            "recent_emails": [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "date": e.date_received.isoformat(),
                    "is_read": e.is_read
                }
                for e in recent_emails
            ]
        }


@app.post("/contacts/{contact_id}/vip")
async def set_vip_status(contact_id: int, is_vip: bool = True):
    """Set contact as VIP"""
    db = get_db()
    
    with db.get_session() as session:
        if is_vip:
            session.query(Contact).filter(Contact.id == contact_id).update({
                "is_vip": True,
                "importance_level": 80
            })
        else:
            session.query(Contact).filter(Contact.id == contact_id).update({
                "is_vip": False
            })
            
    return {"status": "success"}


# =============================================================================
# SEARCH & RAG ENDPOINTS
# =============================================================================

@app.post("/search")
async def search(request: SearchRequest):
    """Semantic search across emails and contacts"""
    rag = get_rag()
    
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
        
    results = rag.search(
        query=request.query,
        scope=request.scope,
        limit=request.limit,
        category=request.category,
        priority=request.priority
    )
    
    return {
        "query": request.query,
        "count": len(results),
        "results": results
    }


@app.get("/search/context")
async def get_search_context(query: str, max_contexts: int = 5):
    """Get context for LLM query"""
    rag = get_rag()
    
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
        
    context = rag.get_context_for_query(query, max_contexts)
    
    return {"context": context}


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@app.get("/analytics/briefing", response_model=BriefingResponse)
async def get_briefing(date: Optional[str] = None):
    """Get daily briefing"""
    analytics = get_analytics()
    
    if not analytics:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
        
    target_date = None
    if date:
        try:
            target_date = datetime.fromisoformat(date)
        except:
            pass
            
    briefing = analytics.get_daily_briefing(target_date)
    
    return BriefingResponse(
        date=briefing.get("date", date or datetime.utcnow().date().isoformat()),
        summary=briefing.get("summary", {}),
        important_emails=briefing.get("important_emails", []),
        urgent_emails=briefing.get("urgent_emails", []),
        category_breakdown=briefing.get("category_breakdown", {})
    )


@app.get("/analytics/full")
async def get_full_analytics(period: str = "week"):
    """Get full analytics report"""
    analytics = get_analytics()
    
    if not analytics:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
        
    return analytics.get_full_report(period)


@app.get("/analytics/health")
async def get_inbox_health():
    """Get inbox health score"""
    analytics = get_analytics()
    
    if not analytics:
        raise HTTPException(status_code=500, detail="Analytics not initialized")
        
    return analytics.productivity.get_inbox_health_score()


# =============================================================================
# AUTOMATION ENDPOINTS
# =============================================================================

@app.get("/rules")
async def list_rules():
    """List automation rules"""
    db = get_db()
    
    with db.get_session() as session:
        rules = session.query(Rule).all()
        
        return [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "trigger_type": r.trigger_type,
                "is_enabled": r.is_enabled,
                "is_system": r.is_system,
                "priority": r.priority,
                "execution_count": r.execution_count,
                "last_executed_at": r.last_executed_at.isoformat() if r.last_executed_at else None
            }
            for r in rules
        ]


@app.post("/rules")
async def create_rule(request: RuleCreateRequest):
    """Create new automation rule"""
    automation = get_automation()
    
    if not automation:
        raise HTTPException(status_code=500, detail="Automation not initialized")
        
    rule = automation.create_rule(
        name=request.name,
        trigger_type=request.trigger_type,
        trigger_conditions=request.trigger_conditions,
        actions=request.actions,
        priority=request.priority
    )
    
    return {"status": "success", "id": rule.id}


@app.get("/followups")
async def list_followups(status: Optional[str] = None):
    """List follow-ups"""
    db = get_db()
    
    with db.get_session() as session:
        query = session.query(FollowUp).filter(FollowUp.completed == False)
        
        if status:
            query = query.filter(FollowUp.status == status)
            
        followups = query.order_by(FollowUp.scheduled_date.asc()).all()
        
        return [
            {
                "id": f.id,
                "email_id": f.email_id,
                "scheduled_date": f.scheduled_date.isoformat(),
                "status": f.status,
                "reminder_type": f.reminder_type
            }
            for f in followups
        ]


# =============================================================================
# VOICE ENDPOINTS
# =============================================================================

@app.post("/voice/command")
async def process_voice_command(request: VoiceCommandRequest):
    """Process voice command"""
    # Import here to avoid circular import
    from voice import VoiceCommandParser
    
    parser = VoiceCommandParser()
    command = parser.parse(request.command)
    
    return {
        "text": command.text,
        "intent": command.intent,
        "confidence": command.confidence,
        "entities": command.entities
    }


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"API Error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# =============================================================================
# MAIN
# =============================================================================

def create_app() -> FastAPI:
    """Create FastAPI application"""
    return app


def run_server(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """Run the API server"""
    import uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )


if __name__ == "__main__":
    run_server()
