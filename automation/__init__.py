# =============================================================================
# AUTOMATION ENGINE - Rules, Follow-ups, Escalations
# =============================================================================

import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database import (
    Email, Contact, Rule, FollowUp, Escalation, ScheduledEmail,
    get_db_manager, EmailPriority, EmailCategory
)
from core import Config, DragonModule, logger, events

# Import other modules
from email_engine import EmailEngine
from voice import VoiceSystem


class RuleTriggerType(Enum):
    """Trigger types for rules"""
    KEYWORD = "keyword"
    SENDER = "sender"
    CATEGORY = "category"
    PRIORITY = "priority"
    SCHEDULE = "schedule"
    ATTACHMENT = "attachment"


class ActionType(Enum):
    """Action types for automation"""
    HIGHLIGHT = "highlight"
    MARK_READ = "mark_read"
    ARCHIVE = "archive"
    DELETE = "delete"
    PIN = "pin"
    STAR = "star"
    SET_PRIORITY = "set_priority"
    SET_CATEGORY = "set_category"
    FORWARD_TO = "forward_to"
    ESCALATE = "escalate"
    CREATE_FOLLOW_UP = "create_follow_up"
    CREATE_REMINDER = "create_reminder"
    VOICE_ALERT = "voice_alert"
    DESKTOP_NOTIFICATION = "desktop_notification"
    FULLSCREEN_ALERT = "fullscreen_alert"
    AUTO_REPLY = "auto_reply"
    ADD_LABEL = "add_label"
    MOVE_TO_FOLDER = "move_to_folder"


@dataclass
class AutomationEvent:
    """Event for automation processing"""
    event_type: str
    email: Optional[Email] = None
    contact: Optional[Contact] = None
    rule: Optional[Rule] = None
    metadata: Dict[str, Any] = None


