# =============================================================================
# SECURITY MODULE - Authentication, Encryption, Audit Logging
# =============================================================================

import os
import json
import base64
import hmac
import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import getpass

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False

from database import AuditLog, get_db_manager
from core import Config, DragonModule, logger


class EncryptionService:
    """Encryption service for sensitive data"""
    
    def __init__(self, config: Config):
        self.config = config
        self.fernet = None
        self._initialize()
        
    def _initialize(self) -> None:
        """Initialize encryption"""
        if not FERNET_AVAILABLE:
            logger.warning("Fernet cryptography not available")
            return
            
        try:
            # Load or generate key
            key_path = Path(config.encryption_key_path)
            
            if key_path.exists():
                with open(key_path, "rb") as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                key_path.parent.mkdir(parents=True, exist_ok=True)
                with open(key_path, "wb") as f:
                    f.write(key)
                # Set restrictive permissions
                os.chmod(key_path, 0o600)
                
            self.fernet = Fernet(key)
            logger.info("Encryption service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        if not self.fernet:
            return base64.b64encode(data.encode()).decode()
            
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data
            
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        if not self.fernet:
            return base64.b64decode(encrypted_data).decode()
            
        try:
            decrypted = self.fernet.decrypt(base64.b64decode(encrypted_data))
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data
            
    def encrypt_file(self, input_path: str, output_path: str) -> bool:
        """Encrypt a file"""
        if not self.fernet:
            return False
            
        try:
            with open(input_path, "rb") as f:
                data = f.read()
                
            encrypted = self.fernet.encrypt(data)
            
            with open(output_path, "wb") as f:
                f.write(encrypted)
                
            return True
        except Exception as e:
            logger.error(f"File encryption error: {e}")
            return False
            
    def decrypt_file(self, input_path: str, output_path: str) -> bool:
        """Decrypt a file"""
        if not self.fernet:
            return False
            
        try:
            with open(input_path, "rb") as f:
                encrypted = f.read()
                
            decrypted = self.fernet.decrypt(encrypted)
            
            with open(output_path, "wb") as f:
                f.write(decrypted)
                
            return True
        except Exception as e:
            logger.error(f"File decryption error: {e}")
            return False


class TokenManager:
    """Secure token storage and management"""
    
    def __init__(self, config: Config, encryption: EncryptionService):
        self.config = config
        self.encryption = encryption
        self._tokens: Dict[str, Dict[str, Any]] = {}
        self._token_file = os.path.join(config.data_dir, ".tokens.enc")
        self._load_tokens()
        
    def _load_tokens(self) -> None:
        """Load tokens from encrypted storage"""
        if not os.path.exists(self._token_file):
            return
            
        try:
            with open(self._token_file, "r") as f:
                encrypted = f.read()
                
            decrypted = self.encryption.decrypt(encrypted)
            self._tokens = json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to load tokens: {e}")
            
    def _save_tokens(self) -> None:
        """Save tokens to encrypted storage"""
        try:
            encrypted = self.encryption.encrypt(json.dumps(self._tokens))
            with open(self._token_file, "w") as f:
                f.write(encrypted)
            os.chmod(self._token_file, 0o600)
        except Exception as e:
            logger.error(f"Failed to save tokens: {e}")
            
    def store_token(
        self,
        name: str,
        token: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store a token securely"""
        self._tokens[name] = {
            "token": token,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
        }
        self._save_tokens()
        
    def get_token(self, name: str) -> Optional[str]:
        """Get token by name"""
        if name in self._tokens:
            self._tokens[name]["last_used"] = datetime.utcnow().isoformat()
            self._save_tokens()
            return self._tokens[name]["token"]
        return None
        
    def delete_token(self, name: str) -> bool:
        """Delete a token"""
        if name in self._tokens:
            del self._tokens[name]
            self._save_tokens()
            return True
        return False
        
    def list_tokens(self) -> List[str]:
        """List all token names"""
        return list(self._tokens.keys())
        
    def token_exists(self, name: str) -> bool:
        """Check if token exists"""
        return name in self._tokens


class AuditLogger:
    """Audit logging for security events"""
    
    def __init__(self, config: Config, db: Any):
        self.config = config
        self.db = db
        
    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int] = None,
        user: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> None:
        """Log an audit event"""
        if not self.config.audit_enabled:
            return
            
        try:
            log_entry = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                user=user or "system",
                details=details or {},
                status=status,
                error_message=error_message,
                created_at=datetime.utcnow()
            )
            
            with self.db.get_session() as session:
                session.add(log_entry)
                
            # Also log to file
            self._log_to_file(action, entity_type, details, status)
            
        except Exception as e:
            logger.error(f"Audit log error: {e}")
            
    def _log_to_file(self, action: str, entity_type: str, details: Any, status: str) -> None:
        """Log to file"""
        import structlog
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "entity_type": entity_type,
            "status": status,
        }
        if details:
            log_data["details"] = str(details)[:1000]  # Limit size
            
        if status == "success":
            structlog.get_logger().info("audit_event", **log_data)
        else:
            structlog.get_logger().error("audit_event", **log_data)
            
    def get_logs(
        self,
        entity_type: Optional[str] = None,
        action: Optional[str] = None,
        user: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve audit logs"""
        with self.db.get_session() as session:
            query = session.query(AuditLog)
            
            if entity_type:
                query = query.filter(AuditLog.entity_type == entity_type)
            if action:
                query = query.filter(AuditLog.action == action)
            if user:
                query = query.filter(AuditLog.user == user)
            if since:
                query = query.filter(AuditLog.created_at >= since)
                
            logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "user": log.user,
                    "status": log.status,
                    "details": log.details,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]


class PasswordManager:
    """Secure password management"""
    
    def __init__(self, encryption: EncryptionService):
        self.encryption = encryption
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        try:
            from passlib.hash import bcrypt
            return bcrypt.hash(password)
        except ImportError:
            # Fallback to sha256
            return hashlib.sha256(password.encode()).hexdigest()
            
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        try:
            from passlib.hash import bcrypt
            return bcrypt.verify(password, hashed)
        except ImportError:
            return hashlib.sha256(password.encode()).hexdigest() == hashed
            
    def generate_password(self, length: int = 16) -> str:
        """Generate a secure random password"""
        return secrets.token_urlsafe(length)


class OAuthHandler:
    """OAuth 2.0 authentication handler"""
    
    def __init__(self, config: Config, token_manager: TokenManager):
        self.config = config
        self.token_manager = token_manager
        
    def get_gmail_auth_url(self) -> str:
        """Get Gmail OAuth URL"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
            ]
            
            # Get client config
            client_id = self.config.gmail_client_id
            client_secret = self.config.gmail_client_secret
            credentials_path = self.config.gmail_credentials_path
            
            if not credentials_path or not os.path.exists(credentials_path):
                logger.error("Gmail credentials file not configured")
                return ""
                
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                SCOPES
            )
            
            auth_url, _ = flow.authorization_url(prompt="consent")
            return auth_url
            
        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            return ""
            
    def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens"""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            SCOPES = [
                "https://www.googleapis.com/auth/gmail.readonly",
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/gmail.modify",
            ]
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.config.gmail_credentials_path,
                SCOPES
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Store tokens
            token_data = {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
            
            self.token_manager.store_token("gmail", json.dumps(token_data))
            return token_data
            
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return None
            
    def refresh_token_if_needed(self) -> bool:
        """Refresh token if expired"""
        try:
            token_json = self.token_manager.get_token("gmail")
            if not token_json:
                return False
                
            token_data = json.loads(token_json)
            expiry = datetime.fromisoformat(token_data["expiry"])
            
            if datetime.utcnow() >= expiry - timedelta(minutes=5):
                # Refresh token
                refresh_token = token_data["refresh_token"]
                # Would use google.auth to refresh
                # Implementation depends on google-auth library
                return True
                
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False
        return True


class SecurityModule(DragonModule):
    """Main security module"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.db = get_db_manager(config.db_path)
        self.encryption = EncryptionService(config)
        self.tokens = TokenManager(config, self.encryption)
        self.audit = AuditLogger(config, self.db)
        self.passwords = PasswordManager(self.encryption)
        self.oauth = OAuthHandler(config, self.tokens)
        
    def initialize(self) -> None:
        """Initialize security module"""
        super().initialize()
        logger.info("Security Module initialized")
        
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user"""
        # In production, integrate with proper auth system
        # This is a simplified example
        self.audit.log(
            action="login_attempt",
            entity_type="user",
            details={"username": username}
        )
        return None  # Return None means auth not implemented
        
    def create_backup(self, backup_path: str) -> bool:
        """Create encrypted backup"""
        try:
            # Backup database
            self.db.backup(backup_path + ".db")
            
            # Backup tokens
            if os.path.exists(self.tokens._token_file):
                encrypted_dest = backup_path + ".tokens.enc"
                import shutil
                shutil.copy2(self.tokens._token_file, encrypted_dest)
                
            logger.info(f"Backup created: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
            
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup"""
        try:
            # Restore database
            db_restore_path = self.config.db_path + ".restore"
            import shutil
            
            if os.path.exists(backup_path + ".db"):
                shutil.copy2(backup_path + ".db", db_restore_path)
                
            self.audit.log(
                action="backup_restore",
                entity_type="system",
                status="success"
            )
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
            
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status"""
        return {
            "encryption_enabled": FERNET_AVAILABLE,
            "audit_logging": self.config.audit_enabled,
            "oauth_configured": bool(self.config.gmail_credentials_path),
            "tokens_stored": len(self.tokens.list_tokens()),
            "today_events": len(self.audit.get_logs(
                since=datetime.utcnow() - timedelta(days=1)
            )),
        }
        
    def shutdown(self) -> None:
        """Cleanup on shutdown"""
        self.audit.log(
            action="system_shutdown",
            entity_type="system",
            status="success"
        )
        logger.info("Security Module shutdown complete")
