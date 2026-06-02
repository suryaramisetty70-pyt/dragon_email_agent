#!/usr/bin/env python3
# =============================================================================
# PROJECT DRAGON - EMAIL AI AGENT
# Main Entry Point
# =============================================================================

import os
import sys
import signal
import asyncio
import argparse
import logging
from typing import Optional
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging before imports
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

from loguru import logger

# =============================================================================
# CORE IMPORTS
# =============================================================================

# Direct imports for the package
from core import Config, DragonModule, logger, events
from database import get_db_manager, DatabaseManager
from email_engine import EmailEngine
from voice import VoiceSystem, VoiceCommand
from memory import MemorySystem
from rag import RAGSystem
from security import SecurityModule
from automation import AutomationEngine
from analytics import Analytics
from integrations import IntegrationManager
from api import create_app


# =============================================================================
# DRAGON EMAIL AGENT - MAIN CLASS
# =============================================================================

class DragonEmailAgent:
    """Main Dragon Email Agent Controller"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._running = False
        self._shutdown_requested = False
        
        # Core systems
        self.db: Optional[DatabaseManager] = None
        self.email_engine: Optional[EmailEngine] = None
        self.voice: Optional[VoiceSystem] = None
        self.memory: Optional[MemorySystem] = None
        self.rag: Optional[RAGSystem] = None
        self.security: Optional[SecurityModule] = None
        self.automation: Optional[AutomationEngine] = None
        self.analytics: Optional[Analytics] = None
        self.integrations: Optional[IntegrationManager] = None
        
        # API app
        self.app = None
        
    def initialize(self) -> bool:
        """Initialize all systems"""
        logger.info("Initializing Dragon Email Agent...")
        
        try:
            # Initialize database
            logger.info("Setting up database...")
            self.db = get_db_manager(self.config.db_path)
            self.db.initialize()
            logger.info("Database initialized")
            
            # Initialize core systems
            logger.info("Initializing email engine...")
            self.email_engine = EmailEngine(self.config)
            self.email_engine.initialize()
            
            logger.info("Initializing memory system...")
            self.memory = MemorySystem(self.config)
            self.memory.initialize()
            
            logger.info("Initializing RAG system...")
            self.rag = RAGSystem(self.config)
            self.rag.initialize()
            
            logger.info("Initializing security...")
            self.security = SecurityModule(self.config)
            self.security.initialize()
            
            logger.info("Initializing automation...")
            self.automation = AutomationEngine(self.config)
            self.automation.initialize()
            
            logger.info("Initializing analytics...")
            self.analytics = Analytics(self.config)
            self.analytics.initialize()
            
            logger.info("Initializing integrations...")
            self.integrations = IntegrationManager(self.config)
            self.integrations.initialize()
            
            # Connect email engine to integrations
            self.email_engine.set_integration_manager(self.integrations)
            
            # Initialize voice if enabled
            if self.config.voice_enabled:
                logger.info("Initializing voice system...")
                self.voice = VoiceSystem(self.config)
                self.voice.initialize()
                self.voice.set_command_callback(self._handle_voice_command)
            
            # Register event handlers
            self._register_event_handlers()
            
            # Load memories
            logger.info("Loading contact memories...")
            self.memory.load_contact_memories()
            self.memory.load_conversation_memories()
            
            logger.info("Dragon Email Agent initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
            
    def _register_event_handlers(self) -> None:
        """Register event handlers"""
        events.on("email_new", self._on_new_email)
        events.on("daily_briefing_requested", self._on_daily_briefing)
        events.on("voice_alert", self._on_voice_alert)
        events.on("desktop_notification", self._on_desktop_notification)
        events.on("escalation_trigger", self._on_escalation)
        
    def start(self) -> None:
        """Start the agent"""
        if self._running:
            logger.warning("Agent is already running")
            return
            
        logger.info("Starting Dragon Email Agent...")
        self._running = True
        
        # Start voice listening if enabled
        if self.voice:
            self.voice.activate()
            logger.info("Voice system activated")
            
        # Start background tasks
        self._start_background_tasks()
        
        # Main loop
        self._main_loop()
        
    def _start_background_tasks(self) -> None:
        """Start background tasks"""
        # Schedule periodic email sync
        import threading
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self._sync_emails,
            trigger=IntervalTrigger(minutes=5),
            id="email_sync",
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Background scheduler started")
        
    def _main_loop(self) -> None:
        """Main interaction loop"""
        logger.info("Dragon Email Agent is running. Type 'help' for commands.")
        
        while not self._shutdown_requested:
            try:
                # Interactive mode
                if sys.stdin.isatty():
                    command = input("\nDragon> ").strip()
                    if command:
                        self._process_command(command)
                else:
                    # Non-interactive - just wait
                    import time
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                self._shutdown_requested = True
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                import time
                time.sleep(5)
                
    def _process_command(self, command: str) -> None:
        """Process text command"""
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        # Check for @dragon text commands and route to voice system
        if command.strip().lower().startswith(("@dragon", "/dragon")):
            if self.voice:
                self.voice.process_text_command(command)
                return
            else:
                print("Voice system not available")
                return
        
        if cmd in ["help", "h", "?"]:
            self._show_help()
        elif cmd in ["quit", "exit", "q"]:
            self.shutdown()
        elif cmd == "status":
            self._show_status()
        elif cmd == "sync":
            self._sync_emails()
        elif cmd == "briefing":
            self._show_briefing()
        elif cmd == "emails":
            self._show_emails(args)
        elif cmd == "contacts":
            self._show_contacts(args)
        elif cmd == "search":
            self._search(args)
        elif cmd == "voice":
            if self.voice:
                self._toggle_voice()
            else:
                print("Voice system not enabled")
        elif cmd == "analytics":
            self._show_analytics()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            
    def _show_help(self) -> None:
        """Show available commands"""
        help_text = """
