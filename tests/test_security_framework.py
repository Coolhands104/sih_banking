"""
Comprehensive Security Framework Tests
Testing fraud detection, authentication, and performance
"""

import unittest
import time
import json
import tempfile
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from security.core import SecurityCore, DeviceFingerprinting, SecurityAudit
from security.authentication import AdaptiveAuthentication, MultiFactorAuth, SessionManager
from security.fraud_detection import FraudDetectionEngine, BehavioralAnalytics
from security.offline_security import OfflineTransactionManager, OfflineValidator
from security.performance import PerformanceMonitor, LRUCache

class TestSecurityCore(unittest.TestCase):
    """Test core security functionality"""
    
    def setUp(self):
        self.security_core = SecurityCore()
    
    def test_encryption_decryption(self):
        """Test data encryption and decryption"""
        test_data = "sensitive banking information"
        
        # Encrypt data
        encrypted = self.security_core.encrypt_data(test_data)
        self.assertNotEqual(encrypted, test_data)
        self.assertIsInstance(encrypted, str)
        
        # Decrypt data
        decrypted = self.security_core.decrypt_data(encrypted)
        self.assertEqual(decrypted, test_data)
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test123"
        
        # Hash password
        hash_value, salt = self.security_core.hash_password(password)
        self.assertIsInstance(hash_value, str)
        self.assertIsInstance(salt, str)
        self.assertNotEqual(hash_value, password)
        
        # Verify correct password
        self.assertTrue(self.security_core.verify_password(password, hash_value, salt))
        
        # Verify incorrect password
        self.assertFalse(self.security_core.verify_password("wrong", hash_value, salt))
    
    def test_token_generation(self):
        """Test secure token generation"""
        token1 = self.security_core.generate_secure_token()
        token2 = self.security_core.generate_secure_token()
        
        self.assertNotEqual(token1, token2)
        self.assertIsInstance(token1, str)
        self.assertGreater(len(token1), 20)  # Should be reasonably long
    
    def test_session_token_creation_verification(self):
        """Test session token creation and verification"""
        user_id = "test_user"
        device_id = "test_device"
        
        # Create session token
        token = self.security_core.create_session_token(user_id, device_id)
        self.assertIsInstance(token, str)
        
        # Verify session token
        payload = self.security_core.verify_session_token(token, device_id)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_id'], user_id)
        self.assertEqual(payload['device_id'], device_id)
        
        # Verify with wrong device
        wrong_payload = self.security_core.verify_session_token(token, "wrong_device")
        self.assertIsNone(wrong_payload)

class TestFraudDetection(unittest.TestCase):
    """Test fraud detection functionality"""
    
    def setUp(self):
        self.fraud_engine = FraudDetectionEngine()
        self.behavioral_analytics = BehavioralAnalytics()
    
    def test_behavioral_analytics(self):
        """Test behavioral analytics"""
        user_id = "test_user"
        
        # Simulate normal transactions
        normal_transactions = [
            {'amount': 1000, 'timestamp': time.time()},
            {'amount': 1200, 'timestamp': time.time() + 100},
            {'amount': 800, 'timestamp': time.time() + 200},
        ]
        
        for transaction in normal_transactions:
            self.behavioral_analytics.update_user_profile(user_id, transaction)
        
        # Test normal behavior score
        normal_score = self.behavioral_analytics.calculate_behavior_score(
            user_id, {'amount': 1100}
        )
        self.assertLess(normal_score, 0.5)  # Should be low risk
        
        # Test suspicious behavior score
        suspicious_score = self.behavioral_analytics.calculate_behavior_score(
            user_id, {'amount': 10000}  # Much higher than normal
        )
        self.assertGreater(suspicious_score, 0.3)  # Should be higher risk
    
    def test_fraud_detection_engine(self):
        """Test complete fraud detection engine"""
        user_id = "test_user"
        
        # Test low-risk transaction
        low_risk_transaction = {
            'amount': 500,
            'timestamp': time.time(),
            'device_id': 'trusted_device'
        }
        
        result = self.fraud_engine.analyze_transaction(user_id, low_risk_transaction)
        self.assertFalse(result.is_fraud)
        
        # Test high-risk transaction
        high_risk_transaction = {
            'amount': 100000,  # Very high amount
            'timestamp': time.time(),
            'device_id': 'unknown_device'
        }
        
        result = self.fraud_engine.analyze_transaction(user_id, high_risk_transaction)
        # Should be flagged as high risk or fraud
        self.assertTrue(result.is_fraud or result.risk_level.value >= 3)

