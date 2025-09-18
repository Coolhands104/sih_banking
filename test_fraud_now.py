#!/usr/bin/env python3
"""
Quick fraud detection test
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from security.fraud_detection import fraud_engine
import time

def test_fraud_detection():
    """Test fraud detection with different amounts"""
    
    print("🚨 FRAUD DETECTION TEST")
    print("=" * 50)
    
    # Test user and transaction data
    user_id = "test_user"
    
    test_amounts = [50000, 100000, 150000, 200000, 300000]
    
    for amount in test_amounts:
        print(f"\n💰 Testing amount: ₹{amount:,}")
        
        transaction_data = {
            'user_id': user_id,
            'amount': amount,
            'timestamp': time.time(),
            'device_id': 'test_device'
        }
        
        # Analyze transaction
        result = fraud_engine.analyze_transaction(user_id, transaction_data)
        
        print(f"   🔍 Risk Level: {result.risk_level.name}")
        print(f"   🎯 Is Fraud: {result.is_fraud}")
        print(f"   📊 Confidence: {result.confidence:.2f}")
        print(f"   ⚠️  Risk Factors: {result.risk_factors}")
        
        if result.is_fraud:
            print(f"   🚨 FRAUD DETECTED! Transaction would be BLOCKED")
        else:
            print(f"   ✅ Transaction would be allowed")

if __name__ == "__main__":
    test_fraud_detection()