╔══════════════════════════════════════════════════════════════════╗
║             DRAGON EMAIL AGENT - COMMAND REFERENCE             ║
╠══════════════════════════════════════════════════════════════════╣
║  COMMANDS                                                      ║
║  ---------------------------------------------------------------- ║
║  help, h          - Show this help message                      ║
║  status           - Show system status                          ║
║  sync             - Sync emails from all accounts              ║
║  briefing         - Generate daily briefing                     ║
║  emails [filter]  - List emails (filter: unread, important)     ║
║  contacts         - List contacts                                ║
║  search <query>   - Search emails and contacts                 ║
║  analytics        - Show productivity analytics                ║
║  voice            - Toggle voice system                         ║
║  exit, quit       - Shut down the agent                         ║
╠══════════════════════════════════════════════════════════════════╣
║  VOICE COMMANDS (when voice is enabled)                         ║
║  ---------------------------------------------------------------- ║
║  "Read important emails"                                        ║
║  "Show unread emails"                                           ║
║  "Reply to [contact]"                                          ║
║  "Summarize my inbox"                                           ║
║  "Search for [query]"                                          ║
║  "What's my inbox status?"                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  TEXT COMMANDS (@dragon prefix)                                 ║
║  ---------------------------------------------------------------- ║
║  @dragon read important emails                                  ║
║  @dragon show unread                                             ║
║  @dragon reply to [contact]                                      ║
║  @dragon summarize inbox                                         ║
║  @dragon inbox status                                            ║
║  @dragon search [query]                                          ║
║  @dragon draft professional response                             ║
║  @dragon create follow-up                                        ║
╚══════════════════════════════════════════════════════════════════╝
        """
        print(help_text)
        
    def _show_status(self) -> None:
        """Show system status"""
        if not self.db:
            print("Error: Database not initialized")
            return
            
        with self.db.get_session() as session:
            from database import Email, Contact, FollowUp
            
            total_emails = session.query(Email).count()
            unread = session.query(Email).filter(Email.is_read == False).count()
            total_contacts = session.query(Contact).count()
            pending_followups = session.query(FollowUp).filter(
                FollowUp.completed == False
            ).count()
            
            rag_stats = self.rag.get_index_stats() if self.rag else {}
            
            print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    DRAGON STATUS REPORT                          ║
╠══════════════════════════════════════════════════════════════════╣
║  DATABASE                                                       ║
║    Total Emails:     {total_emails:<40} ║
║    Unread Emails:     {unread:<40} ║
║    Total Contacts:    {total_contacts:<40} ║
║    Pending Follow-ups: {pending_followups:<40} ║
╠══════════════════════════════════════════════════════════════════╣
║  RAG INDEX                                                       ║
║    Emails Indexed:    {rag_stats.get('emails_indexed', 0):<40} ║
║    Contacts Indexed:  {rag_stats.get('contacts_indexed', 0):<40} ║
╠══════════════════════════════════════════════════════════════════╣
║  SERVICES                                                       ║
║    Voice System:      {'Enabled' if self.voice and self.voice._is_active else 'Disabled':<40} ║
║    Automation:        {'Running' if self.automation else 'Stopped':<40} ║
║    Analytics:         {'Ready' if self.analytics else 'Not Ready':<40} ║
╚══════════════════════════════════════════════════════════════════╝
            """)
            
    def _show_briefing(self) -> None:
        """Show daily briefing"""
        if not self.analytics:
            print("Error: Analytics not initialized")
            return
            
        briefing = self.analytics.get_daily_briefing()
        
        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    DAILY BRIEFING                                ║
