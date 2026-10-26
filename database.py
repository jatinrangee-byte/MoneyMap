"""
Database layer for Personal Expense Tracker.
Handles SQLite schema creation, migrations, and CRUD operations.
"""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")


def get_db_path():
    """Returns database path, ensuring writable /tmp location in serverless (e.g. Vercel)."""
    if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.abspath(__file__)), os.W_OK):
        tmp_db = os.environ.get("TRACKER_DB_PATH", "/tmp/tracker.db")
        if not os.path.exists(tmp_db) and os.path.exists(DEFAULT_DB_PATH):
            try:
                shutil.copy2(DEFAULT_DB_PATH, tmp_db)
            except Exception:
                pass
        return tmp_db
    return os.environ.get("TRACKER_DB_PATH", DEFAULT_DB_PATH)


DB_PATH = get_db_path()


def get_db_connection(db_path=None):
    """Returns a connection to the SQLite database with Row factory enabled."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=None):
    """Initializes the database schema if tables do not exist."""
    path = db_path or get_db_path()
    conn = get_db_connection(path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                currency TEXT DEFAULT '₹',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL CHECK(amount > 0),
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                is_anomaly INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL CHECK(monthly_limit >= 0),
                month_year TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, category, month_year)
            )
        """)
        
        # Indexes for fast querying
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_user_date ON transactions(user_id, date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_user_cat ON transactions(user_id, category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id, month_year)")

        # Ensure demo user exists
        demo_user = conn.execute("SELECT id FROM users WHERE email = 'demo@moneymap.io'").fetchone()
        demo_user_id = None
        if not demo_user:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, currency) VALUES (?, ?, ?, ?)",
                ("Alex Sharma", "demo@moneymap.io", "f384560cf382b401d9591b701b68774b$52c60be35264ac3dcf603d6e18c6ea668d1e8959f909298a949123f895561ecf", "₹")
            )
            demo_user_id = cursor.lastrowid
    conn.close()

    if demo_user_id:
        seed_demo_data(demo_user_id, db_path=path)


# ---------------- USER CRUD ----------------

def create_user(name, email, password_hash, currency='₹', db_path=None):
    """Inserts a new user and returns their user_id."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO users (name, email, password_hash, currency) VALUES (?, ?, ?, ?)",
                (name.strip(), email.strip().lower(), password_hash, currency)
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email, db_path=None):
    """Retrieves a user record by email."""
    conn = get_db_connection(db_path)
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id, db_path=None):
    """Retrieves a user record by user_id."""
    conn = get_db_connection(db_path)
    user = conn.execute(
        "SELECT id, name, email, currency, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def update_user_currency(user_id, currency, db_path=None):
    """Updates user's preferred currency symbol."""
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("UPDATE users SET currency = ? WHERE id = ?", (currency, user_id))
    conn.close()


# ---------------- TRANSACTION CRUD ----------------

def add_transaction(user_id, type_, amount, category, date, description="", is_anomaly=0, db_path=None):
    """Adds a new transaction record."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO transactions (user_id, type, amount, category, date, description, is_anomaly)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, type_, float(amount), category.strip(), date, (description or "").strip(), int(is_anomaly))
        )
        t_id = cursor.lastrowid
    conn.close()
    return t_id


def get_transactions(user_id, category=None, type_=None, start_date=None, end_date=None, search=None, limit=None, offset=None, db_path=None):
    """Fetches transactions with optional filters."""
    conn = get_db_connection(db_path)
    query = "SELECT * FROM transactions WHERE user_id = ?"
    params = [user_id]

    if category and category != 'all':
        query += " AND category = ?"
        params.append(category)

    if type_ and type_ != 'all':
        query += " AND type = ?"
        params.append(type_)

    if start_date:
        query += " AND date >= ?"
        params.append(start_date)

    if end_date:
        query += " AND date <= ?"
        params.append(end_date)

    if search:
        query += " AND (description LIKE ? OR category LIKE ?)"
        term = f"%{search.strip()}%"
        params.extend([term, term])

    query += " ORDER BY date DESC, id DESC"

    if limit is not None:
        query += " LIMIT ?"
        params.append(int(limit))
        if offset is not None:
            query += " OFFSET ?"
            params.append(int(offset))

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_transaction_by_id(transaction_id, user_id, db_path=None):
    """Gets a specific transaction by ID belonging to user_id."""
    conn = get_db_connection(db_path)
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_transaction(transaction_id, user_id, type_, amount, category, date, description="", is_anomaly=0, db_path=None):
    """Updates an existing transaction."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            """
            UPDATE transactions
            SET type = ?, amount = ?, category = ?, date = ?, description = ?, is_anomaly = ?
            WHERE id = ? AND user_id = ?
            """,
            (type_, float(amount), category.strip(), date, (description or "").strip(), int(is_anomaly), transaction_id, user_id)
        )
        updated = cursor.rowcount > 0
    conn.close()
    return updated


def delete_transaction(transaction_id, user_id, db_path=None):
    """Deletes a transaction."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (transaction_id, user_id)
        )
        deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ---------------- BUDGET CRUD ----------------

