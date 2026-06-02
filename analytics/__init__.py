# =============================================================================
# ANALYTICS MODULE - Metrics and Reporting
# =============================================================================

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict
import statistics

from database import (
    Email, Contact, Thread, FollowUp, Escalation, AuditLog,
    get_db_manager, EmailPriority, EmailCategory, EmailDirection, DailyBriefing
)
from core import Config, DragonModule, logger


class MetricCollector:
    """Collect email metrics"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        
    def get_email_volume_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get email volume statistics"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            emails = session.query(Email).filter(
                Email.date_received >= cutoff
            ).all()
            
            # Daily breakdown
            daily_counts = defaultdict(int)
            for email in emails:
                day = email.date_received.date()
                daily_counts[day] = daily_counts[day] + 1
                
            # Category breakdown
            category_counts = defaultdict(int)
            for email in emails:
                category_counts[email.category.value if email.category else "unknown"] += 1
                
            # Priority breakdown
            priority_counts = defaultdict(int)
            for email in emails:
                priority_counts[email.priority.value if email.priority else "unknown"] += 1
                
            return {
                "total_emails": len(emails),
                "period_days": days,
                "daily_average": len(emails) / days if days > 0 else 0,
                "daily_counts": dict(sorted(daily_counts.items())),
                "by_category": dict(category_counts),
                "by_priority": dict(priority_counts),
            }
            
    def get_priority_distribution(self) -> Dict[str, Any]:
        """Get priority distribution"""
        with self.db.get_session() as session:
            counts = {
                "P0_Emergency": session.query(Email).filter(
                    Email.priority == EmailPriority.P0_EMERGENCY,
                    Email.direction == EmailDirection.INCOMING
                ).count(),
                "P1_Critical": session.query(Email).filter(
                    Email.priority == EmailPriority.P1_CRITICAL,
                    Email.direction == EmailDirection.INCOMING
                ).count(),
                "P2_Important": session.query(Email).filter(
                    Email.priority == EmailPriority.P2_IMPORTANT,
                    Email.direction == EmailDirection.INCOMING
                ).count(),
                "P3_Normal": session.query(Email).filter(
                    Email.priority == EmailPriority.P3_NORMAL,
                    Email.direction == EmailDirection.INCOMING
                ).count(),
                "P4_Low": session.query(Email).filter(
                    Email.priority == EmailPriority.P4_LOW,
                    Email.direction == EmailDirection.INCOMING
                ).count(),
            }
            
            total = sum(counts.values())
            
            return {
                "counts": counts,
                "percentages": {
                    k: round(v / total * 100, 2) if total > 0 else 0 
                    for k, v in counts.items()
                },
                "total": total,
            }
            
    def get_response_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get response time metrics"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            # Get replied emails with metrics
            replied_emails = session.query(Email).filter(
                Email.is_replied == True,
                Email.date_received >= cutoff
            ).all()
            
            response_times = []
            for email in replied_emails:
                # This would need better tracking - for now estimate
                if email.action_deadline:
                    response_times.append(24)  # Placeholder
                    
            return {
                "total_replied": len(replied_emails),
                "avg_response_hours": statistics.mean(response_times) if response_times else 0,
                "min_response_hours": min(response_times) if response_times else 0,
                "max_response_hours": max(response_times) if response_times else 0,
            }
            
    def get_contact_activity(self) -> Dict[str, Any]:
        """Get contact activity metrics"""
        with self.db.get_session() as session:
            # Top contacted
            from sqlalchemy import func
            
            top_contacts = session.query(
                Email.sender_email,
                Email.sender_name,
                func.count(Email.id).label("email_count")
            ).filter(
                Email.direction == EmailDirection.INCOMING
            ).group_by(
                Email.sender_email, Email.sender_name
            ).order_by(
                func.count(Email.id).desc()
            ).limit(20).all()
            
            # Read vs unread ratio
            total_incoming = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            unread_incoming = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING,
                Email.is_read == False
            ).count()
            
            return {
                "total_contacts": session.query(Contact).count(),
                "vip_contacts": session.query(Contact).filter(
                    Contact.is_vip == True
                ).count(),
                "top_contacted": [
                    {
                        "email": c.sender_email,
                        "name": c.sender_name,
                        "count": c.email_count
                    }
                    for c in top_contacts
                ],
                "read_ratio": round((total_incoming - unread_incoming) / total_incoming * 100, 2) if total_incoming > 0 else 0,
            }


class DailyBriefingGenerator:
    """Generate daily briefings"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        self.metric_collector = MetricCollector(config, db)
        
    def generate(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Generate daily briefing"""
        if date is None:
            date = datetime.utcnow()
            
        target_date = date.date()
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        with self.db.get_session() as session:
            # Emails for today
            today_emails = session.query(Email).filter(
                Email.date_received >= start_of_day,
                Email.date_received <= end_of_day,
                Email.direction == EmailDirection.INCOMING
            ).all()
            
            # Unread count
            unread_count = session.query(Email).filter(
                Email.is_read == False,
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            # Pending replies
            pending_replies = session.query(Email).filter(
                Email.action_required == True,
                Email.is_replied == False
            ).count()
            
            # Important emails (score >= 70)
            important_emails = [
                {
                    "id": e.id,
                    "subject": e.subject,
                    "from": e.sender_name or e.sender_email,
                    "score": e.importance_score,
                    "priority": e.priority.value if e.priority else "unknown",
                    "category": e.category.value if e.category else "unknown",
                }
                for e in today_emails if e.importance_score >= 70
            ]
            important_emails.sort(key=lambda x: x["score"], reverse=True)
            
            # Category breakdown
            category_breakdown = defaultdict(int)
            for email in today_emails:
                category_breakdown[email.category.value if email.category else "unknown"] += 1
                
            # High priority emails
            urgent_emails = [
                {
                    "from": e.sender_name or e.sender_email,
                    "subject": e.subject[:80],
                }
                for e in today_emails 
                if e.priority in [EmailPriority.P0_EMERGENCY, EmailPriority.P1_CRITICAL]
            ]
            
            # Follow-ups due today
            due_followups = session.query(FollowUp).filter(
                FollowUp.scheduled_date >= start_of_day,
                FollowUp.scheduled_date <= end_of_day,
                FollowUp.completed == False
            ).count()
            
            # Active escalations
            active_escalations = session.query(Escalation).filter(
                Escalation.resolved_at.is_(None)
            ).count()
            
            # Top senders today
            from sqlalchemy import func
            top_senders = session.query(
                Email.sender_email,
                func.count(Email.id).label("count")
            ).filter(
                Email.date_received >= start_of_day,
                Email.date_received <= end_of_day,
                Email.direction == EmailDirection.INCOMING
            ).group_by(Email.sender_email).order_by(
                func.count(Email.id).desc()
            ).limit(5).all()
            
            briefing = {
                "date": target_date.isoformat(),
                "summary": {
                    "total_emails": len(today_emails),
                    "unread_inbox": unread_count,
                    "pending_replies": pending_replies,
                    "important": len(important_emails),
                    "urgent": len(urgent_emails),
                    "due_followups": due_followups,
                    "active_escalations": active_escalations,
                },
                "important_emails": important_emails[:10],
                "urgent_emails": urgent_emails,
                "category_breakdown": dict(category_breakdown),
                "top_senders": [
                    {"email": s.sender_email, "count": s.count}
                    for s in top_senders
                ],
                "metrics": self.metric_collector.get_email_volume_stats(days=7),
            }
            
            # Store briefing
            db_briefing = DailyBriefing(
                date=start_of_day,
                summary=briefing["summary"],
                important_emails=[e["id"] for e in important_emails[:20]],
                unread_count=unread_count,
                pending_replies=pending_replies,
                generated_at=datetime.utcnow(),
            )
            session.add(db_briefing)
            
            return briefing
            
    def get_cached(self, date: datetime) -> Optional[Dict[str, Any]]:
        """Get cached briefing for date"""
        target_date = date.date()
        start_of_day = datetime.combine(target_date, datetime.min.time())
        
        with self.db.get_session() as session:
            briefing = session.query(DailyBriefing).filter(
                DailyBriefing.date == start_of_day
            ).first()
            
            if briefing:
                return {
                    "date_generated": briefing.generated_at.isoformat(),
                    "is_cached": True,
                    "summary": briefing.summary,
                    "unread_count": briefing.unread_count,
                    "pending_replies": briefing.pending_replies,
                }
        return None


class ProductivityAnalyzer:
    """Analyze email productivity"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        
    def get_inbox_health_score(self) -> Dict[str, Any]:
        """Calculate inbox health score"""
        with self.db.get_session() as session:
            total_incoming = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING
            ).count()
            
            unread_incoming = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING,
                Email.is_read == False
            ).count()
            
            # Calculate age of unread
            oldest_unread = session.query(Email).filter(
                Email.direction == EmailDirection.INCOMING,
                Email.is_read == False
            ).order_by(Email.date_received.asc()).first()
            
            age_days = 0
            if oldest_unread:
                age_days = (datetime.utcnow() - oldest_unread.date_received).days
                
            # Inbox zero status
            inbox_zero = unread_incoming == 0
            
            # Response rate (replied emails / total sent)
            sent_emails = session.query(Email).filter(
                Email.direction == EmailDirection.OUTGOING
            ).count()
            
            # Score calculation
            score = 100
            
            # Deduct for unread percentage
            if total_incoming > 0:
                unread_pct = unread_incoming / total_incoming
                score -= unread_pct * 30
                
            # Deduct for old unread
            score -= min(age_days * 2, 30)
            
            # Deduct for no inbox zero
            if not inbox_zero:
                score -= 10
                
            score = max(0, min(100, score))
            
            return {
                "overall_score": round(score, 1),
                "unread_count": unread_incoming,
                "inbox_zero_achieved": inbox_zero,
                "oldest_unread_days": age_days,
            }
            
    def get_response_time_analysis(self, days: int = 30) -> Dict[str, Any]:
        """Analyze response times"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        with self.db.get_session() as session:
            # This would need actual reply time tracking
            # For now, estimate based on time patterns
            recent_emails = session.query(Email).filter(
                Email.date_received >= cutoff,
                Email.direction == EmailDirection.INCOMING
            ).all()
            
            hour_distribution = defaultdict(int)
            day_distribution = defaultdict(int)
            
            for email in recent_emails:
                hour_distribution[email.date_received.hour] += 1
                day_distribution[email.date_received.strftime("%A")] += 1
                
            return {
                "分析了": days,
                "email_volume": len(recent_emails),
                "busiest_hour": max(hour_distribution, key=hour_distribution.get, default=9),
                "busiest_day": max(day_distribution, key=day_distribution.get, default="Monday"),
                "hourly_distribution": dict(hour_distribution),
                "daily_distribution": dict(day_distribution),
            }
            
    def get_trend_analysis(self, period: str = "week") -> Dict[str, Any]:
        """Get email trend analysis"""
        if period == "week":
            days = 7
        elif period == "month":
            days = 30
        else:
            days = 7
            
        stats = self._get_daily_trends(days)
        
        # Calculate trend
        if len(stats) >= 2:
            recent = stats[-7:] if len(stats) >= 7 else stats
            older = stats[:-7] if len(stats) >= 14 else stats[:7]
            
            recent_avg = sum(s["count"] for s in recent) / len(recent) if recent else 0
            older_avg = sum(s["count"] for s in older) / len(older) if older else 0
            
            if older_avg > 0:
                trend_pct = ((recent_avg - older_avg) / older_avg) * 100
            else:
                trend_pct = 0
        else:
            trend_pct = 0
            
        return {
            "period": period,
            "trend": "increasing" if trend_pct > 10 else "decreasing" if trend_pct < -10 else "stable",
            "trend_percentage": round(trend_pct, 1),
            "daily_data": stats,
        }
        
    def _get_daily_trends(self, days: int) -> List[Dict[str, Any]]:
        """Get daily trend data"""
        stats = []
        
        for i in range(days):
            date = datetime.utcnow().date() - timedelta(days=i)
            start = datetime.combine(date, datetime.min.time())
            end = datetime.combine(date, datetime.max.time())
            
            with self.db.get_session() as session:
                count = session.query(Email).filter(
                    Email.date_received >= start,
                    Email.date_received <= end,
                    Email.direction == EmailDirection.INCOMING
                ).count()
                
                unread = session.query(Email).filter(
                    Email.date_received >= start,
                    Email.date_received <= end,
                    Email.is_read == False
                ).count()
                
                stats.append({
                    "date": date.isoformat(),
                    "count": count,
                    "unread": unread,
                })
                
        return list(reversed(stats))


class Analytics(DragonModule):
    """Main analytics module"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.metrics = MetricCollector(config, self.db)
        self.briefing_generator = DailyBriefingGenerator(config, self.db)
        self.productivity = ProductivityAnalyzer(config, self.db)
        
    def initialize(self) -> None:
        """Initialize analytics"""
        super().initialize()
        logger.info("Analytics Module initialized")
        
    def get_full_report(self, period: str = "week") -> Dict[str, Any]:
        """Generate full analytics report"""
        return {
            "inbox_health": self.productivity.get_inbox_health_score(),
            "email_volume": self.metrics.get_email_volume_stats(
                days=7 if period == "week" else 30
            ),
            "priority_distribution": self.metrics.get_priority_distribution(),
            "response_metrics": self.metrics.get_response_metrics(),
            "contact_activity": self.metrics.get_contact_activity(),
            "trends": self.productivity.get_trend_analysis(period),
        }
        
    def get_daily_briefing(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily briefing"""
        # Check cache first
        if date:
            cached = self.briefing_generator.get_cached(date)
            if cached:
                return cached
                
        # Generate new briefing
        return self.briefing_generator.generate(date)
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        logger.info("Analytics Module shutdown complete")
