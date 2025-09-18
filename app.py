from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, jsonify
import bcrypt
import json
import os
import random
import time
from gtts import gTTS
from alert import send_sms, send_fraud_alert, send_pin_lockout_alert  # Import SMS functions

# Import enhanced security modules
from security.core import security_core, security_audit, DeviceFingerprinting
from security.authentication import (
    adaptive_auth, mfa, session_manager,
    AuthenticationLevel, RiskLevel, AuthenticationAttempt
)
from security.fraud_detection import fraud_engine, FraudRiskLevel
from security.offline_security import offline_manager
from security.dashboard import dashboard_bp, security_metrics
from security.performance import (
    performance_monitor, resource_manager, performance_timer,
    memory_efficient_cache, start_performance_monitoring
)
from banking.account_manager import account_manager, TransactionType

app = Flask(__name__)
app.secret_key = security_core.generate_secure_token(32)  # Use secure random key

# Register dashboard blueprint
app.register_blueprint(dashboard_bp)

# Start performance monitoring
start_performance_monitoring()

DB_FILE = "database.json"
HIGH_VALUE_LIMIT = 50000  # Transactions above this send alerts
MEDIUM_VALUE_LIMIT = 5000  # Threshold for additional authentication

# Performance optimization middleware
@app.before_request
def before_request():
    """Pre-request performance monitoring"""
    request.start_time = time.time()
    resource_manager.cleanup_if_needed()

@app.after_request
def after_request(response):
    """Post-request performance monitoring"""
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        performance_monitor.record_response_time(duration)
    return response

# -------- Utility functions --------
@memory_efficient_cache(max_size=10)
@performance_timer
def load_db():
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        return {}
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            # Decrypt sensitive data if encrypted
            if 'encrypted' in data and data['encrypted']:
                for key in ['user_pin', 'user_number', 'trusted_number']:
                    if key in data and isinstance(data[key], str):
                        try:
                            data[key] = security_core.decrypt_data(data[key])
                        except:
                            pass  # Keep original if decryption fails
            return data
    except json.JSONDecodeError:
        return {}

@performance_timer
def save_db(data):
    # Clear cache when data is saved
    if hasattr(load_db, 'cache_clear'):
        load_db.cache_clear()

    # Encrypt sensitive data before saving
    encrypted_data = data.copy()
    sensitive_fields = ['user_number', 'trusted_number']

    for field in sensitive_fields:
        if field in encrypted_data and isinstance(encrypted_data[field], str):
            encrypted_data[field] = security_core.encrypt_data(encrypted_data[field])

    encrypted_data['encrypted'] = True

    with open(DB_FILE, "w") as f:
        json.dump(encrypted_data, f)

def get_device_id():
    """Get device fingerprint for current request"""
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr or '127.0.0.1'
    return DeviceFingerprinting.generate_device_id(user_agent, ip_address)

def save_transaction_history(user_id, amount, status, description=""):
    """Save transaction to history"""
    try:
        # Load existing transaction history
        try:
            with open("transaction_history.json", "r") as f:
                history = json.load(f)
        except FileNotFoundError:
            history = []

        # Add new transaction
        transaction = {
            "id": len(history) + 1,
            "user_id": user_id,
            "amount": amount,
            "status": status,
            "description": description,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "device_id": get_device_id()
        }

        history.append(transaction)

        # Keep only last 100 transactions per user
        user_transactions = [t for t in history if t["user_id"] == user_id]
        if len(user_transactions) > 100:
            # Remove oldest transactions for this user
            history = [t for t in history if t["user_id"] != user_id] + user_transactions[-100:]

        # Save updated history
        with open("transaction_history.json", "w") as f:
            json.dump(history, f, indent=2)

    except Exception as e:
        print(f"Error saving transaction history: {e}")

def get_transaction_history(user_id, limit=20):
    """Get transaction history for a user"""
    try:
        with open("transaction_history.json", "r") as f:
            history = json.load(f)

        # Filter transactions for this user and sort by timestamp (newest first)
        user_transactions = [t for t in history if t["user_id"] == user_id]
        user_transactions.sort(key=lambda x: x["timestamp"], reverse=True)

        return user_transactions[:limit]
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Error loading transaction history: {e}")
        return []