class TestAuthentication(unittest.TestCase):
    """Test authentication functionality"""
    
    def setUp(self):
        self.adaptive_auth = AdaptiveAuthentication()
        self.mfa = MultiFactorAuth()
        self.session_manager = SessionManager()
    
    def test_risk_assessment(self):
        """Test risk assessment"""
        user_id = "test_user"
        device_id = "test_device"
        
        # Low-risk transaction
        low_risk_data = {
            'amount': 1000,
            'timestamp': time.time()
        }
        
        risk_level = self.adaptive_auth.assess_risk(user_id, device_id, low_risk_data)
        self.assertIn(risk_level.value, [1, 2])  # Should be low or medium
        
        # High-risk transaction
        high_risk_data = {
            'amount': 200000,  # Very high amount
            'timestamp': time.time()
        }
        
        risk_level = self.adaptive_auth.assess_risk(user_id, device_id, high_risk_data)
        self.assertGreaterEqual(risk_level.value, 2)  # Should be medium or higher
    
    def test_otp_generation_verification(self):
        """Test OTP generation and verification"""
        user_id = "test_user"
        
        # Generate OTP challenge
        challenge = self.mfa.generate_otp_challenge(user_id)
        self.assertIn('challenge_id', challenge)
        self.assertIn('otp', challenge)
        self.assertEqual(len(challenge['otp']), 6)
        
        # Verify correct OTP
        success, message = self.mfa.verify_otp(challenge['challenge_id'], challenge['otp'])
        self.assertTrue(success)
        
        # Verify incorrect OTP
        success, message = self.mfa.verify_otp(challenge['challenge_id'], "000000")
        self.assertFalse(success)
    
    def test_session_management(self):
        """Test session management"""
        user_id = "test_user"
        device_id = "test_device"
        auth_level = 2  # Medium authentication level
        
        # Create session
        session_token = self.session_manager.create_session(user_id, device_id, auth_level)
        self.assertIsInstance(session_token, str)
        
        # Validate session
        session_data = self.session_manager.validate_session(session_token, device_id)
        self.assertIsNotNone(session_data)
        self.assertEqual(session_data['user_id'], user_id)
        
        # Invalidate session
        self.session_manager.invalidate_session(session_token)
        session_data = self.session_manager.validate_session(session_token, device_id)
        self.assertIsNone(session_data)

class TestOfflineSecurity(unittest.TestCase):
    """Test offline security functionality"""
    
    def setUp(self):
        # Use temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        
        self.offline_manager = OfflineTransactionManager()
        self.offline_manager.local_db.db_path = self.temp_db.name
        self.offline_manager.local_db._init_database()
        
        self.validator = OfflineValidator()
    
    def tearDown(self):
        os.unlink(self.temp_db.name)
    
    def test_offline_validation(self):
        """Test offline transaction validation"""
        user_id = "test_user"
        
        # Valid transaction
        valid_transaction = {
            'amount': 5000,  # Within offline limit
            'device_id': 'trusted_device'
        }
        
        is_valid, score, issues = self.validator.validate_transaction(
            user_id, valid_transaction
        )
        self.assertTrue(is_valid)
        self.assertLess(score, 0.5)
        
        # Invalid transaction (too high amount)
        invalid_transaction = {
            'amount': 50000,  # Exceeds offline limit
            'device_id': 'trusted_device'
        }
        
        is_valid, score, issues = self.validator.validate_transaction(
            user_id, invalid_transaction
        )
        self.assertFalse(is_valid)
        self.assertGreater(score, 0.5)
        self.assertGreater(len(issues), 0)
    
    def test_offline_transaction_processing(self):
        """Test offline transaction processing"""
        user_id = "test_user"
        transaction_data = {
            'amount': 3000,
            'device_id': 'test_device'
        }
        
        result = self.offline_manager.process_offline_transaction(
            user_id, transaction_data
        )
        
        self.assertTrue(result['success'])
        self.assertIn('transaction_id', result)

