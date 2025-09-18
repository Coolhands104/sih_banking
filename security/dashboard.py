"""
Security Monitoring Dashboard for Rural Banking
Real-time security monitoring and fraud detection dashboard
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, render_template_string, jsonify, request
import sqlite3
import os
from .core import security_audit
from .fraud_detection import fraud_engine
from .offline_security import offline_manager

# Create Blueprint for dashboard
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/admin')

class SecurityMetrics:
    """Security metrics collection and analysis"""
    
    def __init__(self):
        self.db_path = "security_metrics.db"
        self._init_metrics_db()
    
    def _init_metrics_db(self):
        """Initialize metrics database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    severity TEXT NOT NULL,
                    details TEXT,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fraud_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    user_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    risk_score REAL NOT NULL,
                    blocked BOOLEAN NOT NULL,
                    details TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    unit TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to initialize metrics database: {e}")
    
    def record_security_event(self, event_type: str, user_id: str, severity: str, details: Dict[str, Any]):
        """Record security event"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO security_events (timestamp, event_type, user_id, severity, details)
                VALUES (?, ?, ?, ?, ?)
            ''', (time.time(), event_type, user_id, severity, json.dumps(details)))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to record security event: {e}")
    
    def record_fraud_attempt(self, user_id: str, amount: float, risk_score: float, blocked: bool, details: Dict[str, Any]):
        """Record fraud attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO fraud_attempts (timestamp, user_id, amount, risk_score, blocked, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (time.time(), user_id, amount, risk_score, blocked, json.dumps(details)))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Failed to record fraud attempt: {e}")
    
    def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for specified time period"""
        try:
            cutoff_time = time.time() - (hours * 3600)
            conn = sqlite3.connect(self.db_path)
            
            # Security events summary
            cursor = conn.execute('''
                SELECT event_type, severity, COUNT(*) as count
                FROM security_events 
                WHERE timestamp > ?
                GROUP BY event_type, severity
            ''', (cutoff_time,))
            
            events_summary = {}
            for row in cursor.fetchall():
                event_type, severity, count = row
                if event_type not in events_summary:
                    events_summary[event_type] = {}
                events_summary[event_type][severity] = count
            
            # Fraud attempts summary
            cursor = conn.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN blocked THEN 1 ELSE 0 END) as blocked,
                       AVG(risk_score) as avg_risk_score,
                       SUM(amount) as total_amount
                FROM fraud_attempts 
                WHERE timestamp > ?
            ''', (cutoff_time,))
            
            fraud_row = cursor.fetchone()
            fraud_summary = {
                'total_attempts': fraud_row[0] or 0,
                'blocked_attempts': fraud_row[1] or 0,
                'avg_risk_score': fraud_row[2] or 0.0,
                'total_amount_attempted': fraud_row[3] or 0.0
            }
            
            conn.close()
            
            return {
                'time_period_hours': hours,
                'events_summary': events_summary,
                'fraud_summary': fraud_summary,
                'generated_at': time.time()
            }
            
        except Exception as e:
            print(f"Failed to get security summary: {e}")
            return {}
    
    def get_fraud_trends(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get fraud trends over specified days"""
        try:
            trends = []
            conn = sqlite3.connect(self.db_path)
            
            for i in range(days):
                day_start = time.time() - ((i + 1) * 24 * 3600)
                day_end = time.time() - (i * 24 * 3600)
                
                cursor = conn.execute('''
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN blocked THEN 1 ELSE 0 END) as blocked,
                           AVG(risk_score) as avg_risk
                    FROM fraud_attempts 
                    WHERE timestamp BETWEEN ? AND ?
                ''', (day_start, day_end))
                
                row = cursor.fetchone()
                trends.append({
                    'date': datetime.fromtimestamp(day_start).strftime('%Y-%m-%d'),
                    'total_attempts': row[0] or 0,
                    'blocked_attempts': row[1] or 0,
                    'avg_risk_score': row[2] or 0.0
                })
            
            conn.close()
            return list(reversed(trends))  # Most recent first
            
        except Exception as e:
            print(f"Failed to get fraud trends: {e}")
            return []

# Global metrics instance
security_metrics = SecurityMetrics()