def set_budget(user_id, category, monthly_limit, month_year=None, db_path=None):
    """Sets or updates a monthly budget for a category."""
    if not month_year:
        month_year = datetime.now().strftime("%Y-%m")
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO budgets (user_id, category, monthly_limit, month_year)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, category, month_year)
            DO UPDATE SET monthly_limit = excluded.monthly_limit
            """,
            (user_id, category.strip(), float(monthly_limit), month_year)
        )
        budget_id = cursor.lastrowid
    conn.close()
    return budget_id


def get_budgets(user_id, month_year=None, db_path=None):
    """Gets all budgets for a user in a given month, with actual spend calculated."""
    if not month_year:
        month_year = datetime.now().strftime("%Y-%m")

    conn = get_db_connection(db_path)
    
    # Fetch budgets
    budget_rows = conn.execute(
        "SELECT * FROM budgets WHERE user_id = ? AND month_year = ?",
        (user_id, month_year)
    ).fetchall()

    # Calculate actual spending per category for this month
    spend_rows = conn.execute(
        """
        SELECT category, SUM(amount) as total_spent
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND date LIKE ?
        GROUP BY category
        """,
        (user_id, f"{month_year}%")
    ).fetchall()
    conn.close()

    spend_map = {r["category"]: float(r["total_spent"]) for r in spend_rows}
    result = []
    for b in budget_rows:
        b_dict = dict(b)
        spent = spend_map.get(b_dict["category"], 0.0)
        b_dict["spent"] = spent
        b_dict["remaining"] = max(0.0, b_dict["monthly_limit"] - spent)
        b_dict["percentage"] = round((spent / b_dict["monthly_limit"] * 100), 1) if b_dict["monthly_limit"] > 0 else 0
        b_dict["is_exceeded"] = spent > b_dict["monthly_limit"]
        result.append(b_dict)
    return result


def delete_budget(budget_id, user_id, db_path=None):
    """Deletes a budget entry."""
    conn = get_db_connection(db_path)
    with conn:
        cursor = conn.execute(
            "DELETE FROM budgets WHERE id = ? AND user_id = ?",
            (budget_id, user_id)
        )
        deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ---------------- AGGREGATION & SUMMARY ----------------

def get_financial_summary(user_id, month_year=None, db_path=None):
    """Calculates overall totals, category distribution, and cash flow."""
    conn = get_db_connection(db_path)

    # Date filter: default to current month if specified, or all-time if None
    date_filter = f"AND date LIKE '{month_year}%'" if month_year else ""

    # Totals
    totals = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expenses,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE user_id = ? {date_filter}
    """, (user_id,)).fetchone()

    total_income = float(totals["total_income"])
    total_expenses = float(totals["total_expenses"])
    balance = total_income - total_expenses
    savings_rate = round(((balance / total_income) * 100), 1) if total_income > 0 else 0.0

    # Expense by category
    category_rows = conn.execute(f"""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE user_id = ? AND type = 'expense' {date_filter}
        GROUP BY category
        ORDER BY total DESC
    """, (user_id,)).fetchall()

    category_breakdown = [
        {"category": r["category"], "total": float(r["total"]), "count": r["count"]}
        for r in category_rows
    ]

    # Daily breakdown for spending chart
    daily_rows = conn.execute(f"""
        SELECT date,
               COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
               COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
        FROM transactions
        WHERE user_id = ? {date_filter}
        GROUP BY date
        ORDER BY date ASC
    """, (user_id,)).fetchall()

    daily_timeline = [
        {"date": r["date"], "income": float(r["income"]), "expense": float(r["expense"])}
        for r in daily_rows
    ]

    conn.close()
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "savings_rate": savings_rate,
        "transaction_count": totals["transaction_count"],
        "category_breakdown": category_breakdown,
        "daily_timeline": daily_timeline
    }


# ---------------- SEED DEMO DATA ----------------

