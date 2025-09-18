"""
Bank Account Management System
Handles account balances, transaction limits, and account operations
"""

import json
import time
import sqlite3
import threading
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

class TransactionType(Enum):
    """Transaction types"""
    DEBIT = "debit"
    CREDIT = "credit"
    TRANSFER = "transfer"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"

@dataclass
class AccountTransaction:
    """Account transaction record"""
    transaction_id: str
    account_id: str
    transaction_type: TransactionType
    amount: float
    balance_before: float
    balance_after: float
    timestamp: float
    description: str
    reference_id: Optional[str] = None

class BankAccountManager:
    """Manage bank accounts and balances"""
    
    def __init__(self, db_path: str = "banking_accounts.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_database()
        
    def _init_database(self):
        """Initialize account database"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Accounts table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id TEXT PRIMARY KEY,
                    user_id TEXT UNIQUE NOT NULL,
                    account_number TEXT UNIQUE NOT NULL,
                    balance REAL NOT NULL DEFAULT 0.0,
                    daily_limit REAL NOT NULL DEFAULT 50000.0,
                    monthly_limit REAL NOT NULL DEFAULT 500000.0,
                    account_type TEXT NOT NULL DEFAULT 'savings',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            ''')
            
            # Transaction history table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS account_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    balance_before REAL NOT NULL,
                    balance_after REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    description TEXT NOT NULL,
                    reference_id TEXT,
                    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
                )
            ''')
            
            # Daily transaction limits tracking
            conn.execute('''
                CREATE TABLE IF NOT EXISTS daily_usage (
                    account_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    total_debits REAL NOT NULL DEFAULT 0.0,
                    transaction_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (account_id, date),
                    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Account database initialization failed: {e}")
            raise
    
    def create_account(self, user_id: str, initial_balance: float = 10000.0) -> Dict[str, Any]:
        """Create a new bank account"""
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                
                # Generate account number
                account_number = f"ACC{int(time.time())}{user_id[-4:]}"
                account_id = f"acc_{user_id}"
                
                current_time = time.time()
                
                conn.execute('''
                    INSERT OR REPLACE INTO accounts 
                    (account_id, user_id, account_number, balance, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (account_id, user_id, account_number, initial_balance, current_time, current_time))
                
                # Record initial deposit transaction
                if initial_balance > 0:
                    self._record_transaction(
                        conn, account_id, TransactionType.CREDIT, initial_balance,
                        0.0, initial_balance, "Initial account deposit", f"init_{account_id}"
                    )
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'account_id': account_id,
                    'account_number': account_number,
                    'balance': initial_balance,
                    'message': f'Account created successfully with ₹{initial_balance:,.2f}'
                }
                
        except Exception as e:
            logging.error(f"Account creation failed: {e}")
            return {'success': False, 'message': f'Account creation failed: {str(e)}'}
    
    def get_account_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute('''
                SELECT account_id, account_number, balance, daily_limit, monthly_limit, 
                       account_type, status, created_at, updated_at
                FROM accounts WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    'account_id': row[0],
                    'account_number': row[1],
                    'balance': row[2],
                    'daily_limit': row[3],
                    'monthly_limit': row[4],
                    'account_type': row[5],
                    'status': row[6],
                    'created_at': row[7],
                    'updated_at': row[8]
                }
            return None
            
        except Exception as e:
            logging.error(f"Failed to get account info: {e}")
            return None
    
    def get_balance(self, user_id: str) -> float:
        """Get current account balance"""
        account_info = self.get_account_info(user_id)
        return account_info['balance'] if account_info else 0.0
    
    def process_transaction(self, user_id: str, amount: float, transaction_type: TransactionType, 
                          description: str, reference_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a transaction (debit/credit)"""
        try:
            with self.lock:
                account_info = self.get_account_info(user_id)
                if not account_info:
                    return {'success': False, 'message': 'Account not found'}
                
                if account_info['status'] != 'active':
                    return {'success': False, 'message': 'Account is not active'}
                
                current_balance = account_info['balance']
                
                # Check for sufficient balance on debits
                if transaction_type in [TransactionType.DEBIT, TransactionType.WITHDRAWAL, TransactionType.TRANSFER]:
                    if current_balance < amount:
                        return {
                            'success': False, 
                            'message': f'Insufficient balance. Available: ₹{current_balance:,.2f}'
                        }
                    
                    # Check daily limits
                    if not self._check_daily_limit(account_info['account_id'], amount):
                        return {'success': False, 'message': 'Daily transaction limit exceeded'}
                    
                    new_balance = current_balance - amount
                else:
                    new_balance = current_balance + amount
                
                # Update account balance
                conn = sqlite3.connect(self.db_path)
                conn.execute('''
                    UPDATE accounts SET balance = ?, updated_at = ? 
                    WHERE account_id = ?
                ''', (new_balance, time.time(), account_info['account_id']))
                
                # Record transaction
                transaction_id = f"txn_{int(time.time())}_{user_id[-4:]}"
                self._record_transaction(
                    conn, account_info['account_id'], transaction_type, amount,
                    current_balance, new_balance, description, reference_id or transaction_id
                )
                
                # Update daily usage for debits
                if transaction_type in [TransactionType.DEBIT, TransactionType.WITHDRAWAL, TransactionType.TRANSFER]:
                    self._update_daily_usage(conn, account_info['account_id'], amount)
                
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'balance_before': current_balance,
                    'balance_after': new_balance,
                    'message': f'Transaction successful. New balance: ₹{new_balance:,.2f}'
                }
                
        except Exception as e:
            logging.error(f"Transaction processing failed: {e}")
            return {'success': False, 'message': f'Transaction failed: {str(e)}'}
    
    def _record_transaction(self, conn, account_id: str, transaction_type: TransactionType, 
                          amount: float, balance_before: float, balance_after: float, 
                          description: str, reference_id: str):
        """Record transaction in database"""
        conn.execute('''
            INSERT INTO account_transactions 
            (transaction_id, account_id, transaction_type, amount, balance_before, 
             balance_after, timestamp, description, reference_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (reference_id, account_id, transaction_type.value, amount, balance_before, 
              balance_after, time.time(), description, reference_id))
    
    def _check_daily_limit(self, account_id: str, amount: float) -> bool:
        """Check if transaction is within daily limits"""
        try:
            today = time.strftime('%Y-%m-%d')
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute('''
                SELECT total_debits FROM daily_usage 
                WHERE account_id = ? AND date = ?
            ''', (account_id, today))
            
            row = cursor.fetchone()
            current_usage = row[0] if row else 0.0
            
            # Get account daily limit
            cursor = conn.execute('SELECT daily_limit FROM accounts WHERE account_id = ?', (account_id,))
            daily_limit = cursor.fetchone()[0]
            
            conn.close()
            
            return (current_usage + amount) <= daily_limit
            
        except Exception as e:
            logging.error(f"Daily limit check failed: {e}")
            return False
    
    def _update_daily_usage(self, conn, account_id: str, amount: float):
        """Update daily usage tracking"""
        today = time.strftime('%Y-%m-%d')
        conn.execute('''
            INSERT OR REPLACE INTO daily_usage (account_id, date, total_debits, transaction_count)
            VALUES (?, ?, 
                    COALESCE((SELECT total_debits FROM daily_usage WHERE account_id = ? AND date = ?), 0) + ?,
                    COALESCE((SELECT transaction_count FROM daily_usage WHERE account_id = ? AND date = ?), 0) + 1)
        ''', (account_id, today, account_id, today, amount, account_id, today))

# Global account manager instance
account_manager = BankAccountManager()