def check_session_security():
    """Check session security and device binding"""
    session_token = session.get('session_token')
    device_id = get_device_id()

    if not session_token:
        return False

    session_data = session_manager.validate_session(session_token, device_id)
    if not session_data:
        session.clear()
        return False

    # Update session data
    session['user_id'] = session_data['user_id']
    session['auth_level'] = session_data['auth_level']
    return True

# -------- Helper to generate audio --------
def generate_audio(captcha_code, language):
    timestamp = int(time.time() * 1000)
    filename = f"captcha_{captcha_code}_{timestamp}.mp3"
    try:
        tts_text = (
            f"कृपया यह संख्या दर्ज करें {captcha_code}" if language == "hi"
            else f"இந்த எண்ணை உள்ளிடவும் {captcha_code}" if language == "ta"
            else f"దయచేసి ఈ సంఖ్యను నమోదు చేయండి {captcha_code}" if language == "te"
            else f"Please enter this number {captcha_code}"
        )
        tts = gTTS(text=tts_text, lang=language)
        tts.save(filename)
    except Exception:
        tts = gTTS(text=f"Please enter this number {captcha_code}", lang="en")
        tts.save(filename)

    db = load_db()
    old_file = db.get("captcha_file")
    if old_file and os.path.exists(old_file):
        os.remove(old_file)
    db["captcha_file"] = filename
    save_db(db)
    return filename

# -------- Home route --------
@app.route("/")
def home():
    # Check session security
    if not check_session_security():
        return redirect(url_for("setup_pin"))

    db = load_db()
    user_id = db.get("user_id", "Guest")

    # Get or create account
    account_info = account_manager.get_account_info(user_id)
    if not account_info:
        # Create account with initial balance
        result = account_manager.create_account(user_id, initial_balance=50000.0)  # ₹50,000 initial balance
        if result['success']:
            account_info = account_manager.get_account_info(user_id)

    balance = account_info['balance'] if account_info else 0.0
    account_number = account_info['account_number'] if account_info else "N/A"

    return render_template("home.html", user_id=user_id, balance=balance, account_number=account_number)

# -------- Logout --------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

# -------- PIN Setup --------
@app.route("/setup_pin", methods=["GET", "POST"])
def setup_pin():
    if request.method == "POST":
        pin = request.form.get("pin")
        user_number = request.form.get("user_number")
        trusted_number = request.form.get("trusted_number")

        # Enhanced validation
        if not pin or len(pin) < 4 or not user_number or not trusted_number:
            flash("All fields are required. PIN must be at least 4 digits.", "danger")
            return redirect(url_for("setup_pin"))

        # Validate PIN strength
        if not pin.isdigit():
            flash("PIN must contain only numbers.", "danger")
            return redirect(url_for("setup_pin"))

        if len(set(pin)) < 2:  # Check for repeated digits
            flash("PIN should not contain all same digits.", "danger")
            return redirect(url_for("setup_pin"))

        # Use enhanced password hashing
        pin_hash, salt = security_core.hash_password(pin)
        device_id = get_device_id()

        db = load_db()
        db["user_pin"] = pin_hash
        db["pin_salt"] = salt
        db["user_number"] = user_number
        db["trusted_number"] = trusted_number
        db["wrong_pin_count"] = 0
        db["device_id"] = device_id
        db["setup_timestamp"] = time.time()

        # Initialize user profile for fraud detection
        user_id = f"user_{int(time.time())}"
        db["user_id"] = user_id

        save_db(db)

        # Create initial session
        session_token = session_manager.create_session(user_id, device_id, AuthenticationLevel.LOW)
        session['session_token'] = session_token
        session['user_id'] = user_id

        # Log security event
        security_audit.log_security_event(
            'USER_SETUP',
            user_id,
            {'device_id': device_id, 'timestamp': time.time()}
        )

        flash("✅ PIN setup successful! Enhanced security enabled.", "success")
        return redirect(url_for("transaction"))

    return render_template("setup_pin.html")

