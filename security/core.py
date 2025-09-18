"""
Core Security Framework for Rural Banking
Lightweight cybersecurity framework optimized for low-resource devices
"""

import hashlib
import hmac
import secrets
import time
import json
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import jwt
from typing import Dict, Any, Optional, Tuple
import logging
import numpy as np

# Configure logging for security events
logging.basicConfig(level=logging.INFO)
security_logger = logging.getLogger('security')

def convert_numpy_types(obj):
    """Convert numpy types to JSON-serializable Python types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj

class SecurityCore:
    """Core security class for encryption, hashing, and secure operations"""
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or self._generate_master_key()
        self.cipher_suite = self._initialize_cipher()
        self.session_timeout = 900  # 15 minutes for rural users
        
    def _generate_master_key(self) -> str:
        """Generate a secure master key for encryption"""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
    
    def _initialize_cipher(self) -> Fernet:
        """Initialize Fernet cipher for symmetric encryption"""
        key = base64.urlsafe_b64encode(
            PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'rural_banking_salt',  # In production, use random salt
                iterations=100000,
                backend=default_backend()
            ).derive(self.master_key.encode())
        )
        return Fernet(key)
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            encrypted = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            security_logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            security_logger.error(f"Decryption failed: {e}")
            raise
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Create secure password hash with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing (more secure than bcrypt for this use case)
        key = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        hash_value = base64.urlsafe_b64encode(key.derive(password.encode())).decode()
        return hash_value, salt
    
    def verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """Verify password against hash"""
        try:
            computed_hash, _ = self.hash_password(password, salt)
            return hmac.compare_digest(hash_value, computed_hash)
        except Exception as e:
            security_logger.error(f"Password verification failed: {e}")
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    def create_session_token(self, user_id: str, device_id: str) -> str:
        """Create JWT session token with device binding"""
        payload = {
            'user_id': user_id,
            'device_id': device_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + self.session_timeout,
            'type': 'session'
        }
        return jwt.encode(payload, self.master_key, algorithm='HS256')
    
    def verify_session_token(self, token: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Verify and decode session token"""
        try:
            payload = jwt.decode(token, self.master_key, algorithms=['HS256'])
            
            # Verify device binding
            if payload.get('device_id') != device_id:
                security_logger.warning(f"Device mismatch for token: {device_id}")
                return None
            
            # Check if token is expired
            if payload.get('exp', 0) < time.time():
                return None
                
            return payload
        except jwt.InvalidTokenError as e:
            security_logger.warning(f"Invalid token: {e}")
            return None
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate numeric OTP for rural users"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    def create_transaction_signature(self, transaction_data: Dict[str, Any]) -> str:
        """Create HMAC signature for transaction integrity"""
        # Convert numpy types and sort keys for consistent signature
        clean_data = convert_numpy_types(transaction_data)
        sorted_data = json.dumps(clean_data, sort_keys=True)
        signature = hmac.new(
            self.master_key.encode(),
            sorted_data.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_transaction_signature(self, transaction_data: Dict[str, Any], signature: str) -> bool:
        """Verify transaction signature"""
        expected_signature = self.create_transaction_signature(transaction_data)
        return hmac.compare_digest(signature, expected_signature)

class DeviceFingerprinting:
    """Device fingerprinting for additional security"""
    
    @staticmethod
    def generate_device_id(user_agent: str, ip_address: str, additional_data: str = "") -> str:
        """Generate device fingerprint"""
        fingerprint_data = f"{user_agent}:{ip_address}:{additional_data}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    @staticmethod
    def is_trusted_device(device_id: str, user_id: str, trusted_devices: list) -> bool:
        """Check if device is in trusted list"""
        return device_id in trusted_devices

class SecurityAudit:
    """Security audit and logging"""
    
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Setup security audit logger"""
        logger = logging.getLogger('security_audit')
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger
    
    def log_security_event(self, event_type: str, user_id: str, details: Dict[str, Any]):
        """Log security events with proper type conversion"""
        log_entry = {
            'timestamp': time.time(),
            'event_type': event_type,
            'user_id': user_id,
            'details': convert_numpy_types(details)  # Convert numpy types to JSON-serializable types
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_failed_authentication(self, user_id: str, device_id: str, reason: str):
        """Log failed authentication attempts"""
        self.log_security_event(
            'FAILED_AUTH',
            user_id,
            {'device_id': device_id, 'reason': reason}
        )
    
    def log_suspicious_transaction(self, user_id: str, transaction_data: Dict[str, Any], risk_score: float):
        """Log suspicious transactions"""
        self.log_security_event(
            'SUSPICIOUS_TRANSACTION',
            user_id,
            {'transaction': transaction_data, 'risk_score': risk_score}
        )

# Global security instance
security_core = SecurityCore()
security_audit = SecurityAudit()
