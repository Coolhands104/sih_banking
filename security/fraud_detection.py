"""
Advanced Fraud Detection Engine for Rural Banking
Enhanced ML-based fraud detection with behavioral analytics
"""

import os
import time
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import pickle
from datetime import datetime, timedelta
import logging

# Suppress TensorFlow warnings for low-resource devices
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

try:
    from tensorflow import keras
    from huggingface_hub import hf_hub_download
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logging.warning("ML libraries not available. Using rule-based detection only.")

from .core import security_audit

class FraudRiskLevel(Enum):
    """Fraud risk levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class TransactionFeatures:
    """Transaction features for fraud detection"""
    amount: float
    hour: int
    day_of_week: int
    is_weekend: bool
    location_risk: float
    velocity_score: float
    amount_deviation: float
    frequency_score: float
    device_trust: float
    user_behavior_score: float

@dataclass
class FraudDetectionResult:
    """Fraud detection result"""
    is_fraud: bool
    risk_level: FraudRiskLevel
    confidence: float
    risk_factors: List[str]
    recommended_action: str
    ml_score: Optional[float] = None
    rule_based_score: float = 0.0

class BehavioralAnalytics:
    """Behavioral analytics for fraud detection"""
    
    def __init__(self):
        self.user_profiles = {}
        self.transaction_history = {}
        
    def update_user_profile(self, user_id: str, transaction: Dict[str, Any]):
        """Update user behavioral profile"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                'total_transactions': 0,
                'avg_amount': 0,
                'common_hours': [],
                'common_days': [],
                'max_amount': 0,
                'min_amount': float('inf'),
                'last_transaction_time': 0,
                'velocity_pattern': [],
                'amount_pattern': []
            }
        
        profile = self.user_profiles[user_id]
        amount = transaction['amount']
        current_time = time.time()
        
        # Update basic stats
        profile['total_transactions'] += 1
        profile['avg_amount'] = (
            (profile['avg_amount'] * (profile['total_transactions'] - 1) + amount) 
            / profile['total_transactions']
        )
        profile['max_amount'] = max(profile['max_amount'], amount)
        profile['min_amount'] = min(profile['min_amount'], amount)
        
        # Update temporal patterns
        hour = datetime.fromtimestamp(current_time).hour
        day = datetime.fromtimestamp(current_time).weekday()
        
        profile['common_hours'].append(hour)
        profile['common_days'].append(day)
        
        # Keep only recent patterns (last 100 transactions)
        if len(profile['common_hours']) > 100:
            profile['common_hours'] = profile['common_hours'][-100:]
            profile['common_days'] = profile['common_days'][-100:]
        
        # Update velocity pattern
        if profile['last_transaction_time'] > 0:
            time_diff = current_time - profile['last_transaction_time']
            profile['velocity_pattern'].append(time_diff)
            if len(profile['velocity_pattern']) > 50:
                profile['velocity_pattern'] = profile['velocity_pattern'][-50:]
        
        profile['last_transaction_time'] = current_time
        
        # Update amount pattern
        profile['amount_pattern'].append(amount)
        if len(profile['amount_pattern']) > 50:
            profile['amount_pattern'] = profile['amount_pattern'][-50:]
    
    def calculate_behavior_score(self, user_id: str, transaction: Dict[str, Any]) -> float:
        """Calculate behavioral anomaly score (0-1, higher = more suspicious)"""
        if user_id not in self.user_profiles:
            return 0.5  # Neutral score for new users
        
        profile = self.user_profiles[user_id]
        score = 0.0
        
        # Amount deviation
        amount = transaction['amount']
        if profile['avg_amount'] > 0:
            deviation = abs(amount - profile['avg_amount']) / profile['avg_amount']
            if deviation > 2.0:  # More than 200% deviation
                score += 0.3
            elif deviation > 1.0:  # More than 100% deviation
                score += 0.2
        
        # Time pattern analysis
        current_hour = datetime.fromtimestamp(time.time()).hour
        if profile['common_hours']:
            hour_frequency = profile['common_hours'].count(current_hour) / len(profile['common_hours'])
            if hour_frequency < 0.1:  # Unusual hour
                score += 0.2
        
        # Velocity analysis
        current_time = time.time()
        if profile['last_transaction_time'] > 0:
            time_since_last = current_time - profile['last_transaction_time']
            if profile['velocity_pattern']:
                avg_velocity = np.mean(profile['velocity_pattern'])
                if time_since_last < avg_velocity * 0.1:  # Too fast
                    score += 0.3
        
        # Amount pattern analysis
        if len(profile['amount_pattern']) >= 5:
            recent_amounts = profile['amount_pattern'][-5:]
            if amount > max(recent_amounts) * 2:  # Sudden spike
                score += 0.2
        
        return min(score, 1.0)