╠══════════════════════════════════════════════════════════════════╣
║  Date: {briefing.get('date', 'N/A'):<55} ║
╠══════════════════════════════════════════════════════════════════╣
║  SUMMARY                                                        ║
║ ---------------------------------------------------------------- ║""")
        
        summary = briefing.get('summary', {})
        for key, value in summary.items():
            print(f"║    {key.replace('_', ' ').title()}: {value:<45} ║")
            
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  IMPORTANT EMAILS                                               ║")
        print("║ ---------------------------------------------------------------- ║")
        
        important = briefing.get('important_emails', [])
        if important:
            for email in important[:5]:
                print(f"║    • {email.get('subject', 'N/A')[:50]:<51} ║")
                print(f"║      From: {email.get('from', 'N/A'):<48} ║")
        else:
            print("║    No important emails today                                     ║")
            
        print("╚══════════════════════════════════════════════════════════════════╝")
        
    def _show_emails(self, args: list) -> None:
        """Show emails"""
        if not self.db:
            return
            
        filter_type = args[0].lower() if args else ""
        
        with self.db.get_session() as session:
            from database import Email, EmailDirection
            
            query = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING,
                Email.is_deleted == False
            )
            
            if filter_type == "unread":
                query = query.filter(Email.is_read == False)
            elif filter_type == "important":
                query = query.filter(Email.importance_score >= 70)
            elif filter_type == "urgent":
                from database import EmailPriority
                query = query.filter(Email.priority.in_([
                    EmailPriority.P0_EMERGENCY, EmailPriority.P1_CRITICAL
                ]))
                
            emails = query.order_by(Email.date_received.desc()).limit(10).all()
            
            print("\n📧 RECENT EMAILS")
            print("-" * 80)
            
            for email in emails:
                priority_indicator = "🔴" if email.priority and email.priority.value in ["P0_EMERGENCY", "P1_CRITICAL"] else "⚪"
                read_indicator = " " if email.is_read else "●"
                print(f"{priority_indicator} {read_indicator} {email.sender_name or email.sender_email[:20]:<20} | {email.subject[:35]:<35} | {email.date_received.strftime('%m/%d %H:%M')}")
                
            print("-" * 80)
            
    def _show_contacts(self, args: list) -> None:
        """Show contacts"""
        if not self.db:
            return
            
        with self.db.get_session() as session:
            from database import Contact
            
            query = session.query(Contact).filter(Contact.is_blocked == False)
            
            if args and args[0].lower() == "vip":
                query = query.filter(Contact.is_vip == True)
                
            contacts = query.order_by(Contact.last_contact_at.desc()).limit(20).all()
            
            print("\n👥 CONTACTS")
            print("-" * 80)
            
            for contact in contacts:
                vip_indicator = "👑" if contact.is_vip else "  "
                print(f"{vip_indicator} {contact.display_name or contact.email[:25]:<25} | {contact.category or 'general':<10} | {contact.total_emails} emails")
                
            print("-" * 80)
            
    def _search(self, args: list) -> None:
        """Search emails"""
        if not args:
            print("Usage: search <query>")
            return
            
        query = " ".join(args)
        
        if self.rag:
            results = self.rag.search(query, limit=10)
            
            print(f"\n🔍 SEARCH RESULTS FOR: '{query}'")
            print("-" * 80)
            
            for result in results:
                result_type = result.get("type", "unknown")
                doc = result.get("document", "")[:100]
                print(f"[{result_type.upper()}] {doc}...")
                
            print("-" * 80)
        else:
            print("RAG system not available")
            
    def _show_analytics(self) -> None:
        """Show analytics"""
        if not self.analytics:
            print("Analytics not available")
            return
            
        report = self.analytics.get_full_report()
        health = report.get("inbox_health", {})
        
        print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                    PRODUCTIVITY ANALYTICS                        ║
╠══════════════════════════════════════════════════════════════════╣
║  INBOX HEALTH                                                   ║
║ ---------------------------------------------------------------- ║
║    Overall Score:    {health.get('overall_score', 'N/A'):<40} ║
║    Unread Count:     {health.get('unread_count', 0):<40} ║
║    Inbox Zero:       {'✓ Yes' if health.get('inbox_zero_achieved') else '✗ No':<40} ║
╠══════════════════════════════════════════════════════════════════╣
║  VOLUME METRICS                                                  ║
║ ---------------------------------------------------------------- ║""")
        
        volume = report.get("email_volume", {})
        print(f"║    Period Emails:     {volume.get('total_emails', 0):<40} ║")
        print(f"║    Daily Average:    {volume.get('daily_average', 0):.1f}{' emails/day':<38} ║")
        
        print("╚══════════════════════════════════════════════════════════════════╝")
        
    def _toggle_voice(self) -> None:
        """Toggle voice system"""
        if not self.voice:
            print("Voice system not available")
            return
            
        if self.voice._is_active:
            self.voice.deactivate()
            print("Voice system deactivated")
        else:
            self.voice.activate()
            print("Voice system activated")
            
    def _handle_voice_command(self, command) -> None:
        """Handle voice command"""
        self.logger.info(f"Voice command received: {command.text}")
        
        intent = command.intent
        entities = command.entities
        
        if intent == "read_important_emails":
            self._announce_important_emails()
        elif intent == "read_unread_emails":
            self._announce_unread_emails()
        elif intent == "inbox_status":
            self._announce_status()
        elif intent == "summarize_emails":
            self._announce_summary()
        elif intent == "search_emails":
            query = entities.get("query", "")
            self._search_and_announce(query)
        else:
            self.voice.speak("Sorry, I didn't understand that command.")
            
    def _announce_important_emails(self) -> None:
        """Announce important emails via voice"""
        if not self.db or not self.voice:
            return
            
        with self.db.get_session() as session:
            from database import Email, EmailDirection
            
            important = session.query(Email).filter(
                Email.importance_score >= 70,
                Email.direction == EmailDirection.INCOMING,
                Email.is_read == False
            ).order_by(Email.importance_score.desc()).limit(5).all()
            
            if not important:
                self.voice.speak("You have no important unread emails.")
                return
                
            text = f"You have {len(important)} important emails. "
            for email in important:
                text += f"Important email from {email.sender_name or email.sender_email}: {email.subject[:50]}. "
                
            self.voice.speak(text)
            
    def _announce_unread_emails(self) -> None:
        """Announce unread emails count"""
        if not self.db or not self.voice:
            return
            
        with self.db.get_session() as session:
            from database import Email, EmailDirection
            
            count = session.query(Email).filter(
                Email.is_read == False,
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            self.voice.speak(f"You have {count} unread emails.")
            
    def _announce_status(self) -> None:
        """Announce inbox status"""
        if not self.db or not self.voice:
            return
            
        with self.db.get_session() as session:
            from database import Email, Contact, FollowUp, EmailDirection
            
            unread = session.query(Email).filter(
                Email.is_read == False,
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            pending = session.query(Email).filter(
                Email.action_required == True,
                Email.is_replied == False
            ).count()
            
            followups = session.query(FollowUp).filter(
                FollowUp.completed == False
            ).count()
            
            text = f"Here's your inbox status. {unread} unread emails. "
            text += f"{pending} pending replies. "
            text += f"{followups} follow-ups scheduled."
            
            self.voice.speak(text)
            
    def _announce_summary(self) -> None:
        """Announce daily summary"""
        if self.analytics and self.voice:
            briefing = self.analytics.get_daily_briefing()
            self.voice.announce_summary(
                briefing.get("summary", {}).get("total_emails", 0),
                briefing.get("summary", {}).get("unread_inbox", 0),
                briefing.get("summary", {}).get("important", 0)
            )
            
    def _search_and_announce(self, query: str) -> None:
        """Search and announce results"""
        if self.rag and self.voice:
            results = self.rag.search(query, limit=3)
            if results:
                text = f"Found {len(results)} results. "
                for r in results:
                    text += f"{r.get('document', '')[:80]}. "
                self.voice.speak(text)
            else:
                self.voice.speak(f"No results found for {query}.")
            
    def _on_new_email(self, email) -> None:
        """Handle new email event"""
        # Auto-process and emit appropriate notifications
        priority_val = email.priority.value if email.priority else None
        if priority_val in ["P0_EMERGENCY", "P1_CRITICAL"]:
            if self.voice:
                self.voice.announce_email(
                    email.sender_name or email.sender_email,
                    email.subject,
                    priority=0 if priority_val == "P0_EMERGENCY" else 1
                )
                
    def _on_daily_briefing(self) -> None:
        """Handle daily briefing request"""
        if self.analytics and self.voice:
            briefing = self.analytics.get_daily_briefing()
            self.voice.speak(self.voice.prompter.generate_greeting(
                briefing.get("summary", {}).get("total_emails", 0)
            ))
            
    def _on_voice_alert(self, message: str, **kwargs) -> None:
        """Handle voice alert"""
        if self.voice:
            self.voice.speak(message)
            
    def _on_desktop_notification(self, title: str, message: str, **kwargs) -> None:
        """Handle desktop notification"""
        # In a real implementation, would use platform notifications
        logger.info(f"Desktop notification: {title} - {message}")
        
    def _on_escalation(self, email, level: int = 3) -> None:
        """Handle escalation"""
        logger.warning(f"Escalation triggered for email {email.id} at level {level}")
        
        if level >= 4 and self.voice:
            sender = email.sender_email if hasattr(email, 'sender_email') else "unknown"
            self.voice.speak(f"Attention! High priority escalation for email from {sender}.")
            
    def _sync_emails(self) -> None:
        """Sync emails"""
        if self.email_engine:
            logger.info("Starting email sync...")
            result = self.email_engine.sync_email()
            logger.info(f"Email sync complete: {result}")
            
    def shutdown(self) -> None:
        """Shutdown all systems"""
        logger.info("Shutting down Dragon Email Agent...")
        self._running = False
        self._shutdown_requested = True
        
        # Shutdown in reverse order
        if self.voice:
            self.voice.shutdown()
            
        if self.automation:
            self.automation.shutdown()
            
        if self.analytics:
            self.analytics.shutdown()
            
        if self.integrations:
            self.integrations.shutdown()
            
        if self.rag:
            self.rag.shutdown()
            
        if self.security:
            self.security.shutdown()
            
        if self.memory:
            self.memory.shutdown()
            
        if self.email_engine:
            self.email_engine.shutdown()
            
        if self.db:
            self.db.close()
            
        # Stop scheduler
        if hasattr(self, 'scheduler') and self.scheduler.running:
            self.scheduler.shutdown()
            
        logger.info("Dragon Email Agent shutdown complete")
        print("\n👋 Goodbye! Dragon Email Agent stopped.")
        sys.exit(0)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Dragon Email Agent - AI-Powered Email Management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Start with defaults
  python main.py --config config.yaml     # Use custom config
  python main.py --api                    # Start API server only
  python main.py --voice                  # Start with voice enabled
  python main.py --debug                  # Enable debug mode
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        default="config.yaml",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start API server only"
    )
    
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice system"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="API server port"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    from core import load_config
    
    config_path = args.config if os.path.exists(args.config) else None
    config = load_config(config_path) if config_path else Config()
    
    if args.debug:
        config.debug = True
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
        
    if args.voice:
        config.voice_enabled = True
        
    # Handle signals
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        if agent:
            agent.shutdown()
            
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start agent or API
    agent = None
    
    if args.api:
        # Start API server only
        logger.info(f"Starting API server on port {args.port}...")
        from api import run_server
        run_server(port=args.port, debug=args.debug)
    else:
        # Start full agent
        agent = DragonEmailAgent(config)
        
        if not agent.initialize():
            logger.error("Failed to initialize Dragon Email Agent")
            print("\n❌ Initialization failed. Please check logs for details.")
            sys.exit(1)
            
        agent.start()


if __name__ == "__main__":
    main()
