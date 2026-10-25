"""
Comprehensive automated tests for Personal Expense Tracker.
Tests database operations, password security, REST APIs, and Machine Learning models.
"""

import os
import unittest
import tempfile
import json
import sqlite3

# Import application modules
import database
import auth
import ml_engine
from app import app


class TestPersonalExpenseTracker(unittest.TestCase):

    def setUp(self):
        # Create a temporary database for isolation
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        database.init_db(self.db_path)

        # Configure Flask test client
        app.config["TESTING"] = True
        self.client = app.test_client()

        # Monkey-patch database path in modules for testing
        database.DB_PATH = self.db_path

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # ---------------- DATABASE & CRUD TESTS ----------------

    def test_user_creation_and_retrieval(self):
        pwd_hash = auth.hash_password("testSecret123")
        uid = database.create_user("Test Student", "student@test.com", pwd_hash, currency="₹", db_path=self.db_path)
        self.assertIsNotNone(uid)

        user = database.get_user_by_email("student@test.com", db_path=self.db_path)
        self.assertEqual(user["name"], "Test Student")
        self.assertEqual(user["currency"], "₹")

        # Duplicate email should fail
        dup = database.create_user("Duplicate", "student@test.com", pwd_hash, db_path=self.db_path)
        self.assertIsNone(dup)

    def test_transaction_crud_and_balance(self):
        uid = database.create_user("Alice", "alice@test.com", "hash", db_path=self.db_path)

        # Add income
        t1 = database.add_transaction(uid, "income", 10000.0, "Salary / Allowance", "2026-10-01", "Monthly Stipend", db_path=self.db_path)
        # Add expenses
        t2 = database.add_transaction(uid, "expense", 1500.0, "Food & Dining", "2026-10-02", "Grocery items", db_path=self.db_path)
        t3 = database.add_transaction(uid, "expense", 500.0, "Transportation", "2026-10-03", "Bus pass", db_path=self.db_path)

        # Verify list
        transactions = database.get_transactions(uid, db_path=self.db_path)
        self.assertEqual(len(transactions), 3)

        # Verify summary calculations
        summary = database.get_financial_summary(uid, db_path=self.db_path)
        self.assertEqual(summary["total_income"], 10000.0)
        self.assertEqual(summary["total_expenses"], 2000.0)
        self.assertEqual(summary["balance"], 8000.0)
        self.assertEqual(summary["savings_rate"], 80.0)

        # Update transaction
        database.update_transaction(t2, uid, "expense", 1800.0, "Food & Dining", "2026-10-02", "Supermarket grocery", db_path=self.db_path)
        updated = database.get_transaction_by_id(t2, uid, db_path=self.db_path)
        self.assertEqual(updated["amount"], 1800.0)

        # Delete transaction
        deleted = database.delete_transaction(t3, uid, db_path=self.db_path)
        self.assertTrue(deleted)
        self.assertEqual(len(database.get_transactions(uid, db_path=self.db_path)), 2)

    def test_budget_management(self):
        uid = database.create_user("Bob", "bob@test.com", "hash", db_path=self.db_path)
        month = "2026-10"

        database.set_budget(uid, "Food & Dining", 3000.0, month_year=month, db_path=self.db_path)
        database.add_transaction(uid, "expense", 2400.0, "Food & Dining", "2026-10-15", "Canteen food", db_path=self.db_path)

        budgets = database.get_budgets(uid, month_year=month, db_path=self.db_path)
        self.assertEqual(len(budgets), 1)
        b = budgets[0]
        self.assertEqual(b["category"], "Food & Dining")
        self.assertEqual(b["monthly_limit"], 3000.0)
        self.assertEqual(b["spent"], 2400.0)
        self.assertEqual(b["remaining"], 600.0)
        self.assertEqual(b["percentage"], 80.0)
        self.assertFalse(b["is_exceeded"])

    # ---------------- SECURITY & AUTH TESTS ----------------

    def test_password_hashing_and_verification(self):
        raw = "MySuperSecretPassword@2026"
        hashed = auth.hash_password(raw)
        self.assertTrue(hashed.count("$") == 1)
        self.assertTrue(auth.verify_password(hashed, raw))
        self.assertFalse(auth.verify_password(hashed, "WrongPassword"))

    def test_session_token_validation(self):
        token = auth.generate_session_token(42, duration_seconds=3600)
        uid = auth.verify_session_token(token)
        self.assertEqual(uid, 42)

        # Tampered token
        tampered = token[:-4] + "abcd"
        self.assertIsNone(auth.verify_session_token(tampered))

        # Expired token
        expired_token = auth.generate_session_token(42, duration_seconds=-10)
        self.assertIsNone(auth.verify_session_token(expired_token))

    # ---------------- MACHINE LEARNING TESTS ----------------

    def test_nlp_categorizer_predictions(self):
        # Test distinct domain keywords
        food_res = ml_engine.predict_category("Dominos cheese burst pizza")
        self.assertEqual(food_res["category"], "Food & Dining")
        self.assertGreater(food_res["confidence"], 60.0)

        transport_res = ml_engine.predict_category("Monthly metro smart card recharge")
        self.assertEqual(transport_res["category"], "Transportation")

        edu_res = ml_engine.predict_category("Machine Learning textbook and university lab fees")
        self.assertEqual(edu_res["category"], "Education")

        netflix_res = ml_engine.predict_category("Netflix 4k monthly streaming subscription")
        self.assertEqual(netflix_res["category"], "Entertainment")

    def test_spending_forecasting(self):
        sample_transactions = [
            {"type": "expense", "amount": 500.0, "date": "2026-10-01"},
            {"type": "expense", "amount": 300.0, "date": "2026-10-05"},
            {"type": "expense", "amount": 400.0, "date": "2026-10-10"},
        ]
        forecast = ml_engine.forecast_monthly_spending(sample_transactions, monthly_budget=15000.0)
        self.assertIn("projected_total", forecast)
        self.assertIn("daily_burn_rate", forecast)
        self.assertGreater(forecast["projected_total"], 0)

    def test_anomaly_detection(self):
        # Normal food expenses
        normal_history = [
            {"category": "Food & Dining", "type": "expense", "amount": 200.0},
            {"category": "Food & Dining", "type": "expense", "amount": 250.0},
            {"category": "Food & Dining", "type": "expense", "amount": 180.0},
            {"category": "Food & Dining", "type": "expense", "amount": 220.0},
            {"category": "Food & Dining", "type": "expense", "amount": 190.0},
        ]
        # Normal expense: 230
        is_anomaly_normal, _ = ml_engine.detect_anomaly(230.0, "Food & Dining", normal_history)
        self.assertFalse(is_anomaly_normal)

        # Huge outlier expense: 5,500 for single lunch
        is_anomaly_high, reason = ml_engine.detect_anomaly(5500.0, "Food & Dining", normal_history)
        self.assertTrue(is_anomaly_high)
        self.assertIn("Anomaly", reason)

    # ---------------- REST API INTEGRATION TESTS ----------------

    def test_rest_api_auth_and_transactions(self):
        # 1. Register user
        reg_resp = self.client.post("/api/auth/register", json={
            "name": "Integration User",
            "email": "integration@test.com",
            "password": "password123",
            "currency": "₹"
        })
        self.assertEqual(reg_resp.status_code, 201)
        data = reg_resp.get_json()
        token = data["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get me
        me_resp = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(me_resp.status_code, 200)

        # 3. Create transaction
        tx_resp = self.client.post("/api/transactions", headers=headers, json={
            "type": "expense",
            "amount": 250.0,
            "category": "Food & Dining",
            "date": "2026-10-25",
            "description": "Starbucks cold brew"
        })
        self.assertEqual(tx_resp.status_code, 201)

        # 4. Predict Category API
        pred_resp = self.client.post("/api/ml/predict-category", json={
            "description": "Zomato dinner delivery"
        })
        self.assertEqual(pred_resp.status_code, 200)
        self.assertEqual(pred_resp.get_json()["category"], "Food & Dining")

        # 5. ML Insights API
        insights_resp = self.client.get("/api/ml/insights", headers=headers)
        self.assertEqual(insights_resp.status_code, 200)
        insights_data = insights_resp.get_json()
        self.assertIn("forecast", insights_data)
        self.assertIn("health", insights_data)

        # 6. Export CSV
        csv_resp = self.client.get("/api/export/csv", headers=headers)
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("text/csv", csv_resp.content_type)

        # 7. AI Chatbot Advisor API (Expense Reduction Inquiry)
        chat_resp = self.client.post("/api/ai/chat", headers=headers, json={
            "message": "How can I reduce my expenses this month?",
            "history": []
        })
        self.assertEqual(chat_resp.status_code, 200)
        chat_data = chat_resp.get_json()
        self.assertIn("reply", chat_data)
        self.assertIn("suggested_actions", chat_data)
        self.assertIn("Reduction", chat_data["reply"])
        self.assertEqual(chat_data["intent"], "expense_reduction")

        # 8. Local Category Static Images Availability
        for img_name in ["transportation.jpg", "food.jpg", "education.jpg", "housing.jpg", "hero.jpg"]:
            img_resp = self.client.get(f"/static/images/{img_name}")
            self.assertEqual(img_resp.status_code, 200, f"Image {img_name} should return 200 OK")
            img_resp.close()


if __name__ == "__main__":
    unittest.main()
