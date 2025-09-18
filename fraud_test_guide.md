# 🚨 Fraud Detection Test Guide

## How to Trigger Fraud Alerts in Your Rural Banking App

### 🎯 **Fraud Detection Rules Currently Active:**

1. **High Amount Transactions** (40% risk weight)
   - **Trigger**: Amount > ₹100,000
   - **Example**: Try ₹150,000

2. **Unusual Hour Transactions** (20% risk weight)
   - **Trigger**: Between 11 PM - 6 AM (23:00 - 06:00)
   - **Example**: Make transaction late night

3. **Rapid Transactions** (30% risk weight)
   - **Trigger**: Multiple transactions within 5 minutes (300 seconds)
   - **Example**: Make 2 transactions quickly

4. **Amount Spike** (30% risk weight)
   - **Trigger**: Amount > 5x your average transaction
   - **Example**: If you usually do ₹1,000, try ₹6,000+

5. **Weekend Large Transactions** (10% risk weight)
   - **Trigger**: Amount > ₹50,000 on weekends
   - **Example**: Try ₹60,000 on Saturday/Sunday

6. **High Velocity** (40% risk weight)
   - **Trigger**: More than 10 transactions per hour
   - **Example**: Make many transactions quickly

---

## 🧪 **Easy Test Scenarios:**

### **Scenario 1: High Amount Fraud** ⚠️
```
1. Go to Make Transaction
2. Enter amount: 150000 (₹1,50,000)
3. Enter your PIN
4. Result: Should trigger "High amount transaction" fraud alert
```

### **Scenario 2: Rapid Transaction Fraud** ⚠️
```
1. Make a small transaction (₹1000)
2. Immediately make another transaction (₹2000)
3. Result: Should trigger "Rapid transaction" fraud alert
```

### **Scenario 3: Amount Spike Fraud** ⚠️
```
1. First make a few small transactions (₹500, ₹800, ₹1200)
2. Then try a large amount (₹10000)
3. Result: Should trigger "Amount spike" fraud alert
```

### **Scenario 4: Multiple Rules Triggered** 🚨
```
1. Late night (after 11 PM): Enter amount ₹120000
2. This will trigger BOTH:
   - High amount rule (₹120000 > ₹100000)
   - Unusual hour rule (late night)
3. Result: High fraud score, transaction blocked
```

---

## 📊 **Fraud Score Calculation:**

- **Low Risk**: Score < 0.3 → Transaction approved
- **Medium Risk**: Score 0.3-0.6 → Additional verification required
- **High Risk**: Score 0.6-0.8 → Enhanced security checks
- **Critical Risk**: Score > 0.8 → Transaction blocked as fraud

---

## 🎮 **Step-by-Step Test:**

### **Test 1: Guaranteed Fraud Detection**
1. **Setup PIN** first (if not done)
2. **Go to Transaction page**
3. **Enter amount: 200000** (₹2,00,000)
4. **Enter your PIN**
5. **Expected Result**: 
   ```
   ❌ Transaction blocked due to security concerns. 
   Please contact support.
   ```

### **Test 2: Rapid Fire Fraud**
1. **Make transaction**: ₹5000 (should work)
2. **Immediately make another**: ₹3000
3. **Expected Result**: Fraud alert for rapid transactions

### **Test 3: Late Night Fraud**
1. **Change your computer time** to 2:00 AM (or wait until late night)
2. **Make transaction**: ₹80000
3. **Expected Result**: Unusual hour fraud alert

---

## 🔍 **How to See Fraud Detection in Action:**

### **Console Output:**
Watch the terminal where Flask is running. You'll see:
```
INFO:security_audit:{"event_type": "FRAUD_ANALYSIS", "is_fraud": true, "risk_level": "HIGH"}
```

### **Web Interface:**
- **Red error message**: "Transaction blocked due to security concerns"
- **SMS Alert**: Sent to trusted contact (if configured)
- **Security Dashboard**: Shows fraud attempts at `/admin`

### **Transaction History:**
- Blocked transactions won't appear in history
- Only approved transactions are saved

---

## 🛡️ **Security Dashboard Monitoring:**

1. **Go to**: http://localhost:5000/admin
2. **View**: Real-time fraud detection events
3. **Monitor**: Risk scores and triggered rules
4. **Analyze**: Fraud patterns and trends

---

## 💡 **Pro Tips for Testing:**

1. **Start Small**: Make a few normal transactions first (₹500-2000)
2. **Build Profile**: This creates your "normal" spending pattern
3. **Then Test**: Try the fraud scenarios above
4. **Check Dashboard**: Monitor the security dashboard for real-time alerts
5. **View History**: See which transactions were approved vs blocked

---

## 🚨 **Expected Fraud Triggers:**

| Amount | Time | Expected Result |
|--------|------|----------------|
| ₹150,000 | Any | 🚨 HIGH AMOUNT FRAUD |
| ₹60,000 | Weekend | ⚠️ WEEKEND LARGE |
| ₹5,000 | 2:00 AM | ⚠️ UNUSUAL HOUR |
| ₹10,000 | After ₹1,000 avg | ⚠️ AMOUNT SPIKE |
| Any | <5 min apart | ⚠️ RAPID TRANSACTION |

---

## 🎯 **Quick Test Commands:**

**Guaranteed Fraud (Copy-Paste Ready):**
- Amount: `200000`
- PIN: `your_pin`
- Result: Instant fraud detection! 🚨

**Try these amounts for different fraud levels:**
- `50000` - Low risk
- `80000` - Medium risk  
- `120000` - High risk
- `200000` - Critical risk (blocked)

---

**Happy Fraud Testing! 🕵️‍♂️🔍**
