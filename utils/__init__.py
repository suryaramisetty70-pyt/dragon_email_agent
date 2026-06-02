# =============================================================================
# UTILS MODULE - Utility Functions
# =============================================================================

import os
import re
import json
import uuid
import hashlib
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import mimetypes


def generate_id(prefix: str = "") -> str:
    """Generate unique ID"""
    return f"{prefix}{uuid.uuid4().hex[:12]}" if prefix else uuid.uuid4().hex[:12]


def hash_string(text: str) -> str:
    """Generate hash of string"""
    return hashlib.sha256(text.encode()).hexdigest()


def hash_file(filepath: str) -> str:
    """Generate hash of file"""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration"""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m"
    elif seconds < 86400:
        return f"{int(seconds/3600)}h"
    else:
        return f"{int(seconds/86400)}d"


def format_date(dt: Optional[datetime], format_str: str = "%Y-%m-%d") -> str:
    """Format datetime to string"""
    if not dt:
        return ""
    return dt.strftime(format_str)


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time"""
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    elif diff.days == 1:
        return "yesterday"
    elif diff.days < 7:
        return f"{diff.days}d ago"
    elif diff.days < 30:
        return f"{diff.days//7}w ago"
    else:
        return dt.strftime("%b %d")


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats"""
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    # Try relative date parsing
    date_str_lower = date_str.lower().strip()
    
    if date_str_lower in ["today"]:
        return datetime.combine(datetime.utcnow().date(), datetime.min.time())
    elif date_str_lower in ["yesterday"]:
        yesterday = datetime.utcnow().date() - timedelta(days=1)
        return datetime.combine(yesterday, datetime.min.time())
    elif date_str_lower in ["tomorrow"]:
        tomorrow_chrd = datetime.utcnow().date() + timedelta(days=1)
        return datetime.combine(tomorrow_chrd, datetime.min.time())
        
    return None


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize text for safe display"""
    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    if max_length and len(text) > max_length:
        text = text[:max_length-3] + "..."
        
    return text


def sanitize_filename(filename: str) -> str:
    """Sanitize filename"""
    # Remove/replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
        
    return filename


def is_valid_email(email: str) -> bool:
    """Validate email address"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def extract_domain(email: str) -> str:
    """Extract domain from email"""
    if '@' in email:
        return email.split('@')[1].lower()
    return ""


def extract_name_from_email(email: str) -> str:
    """Extract name-like part from email"""
    if '@' in email:
        name = email.split('@')[0]
        name = name.split('+')[0]  # Remove +tag
        # Convert underscores and dots to spaces
        name = re.sub(r'[._]', ' ', name)
        # Capitalize
        name = ' '.join(w.capitalize() for w in name.split())
        return name
    return ""


def truncate_text(text: str, length: int, suffix: str = "...") -> str:
    """Truncate text to length"""
    if len(text) <= length:
        return text
    return text[:length - len(suffix)] + suffix


def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from text"""
    return re.findall(r'#(\w+)', text)


def extract_mentions(text: str) -> List[str]:
    """Extract mentions from text"""
    return re.findall(r'@(\w+)', text)


def clean_html(html: str) -> str:
    """Remove HTML tags from text"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text()


def get_mime_type(filename: str) -> str:
    """Get MIME type from filename"""
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or "application/octet-stream"


def ensure_directory(path: Union[str, Path]) -> Path:
    """Ensure directory exists"""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safe JSON parsing"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, default: str = "{}") -> str:
    """Safe JSON serialization"""
    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return default


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict) -> Dict:
    """Merge multiple dictionaries"""
    result = {}
    for d in dicts:
        result.update(d)
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_file_extension(filename: str) -> str:
    """Get file extension without dot"""
    return os.path.splitext(filename)[1].lstrip('.')


def is_same_day(dt1: datetime, dt2: datetime) -> bool:
    """Check if two datetimes are on the same day"""
    return dt1.date() == dt2.date()


def is_weekend(dt: Optional[datetime] = None) -> bool:
    """Check if date is weekend"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.weekday() >= 5


def get_week_start(dt: Optional[datetime] = None) -> date:
    """Get start of week (Monday)"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.date() - timedelta(days=dt.weekday())


def get_month_start(dt: Optional[datetime] = None) -> date:
    """Get start of month"""
    if dt is None:
        dt = datetime.utcnow()
    return dt.date().replace(day=1)


class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self.calls: List[datetime] = []
        
    def is_allowed(self) -> bool:
        """Check if call is allowed"""
        now = datetime.utcnow()
        
        # Remove old calls
        self.calls = [
            c for c in self.calls 
            if (now - c).total_seconds() < self.period
        ]
        
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
            
        return False
        
    def wait_time(self) -> float:
        """Get wait time in seconds"""
        if not self.calls:
            return 0
            
        oldest = min(self.calls)
        elapsed = (datetime.utcnow() - oldest).total_seconds()
        return max(0, self.period - elapsed)


class RetryHelper:
    """Helper for retry logic"""
    
    def __init__(
        self, 
        max_attempts: int = 3, 
        base_delay: float = 1.0,
        exponential_backoff: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.exponential = exponential_backoff
        
    def execute(self, func, *args, **kwargs):
        """Execute function with retry"""
        import time
        
        last_error = None
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if attempt < self.max_attempts - 1:
                    delay = self.base_delay * (2 ** attempt if self.exponential else 1)
                    time.sleep(delay)
                    
        if last_error:
            raise last_error
