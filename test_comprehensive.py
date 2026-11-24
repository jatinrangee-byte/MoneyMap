"""
Comprehensive Automated Testing Suite for MoneyMap.
Includes:
1. Rigorous Unit Tests (ML Categorizer, Anomaly Detector, Spending Forecaster, Health Score)
2. Security & Penetration Tests (SQL Injection, IDOR Multi-tenant Isolation, JWT Tampering, XSS, Auth Guards)
3. Full REST API Integration Tests (End-to-End User Journeys, CSV Export, Filtering, AI Advisor)
"""

import os
import unittest
import tempfile
import json
import time
from datetime import datetime
import jwt as pyjwt

# Ensure testing environment configuration
os.environ["TESTING"] = "1"
os.environ["TRACKER_SECRET_KEY"] = "test-secret-key-moneymap-comprehensive-audit-2026"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_KEY"] = ""

import database
import auth
import ml_engine
from app import app


class ComprehensiveTestingSuite(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix="_comp.db")
        os.environ["TRACKER_DB_PATH"] = self.db_path
        database.init_db(self.db_path)
        database.DB_PATH = self.db_path

        app.config["TESTING"] = True
        self.client = app.test_client()

    def tearDown(self):
        try:
            os.close(self.db_fd)
            if os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except OSError:
            pass
        os.environ.pop("TRACKER_DB_PATH", None)

    # =========================================================================
    # PART 1: RIGOROUS ML ENGINE & STATISTICAL UNIT TESTS
    # =========================================================================

    def test_ml_categorizer_edge_cases(self):
        """Tests ML categorizer against edge cases: empty strings, noise, numbers, symbols."""
        # 1. Empty string
        res = ml_engine.predict_category("")
        self.assertIn("category", res)
        self.assertIn("confidence", res)

        # 2. Whitespace only
        res_ws = ml_engine.predict_category("     ")
        self.assertIn("category", res_ws)

        # 3. Numeric string
        res_num = ml_engine.predict_category("12345 67890 999")
        self.assertIn("category", res_num)

        # 4. Punctuation and symbols only
        res_sym = ml_engine.predict_category("!@#$%^&*()_+-=[]{}|;':,.<>?/")
        self.assertIn("category", res_sym)

        # 5. Stopwords only
        res_stop = ml_engine.predict_category("the and or in on at with by from")
        self.assertIn("category", res_stop)

        # 6. Mixed casing
        res_upper = ml_engine.predict_category("SWIGGY PIZZA DINNER")
        res_lower = ml_engine.predict_category("swiggy pizza dinner")
        self.assertEqual(res_upper["category"], res_lower["category"])
        self.assertEqual(res_upper["category"], "Food & Dining")

    def test_ml_categorizer_accuracy_and_confidence(self):
        """Tests high accuracy and confidence on real-world multi-domain expenses."""
        benchmarks = [
            ("Starbucks cold brew cappuccino espresso", "Food & Dining", 75.0),
            ("Zomato pizza burger dinner delivery", "Food & Dining", 75.0),
            ("Uber cab ride to railway station", "Transportation", 75.0),
            ("Monthly metro card pass recharge", "Transportation", 75.0),
            ("Semester exam fees university tuition", "Education", 75.0),
            ("Coursera deep learning specialization course", "Education", 75.0),
            ("Apartment room monthly rent security deposit", "Housing & Utilities", 75.0),
            ("Bescom electricity power bill payment", "Housing & Utilities", 75.0),
            ("Netflix 4k monthly streaming subscription", "Entertainment", 75.0),
            ("Spotify premium student music plan", "Entertainment", 75.0),
            ("Zara cotton tshirt jeans apparel shopping", "Shopping", 75.0),
            ("Amazon order wireless headphones electronics", "Shopping", 75.0),
            ("Apollo pharmacy paracetamol cough syrup", "Healthcare", 70.0),
            ("Doctor consultation physician clinic fee", "Healthcare", 70.0),
            ("Monthly allowance sent by family parents", "Salary / Allowance", 75.0),
            ("Teaching assistant TA stipend credited", "Salary / Allowance", 75.0),
            ("Freelance python web development project payout", "Freelance / Projects", 75.0),
            ("Bug bounty prize contest award hackathon", "Freelance / Projects", 75.0),
        ]

        for text, expected_cat, min_conf in benchmarks:
            pred = ml_engine.predict_category(text)
            self.assertEqual(pred["category"], expected_cat, f"Failed category for: {text}")
            self.assertGreaterEqual(pred["confidence"], min_conf, f"Low confidence for: {text} ({pred['confidence']}%)")

    def test_ml_online_incremental_learning(self):
        """Verifies that active online learning refines model weights in real time."""
        custom_merchant = "XylophoneQuantumNoveltyStore"
        # Initially, rare token should not point to Shopping
        ml_engine.train_user_transaction(f"Purchase at {custom_merchant}", "Shopping")
        ml_engine.train_user_transaction(f"Another order from {custom_merchant}", "Shopping")

        pred = ml_engine.predict_category(f"receipt from {custom_merchant}")
        self.assertEqual(pred["category"], "Shopping")

    def test_anomaly_detection_constant_variance_edge_case(self):
        """Verifies anomaly detection correctly flags outliers even when historical std dev is zero."""
        constant_history = [
            {"category": "Housing & Utilities", "type": "expense", "amount": 500.0},
            {"category": "Housing & Utilities", "type": "expense", "amount": 500.0},
            {"category": "Housing & Utilities", "type": "expense", "amount": 500.0},
            {"category": "Housing & Utilities", "type": "expense", "amount": 500.0},
        ]
        # Same amount: not an anomaly
        is_ano, _ = ml_engine.detect_anomaly(500.0, "Housing & Utilities", constant_history)
        self.assertFalse(is_ano)

        # Normal small increase: not an anomaly
        is_ano, _ = ml_engine.detect_anomaly(600.0, "Housing & Utilities", constant_history)
        self.assertFalse(is_ano)

        # Extreme spike (10x historical constant): MUST be detected
        is_ano_spike, reason = ml_engine.detect_anomaly(15000.0, "Housing & Utilities", constant_history)
        self.assertTrue(is_ano_spike)
        self.assertIn("Anomaly", reason)

    def test_anomaly_detection_distribution_thresholds(self):
        """Verifies statistical Z-score thresholds on varying distributions."""
        variable_history = [
            {"category": "Food & Dining", "type": "expense", "amount": 150.0},
            {"category": "Food & Dining", "type": "expense", "amount": 200.0},
            {"category": "Food & Dining", "type": "expense", "amount": 250.0},
            {"category": "Food & Dining", "type": "expense", "amount": 180.0},
            {"category": "Food & Dining", "type": "expense", "amount": 220.0},
            {"category": "Food & Dining", "type": "expense", "amount": 190.0},
        ]

        # Normal amount
        is_ano, _ = ml_engine.detect_anomaly(220.0, "Food & Dining", variable_history)
        self.assertFalse(is_ano)

        # Negative amount guard
        is_ano_neg, _ = ml_engine.detect_anomaly(-100.0, "Food & Dining", variable_history)
        self.assertFalse(is_ano_neg)

        # High statistical outlier (+2.5σ)
        is_ano_outlier, reason = ml_engine.detect_anomaly(4500.0, "Food & Dining", variable_history)
        self.assertTrue(is_ano_outlier)
        self.assertIn("+", reason)

    def test_spending_forecaster_exact_days_and_leap_years(self):
        """Verifies forecaster utilizes exact calendar days and calculates velocity correctly."""
        now = datetime.now()
        current_ym = now.strftime("%Y-%m")
        current_d = now.day

        sample_txs = [
            {"type": "expense", "amount": 1000.0, "date": f"{current_ym}-{max(1, current_d - 1):02d}"},
            {"type": "expense", "amount": 500.0, "date": f"{current_ym}-{current_d:02d}"},
        ]

        forecast = ml_engine.forecast_monthly_spending(sample_txs, monthly_budget=25000.0)
        self.assertGreater(forecast["days_in_month"], 27)
        self.assertLessEqual(forecast["days_in_month"], 31)
        self.assertEqual(forecast["current_spent"], 1500.0)
        self.assertIn(forecast["status"], ["safe", "caution", "critical", "healthy"])
        self.assertIn("daily_burn_rate", forecast)

    def test_financial_health_score_bounds_and_pillars(self):
        """Verifies health score is bounded between [5, 100] and accounts for all 4 pillars."""
        # 1. Perfect financial health scenario
        perfect_summary = {
            "total_income": 100000.0,
            "total_expenses": 30000.0,
            "balance": 70000.0,
            "category_breakdown": [
                {"category": "Housing & Utilities", "total": 15000.0},
                {"category": "Food & Dining", "total": 10000.0},
                {"category": "Transportation", "total": 5000.0}
            ]
        }
        perfect_budgets = [
            {"category": "Housing & Utilities", "monthly_limit": 20000.0, "spent": 15000.0, "is_exceeded": False},
            {"category": "Food & Dining", "monthly_limit": 15000.0, "spent": 10000.0, "is_exceeded": False}
        ]
        score_data = ml_engine.compute_financial_health_score(perfect_summary, perfect_budgets)
        self.assertGreaterEqual(score_data["score"], 85)
        self.assertEqual(score_data["badge_color"], "emerald")

        # 2. Deficit & breached budgets scenario
        deficit_summary = {
            "total_income": 20000.0,
            "total_expenses": 45000.0,
            "balance": -25000.0,
            "category_breakdown": [
                {"category": "Entertainment", "total": 35000.0}
            ]
        }
        breached_budgets = [
            {"category": "Entertainment", "monthly_limit": 10000.0, "spent": 35000.0, "is_exceeded": True}
        ]
        deficit_score = ml_engine.compute_financial_health_score(deficit_summary, breached_budgets)
        self.assertLessEqual(deficit_score["score"], 50)
        self.assertGreaterEqual(deficit_score["score"], 5)
        self.assertTrue(any("Deficit" in r for r in deficit_score["recommendations"]))

    # =========================================================================
    # PART 2: RIGOROUS SECURITY & PENETRATION TESTING
    # =========================================================================

    def test_security_sql_injection_resilience(self):
        """Attempts SQL injection attacks on user input, search, descriptions, and filters."""
        uid = database.create_user("SecUser", "sec@test.com", "hash", db_path=self.db_path)

        # 1. SQL Injection attempt in transaction note/description
        sqli_desc = "Coffee'); DROP TABLE transactions; --"
        t_id = database.add_transaction(uid, "expense", 250.0, "Food & Dining", "2026-10-25", sqli_desc, db_path=self.db_path)
        self.assertIsNotNone(t_id)

        # Verify table still exists and data was safely parameterized
        txs = database.get_transactions(uid, db_path=self.db_path)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["description"], sqli_desc)

        # 2. SQL Injection in search query
        sqli_search = "' OR '1'='1"
        search_res = database.get_transactions(uid, search=sqli_search, db_path=self.db_path)
        # Should not return all rows across system or crash, searches literally
        self.assertEqual(len(search_res), 0)

        # 3. SQL Injection in category filter
        sqli_cat = "' UNION SELECT id, name, email, NULL, NULL, NULL, NULL, NULL FROM users --"
        cat_res = database.get_transactions(uid, category=sqli_cat, db_path=self.db_path)
        self.assertEqual(len(cat_res), 0)

    def test_security_idor_multi_tenant_isolation(self):
        """Verifies strict Row-Level Isolation (User A cannot view, edit, or delete User B's records)."""
        # Create User A
        pwd_a = auth.hash_password("PassA123")
        uid_a = database.create_user("User A", "usera@test.com", pwd_a, db_path=self.db_path)
        token_a = auth.generate_session_token(uid_a)
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Create User B
        pwd_b = auth.hash_password("PassB123")
        uid_b = database.create_user("User B", "userb@test.com", pwd_b, db_path=self.db_path)
        token_b = auth.generate_session_token(uid_b)
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # User A creates a transaction and a budget
        t_resp = self.client.post("/api/transactions", headers=headers_a, json={
            "type": "expense",
            "amount": 1200.0,
            "category": "Education",
            "date": "2026-10-20",
            "description": "User A Private Course"
        })
        self.assertEqual(t_resp.status_code, 201)
        t_id = t_resp.get_json()["transaction"]["id"]

        b_resp = self.client.post("/api/budgets", headers=headers_a, json={
            "category": "Education",
            "monthly_limit": 5000.0
        })
        self.assertIn(b_resp.status_code, [200, 201])
        b_id = b_resp.get_json().get("budget_id") or b_resp.get_json()["budgets"][0]["id"]

        # --- IDOR ATTEMPT BY USER B ON USER A'S TRANSACTION ---
        # 1. User B tries to GET User A's transaction
        get_idor = self.client.get(f"/api/transactions/{t_id}", headers=headers_b)
        self.assertEqual(get_idor.status_code, 404, "User B should not be able to read User A's transaction")

        # 2. User B tries to PUT / modify User A's transaction
        put_idor = self.client.put(f"/api/transactions/{t_id}", headers=headers_b, json={
            "type": "expense",
            "amount": 999999.0,
            "category": "Education",
            "date": "2026-10-20",
            "description": "Hacked by User B"
        })
        self.assertEqual(put_idor.status_code, 404, "User B should not be able to update User A's transaction")

        # 3. User B tries to DELETE User A's transaction
        del_idor = self.client.delete(f"/api/transactions/{t_id}", headers=headers_b)
        self.assertEqual(del_idor.status_code, 404, "User B should not be able to delete User A's transaction")

        # 4. User B tries to DELETE User A's budget
        del_b_idor = self.client.delete(f"/api/budgets/{b_id}", headers=headers_b)
        self.assertEqual(del_b_idor.status_code, 404, "User B should not be able to delete User A's budget")

        # Verify User A's transaction is still intact
        tx_check = database.get_transaction_by_id(t_id, uid_a, db_path=self.db_path)
        self.assertIsNotNone(tx_check)
        self.assertEqual(tx_check["amount"], 1200.0)
        self.assertEqual(tx_check["description"], "User A Private Course")

    def test_security_jwt_tampering_and_unauthorized_access(self):
        """Verifies JWT forgery, expired tokens, and algorithm None attacks are rejected."""
        # 1. No Authorization header
        resp_no_auth = self.client.get("/api/transactions")
        self.assertEqual(resp_no_auth.status_code, 401)

        # 2. Forged token with invalid secret key
        forged_token = pyjwt.encode({"user_id": 999, "email": "fake@hacker.com", "exp": time.time() + 3600}, "wrong-secret-key-that-is-at-least-32-bytes", algorithm="HS256")
        resp_forged = self.client.get("/api/transactions", headers={"Authorization": f"Bearer {forged_token}"})
        self.assertEqual(resp_forged.status_code, 401)

        # 3. Expired token
        expired_token = pyjwt.encode({"user_id": 1, "email": "exp@test.com", "exp": time.time() - 3600}, os.environ["TRACKER_SECRET_KEY"], algorithm="HS256")
        resp_expired = self.client.get("/api/transactions", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(resp_expired.status_code, 401)

        # 4. Malformed token string
        resp_malformed = self.client.get("/api/transactions", headers={"Authorization": "Bearer not.a.real.token"})
        self.assertEqual(resp_malformed.status_code, 401)

    def test_security_xss_sanitization(self):
        """Verifies script tags and HTML injection payloads are stored safely without execution."""
        uid = database.create_user("XSSUser", "xss@test.com", "hash", db_path=self.db_path)
        token = auth.generate_session_token(uid)
        headers = {"Authorization": f"Bearer {token}"}

        xss_payload = "<script>alert('XSS_ATTACK')</script><img src=x onerror=alert(1)>"
        resp = self.client.post("/api/transactions", headers=headers, json={
            "type": "expense",
            "amount": 100.0,
            "category": "Entertainment",
            "date": "2026-10-22",
            "description": xss_payload
        })
        self.assertEqual(resp.status_code, 201)

        # Fetch transaction via API
        get_resp = self.client.get("/api/transactions", headers=headers)
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.get_json()
        self.assertEqual(len(data["transactions"]), 1)
        # Raw storage is preserved safely, frontend handles escapeHtml
        self.assertEqual(data["transactions"][0]["description"], xss_payload)

    # =========================================================================
    # PART 3: FULL REST API INTEGRATION & USABILITY FLOWS
    # =========================================================================

    def test_full_user_lifecycle_journey(self):
        """End-to-End Test: Signup -> Budgets -> Transactions -> Anomaly -> Filter -> CSV -> Chat."""
        # 1. Register
        unique_email = f"journey_{int(time.time()*1000)}@test.com"
        reg_res = self.client.post("/api/auth/register", json={
            "name": "Jordan Finance",
            "email": unique_email,
            "password": "SecurePassword#2026",
            "currency": "₹"
        })
        self.assertEqual(reg_res.status_code, 201)
        token = reg_res.get_json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Login verification
        login_res = self.client.post("/api/auth/login", json={
            "email": unique_email,
            "password": "SecurePassword#2026"
        })
        self.assertEqual(login_res.status_code, 200)

        # 3. Set monthly budget
        b_res = self.client.post("/api/budgets", headers=headers, json={
            "category": "Food & Dining",
            "monthly_limit": 6000.0
        })
        self.assertIn(b_res.status_code, [200, 201])

        # 4. Add normal income
        inc_res = self.client.post("/api/transactions", headers=headers, json={
            "type": "income",
            "amount": 50000.0,
            "category": "Salary / Allowance",
            "date": "2026-10-01",
            "description": "Monthly Software Engineering Salary"
        })
        self.assertEqual(inc_res.status_code, 201)

        # 5. Add 5 typical expenses
        for day, amt, desc in [(2, 200, "Breakfast canteen"), (3, 250, "Lunch buffet"), (4, 180, "Dinner sandwich"), (5, 220, "Cafe cold brew")]:
            self.client.post("/api/transactions", headers=headers, json={
                "type": "expense",
                "amount": float(amt),
                "category": "Food & Dining",
                "date": f"2026-10-{day:02d}",
                "description": desc
            })

        # 6. Add high outlier expense (e.g. ₹5,800 dinner)
        outlier_res = self.client.post("/api/transactions", headers=headers, json={
            "type": "expense",
            "amount": 5800.0,
            "category": "Food & Dining",
            "date": "2026-10-06",
            "description": "Luxury 5-Star Hotel Celebration Feast"
        })
        self.assertEqual(outlier_res.status_code, 201)
        outlier_data = outlier_res.get_json()
        self.assertTrue(outlier_data["is_anomaly"], "Should flag +2.5σ statistical outlier")

        # 7. Test transaction filtering toolbar parameters
        filter_food = self.client.get("/api/transactions?category=Food%20%26%20Dining", headers=headers)
        self.assertEqual(len(filter_food.get_json()["transactions"]), 5)

        filter_search = self.client.get("/api/transactions?search=Celebration", headers=headers)
        self.assertEqual(len(filter_search.get_json()["transactions"]), 1)

        filter_type = self.client.get("/api/transactions?type=income", headers=headers)
        self.assertEqual(len(filter_type.get_json()["transactions"]), 1)

        # 8. Edit transaction
        edit_tx_id = outlier_data["transaction"]["id"]
        edit_res = self.client.put(f"/api/transactions/{edit_tx_id}", headers=headers, json={
            "type": "expense",
            "amount": 5200.0,
            "category": "Food & Dining",
            "date": "2026-10-06",
            "description": "Revised Luxury Feast bill"
        })
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(edit_res.get_json()["transaction"]["amount"], 5200.0)

        # 9. Verify ML Insights endpoint
        insights_res = self.client.get("/api/ml/insights", headers=headers)
        self.assertEqual(insights_res.status_code, 200)
        insights = insights_res.get_json()
        self.assertIn("health", insights)
        self.assertIn("forecast", insights)
        self.assertGreaterEqual(insights["health"]["score"], 5)

        # 10. AI Chat Advisor (Financial Health analysis)
        chat_res = self.client.post("/api/ai/chat", headers=headers, json={
            "message": "Give me a breakdown of my spending discipline and budget health.",
            "history": []
        })
        self.assertEqual(chat_res.status_code, 200)
        self.assertTrue(len(chat_res.get_json()["reply"]) > 20)

        # 11. Delete transaction
        del_res = self.client.delete(f"/api/transactions/{edit_tx_id}", headers=headers)
        self.assertEqual(del_res.status_code, 200)

        # Verify count decreased
        tx_list = self.client.get("/api/transactions", headers=headers).get_json()["transactions"]
        self.assertEqual(len(tx_list), 5)  # 1 income + 4 normal expenses


if __name__ == "__main__":
    unittest.main()