class RuleEngine:
    """Rule processing engine"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_handlers()
        
    def _register_default_handlers(self) -> None:
        """Register default action handlers"""
        self._action_handlers = {
            ActionType.HIGHLIGHT.value: self._handle_highlight,
            ActionType.MARK_READ.value: self._handle_mark_read,
            ActionType.ARCHIVE.value: self._handle_archive,
            ActionType.PIN.value: self._handle_pin,
            ActionType.SET_PRIORITY.value: self._handle_set_priority,
            ActionType.SET_CATEGORY.value: self._handle_set_category,
            ActionType.ESCALATE.value: self._handle_escalate,
            ActionType.CREATE_FOLLOW_UP.value: self._handle_create_follow_up,
            ActionType.VOICE_ALERT.value: self._handle_voice_alert,
            ActionType.DESKTOP_NOTIFICATION.value: self._handle_desktop_notification,
            ActionType.FORWARD_TO.value: self._handle_forward,
        }
        
    def evaluate_rules(self, email: Email) -> List[Rule]:
        """Evaluate rules against an email"""
        matched_rules = []
        
        with self.db.get_session() as session:
            rules = session.query(Rule).filter(
                Rule.is_enabled == True
            ).order_by(Rule.priority.desc()).all()
            
            for rule in rules:
                if self._email_matches_rule(email, rule):
                    matched_rules.append(rule)
                    
        return matched_rules
        
    def _email_matches_rule(self, email: Email, rule: Rule) -> bool:
        """Check if email matches rule conditions"""
        trigger_conditions = rule.trigger_conditions or {}
        trigger_type = rule.trigger_type
        
        if trigger_type == RuleTriggerType.KEYWORD.value:
            keywords = trigger_conditions.get("keywords", [])
            text = f"{email.subject} {email.body_plain}".lower()
            return any(kw.lower() in text for kw in keywords)
            
        elif trigger_type == RuleTriggerType.SENDER.value:
            sender_email = email.sender_email.lower()
            domains = trigger_conditions.get("domains", [])
            senders = trigger_conditions.get("senders", [])
            
            for domain in domains:
                if domain.lower().lstrip("@") in sender_email:
                    return True
            return sender_email in [s.lower() for s in senders]
            
        elif trigger_type == RuleTriggerType.CATEGORY.value:
            required_category = trigger_conditions.get("category")
            is_replied = trigger_conditions.get("is_replied")
            
            if required_category and email.category and email.category.value == required_category:
                if is_replied is None or email.is_replied == is_replied:
                    return True
                    
        elif trigger_type == RuleTriggerType.PRIORITY.value:
            required_priority = trigger_conditions.get("priority")
            if required_priority and email.priority and email.priority.value == required_priority:
                return True
                
        elif trigger_type == RuleTriggerType.ATTACHMENT.value:
            has_attachment = trigger_conditions.get("has_attachment", True)
            content_types = trigger_conditions.get("content_types", [])
            
            if email.has_attachments == has_attachment:
                if content_types:
                    # Check attachment types
                    pass
                return True
                
        return False
        
    def execute_rule(self, rule: Rule, email: Email) -> None:
        """Execute rule actions"""
        actions = rule.actions or []
        
        for action in actions:
            action_type = action.get("action_type")
            action_params = action.get("params", {})
            
            handler = self._action_handlers.get(action_type)
            if handler:
                try:
                    handler(email, action_params)
                    rule.execution_count += 1
                    rule.last_executed_at = datetime.utcnow()
                    rule.last_triggered_by = email.sender_email
                except Exception as e:
                    logger.error(f"Action execution error: {e}")
                    
    def _handle_highlight(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle highlight action"""
        color = params.get("color", "yellow")
        events.emit("email_highlight", email=email, color=color)
        
    def _handle_mark_read(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle mark read action"""
        email.is_read = True
        
    def _handle_archive(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle archive action"""
        email.is_archived = True
        events.emit("email_archived", email=email)
        
    def _handle_pin(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle pin action"""
        email.is_pinned = True
        events.emit("email_pinned", email=email)
        
    def _handle_set_priority(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle set priority action"""
        priority = params.get("priority", "P3")
        try:
            email.priority = EmailPriority[priority]
            events.emit("email_priority_changed", email=email, new_priority=priority)
        except:
            pass
            
    def _handle_set_category(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle set category action"""
        category = params.get("category", "NORMAL")
        try:
            email.category = EmailCategory[category]
        except:
            pass
            
    def _handle_escalate(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle escalate action"""
        level = params.get("level", 3)
        events.emit("escalation_trigger", email=email, level=level)
        
    def _handle_create_follow_up(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle create follow-up action"""
        reminder = params.get("reminder", "1 day")
        
        # Parse duration
        # Format: "2 hours", "1 day", "30 minutes"
        hours = 24  # Default
        if "hour" in reminder:
            match = re.search(r'(\d+)', reminder)
            hours = int(match.group(1)) if match else 1
        elif "day" in reminder:
            match = re.search(r'(\d+)', reminder)
            hours = int(match.group(1)) * 24 if match else 1
            
        follow_up_date = datetime.utcnow() + timedelta(hours=hours)
        
        follow_up = FollowUp(
            email_id=email.id,
            contact_id=email.contact_id,
            scheduled_date=follow_up_date,
            reminder_type=params.get("type", "notification"),
        )
        
        with self.db.get_session() as session:
            session.add(follow_up)
            
    def _handle_voice_alert(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle voice alert action"""
        message = params.get("message", f"Important email from {email.sender_name or email.sender_email}")
        events.emit("voice_alert", message=message, email=email)
        
    def _handle_desktop_notification(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle desktop notification action"""
        title = params.get("title", "New Email")
        message = params.get("message", email.subject[:100])
        events.emit("desktop_notification", title=title, message=message, email=email)
        
    def _handle_forward(self, email: Email, params: Dict[str, Any]) -> None:
        """Handle forward to agent action"""
        agent = params.get("agent")
        events.emit("forward_to_agent", email=email, agent=agent)


class EscalationManager:
    """Manage email escalations"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        self._active_escalations: Dict[int, Dict[str, Any]] = {}
        
    def escalate(
        self,
        email: Email,
        level: int,
        reason: Optional[str] = None
    ) -> Escalation:
        """Escalate an email"""
        # Check if already escalated at this level
        if email.id in self._active_escalations:
            existing = self._active_escalations[email.id]
            if existing["level"] >= level:
                return existing["escalation"]
                
        escalation = Escalation(
            email_id=email.id,
            escalation_level=level,
            reason=reason,
            notification_type=self._level_to_notification_type(level),
        )
        
        with self.db.get_session() as session:
            session.add(escalation)
            session.flush()
            
        self._active_escalations[email.id] = {
            "escalation": escalation,
            "level": level,
            "started_at": datetime.utcnow(),
        }
        
        # Execute escalation actions
        self._execute_escalation(email, level)
        
        return escalation
        
    def _level_to_notification_type(self, level: int) -> str:
        """Map escalation level to notification type"""
        mapping = {
            1: "desktop",
            2: "voice",
            3: "fullscreen",
            4: "dragon",
            5: "calling",
        }
        return mapping.get(level, "desktop")
        
    def _execute_escalation(self, email: Email, level: int) -> None:
        """Execute escalation actions based on level"""
        if level == 1:
            events.emit("desktop_notification", 
                       title="Email Alert", 
                       message=f"High priority email: {email.subject[:100]}")
        elif level == 2:
            events.emit("voice_alert",
                       message=f"Reminder: {email.subject[:50]}")
        elif level == 3:
            events.emit("fullscreen_alert",
                       title="Important",
                       message=email.subject)
        elif level >= 4:
            sender = email.sender_email if hasattr(email, 'sender_email') else "unknown"
            events.emit("dragon_announce",
                       message=f"Attention! Important email from {sender}")
        
    def acknowledge(self, escalation_id: int, user: Optional[str] = None) -> bool:
        """Acknowledge an escalation"""
        with self.db.get_session() as session:
            escalation = session.query(Escalation).filter(
                Escalation.id == escalation_id
            ).first()
            
            if escalation:
                escalation.acknowledged_at = datetime.utcnow()
                escalation.notification_sent = True
                
                # Clear from active
                for email_id, data in list(self._active_escalations.items()):
                    if data["escalation"].id == escalation_id:
                        del self._active_escalations[email_id]
                        break
                        
                return True
        return False
        
    def resolve(self, escalation_id: int) -> bool:
        """Resolve an escalation"""
        with self.db.get_session() as session:
            escalation = session.query(Escalation).filter(
                Escalation.id == escalation_id
            ).first()
            
            if escalation:
                escalation.resolved_at = datetime.utcnow()
                
                # Clear from active
                for email_id, data in list(self._active_escalations.items()):
                    if data["escalation"].id == escalation_id:
                        del self._active_escalations[email_id]
                        break
                        
                return True
        return False
        
    def get_active_escalations(self) -> List[Dict[str, Any]]:
        """Get all active escalations"""
        results = []
        
        for email_id, data in self._active_escalations.items():
            escalation = data["escalation"]
            results.append({
                "id": escalation.id,
                "email_id": email_id,
                "level": data["level"],
                "started_at": data["started_at"].isoformat(),
                "acknowledged": escalation.acknowledged_at is not None,
                "duration_minutes": (datetime.utcnow() - data["started_at"]).seconds / 60,
            })
            
        return results


class FollowUpManager:
    """Manage email follow-ups"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        
    def create_follow_up(
        self,
        email: Email,
        scheduled_date: datetime,
        reminder_type: str = "notification",
        notes: Optional[str] = None
    ) -> FollowUp:
        """Create a follow-up"""
        follow_up = FollowUp(
            email_id=email.id,
            contact_id=email.contact_id,
            scheduled_date=scheduled_date,
            reminder_type=reminder_type,
            notes=notes,
        )
        
        with self.db.get_session() as session:
            session.add(follow_up)
            session.flush()
            
        # Mark email as requiring action
        email.action_required = True
        
        return follow_up
        
    def create_auto_follow_up(
        self,
        email: Email,
        contact: Optional[Contact] = None
    ) -> Optional[FollowUp]:
        """Create auto follow-up based on contact type"""
        # Determine response time based on contact
        hours = self.config.response_thresholds.get("other", 72)
        
        if contact:
            if contact.category == "client":
                hours = self.config.response_thresholds.get("client", 6)
            elif contact.category == "faculty":
                hours = self.config.response_thresholds.get("faculty", 4)
            elif contact.category == "work":
                hours = self.config.response_thresholds.get("work", 24)
                
        # Check if this contact typically responds slowly
        if contact and contact.meta_data:
            avg_response = contact.meta_data.get("avg_response_hours")
            if avg_response:
                hours = max(hours, avg_response * 1.5)  # Add buffer
                
        scheduled_date = datetime.utcnow() + timedelta(hours=hours)
        
        return self.create_follow_up(
            email=email,
            scheduled_date=scheduled_date,
            reminder_type="voice",
            notes=f"Auto follow-up: {hours} hours"
        )
        
    def get_pending_follow_ups(self, limit: int = 50) -> List[FollowUp]:
        """Get pending follow-ups"""
        with self.db.get_session() as session:
            return session.query(FollowUp).filter(
                FollowUp.completed == False,
                FollowUp.status == "pending"
            ).order_by(FollowUp.scheduled_date.asc()).limit(limit).all()
            
    def get_due_follow_ups(self) -> List[FollowUp]:
        """Get follow-ups due now"""
        now = datetime.utcnow()
        
        with self.db.get_session() as session:
            return session.query(FollowUp).filter(
                FollowUp.completed == False,
                FollowUp.scheduled_date <= now
            ).all()
            
    def complete_follow_up(self, follow_up_id: int) -> bool:
        """Mark follow-up as complete"""
        with self.db.get_session() as session:
            follow_up = session.query(FollowUp).filter(
                FollowUp.id == follow_up_id
            ).first()
            
            if follow_up:
                follow_up.completed = True
                follow_up.completed_at = datetime.utcnow()
                follow_up.status = "completed"
                
                # Update email
                email = session.query(Email).filter(
                    Email.id == follow_up.email_id
                ).first()
                if email:
                    email.action_required = False
                    
                return True
            return False
    
    def skip_follow_up(self, follow_up_id: int, reason: Optional[str] = None) -> bool:
        """Skip a follow-up"""
        with self.db.get_session() as session:
            follow_up = session.query(FollowUp).filter(
                FollowUp.id == follow_up_id
            ).first()
            
            if follow_up:
                follow_up.status = "skipped"
                follow_up.notes = reason
                return True
        return False


class SchedulerManager:
    """Manage scheduled tasks"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scheduler = BackgroundScheduler()
        self._jobs: Dict[str, Any] = {}
        
    def start(self) -> None:
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Automation scheduler started")
            
    def stop(self) -> None:
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Automation scheduler stopped")
            
    def schedule_email_send(
        self,
        scheduled_email: ScheduledEmail,
        email_data: Dict[str, Any]
    ) -> str:
        """Schedule an email to be sent"""
        email_id = scheduled_email.id
        
        def send_scheduled_email():
            try:
                # Import email engine
                from email_engine import EmailEngine
                engine = EmailEngine(self.config)
                engine.initialize()
                
                # Parse email data
                to = email_data.get("to", [])
                subject = email_data.get("subject", "")
                body = email_data.get("body", "")
                cc = email_data.get("cc")
                is_html = email_data.get("is_html", False)
                
                success = engine.sender.send(to, subject, body, cc=cc, is_html=is_html)
                
                with self.config.db.get_session() as session:
                    email = session.query(ScheduledEmail).filter(
                        ScheduledEmail.id == email_id
                    ).first()
                    
                    if email:
                        email.sent = True
                        email.sent_at = datetime.utcnow()
                        
                        return success
            except Exception as e:
                logger.error(f"Scheduled email failed: {e}")
                
        job = self.scheduler.add_job(
            send_scheduled_email,
            trigger=CronTrigger.from_crontab("0 * * * *"),  # Will be overridden
            id=f"scheduled_email_{email_id}",
            replace_existing=True,
        )
        
        # Actually use the scheduled time
        self.scheduler.reschedule_job(
            job.id,
            trigger=CronTrigger.from_datetime(scheduled_email.scheduled_at)
        )
        
        self._jobs[email_id] = job.id
        return job.id
        
    def schedule_daily_briefing(self, hour: int = 9, minute: int = 0) -> str:
        """Schedule daily briefing"""
        def generate_briefing():
            events.emit("generate_daily_briefing")
            
        return self.scheduler.add_job(
            generate_briefing,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="daily_briefing",
            replace_existing=True,
        )
        
    def schedule_sync(self, interval_minutes: int = 5) -> str:
        """Schedule periodic email sync"""
        def sync_emails():
            events.emit("email_sync_requested")
            
        return self.scheduler.add_job(
            sync_emails,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="email_sync",
            replace_existing=True,
        )


class AutomationEngine(DragonModule):
    """Main automation engine"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.rule_engine = RuleEngine(config, self.db)
        self.escalation_manager = EscalationManager(config, self.db)
        self.followup_manager = FollowUpManager(config, self.db)
        self.scheduler = SchedulerManager(config)
        
        # Register event handlers
        events.on("email_new", self._on_new_email)
        events.on("escalation_trigger", self._on_escalation_trigger)
        events.on("generate_daily_briefing", self._on_daily_briefing)
        
    def initialize(self) -> None:
        """Initialize automation engine"""
        super().initialize()
        self.scheduler.start()
        
        # Schedule default tasks
        self.scheduler.schedule_daily_briefing(hour=9)
        self.scheduler.schedule_sync(interval_minutes=self.config.sync_interval // 60)
        
        logger.info("Automation Engine initialized")
        
    def _on_new_email(self, email: Email) -> None:
        """Handle new email event"""
        # Evaluate rules
        matched_rules = self.rule_engine.evaluate_rules(email)
        for rule in matched_rules:
            self.rule_engine.execute_rule(rule, email)
            
        # Check for auto follow-up
        if email.action_required and not email.is_replied:
            contact = None
            if email.contact_id:
                with self.db.get_session() as session:
                    contact = session.query(Contact).filter(
                        Contact.id == email.contact_id
                    ).first()
                    
            self.followup_manager.create_auto_follow_up(email, contact)
            
    def _on_escalation_trigger(self, email: Email, level: int = 3) -> None:
        """Handle escalation trigger"""
        self.escalation_manager.escalate(email, level, "Auto-escalation triggered")
        
    def _on_daily_briefing(self) -> None:
        """Generate daily briefing"""
        events.emit("daily_briefing_requested")
        
    def create_rule(
        self,
        name: str,
        trigger_type: str,
        trigger_conditions: Dict[str, Any],
        actions: List[Dict[str, Any]],
        priority: int = 50
    ) -> Rule:
        """Create a new automation rule"""
        rule = Rule(
            name=name,
            trigger_type=trigger_type,
            trigger_conditions=trigger_conditions,
            actions=actions,
            priority=priority,
        )
        
        with self.db.get_session() as session:
            session.add(rule)
            session.flush()
            
        return rule
        
    def get_rule_stats(self) -> Dict[str, Any]:
        """Get rule execution statistics"""
        with self.db.get_session() as session:
            rules = session.query(Rule).all()
            
            total_executions = sum(r.execution_count for r in rules)
            
            return {
                "total_rules": len(rules),
                "active_rules": sum(1 for r in rules if r.is_enabled),
                "total_executions": total_executions,
                "system_rules": sum(1 for r in rules if r.is_system),
                "rules_by_trigger": self._count_by_trigger(rules),
            }
            
    def _count_by_trigger(self, rules: List[Rule]) -> Dict[str, int]:
        """Count rules by trigger type"""
        counts = {}
        for rule in rules:
            trigger = rule.trigger_type
            counts[trigger] = counts.get(trigger, 0) + 1
        return counts
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        self.scheduler.stop()
        logger.info("Automation Engine shutdown complete")
