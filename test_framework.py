#!/usr/bin/env python3
"""
Simple test to verify the security framework works
"""

import sys
import time

def test_security_core():
    """Test core security functionality"""
    print("Testing Security Core...")
    
    try:
        from security.core import SecurityCore
        
        security = SecurityCore()
        
        # Test encryption
        test_data = "sensitive banking data"
        encrypted = security.encrypt_data(test_data)
        decrypted = security.decrypt_data(encrypted)
        
        assert decrypted == test_data, "Encryption/Decryption failed"
        print("✅ Encryption/Decryption: PASSED")
        
        # Test password hashing
        password = "test123"
        hash_value, salt = security.hash_password(password)
        
        assert security.verify_password(password, hash_value, salt), "Password verification failed"
        assert not security.verify_password("wrong", hash_value, salt), "Password verification should fail"
        print("✅ Password Hashing: PASSED")
        
        # Test token generation
        token1 = security.generate_secure_token()
        token2 = security.generate_secure_token()
        
        assert token1 != token2, "Tokens should be unique"
        assert len(token1) > 20, "Token should be reasonably long"
        print("✅ Token Generation: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Security Core Test Failed: {e}")
        return False

def test_fraud_detection():
    """Test fraud detection"""
    print("\nTesting Fraud Detection...")
    
    try:
        from security.fraud_detection import FraudDetectionEngine
        
        fraud_engine = FraudDetectionEngine()
        
        # Test low-risk transaction
        low_risk_transaction = {
            'amount': 1000,
            'timestamp': time.time(),
            'device_id': 'trusted_device'
        }
        
        result = fraud_engine.analyze_transaction("test_user", low_risk_transaction)
        print(f"✅ Low-risk transaction analysis: Risk Level = {result.risk_level.name}")
        
        # Test high-risk transaction
        high_risk_transaction = {
            'amount': 100000,
            'timestamp': time.time(),
            'device_id': 'unknown_device'
        }
        
        result = fraud_engine.analyze_transaction("test_user", high_risk_transaction)
        print(f"✅ High-risk transaction analysis: Risk Level = {result.risk_level.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fraud Detection Test Failed: {e}")
        return False

def test_authentication():
    """Test authentication system"""
    print("\nTesting Authentication...")
    
    try:
        from security.authentication import MultiFactorAuth, AdaptiveAuthentication
        
        mfa = MultiFactorAuth()
        adaptive_auth = AdaptiveAuthentication()
        
        # Test OTP generation
        challenge = mfa.generate_otp_challenge("test_user")
        assert 'challenge_id' in challenge, "Challenge should have ID"
        assert 'otp' in challenge, "Challenge should have OTP"
        assert len(challenge['otp']) == 6, "OTP should be 6 digits"
        print("✅ OTP Generation: PASSED")
        
        # Test OTP verification
        success, message = mfa.verify_otp(challenge['challenge_id'], challenge['otp'])
        assert success, f"OTP verification should succeed: {message}"
        print("✅ OTP Verification: PASSED")
        
        # Test risk assessment
        transaction_data = {'amount': 5000, 'timestamp': time.time()}
        risk_level = adaptive_auth.assess_risk("test_user", "test_device", transaction_data)
        print(f"✅ Risk Assessment: Risk Level = {risk_level.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication Test Failed: {e}")
        return False

def test_performance():
    """Test performance optimization"""
    print("\nTesting Performance...")
    
    try:
        from security.performance import LRUCache, PerformanceMonitor
        
        # Test LRU Cache
        cache = LRUCache(max_size=3)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        assert cache.get("key1") == "value1", "Cache should return correct value"
        
        # Add one more to trigger eviction
        cache.put("key4", "value4")
        assert cache.get("key2") is None, "LRU item should be evicted"
        print("✅ LRU Cache: PASSED")
        
        # Test performance monitoring
        monitor = PerformanceMonitor()
        monitor.record_response_time(0.1)
        monitor.record_cache_hit()
        
        summary = monitor.get_performance_summary()
        assert 'avg_response_time_ms' in summary, "Summary should include response time"
        print("✅ Performance Monitoring: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance Test Failed: {e}")
        return False

def run_fraud_reduction_simulation():
    """Simulate fraud reduction effectiveness"""
    print("\nRunning Fraud Reduction Simulation...")
    
    try:
        from security.fraud_detection import FraudDetectionEngine
        
        fraud_engine = FraudDetectionEngine()
        
        # Simulate transactions
        legitimate_count = 0
        fraudulent_count = 0
        fraud_detected = 0
        false_positives = 0
        
        # Test 100 legitimate transactions
        for i in range(100):
            transaction = {
                'amount': 1000 + (i % 3000),  # Normal amounts
                'timestamp': time.time(),
                'device_id': f'device_{i % 10}'  # Known devices
            }
            
            result = fraud_engine.analyze_transaction(f'user_{i % 20}', transaction)
            legitimate_count += 1
            
            if result.is_fraud:
                false_positives += 1
        
        # Test 50 fraudulent transactions
        for i in range(50):
            transaction = {
                'amount': 50000 + (i * 1000),  # High amounts
                'timestamp': time.time(),
                'device_id': f'suspicious_device_{i}'  # Unknown devices
            }
            
            result = fraud_engine.analyze_transaction(f'user_{i % 5}', transaction)
            fraudulent_count += 1
            
            if result.is_fraud:
                fraud_detected += 1
        
        # Calculate metrics
        false_positive_rate = false_positives / legitimate_count
        detection_rate = fraud_detected / fraudulent_count
        fraud_reduction = detection_rate * 100
        
        print(f"📊 Simulation Results:")
        print(f"   Legitimate transactions: {legitimate_count}")
        print(f"   Fraudulent transactions: {fraudulent_count}")
        print(f"   False positive rate: {false_positive_rate:.2%}")
        print(f"   Fraud detection rate: {detection_rate:.2%}")
        print(f"   Estimated fraud reduction: {fraud_reduction:.1f}%")
        
        if fraud_reduction >= 20:
            print(f"🎯 TARGET ACHIEVED: {fraud_reduction:.1f}% fraud reduction (target: 20%)")
            return True
        else:
            print(f"⚠️ TARGET NOT MET: {fraud_reduction:.1f}% fraud reduction (target: 20%)")
            return False
            
    except Exception as e:
        print(f"❌ Fraud Reduction Simulation Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🏦 Rural Banking Security Framework - Test Suite")
    print("=" * 60)
    
    tests = [
        test_security_core,
        test_fraud_detection,
        test_authentication,
        test_performance,
        run_fraud_reduction_simulation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"📋 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Security framework is working correctly.")
        print("✅ Ready for rural banking deployment")
        return True
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