# -------- Transaction --------
@app.route("/transaction", methods=["GET", "POST"])
def transaction():
    # Check session security
    if not check_session_security():
        flash("Please log in first.", "warning")
        return redirect(url_for("home"))

    db = load_db()
    if request.method == "POST":
        amount_str = request.form.get("amount")
        entered_pin = request.form.get("pin")
        recipient = request.form.get("recipient", "")
        description = request.form.get("description", "Transaction")
        language = request.form.get("language", "en")
        offline_mode = request.form.get("offline_mode") == 'true'

        # Enhanced input validation
        if not amount_str or not amount_str.replace('.', '').isdigit():
            flash("❌ Please enter a valid amount.", "danger")
            return redirect(url_for("transaction"))

        try:
            amount = float(amount_str)
            if amount <= 0 or amount > 1000000:  # Reasonable limits
                flash("❌ Amount must be between ₹1 and ₹10,00,000.", "danger")
                return redirect(url_for("transaction"))
        except ValueError:
            flash("❌ Invalid amount format.", "danger")
            return redirect(url_for("transaction"))

        stored_hash = db.get("user_pin")
        pin_salt = db.get("pin_salt")
        user_id = db.get("user_id", "unknown")
        device_id = get_device_id()

        if not stored_hash or not pin_salt:
            flash("No PIN found! Please set up a PIN first.", "danger")
            return redirect(url_for("setup_pin"))

        # Enhanced PIN verification
        if not security_core.verify_password(entered_pin, stored_hash, pin_salt):
            db["wrong_pin_count"] = db.get("wrong_pin_count", 0) + 1
            remaining_attempts = 3 - db["wrong_pin_count"]
            save_db(db)

            # Log failed authentication
            security_audit.log_failed_authentication(
                user_id, device_id, "Invalid PIN"
            )

            if remaining_attempts <= 0:
                flash("❌ Too many wrong attempts. Account temporarily locked.", "danger")
                # Send PIN lockout alert with error handling
                trusted_number = db.get("trusted_number")
                if trusted_number:
                    send_pin_lockout_alert(trusted_number, user_id)
                db["wrong_pin_count"] = 0
                db["lockout_until"] = time.time() + 1800  # 30 minute lockout
                save_db(db)
                session.clear()
                return redirect(url_for("home"))

            flash(f"❌ Invalid PIN. {remaining_attempts} attempts left.", "danger")
            return redirect(url_for("transaction"))

        # Reset failed attempts on successful PIN
        db["wrong_pin_count"] = 0
        save_db(db)

        # Prepare transaction data
        transaction_data = {
            'user_id': user_id,
            'amount': amount,
            'recipient': recipient,
            'description': description,
            'timestamp': time.time(),
            'device_id': device_id,
            'language': language,
            'offline_mode': offline_mode
        }

        # Risk assessment and fraud detection
        risk_level = adaptive_auth.assess_risk(user_id, device_id, transaction_data)
        fraud_result = fraud_engine.analyze_transaction(user_id, transaction_data)

        # Debug logging for fraud detection
        print(f"🔍 FRAUD DEBUG: Amount=₹{amount}, Risk Level={fraud_result.risk_level.name}, Is Fraud={fraud_result.is_fraud}, Score={fraud_result.confidence}")

        # Check for fraud
        if fraud_result.is_fraud or fraud_result.risk_level == FraudRiskLevel.CRITICAL:
            flash("❌ Transaction blocked due to security concerns. Please contact support.", "danger")
            # Send fraud alert with error handling
            trusted_number = db.get("trusted_number")
            if trusted_number:
                send_fraud_alert(trusted_number, amount, user_id)

            # Record fraud attempt in dashboard
            security_metrics.record_fraud_attempt(
                user_id=user_id,
                amount=amount,
                risk_score=fraud_result.confidence,
                blocked=True,
                details={
                    'risk_level': fraud_result.risk_level.name,
                    'risk_factors': fraud_result.risk_factors,
                    'device_id': device_id,
                    'timestamp': time.time()
                }
            )

            security_audit.log_suspicious_transaction(
                user_id, transaction_data, fraud_result.confidence
            )
            return redirect(url_for("transaction"))

        # Determine required authentication level
        required_auth_level = adaptive_auth.get_required_auth_level(risk_level)

        # Check if offline mode is needed (simulate poor connectivity)
        is_offline = request.form.get('offline_mode') == 'true'

        if is_offline:
            # Process offline transaction
            offline_result = offline_manager.process_offline_transaction(user_id, transaction_data)
            if offline_result['success']:
                flash(f"✅ {offline_result['message']}", "success")
            else:
                flash(f"❌ {offline_result['message']}", "danger")
            return redirect(url_for("transaction"))

        # Record all transactions in fraud monitoring (for dashboard analytics)
        security_metrics.record_fraud_attempt(
            user_id=user_id,
            amount=amount,
            risk_score=fraud_result.confidence,
            blocked=False,  # This transaction was allowed
            details={
                'risk_level': fraud_result.risk_level.name,
                'risk_factors': fraud_result.risk_factors,
                'device_id': device_id,
                'timestamp': time.time(),
                'auth_level': required_auth_level.name
            }
        )

        # Online transaction processing based on amount and risk
        if amount <= MEDIUM_VALUE_LIMIT and required_auth_level == AuthenticationLevel.LOW:
            # Low-risk, small amount - auto approve
            # Process account debit
            account_result = account_manager.process_transaction(
                user_id, amount, TransactionType.DEBIT,
                f"Payment to {recipient}: {description}", f"txn_{int(time.time())}"
            )

            if account_result['success']:
                save_transaction_history(user_id, amount, "Approved", f"Payment to {recipient}: {description}")
                flash(f"✅ Payment of ₹{amount:,.2f} sent to {recipient}! New balance: ₹{account_result['balance_after']:,.2f}", "success")
            else:
                flash(f"❌ Transaction failed: {account_result['message']}", "danger")

            return redirect(url_for("transaction"))

        elif amount > HIGH_VALUE_LIMIT or required_auth_level >= AuthenticationLevel.HIGH:
            # High-value or high-risk transaction
            message = f"High-value transaction of ₹{amount} requires additional verification."
            # Send alerts with error handling
            user_number = db.get("user_number")
            trusted_number = db.get("trusted_number")

            if user_number:
                send_sms(user_number, message, user_id)
            if trusted_number and trusted_number != user_number:
                send_sms(trusted_number, message, user_id)

            # Require additional authentication
            otp_challenge = mfa.generate_otp_challenge(user_id, 'audio')
            session['otp_challenge_id'] = otp_challenge['challenge_id']

            db["captcha"] = otp_challenge['otp']
            db["language"] = language
            db["amount"] = amount
            save_db(db)

            generate_audio(otp_challenge['otp'], language)
            flash("🔊 High-value transaction detected. Please verify with audio OTP.", "info")
            return redirect(url_for("verify_captcha"))

        else:
            # Medium amount/risk → audio OTP
            otp_challenge = mfa.generate_otp_challenge(user_id, 'audio')
            session['otp_challenge_id'] = otp_challenge['challenge_id']

            db["captcha"] = otp_challenge['otp']
            db["language"] = language
            db["amount"] = amount
            save_db(db)

            generate_audio(otp_challenge['otp'], language)
            flash("🔊 Please listen to the audio and enter the code.", "info")
            return redirect(url_for("verify_captcha"))

    # GET request - show form with current balance
    user_id = db.get("user_id", "unknown")
    account_info = account_manager.get_account_info(user_id)
    balance = account_info['balance'] if account_info else 0.0

    return render_template("transaction_new.html", balance=balance)

