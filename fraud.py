# fraud_monitoring/main.py

import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"   # optional: disable oneDNN logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"    # suppress TF logs (0=all, 1=filter INFO, 2=filter WARNING, 3=filter ERROR)

from flask import Flask, render_template_string, request, redirect, url_for
from huggingface_hub import hf_hub_download
from tensorflow import keras
import numpy as np

# -----------------------------
# Fraud Detection Logic
# -----------------------------

fraud_alerts = []

# Load Hugging Face Fraud Model (once)
MODEL_PATH = hf_hub_download(
    repo_id="CiferAI/cifer-fraud-detection-k1-a",
    filename="cifer-fraud-detection-k1-a.h5"
)
MODEL = keras.models.load_model(MODEL_PATH)

def preprocess(amount, time, location_flag):
    """
    Corrected preprocessing to match the model's expected input of 8 features.
    We add 5 mock values for the demo.
    """
    # The model expects features like original/new balances for sender/rcleceiver.
    # We will create mock data for these missing features.
    oldbalanceOrg = 10000.0
    newbalanceOrig = oldbalanceOrg - amount
    oldbalanceDest = 5000.0
    newbalanceDest = oldbalanceDest + amount
    isFlaggedFraud = 0.0 # A feature the original dataset had

    # Create the final array with exactly 8 features
    feature_array = np.array([[
        amount,
        time,
        int(location_flag),
        oldbalanceOrg,
        newbalanceOrig,
        oldbalanceDest,
        newbalanceDest,
        isFlaggedFraud
    ]])
    
    return feature_array

def check_fraud(amount, time, location_flag):
    """
    Hybrid: Rule-based + AI-based fraud detection.
    """
    # Rule-based check
    rule_flag = (amount > 10000 or location_flag or time not in range(6, 22))

    # AI-based check
    X = preprocess(amount, time, location_flag)
    probs = MODEL.predict(X, verbose=0)
    fraud_prob = float(probs[0][1])  # fraud class probability

    # Decision
    if rule_flag or fraud_prob > 0.7:
        msg = f"⚠ Fraud detected: amount={amount}, time={time}, loc_flag={location_flag}, AI_score={fraud_prob:.2f}"
        fraud_alerts.append(msg)
        return True
    else:
        msg = f"✅ Safe transaction: amount={amount}, time={time}, AI_score={fraud_prob:.2f}"
        fraud_alerts.append(msg)
        return False

def get_alerts():
    return fraud_alerts

# -----------------------------
# Flask Web Dashboard
# -----------------------------

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Fraud Dashboard</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { color: #333; }
    .alert { color: red; margin: 5px 0; }
    .safe { color: green; margin: 5px 0; }
    form { margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>Fraud Detection Dashboard</h1>
  
  <form method="post" action="/check">
    <label>Amount: <input type="number" name="amount" required></label><br><br>
    <label>Time (0-23): <input type="number" name="time" min="0" max="23" required></label><br><br>
    <label>Location Flag (0=normal, 1=suspicious): 
      <input type="number" name="location_flag" min="0" max="1" required>
    </label><br><br>
    <button type="submit">Submit Transaction</button>
  </form>

  <h2>Alerts</h2>
  {% if alerts %}
    <ul>
      {% for alert in alerts %}
        <li class="{% if 'Fraud' in alert %}alert{% else %}safe{% endif %}">{{ alert }}</li>
      {% endfor %}
    </ul>
  {% else %}
    <p>No alerts yet.</p>
  {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def dashboard():
    return render_template_string(TEMPLATE, alerts=get_alerts())

@app.route("/check", methods=["POST"])
def check():
    amount = float(request.form["amount"])
    time = int(request.form["time"])
    location_flag = int(request.form["location_flag"])

    check_fraud(amount, time, location_flag)
    return redirect(url_for("dashboard"))

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":  

    print("🚀 Fraud Monitoring Dashboard Running at http://127.0.0.1:5000/")
    app.run(debug=True)