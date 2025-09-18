"""
Offline Security Capabilities for Rural Banking
Secure offline transaction processing and synchronization
"""

import os
import json
import time
import sqlite3
import hashlib
import hmac
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
from datetime import datetime, timedelta
import logging

from .core import security_core, security_audit
from .llm_fraud_detection import llm_fraud_detector

class TransactionStatus(Enum):
    """Transaction status for offline processing"""
    PENDING = "pending"
    VALIDATED = "validated"
    SYNCED = "synced"
    FAILED = "failed"
    REJECTED = "rejected"

class SyncStatus(Enum):
    """Synchronization status"""
    OFFLINE = "offline"
    SYNCING = "syncing"
    ONLINE = "online"
    ERROR = "error"

@dataclass
class OfflineTransaction:
    """Offline transaction data structure"""
    transaction_id: str
    user_id: str
    amount: float
    timestamp: float
    status: TransactionStatus
    signature: str
    device_id: str
    local_validation_score: float
    retry_count: int = 0
    error_message: Optional[str] = None
    sync_timestamp: Optional[float] = None

class LocalDatabase:
    """Local SQLite database for offline storage"""
    
    def __init__(self, db_path: str = "offline_banking.db"):
        self.db_path = db_path
        self.connection = None
        self._init_database()
    
    def _init_database(self):
        """Initialize local database schema"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS offline_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    timestamp REAL NOT NULL,
                    status TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    local_validation_score REAL NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    sync_timestamp REAL,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS user_cache (
                    user_id TEXT PRIMARY KEY,
                    encrypted_data TEXT NOT NULL,
                    last_updated REAL NOT NULL,
                    checksum TEXT NOT NULL
                )
            ''')
            
            self.connection.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sync_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    details TEXT
                )
            ''')
            
            self.connection.commit()
            logging.info("Local database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization failed: {e}")
            raise
    
    def store_transaction(self, transaction: OfflineTransaction) -> bool:
        """Store transaction in local database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO offline_transactions 
                (transaction_id, user_id, amount, timestamp, status, signature, 
                 device_id, local_validation_score, retry_count, error_message, sync_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction.transaction_id,
                transaction.user_id,
                transaction.amount,
                transaction.timestamp,
                transaction.status.value,
                transaction.signature,
                transaction.device_id,
                transaction.local_validation_score,
                transaction.retry_count,
                transaction.error_message,
                transaction.sync_timestamp
            ))
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to store transaction: {e}")
            return False
    
    def get_pending_transactions(self) -> List[OfflineTransaction]:
        """Get all pending transactions for sync"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT * FROM offline_transactions 
                WHERE status IN (?, ?) 
                ORDER BY timestamp ASC
            ''', (TransactionStatus.PENDING.value, TransactionStatus.VALIDATED.value))
            
            transactions = []
            for row in cursor.fetchall():
                transaction = OfflineTransaction(
                    transaction_id=row[0],
                    user_id=row[1],
                    amount=row[2],
                    timestamp=row[3],
                    status=TransactionStatus(row[4]),
                    signature=row[5],
                    device_id=row[6],
                    local_validation_score=row[7],
                    retry_count=row[8],
                    error_message=row[9],
                    sync_timestamp=row[10]
                )
                transactions.append(transaction)
            
            return transactions
        except Exception as e:
            logging.error(f"Failed to get pending transactions: {e}")
            return []
    
    def cache_user_data(self, user_id: str, data: Dict[str, Any]) -> bool:
        """Cache user data locally with encryption"""
        try:
            # Encrypt user data
            encrypted_data = security_core.encrypt_data(json.dumps(data))
            
            # Create checksum for integrity
            checksum = hashlib.sha256(encrypted_data.encode()).hexdigest()
            
            cursor = self.connection.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_cache 
                (user_id, encrypted_data, last_updated, checksum)
                VALUES (?, ?, ?, ?)
            ''', (user_id, encrypted_data, time.time(), checksum))
            
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Failed to cache user data: {e}")
            return False
    
    def get_cached_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached user data"""
        try:
            cursor = self.connection.cursor()
            cursor.execute('''
                SELECT encrypted_data, checksum FROM user_cache 
                WHERE user_id = ?
            ''', (user_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            encrypted_data, stored_checksum = row
            
            # Verify integrity
            current_checksum = hashlib.sha256(encrypted_data.encode()).hexdigest()
            if current_checksum != stored_checksum:
                logging.warning(f"Data integrity check failed for user {user_id}")
                return None
            
            # Decrypt data
            decrypted_data = security_core.decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
            
        except Exception as e:
            logging.error(f"Failed to get cached user data: {e}")
            return None

class OfflineValidator:
    """Offline transaction validation"""
    
    def __init__(self):
        self.validation_rules = {
            'max_offline_amount': 10000,  # Maximum amount for offline transactions
            'daily_limit': 50000,  # Daily transaction limit
            'transaction_frequency': 5,  # Max transactions per hour
            'suspicious_patterns': True  # Enable pattern detection
        }
    
    def validate_transaction(self, user_id: str, transaction_data: Dict[str, Any], 
                           cached_user_data: Optional[Dict[str, Any]] = None) -> Tuple[bool, float, List[str]]:
        """Validate transaction offline"""
        validation_score = 0.0
        issues = []
        
        amount = transaction_data.get('amount', 0)
        current_time = time.time()
        
        # Amount validation
        if amount > self.validation_rules['max_offline_amount']:
            validation_score += 0.5
            issues.append(f"Amount exceeds offline limit: ₹{amount}")
        
        # Daily limit check (if user data available)
        if cached_user_data:
            daily_total = self._calculate_daily_total(user_id, cached_user_data)
            if daily_total + amount > self.validation_rules['daily_limit']:
                validation_score += 0.4
                issues.append(f"Daily limit exceeded: ₹{daily_total + amount}")
        
        # Frequency check
        recent_count = self._count_recent_transactions(user_id)
        if recent_count >= self.validation_rules['transaction_frequency']:
            validation_score += 0.3
            issues.append(f"Too many recent transactions: {recent_count}")
        
        # Pattern analysis
        if self.validation_rules['suspicious_patterns']:
            pattern_score = self._analyze_patterns(user_id, transaction_data, cached_user_data)
            validation_score += pattern_score
            if pattern_score > 0.2:
                issues.append("Suspicious transaction pattern detected")
        
        # Device validation
        device_id = transaction_data.get('device_id')
        if cached_user_data and not self._is_trusted_device(device_id, cached_user_data):
            validation_score += 0.2
            issues.append("Untrusted device")

        # Enhanced LLM validation (when available and offline)
        try:
            # Use LLM for additional fraud detection
            user_profile = cached_user_data or {}
            llm_result = llm_fraud_detector.analyze_transaction_with_llm(
                user_id, transaction_data, user_profile
            )

            # Combine LLM insights with rule-based validation
            if llm_result.is_fraud and llm_result.confidence > 0.7:
                validation_score = max(validation_score, llm_result.confidence)
                issues.extend(llm_result.risk_factors)
                issues.append(f"LLM fraud detection: {llm_result.reasoning[:100]}...")

            # Log LLM analysis for offline review
            logging.info(f"Offline LLM validation: User={user_id}, Amount=₹{amount}, "
                        f"LLM_Fraud={llm_result.is_fraud}, Confidence={llm_result.confidence:.2f}, "
                        f"Processing_Time={llm_result.processing_time:.2f}s")

        except Exception as e:
            logging.warning(f"LLM offline validation failed, using rule-based only: {e}")

        is_valid = validation_score < 0.5  # Threshold for offline approval
        return is_valid, validation_score, issues
    
    def _calculate_daily_total(self, user_id: str, cached_data: Dict[str, Any]) -> float:
        """Calculate daily transaction total from cached data"""
        today = datetime.now().date()
        daily_transactions = cached_data.get('daily_transactions', {})
        return daily_transactions.get(str(today), 0.0)
    
    def _count_recent_transactions(self, user_id: str) -> int:
        """Count recent transactions from local database"""
        # This would query the local database for recent transactions
        # Simplified implementation
        return 0
    
    def _analyze_patterns(self, user_id: str, transaction_data: Dict[str, Any], 
                         cached_data: Optional[Dict[str, Any]]) -> float:
        """Analyze transaction patterns for anomalies"""
        if not cached_data:
            return 0.0
        
        score = 0.0
        amount = transaction_data.get('amount', 0)
        
        # Check against historical patterns
        avg_amount = cached_data.get('avg_transaction_amount', 0)
        if avg_amount > 0 and amount > avg_amount * 3:
            score += 0.3
        
        # Time pattern analysis
        current_hour = datetime.now().hour
        common_hours = cached_data.get('common_transaction_hours', [])
        if common_hours and current_hour not in common_hours:
            score += 0.2
        
        return min(score, 1.0)
    
    def _is_trusted_device(self, device_id: str, cached_data: Dict[str, Any]) -> bool:
        """Check if device is trusted"""
        trusted_devices = cached_data.get('trusted_devices', [])
        return device_id in trusted_devices

class OfflineTransactionManager:
    """Manage offline transactions and synchronization"""
    
    def __init__(self):
        self.local_db = LocalDatabase()
        self.validator = OfflineValidator()
        self.sync_queue = queue.Queue()
        self.sync_status = SyncStatus.OFFLINE
        self.sync_thread = None
        self.is_running = False
    
    def process_offline_transaction(self, user_id: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transaction in offline mode"""
        try:
            # Generate transaction ID
            transaction_id = security_core.generate_secure_token(16)
            
            # Get cached user data
            cached_user_data = self.local_db.get_cached_user_data(user_id)
            
            # Validate transaction
            is_valid, validation_score, issues = self.validator.validate_transaction(
                user_id, transaction_data, cached_user_data
            )
            
            # Create transaction signature
            transaction_data['transaction_id'] = transaction_id
            transaction_data['timestamp'] = time.time()
            signature = security_core.create_transaction_signature(transaction_data)
            
            # Create offline transaction
            offline_transaction = OfflineTransaction(
                transaction_id=transaction_id,
                user_id=user_id,
                amount=transaction_data['amount'],
                timestamp=transaction_data['timestamp'],
                status=TransactionStatus.VALIDATED if is_valid else TransactionStatus.PENDING,
                signature=signature,
                device_id=transaction_data.get('device_id', 'unknown'),
                local_validation_score=validation_score
            )
            
            # Store in local database
            if self.local_db.store_transaction(offline_transaction):
                # Add to sync queue
                self.sync_queue.put(offline_transaction)
                
                return {
                    'success': True,
                    'transaction_id': transaction_id,
                    'status': offline_transaction.status.value,
                    'validation_score': validation_score,
                    'issues': issues,
                    'message': 'Transaction processed offline' + 
                              (' and approved' if is_valid else ' - pending validation')
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to store transaction locally'
                }
                
        except Exception as e:
            logging.error(f"Offline transaction processing failed: {e}")
            return {
                'success': False,
                'message': f'Transaction processing error: {str(e)}'
            }
    
    def start_sync_service(self):
        """Start background synchronization service"""
        if not self.is_running:
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self.sync_thread.start()
            logging.info("Sync service started")
    
    def stop_sync_service(self):
        """Stop synchronization service"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        logging.info("Sync service stopped")
    
    def _sync_worker(self):
        """Background worker for synchronization"""
        while self.is_running:
            try:
                # Check for pending transactions
                pending_transactions = self.local_db.get_pending_transactions()
                
                if pending_transactions and self._check_connectivity():
                    self.sync_status = SyncStatus.SYNCING
                    self._sync_transactions(pending_transactions)
                    self.sync_status = SyncStatus.ONLINE
                else:
                    self.sync_status = SyncStatus.OFFLINE
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logging.error(f"Sync worker error: {e}")
                self.sync_status = SyncStatus.ERROR
                time.sleep(60)  # Wait longer on error
    
    def _check_connectivity(self) -> bool:
        """Check internet connectivity"""
        try:
            import requests
            response = requests.get('https://httpbin.org/status/200', timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _sync_transactions(self, transactions: List[OfflineTransaction]):
        """Synchronize transactions with server"""
        for transaction in transactions:
            try:
                # Here you would implement actual server synchronization
                # For now, we'll simulate successful sync
                transaction.status = TransactionStatus.SYNCED
                transaction.sync_timestamp = time.time()
                self.local_db.store_transaction(transaction)
                
                logging.info(f"Transaction {transaction.transaction_id} synced successfully")
                
            except Exception as e:
                transaction.retry_count += 1
                transaction.error_message = str(e)
                
                if transaction.retry_count >= 3:
                    transaction.status = TransactionStatus.FAILED
                
                self.local_db.store_transaction(transaction)
                logging.error(f"Failed to sync transaction {transaction.transaction_id}: {e}")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status"""
        pending_count = len(self.local_db.get_pending_transactions())
        
        return {
            'status': self.sync_status.value,
            'pending_transactions': pending_count,
            'queue_size': self.sync_queue.qsize(),
            'last_sync': time.time()  # This would be actual last sync time
        }

# Global offline transaction manager
offline_manager = OfflineTransactionManager()