# -------- Banking Features --------
@app.route("/banking-features")
def banking_features():
    if not check_session_security():
        flash("Please log in first.", "warning")
        return redirect(url_for("home"))

    db = load_db()
    user_id = db.get("user_id", "unknown")

    # Get account info
    account_info = account_manager.get_account_info(user_id)
    balance = account_info['balance'] if account_info else 0.0
    account_number = account_info['account_number'] if account_info else "N/A"

    # Get recent transactions (mock data for now)
    recent_transactions = [
        {
            'description': 'Payment to Grocery Store',
            'amount': 2500.00,
            'type': 'debit',
            'date': '2 hours ago'
        },
        {
            'description': 'Salary Credit',
            'amount': 25000.00,
            'type': 'credit',
            'date': 'Yesterday'
        },
        {
            'description': 'Mobile Recharge',
            'amount': 399.00,
            'type': 'debit',
            'date': '2 days ago'
        }
    ]

    return render_template("banking_features.html",
                         balance=balance,
                         account_number=account_number,
                         recent_transactions=recent_transactions)

# -------- Audio OTP Verification --------
@app.route("/verify_captcha", methods=["GET", "POST"])
def verify_captcha():
    db = load_db()
    stored_captcha = db.get("captcha")
    amount = db.get("amount", 0)
    language = db.get("language", "en")

    if request.method == "POST":
        entered_code = request.form.get("captcha")
        if entered_code == stored_captcha:
            user_id = db.get("user_id", "unknown")

            # Process account debit
            account_result = account_manager.process_transaction(
                user_id, amount, TransactionType.DEBIT,
                f"Verified transaction with Audio OTP", f"otp_txn_{int(time.time())}"
            )

            if account_result['success']:
                save_transaction_history(user_id, amount, "Approved", "Verified with Audio OTP")
                flash(f"✅ Transaction of ₹{amount} Approved with Audio OTP! New balance: ₹{account_result['balance_after']:,.2f}", "success")
            else:
                flash(f"❌ Transaction failed: {account_result['message']}", "danger")

            for key in ["captcha", "captcha_file", "language", "amount"]:
                db.pop(key, None)
            save_db(db)
            return redirect(url_for("transaction"))
        else:
            # Wrong OTP → new OTP
            new_captcha = str(random.randint(1000, 9999))
            db["captcha"] = new_captcha
            db["language"] = language
            save_db(db)
            generate_audio(new_captcha, language)
            flash("❌ Wrong OTP. New OTP generated. Listen to audio.", "danger")
            return redirect(url_for("verify_captcha"))

    return render_template("verify_captcha.html", amount=amount, timestamp=int(time.time() * 1000))