class TestPerformance(unittest.TestCase):
    """Test performance optimization"""
    
    def setUp(self):
        self.performance_monitor = PerformanceMonitor()
        self.cache = LRUCache(max_size=5)
    
    def test_lru_cache(self):
        """Test LRU cache functionality"""
        # Add items to cache
        for i in range(3):
            self.cache.put(f"key{i}", f"value{i}")
        
        # Verify items are in cache
        self.assertEqual(self.cache.get("key0"), "value0")
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")
        
        # Add more items to exceed capacity
        for i in range(3, 7):
            self.cache.put(f"key{i}", f"value{i}")
        
        # Verify LRU eviction
        self.assertIsNone(self.cache.get("key0"))  # Should be evicted
        self.assertIsNone(self.cache.get("key1"))  # Should be evicted
        self.assertEqual(self.cache.get("key6"), "value6")  # Should be present
    
    def test_performance_monitoring(self):
        """Test performance monitoring"""
        # Record some metrics
        self.performance_monitor.record_response_time(0.1)
        self.performance_monitor.record_response_time(0.2)
        self.performance_monitor.record_cache_hit()
        self.performance_monitor.record_cache_miss()
        
        # Get summary
        summary = self.performance_monitor.get_performance_summary()
        
        self.assertIn('avg_response_time_ms', summary)
        self.assertIn('cache_hit_ratio', summary)
        self.assertGreater(summary['avg_response_time_ms'], 0)
        self.assertEqual(summary['cache_hit_ratio'], 0.5)  # 1 hit, 1 miss

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_complete_transaction_flow(self):
        """Test complete transaction flow with all security measures"""
        # This would test the entire flow from authentication to fraud detection
        # to transaction processing
        
        # Setup
        security_core = SecurityCore()
        fraud_engine = FraudDetectionEngine()
        adaptive_auth = AdaptiveAuthentication()
        
        user_id = "integration_test_user"
        device_id = "test_device"
        
        # Simulate transaction
        transaction_data = {
            'user_id': user_id,
            'amount': 15000,
            'device_id': device_id,
            'timestamp': time.time()
        }
        
        # Risk assessment
        risk_level = adaptive_auth.assess_risk(user_id, device_id, transaction_data)
        self.assertIsNotNone(risk_level)
        
        # Fraud detection
        fraud_result = fraud_engine.analyze_transaction(user_id, transaction_data)
        self.assertIsNotNone(fraud_result)
        
        # Transaction should be processed (not blocked for this amount)
        self.assertFalse(fraud_result.is_fraud)

def run_fraud_reduction_benchmark():
    """Benchmark fraud detection effectiveness"""
    print("\n" + "="*50)
    print("FRAUD REDUCTION BENCHMARK")
    print("="*50)
    
    fraud_engine = FraudDetectionEngine()
    
    # Simulate 1000 transactions (800 legitimate, 200 fraudulent)
    legitimate_transactions = []
    fraudulent_transactions = []
    
    # Generate legitimate transactions
    for i in range(800):
        transaction = {
            'user_id': f'user_{i % 100}',  # 100 different users
            'amount': 1000 + (i % 5000),  # Amounts between 1000-6000
            'device_id': f'device_{i % 50}',  # 50 different devices
            'timestamp': time.time() + i
        }
        legitimate_transactions.append(transaction)
    
    # Generate fraudulent transactions
    for i in range(200):
        transaction = {
            'user_id': f'user_{i % 100}',
            'amount': 50000 + (i * 1000),  # High amounts
            'device_id': f'suspicious_device_{i}',  # New devices
            'timestamp': time.time() + 2000 + i  # Unusual times
        }
        fraudulent_transactions.append(transaction)
    
    # Test fraud detection
    legitimate_detected_as_fraud = 0
    fraudulent_detected_as_fraud = 0
    
    print("Testing legitimate transactions...")
    for transaction in legitimate_transactions:
        result = fraud_engine.analyze_transaction(transaction['user_id'], transaction)
        if result.is_fraud:
            legitimate_detected_as_fraud += 1
    
    print("Testing fraudulent transactions...")
    for transaction in fraudulent_transactions:
        result = fraud_engine.analyze_transaction(transaction['user_id'], transaction)
        if result.is_fraud:
            fraudulent_detected_as_fraud += 1
    
    # Calculate metrics
    false_positive_rate = legitimate_detected_as_fraud / len(legitimate_transactions)
    true_positive_rate = fraudulent_detected_as_fraud / len(fraudulent_transactions)
    fraud_reduction = true_positive_rate * 100
    
    print(f"\nResults:")
    print(f"Legitimate transactions: {len(legitimate_transactions)}")
    print(f"Fraudulent transactions: {len(fraudulent_transactions)}")
    print(f"False positives: {legitimate_detected_as_fraud} ({false_positive_rate:.2%})")
    print(f"True positives: {fraudulent_detected_as_fraud} ({true_positive_rate:.2%})")
    print(f"Fraud reduction: {fraud_reduction:.1f}%")
    
    # Check if we meet the 20% fraud reduction target
    if fraud_reduction >= 20:
        print(f"✅ TARGET ACHIEVED: {fraud_reduction:.1f}% fraud reduction (target: 20%)")
    else:
        print(f"❌ TARGET NOT MET: {fraud_reduction:.1f}% fraud reduction (target: 20%)")
    
    return fraud_reduction >= 20

if __name__ == '__main__':
    # Run unit tests
    print("Running Security Framework Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # Run fraud reduction benchmark
    run_fraud_reduction_benchmark()
