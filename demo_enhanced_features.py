#!/usr/bin/env python3
"""
Enhanced Rural Banking Features Demo
Demonstrates bank balance, offline transactions, and LLM fraud detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from banking.account_manager import account_manager, TransactionType
from security.offline_security import offline_manager
from security.llm_fraud_detection import llm_fraud_detector, LLMProvider
import time

def demo_bank_balance():
    """Demo bank balance functionality"""
    print("🏦 BANK BALANCE MANAGEMENT DEMO")
    print("=" * 50)
    
    user_id = "demo_user_001"
    
    # Create account
    print("1. Creating bank account...")
    result = account_manager.create_account(user_id, initial_balance=75000.0)
    print(f"   ✅ {result['message']}")
    print(f"   📋 Account Number: {result['account_number']}")
    print(f"   💰 Initial Balance: ₹{result['balance']:,.2f}")
    
    # Check balance
    print("\n2. Checking account balance...")
    account_info = account_manager.get_account_info(user_id)
    print(f"   💳 Current Balance: ₹{account_info['balance']:,.2f}")
    print(f"   📊 Daily Limit: ₹{account_info['daily_limit']:,.2f}")
    print(f"   🏛️ Account Type: {account_info['account_type']}")
    
    # Make some transactions
    print("\n3. Processing transactions...")
    
    transactions = [
        (5000, "Grocery shopping"),
        (15000, "Medical expenses"),
        (2500, "Utility bills"),
        (25000, "School fees")
    ]
    
    for amount, description in transactions:
        result = account_manager.process_transaction(
            user_id, amount, TransactionType.DEBIT, description
        )
        
        if result['success']:
            print(f"   ✅ ₹{amount:,} - {description}")
            print(f"      💰 New Balance: ₹{result['balance_after']:,.2f}")
        else:
            print(f"   ❌ ₹{amount:,} - {description}: {result['message']}")
    
    # Final balance
    final_balance = account_manager.get_balance(user_id)
    print(f"\n📊 Final Balance: ₹{final_balance:,.2f}")

def demo_offline_transactions():
    """Demo offline transaction processing"""
    print("\n\n📱 OFFLINE TRANSACTION PROCESSING DEMO")
    print("=" * 50)
    
    user_id = "offline_user_001"
    
    # Start offline manager
    print("1. Starting offline transaction service...")
    offline_manager.start_sync_service()
    print("   ✅ Offline service started")
    
    # Process offline transactions
    print("\n2. Processing offline transactions...")
    
    offline_transactions = [
        {"amount": 3000, "description": "Offline grocery purchase"},
        {"amount": 8000, "description": "Offline medical payment"},
        {"amount": 15000, "description": "Offline school fees"},  # This might trigger validation
        {"amount": 25000, "description": "Large offline transaction"}  # This should trigger enhanced validation
    ]
    
    for i, txn_data in enumerate(offline_transactions, 1):
        print(f"\n   Transaction {i}: ₹{txn_data['amount']:,} - {txn_data['description']}")
        
        transaction_data = {
            'user_id': user_id,
            'amount': txn_data['amount'],
            'timestamp': time.time(),
            'device_id': f'device_{user_id}',
            'description': txn_data['description']
        }
        
        result = offline_manager.process_offline_transaction(user_id, transaction_data)
        
        if result['success']:
            print(f"      ✅ Status: {result['status']}")
            print(f"      📊 Validation Score: {result['validation_score']:.2f}")
            if result['issues']:
                print(f"      ⚠️  Issues: {', '.join(result['issues'])}")
        else:
            print(f"      ❌ Failed: {result['message']}")
    
    # Check sync status
    print("\n3. Checking synchronization status...")
    sync_status = offline_manager.get_sync_status()
    print(f"   📡 Sync Status: {sync_status['status']}")
    print(f"   📋 Pending Transactions: {sync_status['pending_transactions']}")
    print(f"   📊 Queue Size: {sync_status['queue_size']}")

def demo_llm_fraud_detection():
    """Demo LLM-based fraud detection"""
    print("\n\n🤖 LLM FRAUD DETECTION DEMO")
    print("=" * 50)
    
    user_id = "llm_test_user"
    
    # Test different transaction scenarios
    test_scenarios = [
        {
            "name": "Normal Transaction",
            "amount": 5000,
            "description": "Regular grocery shopping",
            "expected": "LOW risk"
        },
        {
            "name": "Medium Risk Transaction", 
            "amount": 35000,
            "description": "Medical emergency payment",
            "expected": "MEDIUM risk"
        },
        {
            "name": "High Risk Transaction",
            "amount": 150000,
            "description": "Suspicious large amount",
            "expected": "HIGH risk - likely fraud"
        },
        {
            "name": "Critical Risk Transaction",
            "amount": 500000,
            "description": "Extremely large rural transaction",
            "expected": "CRITICAL risk - definite fraud"
        }
    ]
    
    print("Testing LLM fraud detection on various scenarios...\n")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"{i}. {scenario['name']} (₹{scenario['amount']:,})")
        print(f"   Expected: {scenario['expected']}")
        
        transaction_data = {
            'user_id': user_id,
            'amount': scenario['amount'],
            'timestamp': time.time(),
            'device_id': f'device_{user_id}',
            'description': scenario['description']
        }
        
        user_profile = {
            'avg_amount': 8000,
            'transaction_count': 25,
            'last_transaction_time': time.time() - 3600,
            'is_new_user': False,
            'risk_score': 0.2,
            'location_pattern': 'consistent'
        }
        
        # Analyze with LLM
        start_time = time.time()
        result = llm_fraud_detector.analyze_transaction_with_llm(
            user_id, transaction_data, user_profile
        )
        
        print(f"   🤖 LLM Result:")
        print(f"      🚨 Is Fraud: {result.is_fraud}")
        print(f"      📊 Confidence: {result.confidence:.2f}")
        print(f"      ⚠️  Risk Level: {result.risk_level}")
        print(f"      💭 Reasoning: {result.reasoning[:80]}...")
        print(f"      🎯 Action: {result.recommended_action}")
        print(f"      ⏱️  Processing Time: {result.processing_time:.3f}s")
        
        if result.risk_factors:
            print(f"      🔍 Risk Factors: {', '.join(result.risk_factors)}")
        
        print()

def demo_integration():
    """Demo integration of all features"""
    print("\n\n🔗 INTEGRATED FEATURES DEMO")
    print("=" * 50)
    
    user_id = "integration_user"
    
    print("1. Setting up user account...")
    # Create account
    account_result = account_manager.create_account(user_id, initial_balance=100000.0)
    print(f"   ✅ Account created with ₹{account_result['balance']:,.2f}")
    
    print("\n2. Testing integrated transaction processing...")
    
    # Test transaction that will trigger multiple systems
    transaction_data = {
        'user_id': user_id,
        'amount': 75000,  # High amount to trigger fraud detection
        'timestamp': time.time(),
        'device_id': f'device_{user_id}',
        'description': 'Large integrated transaction test'
    }
    
    user_profile = {
        'avg_amount': 5000,
        'transaction_count': 10,
        'last_transaction_time': time.time() - 1800,
        'is_new_user': False,
        'risk_score': 0.3
    }
    
    # LLM fraud analysis
    print("   🤖 Running LLM fraud analysis...")
    llm_result = llm_fraud_detector.analyze_transaction_with_llm(
        user_id, transaction_data, user_profile
    )
    print(f"      📊 LLM Risk Assessment: {llm_result.risk_level} ({llm_result.confidence:.2f})")
    
    # Offline validation
    print("   📱 Running offline validation...")
    is_valid, score, issues = offline_manager.validator.validate_transaction(
        user_id, transaction_data, user_profile
    )
    print(f"      ✅ Offline Validation: {'PASS' if is_valid else 'FAIL'} (score: {score:.2f})")
    
    # Account balance check
    print("   💰 Checking account balance...")
    current_balance = account_manager.get_balance(user_id)
    print(f"      💳 Available Balance: ₹{current_balance:,.2f}")
    
    # Process transaction if all checks pass
    if not llm_result.is_fraud and is_valid and current_balance >= transaction_data['amount']:
        print("   ✅ All checks passed - processing transaction...")
        account_result = account_manager.process_transaction(
            user_id, transaction_data['amount'], TransactionType.DEBIT,
            transaction_data['description']
        )
        print(f"      💰 New Balance: ₹{account_result['balance_after']:,.2f}")
    else:
        print("   ❌ Transaction blocked due to security concerns")
        if llm_result.is_fraud:
            print(f"      🚨 LLM detected fraud: {llm_result.reasoning[:60]}...")
        if not is_valid:
            print(f"      ⚠️  Validation issues: {', '.join(issues)}")
        if current_balance < transaction_data['amount']:
            print(f"      💸 Insufficient balance")

def main():
    """Run all demos"""
    print("🏦 ENHANCED RURAL BANKING FEATURES DEMONSTRATION")
    print("=" * 60)
    print("This demo showcases:")
    print("✅ Bank Balance Management")
    print("✅ Offline Transaction Processing") 
    print("✅ LLM-Based Fraud Detection")
    print("✅ Integrated Security Framework")
    print("=" * 60)
    
    try:
        demo_bank_balance()
        demo_offline_transactions()
        demo_llm_fraud_detection()
        demo_integration()
        
        print("\n\n🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("\n🌐 Access the web interface at: http://localhost:5000")
        print("📊 View security dashboard at: http://localhost:5000/admin")
        print("🧪 Test fraud detection at: http://localhost:5000/fraud-test")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            offline_manager.stop_sync_service()
        except:
            pass

if __name__ == "__main__":
    main()