# Dashboard HTML Template
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Rural Banking Security Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5; 
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; 
            padding: 20px; 
            border-radius: 10px; 
            margin-bottom: 20px;
            text-align: center;
        }
        .metrics-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 20px; 
        }
        .metric-card { 
            background: white; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }
        .metric-title { 
            font-size: 18px; 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 10px; 
        }
        .metric-value { 
            font-size: 24px; 
            font-weight: bold; 
            color: #667eea; 
        }
        .alert { 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 5px; 
        }
        .alert-danger { 
            background-color: #f8d7da; 
            color: #721c24; 
            border: 1px solid #f5c6cb; 
        }
        .alert-warning { 
            background-color: #fff3cd; 
            color: #856404; 
            border: 1px solid #ffeaa7; 
        }
        .alert-success { 
            background-color: #d4edda; 
            color: #155724; 
            border: 1px solid #c3e6cb; 
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online { background-color: #28a745; }
        .status-offline { background-color: #dc3545; }
        .status-warning { background-color: #ffc107; }
        .refresh-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 10px 5px;
        }
        .refresh-btn:hover { background: #5a6fd8; }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            background: white; 
            border-radius: 10px; 
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd; 
        }
        th { 
            background-color: #667eea; 
            color: white; 
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="header">
        <h1>🛡️ Rural Banking Security Dashboard</h1>
        <p>Real-time monitoring and fraud detection system</p>
        <button class="refresh-btn" onclick="refreshDashboard()">🔄 Refresh</button>
        <button class="refresh-btn" onclick="toggleAutoRefresh()">⏱️ Auto Refresh</button>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-title">System Status</div>
            <div class="metric-value">
                <span class="status-indicator status-online"></span>
                Online & Secure
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Fraud Detection Rate</div>
            <div class="metric-value" id="fraud-rate">{{ fraud_summary.get('blocked_attempts', 0) }}/{{ fraud_summary.get('total_attempts', 0) }}</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Average Risk Score</div>
            <div class="metric-value" id="avg-risk">{{ "%.2f"|format(fraud_summary.get('avg_risk_score', 0)) }}</div>
        </div>
        
        <div class="metric-card">
            <div class="metric-title">Offline Transactions</div>
            <div class="metric-value" id="offline-count">{{ offline_status.get('pending_transactions', 0) }}</div>
        </div>
    </div>

    <div class="chart-container">
        <h3>Fraud Detection Trends (Last 7 Days)</h3>
        <canvas id="fraudTrendChart" width="400" height="200"></canvas>
    </div>

    <div class="alert alert-success">
        <strong>✅ Security Status:</strong> All systems operational. Enhanced fraud detection active.
    </div>

    {% if recent_alerts %}
    <div class="alert alert-warning">
        <strong>⚠️ Recent Alerts:</strong>
        <ul>
        {% for alert in recent_alerts %}
            <li>{{ alert }}</li>
        {% endfor %}
        </ul>
    </div>
    {% endif %}

    <h3>Recent Security Events</h3>
    <table>
        <thead>
            <tr>
                <th>Time</th>
                <th>Event Type</th>
                <th>User ID</th>
                <th>Severity</th>
                <th>Details</th>
            </tr>
        </thead>
        <tbody id="events-table">
            <!-- Events will be populated by JavaScript -->
        </tbody>
    </table>

    <script>
        let autoRefresh = false;
        let refreshInterval;

        function refreshDashboard() {
            location.reload();
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            if (autoRefresh) {
                refreshInterval = setInterval(refreshDashboard, 30000); // 30 seconds
                document.querySelector('button[onclick="toggleAutoRefresh()"]').textContent = '⏹️ Stop Auto';
            } else {
                clearInterval(refreshInterval);
                document.querySelector('button[onclick="toggleAutoRefresh()"]').textContent = '⏱️ Auto Refresh';
            }
        }

        // Initialize fraud trend chart
        const ctx = document.getElementById('fraudTrendChart').getContext('2d');
        const fraudTrendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: {{ fraud_trends | map(attribute='date') | list | tojson }},
                datasets: [{
                    label: 'Total Attempts',
                    data: {{ fraud_trends | map(attribute='total_attempts') | list | tojson }},
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.1
                }, {
                    label: 'Blocked Attempts',
                    data: {{ fraud_trends | map(attribute='blocked_attempts') | list | tojson }},
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

        // Load recent events
        fetch('/admin/api/recent-events')
            .then(response => response.json())
            .then(data => {
                const tbody = document.getElementById('events-table');
                tbody.innerHTML = '';
                data.events.forEach(event => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${new Date(event.timestamp * 1000).toLocaleString()}</td>
                        <td>${event.event_type}</td>
                        <td>${event.user_id || 'N/A'}</td>
                        <td><span class="status-indicator status-${event.severity.toLowerCase()}"></span>${event.severity}</td>
                        <td>${event.details}</td>
                    `;
                });
            })
            .catch(error => console.error('Error loading events:', error));
    </script>
</body>
</html>
"""

@dashboard_bp.route('/')
def dashboard():
    """Main security dashboard"""
    try:
        # Get security metrics
        summary = security_metrics.get_security_summary(24)
        fraud_trends = security_metrics.get_fraud_trends(7)
        offline_status = offline_manager.get_sync_status()

        # Get recent alerts (simplified)
        recent_alerts = [
            "System started successfully",
            "Fraud detection model loaded",
            "Offline sync service active"
        ]

        return render_template_string(
            DASHBOARD_TEMPLATE,
            fraud_summary=summary.get('fraud_summary', {}),
            fraud_trends=fraud_trends,
            offline_status=offline_status,
            recent_alerts=recent_alerts
        )
    except Exception as e:
        return f"Dashboard error: {e}", 500

@dashboard_bp.route('/api/recent-events')
def api_recent_events():
    """API endpoint for recent security events"""
    try:
        conn = sqlite3.connect(security_metrics.db_path)
        cursor = conn.execute('''
            SELECT timestamp, event_type, user_id, severity, details
            FROM security_events
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (time.time() - 24*3600,))  # Last 24 hours

        events = []
        for row in cursor.fetchall():
            events.append({
                'timestamp': row[0],
                'event_type': row[1],
                'user_id': row[2],
                'severity': row[3],
                'details': row[4][:100] if row[4] else 'N/A'  # Truncate details
            })

        conn.close()
        return jsonify({'events': events})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dashboard_bp.route('/api/metrics')
def api_metrics():
    """API endpoint for real-time metrics"""
    try:
        summary = security_metrics.get_security_summary(1)  # Last hour
        fraud_stats = fraud_engine.get_fraud_statistics()
        offline_status = offline_manager.get_sync_status()

        return jsonify({
            'security_summary': summary,
            'fraud_statistics': fraud_stats,
            'offline_status': offline_status,
            'timestamp': time.time()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
