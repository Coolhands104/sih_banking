"""
Enhanced Authentication System for Rural Banking
Multi-factor authentication with adaptive security
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum, IntEnum
import secrets
import re
from .core import security_core, security_audit, DeviceFingerprinting

class AuthenticationLevel(IntEnum):
    """Authentication security levels"""
    LOW = 1      # PIN only
    MEDIUM = 2   # PIN + OTP
    HIGH = 3     # PIN + OTP + Additional verification
    CRITICAL = 4 # All factors + manual approval

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class AuthenticationAttempt:
    """Authentication attempt data"""
    user_id: str
    device_id: str
    timestamp: float
    success: bool
    risk_score: float
    factors_used: List[str]
    location_data: Optional[Dict[str, Any]] = None

class AdaptiveAuthentication:
    """Adaptive authentication based on risk assessment"""
    
    def __init__(self):
        self.failed_attempts = {}  # Track failed attempts per user
        self.device_trust_scores = {}  # Device trust scores
        self.user_behavior_patterns = {}  # User behavior analysis
        
    def assess_risk(self, user_id: str, device_id: str, transaction_data: Dict[str, Any]) -> RiskLevel:
        """Assess authentication risk based on multiple factors"""
        risk_score = 0
        
        # Device trust assessment
        device_trust = self.device_trust_scores.get(device_id, 0)
        if device_trust < 0.3:
            risk_score += 30
        elif device_trust < 0.7:
            risk_score += 15
            
        # Failed attempt history
        recent_failures = self._get_recent_failed_attempts(user_id)
        risk_score += min(recent_failures * 10, 40)
        
        # Transaction amount risk
        amount = transaction_data.get('amount', 0)
        if amount > 100000:  # High value
            risk_score += 25
        elif amount > 50000:  # Medium-high value
            risk_score += 15
        elif amount > 10000:  # Medium value
            risk_score += 10
            
        # Time-based risk (unusual hours)
        current_hour = time.localtime().tm_hour
        if current_hour < 6 or current_hour > 22:
            risk_score += 20
            
        # Behavioral pattern analysis
        if self._is_unusual_behavior(user_id, transaction_data):
            risk_score += 25
            
        # Convert to risk level
        if risk_score >= 70:
            return RiskLevel.CRITICAL
        elif risk_score >= 50:
            return RiskLevel.HIGH
        elif risk_score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def get_required_auth_level(self, risk_level: RiskLevel) -> AuthenticationLevel:
        """Determine required authentication level based on risk"""
        mapping = {
            RiskLevel.LOW: AuthenticationLevel.LOW,
            RiskLevel.MEDIUM: AuthenticationLevel.MEDIUM,
            RiskLevel.HIGH: AuthenticationLevel.HIGH,
            RiskLevel.CRITICAL: AuthenticationLevel.CRITICAL
        }
        return mapping[risk_level]
    
    def _get_recent_failed_attempts(self, user_id: str) -> int:
        """Get number of recent failed attempts"""
        if user_id not in self.failed_attempts:
            return 0
            
        current_time = time.time()
        recent_attempts = [
            attempt for attempt in self.failed_attempts[user_id]
            if current_time - attempt < 3600  # Last hour
        ]
        return len(recent_attempts)
    
    def _is_unusual_behavior(self, user_id: str, transaction_data: Dict[str, Any]) -> bool:
        """Detect unusual user behavior patterns"""
        if user_id not in self.user_behavior_patterns:
            return False
            
        patterns = self.user_behavior_patterns[user_id]
        
        # Check transaction amount patterns
        avg_amount = patterns.get('avg_transaction_amount', 0)
        current_amount = transaction_data.get('amount', 0)
        
        if avg_amount > 0 and current_amount > avg_amount * 3:
            return True
            
        # Check transaction frequency
        last_transaction = patterns.get('last_transaction_time', 0)
        if time.time() - last_transaction < 300:  # Less than 5 minutes
            return True
            
        return False
    
    def record_attempt(self, attempt: AuthenticationAttempt):
        """Record authentication attempt for learning"""
        if not attempt.success:
            if attempt.user_id not in self.failed_attempts:
                self.failed_attempts[attempt.user_id] = []
            self.failed_attempts[attempt.user_id].append(attempt.timestamp)
            
        # Update device trust score
        if attempt.success:
            current_score = self.device_trust_scores.get(attempt.device_id, 0.5)
            self.device_trust_scores[attempt.device_id] = min(current_score + 0.1, 1.0)
        else:
            current_score = self.device_trust_scores.get(attempt.device_id, 0.5)
            self.device_trust_scores[attempt.device_id] = max(current_score - 0.2, 0.0)

class MultiFactorAuth:
    """Multi-factor authentication implementation"""
    
    def __init__(self):
        self.otp_storage = {}  # Store OTPs temporarily
        self.otp_attempts = {}  # Track OTP attempts
        
    def generate_pin_challenge(self, user_id: str) -> Dict[str, Any]:
        """Generate PIN authentication challenge"""
        challenge_id = security_core.generate_secure_token(16)
        return {
            'challenge_id': challenge_id,
            'type': 'pin',
            'user_id': user_id,
            'timestamp': time.time()
        }
    
    def verify_pin(self, user_id: str, pin: str, stored_hash: str, salt: str) -> bool:
        """Verify PIN with enhanced security"""
        try:
            return security_core.verify_password(pin, stored_hash, salt)
        except Exception as e:
            security_audit.log_failed_authentication(
                user_id, 
                "unknown", 
                f"PIN verification error: {e}"
            )
            return False
    
    def generate_otp_challenge(self, user_id: str, delivery_method: str = 'audio') -> Dict[str, Any]:
        """Generate OTP challenge"""
        otp = security_core.generate_otp(6)
        challenge_id = security_core.generate_secure_token(16)
        
        # Store OTP with expiration
        self.otp_storage[challenge_id] = {
            'otp': otp,
            'user_id': user_id,
            'created_at': time.time(),
            'expires_at': time.time() + 300,  # 5 minutes
            'delivery_method': delivery_method,
            'attempts': 0
        }
        
        return {
            'challenge_id': challenge_id,
            'type': 'otp',
            'otp': otp,  # For audio generation
            'delivery_method': delivery_method,
            'expires_in': 300
        }
    
    def verify_otp(self, challenge_id: str, provided_otp: str) -> Tuple[bool, str]:
        """Verify OTP with attempt limiting"""
        if challenge_id not in self.otp_storage:
            return False, "Invalid or expired OTP challenge"
            
        otp_data = self.otp_storage[challenge_id]
        
        # Check expiration
        if time.time() > otp_data['expires_at']:
            del self.otp_storage[challenge_id]
            return False, "OTP expired"
            
        # Check attempt limit
        if otp_data['attempts'] >= 3:
            del self.otp_storage[challenge_id]
            return False, "Too many failed attempts"
            
        # Verify OTP
        if provided_otp == otp_data['otp']:
            del self.otp_storage[challenge_id]
            return True, "OTP verified successfully"
        else:
            otp_data['attempts'] += 1
            return False, f"Invalid OTP. {3 - otp_data['attempts']} attempts remaining"
    
    def generate_biometric_challenge(self, user_id: str) -> Dict[str, Any]:
        """Generate biometric authentication challenge (placeholder for future)"""
        # For rural areas, this could be voice pattern or simple gesture
        challenge_id = security_core.generate_secure_token(16)
        return {
            'challenge_id': challenge_id,
            'type': 'biometric',
            'method': 'voice_pattern',  # Future implementation
            'instructions': "Please speak your name clearly"
        }

class SessionManager:
    """Secure session management"""
    
    def __init__(self):
        self.active_sessions = {}
        self.session_timeout = 900  # 15 minutes for rural users
        
    def create_session(self, user_id: str, device_id: str, auth_level: AuthenticationLevel) -> str:
        """Create authenticated session"""
        session_token = security_core.create_session_token(user_id, device_id)
        
        session_data = {
            'user_id': user_id,
            'device_id': device_id,
            'auth_level': auth_level.value,
            'created_at': time.time(),
            'last_activity': time.time(),
            'expires_at': time.time() + self.session_timeout
        }
        
        self.active_sessions[session_token] = session_data
        return session_token
    
    def validate_session(self, session_token: str, device_id: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session"""
        if session_token not in self.active_sessions:
            return None
            
        session_data = self.active_sessions[session_token]
        
        # Check device binding
        if session_data['device_id'] != device_id:
            del self.active_sessions[session_token]
            return None
            
        # Check expiration
        if time.time() > session_data['expires_at']:
            del self.active_sessions[session_token]
            return None
            
        # Refresh session
        session_data['last_activity'] = time.time()
        session_data['expires_at'] = time.time() + self.session_timeout
        
        return session_data
    
    def invalidate_session(self, session_token: str):
        """Invalidate session"""
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_tokens = [
            token for token, data in self.active_sessions.items()
            if current_time > data['expires_at']
        ]
        
        for token in expired_tokens:
            del self.active_sessions[token]

# Global instances
adaptive_auth = AdaptiveAuthentication()
mfa = MultiFactorAuth()
session_manager = SessionManager()