def seed_demo_data(user_id, db_path=None):
    """
    Populates realistic sample transactions and category budgets.
    Includes normal expenses + 1 or 2 anomalies for demonstration of ML models.
    """
    conn = get_db_connection(db_path)
    now = datetime.now()

    # Clear previous transactions for fresh demo
    with conn:
        conn.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM budgets WHERE user_id = ?", (user_id,))
    conn.close()

    current_month = now.strftime("%Y-%m")

    # Sample demo transactions
    demo_records = [
        # Incomes
        ("income", 25000.0, "Salary / Allowance", (now - timedelta(days=24)).strftime("%Y-%m-%d"), "Monthly income transfer", 0),
        ("income", 8000.0, "Salary / Allowance", (now - timedelta(days=15)).strftime("%Y-%m-%d"), "Consulting & research honorarium", 0),
        ("income", 3500.0, "Freelance / Projects", (now - timedelta(days=7)).strftime("%Y-%m-%d"), "Freelance Python web development task", 0),

        # Education & Courses
        ("expense", 4200.0, "Education", (now - timedelta(days=23)).strftime("%Y-%m-%d"), "Professional certification fee and course manual", 0),
        ("expense", 1250.0, "Education", (now - timedelta(days=19)).strftime("%Y-%m-%d"), "Machine Learning reference textbook", 0),
        ("expense", 450.0, "Education", (now - timedelta(days=12)).strftime("%Y-%m-%d"), "Notebook and stationary set", 0),
        ("expense", 950.0, "Education", (now - timedelta(days=4)).strftime("%Y-%m-%d"), "Online Deep Learning subscription", 0),

        # Food & Dining
        ("expense", 280.0, "Food & Dining", (now - timedelta(days=22)).strftime("%Y-%m-%d"), "Lunch with teammates", 0),
        ("expense", 650.0, "Food & Dining", (now - timedelta(days=20)).strftime("%Y-%m-%d"), "Dominos pizza study group meetup", 0),
        ("expense", 180.0, "Food & Dining", (now - timedelta(days=18)).strftime("%Y-%m-%d"), "Starbucks cold brew coffee", 0),
        ("expense", 120.0, "Food & Dining", (now - timedelta(days=16)).strftime("%Y-%m-%d"), "Cafeteria breakfast", 0),
        ("expense", 420.0, "Food & Dining", (now - timedelta(days=14)).strftime("%Y-%m-%d"), "Swiggy dinner order", 0),
        ("expense", 240.0, "Food & Dining", (now - timedelta(days=11)).strftime("%Y-%m-%d"), "Evening cafe snacks and juices", 0),
        ("expense", 780.0, "Food & Dining", (now - timedelta(days=9)).strftime("%Y-%m-%d"), "Weekend team lunch after hackathon", 0),
        ("expense", 150.0, "Food & Dining", (now - timedelta(days=6)).strftime("%Y-%m-%d"), "Chai and snacks break", 0),
        ("expense", 510.0, "Food & Dining", (now - timedelta(days=3)).strftime("%Y-%m-%d"), "Zomato dinner delivery", 0),
        ("expense", 320.0, "Food & Dining", (now - timedelta(days=1)).strftime("%Y-%m-%d"), "Grocery essentials and milk at mart", 0),
        # Anomaly in Food: Outlier expense ($4,800 dining bill)
        ("expense", 4800.0, "Food & Dining", (now - timedelta(days=5)).strftime("%Y-%m-%d"), "Fancy 5-star birthday treat for 8 friends", 1),

        # Transportation
        ("expense", 600.0, "Transportation", (now - timedelta(days=21)).strftime("%Y-%m-%d"), "Monthly metro card recharge", 0),
        ("expense", 180.0, "Transportation", (now - timedelta(days=17)).strftime("%Y-%m-%d"), "Uber auto ride across city", 0),
        ("expense", 240.0, "Transportation", (now - timedelta(days=10)).strftime("%Y-%m-%d"), "Ola cab ride back from project meetup", 0),
        ("expense", 150.0, "Transportation", (now - timedelta(days=2)).strftime("%Y-%m-%d"), "Bus ticket to tech hub", 0),

        # Housing & Utilities
        ("expense", 8500.0, "Housing & Utilities", (now - timedelta(days=24)).strftime("%Y-%m-%d"), "Monthly apartment accommodation rent", 0),
        ("expense", 999.0, "Housing & Utilities", (now - timedelta(days=15)).strftime("%Y-%m-%d"), "High speed Wi-Fi internet broadband", 0),
        ("expense", 399.0, "Housing & Utilities", (now - timedelta(days=8)).strftime("%Y-%m-%d"), "Mobile recharge 5G data plan", 0),

        # Entertainment
        ("expense", 499.0, "Entertainment", (now - timedelta(days=20)).strftime("%Y-%m-%d"), "Netflix monthly subscription", 0),
        ("expense", 350.0, "Entertainment", (now - timedelta(days=13)).strftime("%Y-%m-%d"), "IMAX Movie ticket with friends", 0),
        ("expense", 199.0, "Entertainment", (now - timedelta(days=7)).strftime("%Y-%m-%d"), "Spotify Premium subscription", 0),

        # Shopping
        ("expense", 1499.0, "Shopping", (now - timedelta(days=18)).strftime("%Y-%m-%d"), "Casual sneakers on sale", 0),
        ("expense", 899.0, "Shopping", (now - timedelta(days=6)).strftime("%Y-%m-%d"), "Ergonomic laptop stand for coding", 0),

        # Healthcare
        ("expense", 350.0, "Healthcare", (now - timedelta(days=16)).strftime("%Y-%m-%d"), "Vitamins and first aid medicine", 0),
        ("expense", 600.0, "Healthcare", (now - timedelta(days=8)).strftime("%Y-%m-%d"), "Dental routine checkup", 0),
    ]

    for item in demo_records:
        add_transaction(user_id, item[0], item[1], item[2], item[3], item[4], item[5], db_path=db_path)

    # Budgets for demo
    budgets = [
        ("Food & Dining", 6000.0),
        ("Education", 8000.0),
        ("Housing & Utilities", 11000.0),
        ("Transportation", 2000.0),
        ("Entertainment", 1500.0),
        ("Shopping", 3000.0),
        ("Healthcare", 1500.0),
    ]

    for cat, lim in budgets:
        set_budget(user_id, cat, lim, month_year=current_month, db_path=db_path)

    return True
