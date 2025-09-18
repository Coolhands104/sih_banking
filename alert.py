# alert.py
from twilio.rest import Client
import logging

def send_sms(to_number, message_text="Alert: Security notification", user_name="User"):
    """Send SMS alert with proper error handling"""
    try:
        account_sid = ""
        auth_token = ""
        twilio_phone = "+"

        # Validate phone numbers
        if not to_number or not to_number.startswith('+'):
            print(f"Invalid phone number format: {to_number}")
            return False

        # Check if to and from numbers are the same
        if to_number == twilio_phone:
            print(f"⚠️ Cannot send SMS: 'To' and 'From' numbers are the same ({to_number})")
            print("💡 Tip: Use a different phone number for testing, or use a different Twilio number")
            return False

        client = Client(account_sid, auth_token)

        # Create the message
        message = client.messages.create(
            body=f"🏦 Rural Banking Alert: {message_text}",
            from_=twilio_phone,
            to=to_number
        )

        print(f"✅ Alert SMS sent successfully: {message.sid}")
        return True

    except Exception as e:
        print(f"❌ Failed to send SMS: {str(e)}")
        logging.error(f"SMS sending failed: {str(e)}")
        return False

def send_fraud_alert(to_number, amount, user_name="User"):
    """Send fraud detection alert"""
    message = f"⚠️ High-risk transaction of ₹{amount} detected for {user_name}. If this wasn't you, contact support immediately."
    return send_sms(to_number, message, user_name)

def send_pin_lockout_alert(to_number, user_name="User"):
    """Send PIN lockout alert"""
    message = f"🔒 Account locked: {user_name} entered wrong PIN 3 times. Contact support to unlock."
    return send_sms(to_number, message, user_name)