class RuleBasedDetection:
    """Rule-based fraud detection for rural banking patterns"""
    
    def __init__(self):
        self.rules = {
            'high_amount': {'threshold': 100000, 'weight': 0.8},  # Increased weight for better detection
            'unusual_hour': {'start': 23, 'end': 6, 'weight': 0.3},
            'rapid_transactions': {'interval': 300, 'weight': 0.4},  # 5 minutes
            'amount_spike': {'multiplier': 5, 'weight': 0.4},
            'weekend_large': {'amount': 50000, 'weight': 0.2},
            'velocity_high': {'transactions_per_hour': 10, 'weight': 0.5}
        }
        
    def evaluate_rules(self, transaction: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Evaluate rule-based fraud indicators"""
        risk_score = 0.0
        triggered_rules = []
        
        amount = transaction['amount']
        current_time = time.time()
        current_hour = datetime.fromtimestamp(current_time).hour
        is_weekend = datetime.fromtimestamp(current_time).weekday() >= 5
        
        # High amount rule
        if amount > self.rules['high_amount']['threshold']:
            risk_score += self.rules['high_amount']['weight']
            triggered_rules.append(f"High amount transaction: ₹{amount}")
        
        # Unusual hour rule
        unusual_start = self.rules['unusual_hour']['start']
        unusual_end = self.rules['unusual_hour']['end']
        if current_hour >= unusual_start or current_hour <= unusual_end:
            risk_score += self.rules['unusual_hour']['weight']
            triggered_rules.append(f"Transaction at unusual hour: {current_hour}:00")
        
        # Rapid transactions rule
        if user_profile.get('last_transaction_time', 0) > 0:
            time_diff = current_time - user_profile['last_transaction_time']
            if time_diff < self.rules['rapid_transactions']['interval']:
                risk_score += self.rules['rapid_transactions']['weight']
                triggered_rules.append(f"Rapid transaction: {time_diff:.0f} seconds since last")
        
        # Amount spike rule
        avg_amount = user_profile.get('avg_amount', 0)
        if avg_amount > 0 and amount > avg_amount * self.rules['amount_spike']['multiplier']:
            risk_score += self.rules['amount_spike']['weight']
            triggered_rules.append(f"Amount spike: {amount/avg_amount:.1f}x average")
        
        # Weekend large transaction rule
        if is_weekend and amount > self.rules['weekend_large']['amount']:
            risk_score += self.rules['weekend_large']['weight']
            triggered_rules.append(f"Large weekend transaction: ₹{amount}")
        
        return min(risk_score, 1.0), triggered_rules

class MLFraudDetection:
    """Machine Learning based fraud detection"""
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.feature_scaler = None
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained fraud detection model"""
        if not ML_AVAILABLE:
            return
            
        try:
            # Load Hugging Face model
            model_path = hf_hub_download(
                repo_id="CiferAI/cifer-fraud-detection-k1-a",
                filename="cifer-fraud-detection-k1-a.h5"
            )
            self.model = keras.models.load_model(model_path)
            self.model_loaded = True
            logging.info("ML fraud detection model loaded successfully")
        except Exception as e:
            logging.error(f"Failed to load ML model: {e}")
            self.model_loaded = False
    
    def extract_features(self, transaction: Dict[str, Any], user_profile: Dict[str, Any]) -> np.ndarray:
        """Extract features for ML model"""
        amount = transaction['amount']
        current_time = time.time()
        
        # Basic features
        features = [
            amount,
            datetime.fromtimestamp(current_time).hour,
            int(transaction.get('location_risk', 0)),
            user_profile.get('avg_amount', 0),
            max(0, user_profile.get('avg_amount', 0) - amount),  # oldbalanceOrig
            user_profile.get('avg_amount', 0),  # oldbalanceDest
            user_profile.get('avg_amount', 0) + amount,  # newbalanceDest
            0.0  # isFlaggedFraud placeholder
        ]
        
        return np.array([features])
    
    def predict_fraud(self, transaction: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[float, float]:
        """Predict fraud probability using ML model"""
        if not self.model_loaded:
            return 0.0, 0.0  # Return neutral scores if model not available
        
        try:
            features = self.extract_features(transaction, user_profile)
            prediction = self.model.predict(features, verbose=0)
            fraud_probability = float(prediction[0][1])  # Fraud class probability
            confidence = max(prediction[0]) - min(prediction[0])  # Confidence measure
            
            return fraud_probability, confidence
        except Exception as e:
            logging.error(f"ML prediction failed: {e}")
            return 0.0, 0.0

class FraudDetectionEngine:
    """Main fraud detection engine combining multiple approaches"""
    
    def __init__(self):
        self.behavioral_analytics = BehavioralAnalytics()
        self.rule_based_detector = RuleBasedDetection()
        self.ml_detector = MLFraudDetection()
        self.fraud_history = []
        
    def analyze_transaction(self, user_id: str, transaction: Dict[str, Any]) -> FraudDetectionResult:
        """Comprehensive fraud analysis"""
        # Get user profile
        user_profile = self.behavioral_analytics.user_profiles.get(user_id, {})
        
        # Calculate behavioral score
        behavior_score = self.behavioral_analytics.calculate_behavior_score(user_id, transaction)
        
        # Rule-based detection
        rule_score, triggered_rules = self.rule_based_detector.evaluate_rules(transaction, user_profile)
        
        # ML-based detection
        ml_score, ml_confidence = self.ml_detector.predict_fraud(transaction, user_profile)
        
        # Combine scores (weighted average)
        combined_score = (
            behavior_score * 0.3 +
            rule_score * 0.4 +
            ml_score * 0.3
        )
        
        # Determine risk level
        if combined_score >= 0.8:
            risk_level = FraudRiskLevel.CRITICAL
            recommended_action = "Block transaction and require manual review"
        elif combined_score >= 0.6:
            risk_level = FraudRiskLevel.HIGH
            recommended_action = "Require additional authentication"
        elif combined_score >= 0.4:
            risk_level = FraudRiskLevel.MEDIUM
            recommended_action = "Send alert and monitor"
        else:
            risk_level = FraudRiskLevel.LOW
            recommended_action = "Allow transaction"
        
        # Compile risk factors
        risk_factors = triggered_rules.copy()
        if behavior_score > 0.5:
            risk_factors.append(f"Behavioral anomaly score: {behavior_score:.2f}")
        if ml_score > 0.7:
            risk_factors.append(f"ML fraud probability: {ml_score:.2f}")
        
        # Create result (lowered threshold for better fraud detection)
        result = FraudDetectionResult(
            is_fraud=combined_score >= 0.4,  # Lowered from 0.6 to 0.4 for better detection
            risk_level=risk_level,
            confidence=ml_confidence,
            risk_factors=risk_factors,
            recommended_action=recommended_action,
            ml_score=ml_score,
            rule_based_score=rule_score
        )
        
        # Update user profile
        self.behavioral_analytics.update_user_profile(user_id, transaction)
        
        # Log fraud detection
        security_audit.log_security_event(
            'FRAUD_ANALYSIS',
            user_id,
            {
                'transaction': transaction,
                'combined_score': combined_score,
                'risk_level': risk_level.name,
                'is_fraud': result.is_fraud
            }
        )
        
        return result
    
    def get_fraud_statistics(self) -> Dict[str, Any]:
        """Get fraud detection statistics"""
        total_transactions = len(self.fraud_history)
        if total_transactions == 0:
            return {'total_transactions': 0, 'fraud_rate': 0.0}
        
        fraud_count = sum(1 for result in self.fraud_history if result.is_fraud)
        fraud_rate = fraud_count / total_transactions
        
        return {
            'total_transactions': total_transactions,
            'fraud_count': fraud_count,
            'fraud_rate': fraud_rate,
            'last_24h_fraud_rate': self._calculate_recent_fraud_rate(24)
        }
    
    def _calculate_recent_fraud_rate(self, hours: int) -> float:
        """Calculate fraud rate for recent period"""
        cutoff_time = time.time() - (hours * 3600)
        recent_results = [
            result for result in self.fraud_history 
            if hasattr(result, 'timestamp') and result.timestamp > cutoff_time
        ]
        
        if not recent_results:
            return 0.0
        
        fraud_count = sum(1 for result in recent_results if result.is_fraud)
        return fraud_count / len(recent_results)

# Global fraud detection engine
fraud_engine = FraudDetectionEngine()
