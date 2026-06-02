# =============================================================================
# PROJECT DRAGON - EMAIL AI AGENT
# Ultimate Email Intelligence System
# =============================================================================

from .core import *
from .database import *
from .email_engine import *
from .voice import *
from .memory import *
from .rag import *
from .security import *
from .automation import *
from .analytics import *
from .integrations import *
from .utils import *

__version__ = "1.0.0"
__all__ = [
    "Config",
    "DragonModule",
    "EmailEngine",
    "VoiceSystem",
    "MemorySystem",
    "RAGSystem",
    "SecurityModule",
    "AutomationEngine",
    "Analytics",
    "IntegrationManager",
    "get_db_manager",
    "EmailCategory",
    "EmailPriority",
]
