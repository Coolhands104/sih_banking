#!/usr/bin/env python3
"""
Test script to generate fraud transactions for dashboard testing
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from security.dashboard import security_metrics
import time

def test_dashboard_fraud():
    """Generate test fraud data for dashboard"""
    
    print("🚨 GENERATING FRAUD DATA FOR DASHBOARD")
    print("=" * 50)
    
    # Test data - mix of fraud and legitimate transactions
    test_transactions = [
        # Legitimate transactions
        {"user_id": "user_001", "amount": 5000, "risk_score": 0.1, "blocked": False, "type": "Normal"},
        {"user_id": "user_002", "amount": 15000, "risk_score": 0.2, "blocked": False, "type": "Normal"},
        {"user_id": "user_003", "amount": 25000, "risk_score": 0.3, "blocked": False, "type": "Normal"},
        
        # Fraud transactions
        {"user_id": "user_004", "amount": 150000, "risk_score": 0.8, "blocked": True, "type": "High Amount Fraud"},
        {"user_id": "user_005", "amount": 200000, "risk_score": 0.9, "blocked": True, "type": "High Amount Fraud"},
        {"user_id": "user_006", "amount": 75000, "risk_score": 0.7, "blocked": True, "type": "Rapid Transaction Fraud"},
        {"user_id": "user_007", "amount": 300000, "risk_score": 0.95, "blocked": True, "type": "Critical Risk"},
        {"user_id": "user_008", "amount": 180000, "risk_score": 0.85, "blocked": True, "type": "Amount Spike Fraud"},
    ]
    
    print("📊 Recording transactions in dashboard database...")
    
    for i, transaction in enumerate(test_transactions):
        print(f"   {i+1}. {transaction['type']}: ₹{transaction['amount']:,} - {'🚨 BLOCKED' if transaction['blocked'] else '✅ ALLOWED'}")
        
        # Record in dashboard
        security_metrics.record_fraud_attempt(
            user_id=transaction["user_id"],
            amount=transaction["amount"],
            risk_score=transaction["risk_score"],
            blocked=transaction["blocked"],
            details={
                "transaction_type": transaction["type"],
                "risk_level": "HIGH" if transaction["risk_score"] > 0.6 else "MEDIUM" if transaction["risk_score"] > 0.3 else "LOW",
                "timestamp": time.time(),
                "test_data": True
            }
        )
        
        # Small delay to spread timestamps
        time.sleep(0.1)
    
    print("\n✅ Test data generated successfully!")
    print("\n📊 Dashboard Summary:")
    
    # Get summary
    summary = security_metrics.get_security_summary(24)
    fraud_summary = summary.get('fraud_summary', {})
    
    print(f"   📈 Total Attempts: {fraud_summary.get('total_attempts', 0)}")
    print(f"   🚨 Blocked Attempts: {fraud_summary.get('blocked_attempts', 0)}")
    print(f"   📊 Average Risk Score: {fraud_summary.get('avg_risk_score', 0):.2f}")
    print(f"   💰 Total Amount Attempted: ₹{fraud_summary.get('total_amount_attempted', 0):,.0f}")
    
    print(f"\n🎯 Fraud Detection Rate: {fraud_summary.get('blocked_attempts', 0)}/{fraud_summary.get('total_attempts', 0)}")
    
    print("\n🌐 View results at: http://localhost:5000/admin")

if __name__ == "__main__":
    test_dashboard_fraud()
