# alert.py
from twilio.rest import Client

def send_sms(to_number, user_name="User"):
    account_sid = "YOUR_TWILIO_SID"
    auth_token = "YOUR_TWILIO_AUTH_TOKEN"
    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body=f"⚠ Alert: {user_name} entered wrong PIN 3 times!",
        from_="+1234567890",
        to=to_number
    )
    print("Alert SMS sent:", message.sid)
