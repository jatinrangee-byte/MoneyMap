"""
Web application backend for Personal Expense Tracker.
Exposes RESTful APIs and serves the presentation UI.
"""

import os
import csv
import io
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, send_from_directory, Response

import database
import auth
import ml_engine
import ai_chat

# Initialize Flask App
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
app.config["SECRET_KEY"] = os.environ.get("TRACKER_SECRET_KEY", "moneymap-finance-secret-key-prod")

# Ensure database is initialized at startup
database.init_db()


# ---------------- AUTHENTICATION DECORATOR ----------------

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        elif "session_token" in request.cookies:
            token = request.cookies.get("session_token")

        if not token:
            return jsonify({"error": "Unauthorized. Please log in."}), 401

        user_id = auth.verify_session_token(token)
        if not user_id:
            return jsonify({"error": "Session expired or invalid. Please log in again."}), 401

        request.user_id = user_id
        return f(*args, **kwargs)
    return decorated


# ---------------- WEB UI ROUTE ----------------

@app.route("/")
def index():
    return render_template("index.html")


# ---------------- AUTH API ----------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    currency = data.get("currency", "₹").strip() or "₹"

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400

    existing = database.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 409

    pwd_hash = auth.hash_password(password)
    user_id = database.create_user(name, email, pwd_hash, currency)

    if not user_id:
        return jsonify({"error": "Failed to create account. Please try again."}), 500

    # Auto-seed initial demo transactions so the user immediately sees rich UI
    database.seed_demo_data(user_id)

    token = auth.generate_session_token(user_id)
    user = database.get_user_by_id(user_id)

    resp = jsonify({"message": "Registration successful", "user": user, "token": token})
    resp.set_cookie("session_token", token, httponly=True, max_age=86400 * 7, samesite="Lax")
    return resp, 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user_record = database.get_user_by_email(email)
    if not user_record or not auth.verify_password(user_record["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    token = auth.generate_session_token(user_record["id"])
    user = database.get_user_by_id(user_record["id"])

    resp = jsonify({"message": "Login successful", "user": user, "token": token})
    resp.set_cookie("session_token", token, httponly=True, max_age=86400 * 7, samesite="Lax")
    return resp, 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Logged out successfully"})
    resp.delete_cookie("session_token")
    return resp, 200


@app.route("/api/auth/me", methods=["GET"])
@require_auth
def get_current_user():
    user = database.get_user_by_id(request.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user})


@app.route("/api/auth/profile", methods=["PUT"])
@require_auth
def update_profile():
    data = request.get_json() or {}
    currency = data.get("currency", "₹").strip()
    if currency:
        database.update_user_currency(request.user_id, currency)
    user = database.get_user_by_id(request.user_id)
    return jsonify({"message": "Profile updated", "user": user})


# ---------------- TRANSACTION API ----------------

@app.route("/api/transactions", methods=["GET"])
@require_auth
def list_transactions():
    category = request.args.get("category")
    type_ = request.args.get("type")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    search = request.args.get("search")
    limit = request.args.get("limit")
    offset = request.args.get("offset")

    transactions = database.get_transactions(
        user_id=request.user_id,
        category=category,
        type_=type_,
        start_date=start_date,
        end_date=end_date,
        search=search,
        limit=limit,
        offset=offset
    )
    return jsonify({"transactions": transactions, "count": len(transactions)})


@app.route("/api/transactions", methods=["POST"])
@require_auth
def create_transaction():
    data = request.get_json() or {}
    type_ = data.get("type", "expense").strip().lower()
    amount_str = data.get("amount")
    category = data.get("category", "").strip()
    date = data.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    description = data.get("description", "").strip()

    if type_ not in ["income", "expense"]:
        return jsonify({"error": "Type must be 'income' or 'expense'."}), 400

    try:
        amount = float(amount_str)
        if amount <= 0:
            return jsonify({"error": "Amount must be a positive number."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Valid positive amount is required."}), 400

    if not category:
        return jsonify({"error": "Category is required."}), 400

    # ML Anomaly Detection: Check if this transaction deviates significantly from past category norms
    all_user_trans = database.get_transactions(request.user_id)
    is_anomaly = 0
    anomaly_reason = ""
    if type_ == "expense":
        flagged, reason = ml_engine.detect_anomaly(amount, category, all_user_trans)
        if flagged:
            is_anomaly = 1
            anomaly_reason = reason

    t_id = database.add_transaction(
        user_id=request.user_id,
        type_=type_,
        amount=amount,
        category=category,
        date=date,
        description=description,
        is_anomaly=is_anomaly
    )

    # Online active learning: feed new user description & verified category to update ML weights
    if description:
        ml_engine.train_user_transaction(description, category)

    new_t = database.get_transaction_by_id(t_id, request.user_id)
    return jsonify({
        "message": "Transaction recorded successfully",
        "transaction": new_t,
        "is_anomaly": bool(is_anomaly),
        "anomaly_reason": anomaly_reason
    }), 201


@app.route("/api/transactions/<int:t_id>", methods=["GET"])
@require_auth
def get_transaction(t_id):
    t = database.get_transaction_by_id(t_id, request.user_id)
    if not t:
        return jsonify({"error": "Transaction not found."}), 404
    return jsonify({"transaction": t})


@app.route("/api/transactions/<int:t_id>", methods=["PUT"])
@require_auth
def edit_transaction(t_id):
    data = request.get_json() or {}
    type_ = data.get("type", "expense").strip().lower()
    amount_str = data.get("amount")
    category = data.get("category", "").strip()
    date = data.get("date", "").strip()
    description = data.get("description", "").strip()

    if type_ not in ["income", "expense"]:
        return jsonify({"error": "Type must be 'income' or 'expense'."}), 400

    try:
        amount = float(amount_str)
        if amount <= 0:
            return jsonify({"error": "Amount must be a positive number."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Valid positive amount is required."}), 400

    # Check anomaly
    all_user_trans = [t for t in database.get_transactions(request.user_id) if t["id"] != t_id]
    is_anomaly = 0
    if type_ == "expense":
        flagged, _ = ml_engine.detect_anomaly(amount, category, all_user_trans)
        if flagged:
            is_anomaly = 1

    success = database.update_transaction(
        transaction_id=t_id,
        user_id=request.user_id,
        type_=type_,
        amount=amount,
        category=category,
        date=date,
        description=description,
        is_anomaly=is_anomaly
    )

    if not success:
        return jsonify({"error": "Transaction not found or could not be updated."}), 404

    updated_t = database.get_transaction_by_id(t_id, request.user_id)
    return jsonify({"message": "Transaction updated successfully", "transaction": updated_t})


@app.route("/api/transactions/<int:t_id>", methods=["DELETE"])
@require_auth
def remove_transaction(t_id):
    success = database.delete_transaction(t_id, request.user_id)
    if not success:
        return jsonify({"error": "Transaction not found or could not be deleted."}), 404
    return jsonify({"message": "Transaction deleted successfully"})


# ---------------- BUDGET API ----------------

@app.route("/api/budgets", methods=["GET"])
@require_auth
def list_budgets():
    month_year = request.args.get("month_year") or datetime.now().strftime("%Y-%m")
    budgets = database.get_budgets(request.user_id, month_year=month_year)
    return jsonify({"budgets": budgets, "month_year": month_year})


@app.route("/api/budgets", methods=["POST"])
@require_auth
def save_budget():
    data = request.get_json() or {}
    category = data.get("category", "").strip()
    limit_str = data.get("monthly_limit")
    month_year = data.get("month_year", "").strip() or datetime.now().strftime("%Y-%m")

    if not category:
        return jsonify({"error": "Category is required."}), 400

    try:
        monthly_limit = float(limit_str)
        if monthly_limit < 0:
            return jsonify({"error": "Limit cannot be negative."}), 400
    except (TypeError, ValueError):
        return jsonify({"error": "Valid budget limit is required."}), 400

    b_id = database.set_budget(request.user_id, category, monthly_limit, month_year=month_year)
    budgets = database.get_budgets(request.user_id, month_year=month_year)
    return jsonify({"message": "Budget saved successfully", "budget_id": b_id, "budgets": budgets})


@app.route("/api/budgets/<int:b_id>", methods=["DELETE"])
@require_auth
def remove_budget(b_id):
    success = database.delete_budget(b_id, request.user_id)
    if not success:
        return jsonify({"error": "Budget not found."}), 404
    return jsonify({"message": "Budget removed successfully"})


# ---------------- SUMMARY & DASHBOARD API ----------------

@app.route("/api/summary", methods=["GET"])
@require_auth
def get_summary():
    month_year = request.args.get("month_year")
    summary = database.get_financial_summary(request.user_id, month_year=month_year)
    return jsonify({"summary": summary})


# ---------------- MACHINE LEARNING APIS ----------------

@app.route("/api/ml/predict-category", methods=["POST"])
def predict_category_endpoint():
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    prediction = ml_engine.predict_category(description)
    return jsonify(prediction)


@app.route("/api/ml/insights", methods=["GET"])
@require_auth
def get_ml_insights():
    month_year = request.args.get("month_year") or datetime.now().strftime("%Y-%m")
    
    # Transactions for user
    transactions = database.get_transactions(request.user_id)
    budgets = database.get_budgets(request.user_id, month_year=month_year)
    summary = database.get_financial_summary(request.user_id, month_year=month_year)

    total_budget = sum(float(b.get("monthly_limit", 0)) for b in budgets)

    # ML Forecast Engine
    forecast = ml_engine.forecast_monthly_spending(transactions, total_budget)

    # AI Financial Health Score & Advisor
    health = ml_engine.compute_financial_health_score(summary, budgets)

    # Flagged Anomalies
    anomalies = [t for t in transactions if t.get("is_anomaly") == 1]

    return jsonify({
        "forecast": forecast,
        "health": health,
        "anomalies": anomalies,
        "total_budget": total_budget
    })


# ---------------- AI CHATBOT ADVISOR API ----------------

@app.route("/api/ai/chat", methods=["POST"])
@require_auth
def ai_chat_endpoint():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    response = ai_chat.generate_advisor_response(request.user_id, message, history)
    return jsonify(response)


# ---------------- SEED DEMO DATA API ----------------

@app.route("/api/demo/seed", methods=["POST"])
@require_auth
def seed_demo():
    database.seed_demo_data(request.user_id)
    return jsonify({"message": "Demo data populated successfully with realistic financial records & ML anomalies!"})


# ---------------- CSV EXPORT API ----------------

@app.route("/api/export/csv", methods=["GET"])
@require_auth
def export_csv():
    transactions = database.get_transactions(request.user_id)
    user = database.get_user_by_id(request.user_id)
    currency = user.get("currency", "₹") if user else "₹"

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Date", "Type", f"Amount ({currency})", "Category", "Description", "Anomaly Flagged"])

    for t in transactions:
        writer.writerow([
            t["id"],
            t["date"],
            t["type"].capitalize(),
            f"{t['amount']:.2f}",
            t["category"],
            t["description"] or "",
            "Yes (Outlier)" if t.get("is_anomaly") else "No"
        ])

    output.seek(0)
    filename = f"MoneyMap_Export_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )


# ---------------- APP LAUNCHER ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n==================================================================")
    print(f"🗺️ MoneyMap — Personal Finance Intelligence running on: http://localhost:{port}")
    print(f"Machine Learning Engine: NLP Categorizer + Predictive Forecasting + Outlier Detection")
    print(f"==================================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
