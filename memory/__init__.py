# =============================================================================
# MEMORY SYSTEM - Contact and Relationship Management
# =============================================================================

from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from database import (
    Contact, Email, Thread, Conversation, get_db_manager, DatabaseManager
)
from core import Config, DragonModule, logger, events


class RelationshipType(Enum):
    """Types of relationships with contacts"""
    CLIENT = "client"
    COLLEAGUE = "colleague"
    FRIEND = "friend"
    FAMILY = "family"
    FACULTY = "faculty"
    MENTOR = "mentor"
    STUDENT = "student"
    VENDOR = "vendor"
    VIP = "vip"


class ContactMemory:
    """Memory/knowledge about a contact"""
    
    def __init__(self, contact_id: int):
        self.contact_id = contact_id
        self.notes: List[str] = []
        self.preferences: Dict[str, Any] = {}
        self.interaction_history: List[Dict[str, Any]] = []
        self.important_dates: Dict[str, date] = {}
        self.projects: List[str] = []
        self.key_topics: List[str] = []
        
    def add_note(self, note: str) -> None:
        """Add a note about contact"""
        self.notes.append({
            "content": note,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference"""
        self.preferences[key] = value
        
    def record_interaction(
        self, 
        interaction_type: str,
        details: Optional[str] = None
    ) -> None:
        """Record an interaction"""
        self.interaction_history.append({
            "type": interaction_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "contact_id": self.contact_id,
            "notes": self.notes,
            "preferences": self.preferences,
            "interaction_count": len(self.interaction_history),
            "last_interaction": self.interaction_history[-1] if self.interaction_history else None,
            "important_dates": self.important_dates,
            "projects": self.projects,
            "key_topics": self.key_topics,
        }


class ConversationMemory:
    """Memory for email conversations/threads"""
    
    def __init__(self, thread_id: Optional[str] = None):
        self.thread_id = thread_id
        self.summary: str = ""
        self.key_points: List[str] = []
        self.decisions: List[str] = []
        self.action_items: List[Dict[str, Any]] = []
        self.sentiment_trend: str = "neutral"
        self.last_updated = datetime.utcnow()
        self.participants: List[str] = []
        
    def update_from_emails(self, emails: List[Email]) -> None:
        """Update memory from email list"""
        if not emails:
            return
            
        self.participants = list(set([
            e.sender_email for e in emails if e.sender_email
        ]))
        
        # Generate simple summary from subjects
        subjects = [e.subject for e in emails[:5]]
        self.summary = f"Thread about: {subjects[0]}"
        
        # Detect key points from body snippets
        # (simplified - would use NLP for better extraction)
        self.last_updated = datetime.utcnow()
        
    def add_decision(self, decision: str) -> None:
        """Record a decision"""
        self.decisions.append({
            "content": decision,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    def add_action_item(
        self, 
        action: str, 
        assignee: Optional[str] = None,
        deadline: Optional[datetime] = None
    ) -> None:
        """Add action item"""
        self.action_items.append({
            "action": action,
            "assignee": assignee,
            "deadline": deadline.isoformat() if deadline else None,
            "completed": False,
            "added_at": datetime.utcnow().isoformat()
        })
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "thread_id": self.thread_id,
            "summary": self.summary,
            "key_points": self.key_points,
            "decisions": self.decisions,
            "action_items": self.action_items,
            "sentiment_trend": self.sentiment_trend,
            "last_updated": self.last_updated.isoformat(),
            "participant_count": len(self.participants),
        }


class RelationshipTracker:
    """Track relationship health and history"""
    
    def __init__(self, config: Config, db: DatabaseManager):
        self.config = config
        self.db = db
        
    def track_interaction(
        self, 
        contact_email: str,
        interaction_type: str,
        details: Optional[str] = None
    ) -> None:
        """Track an interaction with contact"""
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.email == contact_email
            ).first()
            
            if contact:
                contact.last_contact_at = datetime.utcnow()
                
                # Update metadata
                metadata = contact.meta_data or {}
                interactions = metadata.get("interaction_history", [])
                interactions.append({
                    "type": interaction_type,
                    "details": details,
                    "timestamp": datetime.utcnow().isoformat()
                })
                metadata["interaction_history"] = interactions[-50:]  # Keep last 50
                contact.meta_data = metadata
                
    def get_interaction_stats(self, contact_email: str) -> Dict[str, Any]:
        """Get interaction statistics for contact"""
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.email == contact_email
            ).first()
            
            if not contact:
                return {}
                
            metadata = contact.meta_data or {}
            interactions = metadata.get("interaction_history", [])
            
            # Count by type
            type_counts: Dict[str, int] = {}
            for interaction in interactions:
                itype = interaction.get("type", "unknown")
                type_counts[itype] = type_counts.get(itype, 0) + 1
                
            # Calculate response metrics
            emails = session.query(Email).filter(
                Email.sender_email == contact_email
            ).order_by(Email.date_sent.desc()).limit(10).all()
            
            return {
                "total_interactions": len(interactions),
                "interaction_types": type_counts,
                "last_contact": contact.last_contact_at.isoformat() if contact.last_contact_at else None,
                "days_since_contact": (
                    datetime.utcnow() - contact.last_contact_at
                ).days if contact.last_contact_at else None,
                "recent_email_count": len(emails),
                "relationship_strength": self._calculate_strength(contact, interactions),
            }
            
    def _calculate_strength(
        self, 
        contact: Contact, 
        interactions: List[Dict[str, Any]]
    ) -> str:
        """Calculate relationship strength"""
        days_since = (datetime.utcnow() - contact.last_contact_at).days if contact.last_contact_at else 999
        interaction_count = len(interactions)
        
        if contact.is_vip or contact.category == "vip":
            return "strong"
        elif days_since < 7 and interaction_count >= 3:
            return "strong"
        elif days_since < 30 and interaction_count >= 1:
            return "moderate"
        elif days_since < 90:
            return "weak"
        else:
            return "cold"
            
    def get_stale_contacts(self, days: int = 30) -> List[Contact]:
        """Get contacts not contacted in specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            return session.query(Contact).filter(
                Contact.last_contact_at < cutoff,
                Contact.is_blocked == False
            ).order_by(Contact.last_contact_at.asc()).all()


class MemorySystem(DragonModule):
    """Main memory management system"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.relationship_tracker = RelationshipTracker(config, self.db)
        self._contact_memories: Dict[int, ContactMemory] = {}
        self._conversation_memories: Dict[str, ConversationMemory] = {}
        
    def initialize(self) -> None:
        """Initialize memory system"""
        super().initialize()
        logger.info("Memory System initialized")
        
    def get_contact_memory(self, contact_id: int) -> ContactMemory:
        """Get or create contact memory"""
        if contact_id not in self._contact_memories:
            self._contact_memories[contact_id] = ContactMemory(contact_id)
        return self._contact_memories[contact_id]
        
    def get_conversation_memory(
        self, 
        thread_id: str
    ) -> ConversationMemory:
        """Get or create conversation memory"""
        if thread_id not in self._conversation_memories:
            self._conversation_memories[thread_id] = ConversationMemory(thread_id)
        return self._conversation_memories[thread_id]
        
    def load_contact_memories(self) -> None:
        """Load all contact memories from database"""
        with self.db.get_session() as session:
            contacts = session.query(Contact).all()
            
            for contact in contacts:
                if contact.id not in self._contact_memories:
                    memory = ContactMemory(contact.id)
                    
                    # Load from metadata
                    if contact.meta_data:
                        memory.notes = contact.meta_data.get("notes", [])
                        memory.preferences = contact.meta_data.get("preferences", {})
                        memory.interaction_history = contact.meta_data.get("interaction_history", [])
                        memory.projects = contact.meta_data.get("projects", [])
                        
                    self._contact_memories[contact.id] = memory
                    
    def load_conversation_memories(self) -> None:
        """Load conversation memories from database"""
        with self.db.get_session() as session:
            db_conversations = session.query(Conversation).all()
            
            for db_conv in db_conversations:
                if db_conv.thread_id:
                    memory = ConversationMemory(db_conv.thread_id)
                    memory.summary = db_conv.summary or ""
                    memory.key_points = db_conv.key_points or []
                    memory.decisions = db_conv.decisions or []
                    memory.action_items = db_conv.action_items or []
                    memory.sentiment_trend = db_conv.sentiment_trend or "neutral"
                    
                    self._conversation_memories[db_conv.thread_id] = memory
                    
    def remember_contact(
        self, 
        contact_id: int, 
        note: str,
        save: bool = True
    ) -> None:
        """Add a note about contact"""
        memory = self.get_contact_memory(contact_id)
        memory.add_note(note)
        
        if save:
            self._save_contact_memory(contact_id)
            
    def remember_preference(
        self, 
        contact_id: int, 
        key: str, 
        value: Any,
        save: bool = True
    ) -> None:
        """Remember a contact preference"""
        memory = self.get_contact_memory(contact_id)
        memory.set_preference(key, value)
        
        # Also update in database
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(Contact.id == contact_id).first()
            if contact:
                preferences = contact.preferences or {}
                preferences[key] = value
                contact.preferences = preferences
                
    def record_email_interaction(
        self, 
        email: Email,
        interaction_type: str = "email"
    ) -> None:
        """Record an email interaction"""
        if email.contact_id:
            self.relationship_tracker.track_interaction(
                email.sender_email,
                interaction_type,
                f"Subject: {email.subject}"
            )
            
        # Update conversation memory
        if email.thread_id:
            memory = self.get_conversation_memory(email.thread_id)
            
    def get_greeting_and_context(
        self, 
        contact_id: int
    ) -> Dict[str, Any]:
        """Get personalized greeting and context for contact"""
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.id == contact_id
            ).first()
            
            if not contact:
                return {}
                
            stats = self.relationship_tracker.get_interaction_stats(contact.email)
            memory = self.get_contact_memory(contact_id)
            
            # Generate greeting
            name = contact.display_name or contact.name or contact.email.split("@")[0]
            greeting = f"Hello {name}!"
            
            # Add context based on relationship
            context_parts = []
            
            if stats.get("relationship_strength") == "strong":
                context_parts.append("We've been in regular contact.")
            elif stats.get("days_since_contact", 0) > 30:
                context_parts.append(f"We last connected {stats['days_since_contact']} days ago.")
                
            # Add recent topics
            if memory.key_topics:
                recent = ", ".join(memory.key_topics[-3:])
                context_parts.append(f"Recent topics: {recent}.")
                
            return {
                "greeting": greeting,
                "context": " ".join(context_parts) if context_parts else None,
                "stats": stats,
                "contact_name": name,
            }
            
    def get_relationship_status(self) -> Dict[str, Any]:
        """Get overall relationship status"""
        stale_contacts = self.relationship_tracker.get_stale_contacts(30)
        strong_relationships = []
        weak_relationships = []
        
        with self.db.get_session() as session:
            all_contacts = session.query(Contact).filter(
                Contact.is_blocked == False
            ).all()
            
            for contact in all_contacts:
                stats = self.relationship_tracker.get_interaction_stats(contact.email)
                strength = stats.get("relationship_strength", "")
                
                if strength == "strong":
                    strong_relationships.append(contact.display_name or contact.email)
                elif strength in ["weak", "cold"]:
                    weak_relationships.append(contact.email)
                    
        return {
            "total_contacts": len(all_contacts),
            "strong_relationships": strong_relationships,
            "needs_attention": weak_relationships,
            "stale_contacts": [
                c.email for c in stale_contacts
            ],
        }
        
    def _save_contact_memory(self, contact_id: int) -> None:
        """Save contact memory to database"""
        memory = self._contact_memories.get(contact_id)
        if not memory:
            return
            
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.id == contact_id
            ).first()
            
            if contact:
                contact.meta_data = contact.meta_data or {}
                contact.meta_data["notes"] = memory.notes
                contact.meta_data["preferences"] = memory.preferences
                contact.meta_data["interaction_history"] = memory.interaction_history
                contact.meta_data["projects"] = memory.projects
                
    def set_vip_status(
        self, 
        contact_email: str, 
        is_vip: bool = True
    ) -> bool:
        """Set contact as VIP"""
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.email == contact_email
            ).first()
            
            if contact:
                contact.is_vip = is_vip
                if is_vip:
                    contact.importance_level = max(contact.importance_level, 80)
                    contact.category = "vip"
                return True
                
        return False
        
    def block_contact(self, contact_email: str, blocked: bool = True) -> bool:
        """Block/unblock contact"""
        with self.db.get_session() as session:
            contact = session.query(Contact).filter(
                Contact.email == contact_email
            ).first()
            
            if contact:
                contact.is_blocked = blocked
                return True
                
        return False
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        # Save any pending memories
        logger.info("Memory System shutdown complete")
