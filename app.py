from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session
import bcrypt
import json
import os
import random
import time
from gtts import gTTS
from alert import send_sms  # Import SMS function

app = Flask(__name__)
app.secret_key = "sih_secret_key"

DB_FILE = "database.json"
HIGH_VALUE_LIMIT = 50000  # Transactions above this send alerts

# -------- Utility functions --------
def load_db():
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

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
    return render_template("home.html")

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
        if not pin or len(pin) < 4 or not user_number or not trusted_number:
            flash("All fields are required. PIN must be at least 4 digits.", "danger")
            return redirect(url_for("setup_pin"))

        hashed = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt())
        db = load_db()
        db["user_pin"] = hashed.decode("utf-8")
        db["user_number"] = user_number
        db["trusted_number"] = trusted_number
        db["wrong_pin_count"] = 0
        save_db(db)
        flash("✅ PIN setup successful!", "success")
        return redirect(url_for("transaction"))

    return render_template("setup_pin.html")

# -------- Transaction --------
@app.route("/transaction", methods=["GET", "POST"])
def transaction():
    db = load_db()
    if request.method == "POST":
        amount_str = request.form.get("amount")
        entered_pin = request.form.get("pin")
        language = request.form.get("language", "en")

        if not amount_str or not amount_str.isdigit():
            flash("❌ Please enter a valid amount.", "danger")
            return redirect(url_for("transaction"))
        amount = int(amount_str)

        stored_hash = db.get("user_pin")
        if not stored_hash:
            flash("No PIN found! Please set up a PIN first.", "danger")
            return redirect(url_for("setup_pin"))

        if not bcrypt.checkpw(entered_pin.encode("utf-8"), stored_hash.encode("utf-8")):
            db["wrong_pin_count"] += 1
            remaining_attempts = 3 - db["wrong_pin_count"]
            save_db(db)
            if remaining_attempts <= 0:
                flash("❌ Too many wrong attempts. Redirecting to home.", "danger")
                send_sms(db.get("trusted_number"), "Alert: 3 incorrect PIN attempts!")
                db["wrong_pin_count"] = 0
                save_db(db)
                return redirect(url_for("home"))
            flash(f"❌ Invalid PIN. {remaining_attempts} attempts left.", "danger")
            return redirect(url_for("transaction"))

        db["wrong_pin_count"] = 0
        save_db(db)

        # High-value transaction alert
        if amount > HIGH_VALUE_LIMIT:
            message = f"Alert: High-value transaction of ₹{amount} attempted."
            send_sms(db.get("user_number"), message)
            send_sms(db.get("trusted_number"), message)
            flash(f"✅ Transaction of ₹{amount} Approved! SMS alert sent.", "success")
            return redirect(url_for("transaction"))

        # Small/medium amount → auto approve
        if amount <= 5000:
            flash(f"✅ Transaction of ₹{amount} Approved!", "success")
            return redirect(url_for("transaction"))

        # Large amount → generate audio OTP
        captcha_code = str(random.randint(1000, 9999))
        db["captcha"] = captcha_code
        db["language"] = language
        db["amount"] = amount
        save_db(db)
        generate_audio(captcha_code, language)
        flash("🔊 Please listen to the audio and enter the code.", "info")
        return redirect(url_for("verify_captcha"))

    return render_template("transaction.html")

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
            flash(f"✅ Transaction of ₹{amount} Approved with Audio OTP!", "success")
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

# -------- Run Flask App --------
if __name__ == "__main__":
    app.run(debug=True)
