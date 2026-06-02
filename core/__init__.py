# =============================================================================
# CORE MODULE - Base Classes and Configuration
# =============================================================================

import os
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

try:
    from omegaconf import OmegaConf
    OMEGACONF_AVAILABLE = True
except ImportError:
    OMEGACONF_AVAILABLE = False

# Pydantic for configuration
from pydantic import BaseModel, Field

# Configure logging
from loguru import logger

# Add custom format for logging
logger.configure(
    handlers=[
        {
            "sink": "logs/dragon.log",
            "level": "DEBUG",
            "rotation": "100 MB",
            "retention": "30 days",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        },
        {
            "sink": "logs/dragon_error.log",
            "level": "ERROR",
            "rotation": "50 MB",
            "retention": "90 days",
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        },
        {
            "sink": lambda msg: print(msg),
            "level": "INFO",
            "format": "{time:HH:mm:ss} | {level} | {message}",
        },
    ]
)

# =============================================================================
# CONFIGURATION
# =============================================================================

class LLMProvider(Enum):
    """Supported LLM providers"""
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    MISTRAL = "mistral"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Config(BaseModel):
    """Main configuration"""
    # App settings
    app_name: str = "Dragon Email Agent"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    db_path: str = "data/dragon_email.db"
    use_sqlite: bool = True
    
    # LLM Settings
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    llm_base_url: str = "http://localhost:11434"
    llm_api_key: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 4096
    
    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = 32
    
    # Voice Settings
    voice_enabled: bool = True
    wake_word: str = "hey dragon"
    voice_language: str = "en-US"
    tts_rate: float = 170
    tts_pitch: float = 1.0
    
    # Email Settings
    default_account: str = "gmail"
    sync_interval: int = 60  # seconds
    max_email_age_days: int = 365
    batch_size: int = 100
    
    # Priority & Classification
    emergency_keywords: List[str] = [
        "emergency", "urgent", "immediate action", "critical", 
        "asap", "help", "police", "ambulance", "fire"
    ]
    critical_keywords: List[str] = [
        "deadline", "client", "offer", "interview", "hiring",
        "faculty", "professor", "dean", "dean"
    ]
    important_keywords: List[str] = [
        "meeting", "project", "update", "report", "review", 
        "team", "colleague", "document"
    ]
    
    # Escalation
    escalation_levels: Dict[int, Dict[str, Any]] = {
        1: {"name": "notification", "delay_minutes": 0},
        2: {"name": "voice_reminder", "delay_minutes": 15},
        3: {"name": "fullscreen_alert", "delay_minutes": 30},
        4: {"name": "dragon_announce", "delay_minutes": 60},
        5: {"name": "calling_agent", "delay_minutes": 120},
    }
    
    # Response time thresholds (in hours)
    response_thresholds: Dict[str, int] = {
        "emergency": 0.5,
        "client": 6,
        "faculty": 4,
        "work": 24,
        "personal": 48,
        "other": 72,
    }
    
    # VIP Contacts (emails that always get high priority)
    vip_contacts: List[str] = Field(default_factory=list)
    
    # Agent Integration
    dragon_core_url: str = "http://localhost:8000"
    enable_agent_integration: bool = True
    
    # Gmail API
    gmail_client_id: Optional[str] = None
    gmail_client_secret: Optional[str] = None
    gmail_credentials_path: Optional[str] = None
    
    # IMAP Settings
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_use_ssl: bool = True
    
    # SMTP Settings
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    
    # SMTP Credentials
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # Security
    encryption_key_path: str = "data/.encryption.key"
    audit_enabled: bool = True
    
    # Paths
    data_dir: str = "data"
    logs_dir: str = "logs"
    attachments_dir: str = "data/attachments"
    cache_dir: str = "data/cache"
    
    class Config:
        extra = "allow"


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from file"""
    config_file = Path(config_path)
    
    if config_file.exists() and OMEGACONF_AVAILABLE:
        # Load from YAML
        conf = OmegaConf.load(config_file)
        return Config(**OmegaConf.to_container(conf, resolve=True))
    else:
        # Return default config
        return Config()


def save_config(config: Config, config_path: str = "config.yaml") -> None:
    """Save configuration to file"""
    if OMEGACONF_AVAILABLE:
        OmegaConf.save(
            OmegaConf.dict(config.model_dump()),
            config_path
        )
    else:
        # Simple YAML write without OmegaConf
        import yaml
        with open(config_path, "w") as f:
            yaml.dump(config.model_dump(), f)


# =============================================================================
# BASE CLASSES
# =============================================================================

class DragonModule:
    """Base class for all Dragon modules"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logger.bind(module=self.__class__.__name__)
        self._initialized = False
        
    def initialize(self) -> None:
        """Initialize module"""
        if self._initialized:
            return
        self._setup_directories()
        self._initialized = True
        
    def _setup_directories(self) -> None:
        """Create required directories"""
        dirs = [
            self.config.data_dir,
            self.config.logs_dir,
            self.config.attachments_dir,
            self.config.cache_dir,
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        pass


class EventEmitter:
    """Simple event emitter for inter-module communication"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
        
    def on(self, event: str, callback: Callable) -> None:
        """Register event listener"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
        
    def off(self, event: str, callback: Callable) -> None:
        """Remove event listener"""
        if event in self._listeners:
            self._listeners[event].remove(callback)
            
    def emit(self, event: str, *args, **kwargs) -> None:
        """Emit event to all listeners"""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Event handler error: {e}")
                    
    def clear(self, event: Optional[str] = None) -> None:
        """Clear all listeners"""
        if event:
            self._listeners.pop(event, None)
        else:
            self._listeners.clear()


# Global event emitter
events = EventEmitter()


# =============================================================================
# STATUS & UTILITIES
# =============================================================================

class ModuleStatus(Enum):
    """Module operational status"""
    STOPPED = "stopped"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class StatusReport:
    """System status report"""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    modules: Dict[str, ModuleStatus] = field(default_factory=dict)
    database: bool = False
    llm_connected: bool = False
    voice_active: bool = False
    email_accounts: int = 0
    total_emails: int = 0
    unread_emails: int = 0
    pending_actions: int = 0
    errors: List[str] = field(default_factory=list)


def get_version_info() -> Dict[str, str]:
    """Get version information"""
    return {
        "app": Config().app_name,
        "version": Config().app_version,
        "python_version": os.environ.get("PYTHON_VERSION", "Unknown"),
    }


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove/replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename[:255]  # Max filename length
    return filename


def format_email_preview(body: str, max_length: int = 200) -> str:
    """Format email body to preview"""
    import html
    from html.parser import HTMLParser
    
    class HTMLTextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            
        def handle_data(self, d):
            self.result.append(d)
            
        def get_data(self):
            return ''.join(self.result)
    
    # Strip HTML
    try:
        parser = HTMLTextExtractor()
        parser.feed(body)
        text = parser.get_data()
    except:
        text = html.unescape(body)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    return text


def extract_domain(email: str) -> str:
    """Extract domain from email"""
    if '@' in email:
        return email.split('@')[1].lower()
    return ""


def is_email_valid(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def format_timestamp(dt: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format timestamp"""
    return dt.strftime(format_str)


def parse_duration(duration_str: str) -> int:
    """Parse duration string to minutes"""
    import re
    units = {
        's': 1/60,
        'm': 1,
        'h': 60,
        'd': 1440,
        'w': 10080,
    }
    match = re.match(r'^(\d+)\s*([smhdw])', duration_str.lower())
    if match:
        value, unit = match.groups()
        return int(float(value) * units.get(unit, 1))
    return int(duration_str) if duration_str.isdigit() else 0