# -------- Resend OTP --------
@app.route("/resend_captcha")
def resend_captcha():
    db = load_db()
    language = db.get("language", "en")
    new_captcha = str(random.randint(1000, 9999))
    db["captcha"] = new_captcha
    db["language"] = language
    save_db(db)
    generate_audio(new_captcha, language)
    flash("🔊 A new OTP has been generated. Please listen to the audio.", "info")
    return redirect(url_for("verify_captcha"))

# -------- Serve audio file --------
@app.route("/captcha_audio")
def captcha_audio():
    db = load_db()
    audio_file = db.get("captcha_file", "captcha.mp3")
    return send_file(audio_file, mimetype="audio/mpeg")

# -------- Transaction History --------
@app.route("/history")
def transaction_history():
    # Check session security
    if not check_session_security():
        flash("Please log in first.", "warning")
        return redirect(url_for("home"))

    db = load_db()
    user_id = db.get("user_id", "unknown")

    # Get transaction history
    transactions = get_transaction_history(user_id, limit=50)

    return render_template("transaction_history.html", transactions=transactions)

# -------- Fraud Test Helper --------
@app.route("/fraud-test")
def fraud_test():
    """Quick fraud detection test page"""
    return """
    <html>
    <head><title>🚨 Fraud Detection Test</title></head>
    <body style="font-family: Arial; padding: 20px; background: #f0f0f0;">
        <h1>🚨 Fraud Detection Test Guide</h1>
        <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <h2>🎯 Quick Fraud Tests:</h2>
            <ol>
                <li><strong>High Amount Fraud:</strong> Try amount <code>₹200,000</code> - Guaranteed fraud detection!</li>
                <li><strong>Rapid Transaction:</strong> Make 2 transactions within 5 minutes</li>
                <li><strong>Amount Spike:</strong> After small transactions, try <code>₹50,000</code></li>
                <li><strong>Weekend Large:</strong> Try <code>₹60,000</code> on weekend</li>
            </ol>
        </div>

        <div style="background: #ffe6e6; padding: 15px; border-radius: 8px; border-left: 4px solid #ff4444;">
            <h3>🚨 Guaranteed Fraud Trigger:</h3>
            <p><strong>Amount:</strong> <code>200000</code> (₹2,00,000)</p>
            <p><strong>Result:</strong> Transaction will be blocked with fraud alert!</p>
        </div>

        <div style="background: #e6f3ff; padding: 15px; border-radius: 8px; border-left: 4px solid #0066cc; margin-top: 20px;">
            <h3>📊 Monitor Results:</h3>
            <ul>
                <li><a href="/admin" target="_blank">Security Dashboard</a> - Real-time fraud monitoring</li>
                <li><a href="/history" target="_blank">Transaction History</a> - See approved/blocked transactions</li>
                <li><strong>Console Output:</strong> Check Flask terminal for fraud analysis logs</li>
            </ul>
        </div>

        <div style="margin-top: 30px;">
            <a href="/" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Back to Banking App</a>
            <a href="/transaction" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">Make Test Transaction</a>
        </div>
    </body>
    </html>
    """

# -------- Run Flask App --------
if __name__ == "__main__":
    app.run(debug=True)
