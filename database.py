"""
Database layer for Personal Expense Tracker.
Supports both Supabase PostgreSQL (via PostgREST with Row Level Security)
and SQLite (local development / testing fallback).
"""

import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Any, List, Optional, Dict

import supabase_client

try:
    from flask import has_request_context, request
except ImportError:
    has_request_context = lambda: False
    request = None


def _get_current_jwt(explicit_jwt: Optional[str] = None) -> Optional[str]:
    """Retrieves current authenticated user's JWT from explicit arg or Flask context."""
    if explicit_jwt:
        return explicit_jwt
    if has_request_context() and request:
        return getattr(request, "user_token", None)
    return None


# ---------------- SQLITE CONFIGURATION & HELPERS ----------------

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")


def get_db_path() -> str:
    """Returns database path, ensuring writable /tmp location in serverless environments."""
    if os.environ.get("VERCEL") or not os.access(os.path.dirname(os.path.abspath(__file__)), os.W_OK):
        tmp_db = os.environ.get("TRACKER_DB_PATH", "/tmp/tracker.db")
        if not os.path.exists(tmp_db) and os.path.exists(DEFAULT_DB_PATH):
            try:
                shutil.copy2(DEFAULT_DB_PATH, tmp_db)
            except Exception:
                pass
        return tmp_db
    return os.environ.get("TRACKER_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a connection to the SQLite database with Row factory enabled and performance pragmas."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    # Performance tweaks for local dev / serverless environments
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=OFF;')
    conn.execute('PRAGMA cache_size=100000;')
    conn.execute('PRAGMA temp_store=MEMORY;')
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn
    """Returns a connection to the SQLite database with Row factory enabled."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes the SQLite database schema if tables do not exist."""
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
    conn.close()


# ---------------- USER CRUD ----------------

def create_user(name: str, email: str, password_hash: str, currency: str = '₹', db_path: Optional[str] = None):
    """Inserts a new user in SQLite (local dev mode)."""
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


def get_user_by_email(email: str, db_path: Optional[str] = None):
    """Retrieves a user record by email from SQLite."""
    conn = get_db_connection(db_path)
    user = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.strip().lower(),)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Retrieves user profile by ID (Supabase profiles or SQLite users)."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        try:
            client = supabase_client.get_supabase_client(token)
            res = client.table("profiles").select("id, name, email, currency, created_at").eq("id", str(user_id)).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # SQLite fallback
    conn = get_db_connection(db_path)
    user = conn.execute(
        "SELECT id, name, email, currency, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(user) if user else None


def update_user_currency(user_id, currency: str, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Updates user preferred currency symbol."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        try:
            client = supabase_client.get_supabase_client(token)
            client.table("profiles").update({"currency": currency}).eq("id", str(user_id)).execute()
            return True
        except Exception:
            pass

    # SQLite fallback
    conn = get_db_connection(db_path)
    with conn:
        conn.execute("UPDATE users SET currency = ? WHERE id = ?", (currency, user_id))
    conn.close()
    return True


# ---------------- TRANSACTION CRUD ----------------

def add_transaction(user_id, type_, amount, category, date, description="", is_anomaly=0, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Adds a new transaction record."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        payload = {
            "user_id": str(user_id),
            "type": type_,
            "amount": float(amount),
            "category": category.strip(),
            "date": str(date),
            "description": (description or "").strip(),
        }
        try:
            res = client.table("transactions").insert(payload).execute()
            if res.data:
                return res.data[0].get("id")
        except Exception as e:
            err_str = str(e)
            # Fall back to 'note' if schema uses 'note' instead of 'description'
            if "description" in err_str:
                alt_payload = {
                    "user_id": str(user_id),
                    "type": type_,
                    "amount": float(amount),
                    "category": category.strip(),
                    "date": str(date),
                    "note": (description or "").strip(),
                }
                res = client.table("transactions").insert(alt_payload).execute()
                if res.data:
                    return res.data[0].get("id")
            raise

    # SQLite fallback
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


def get_transactions(user_id, category=None, type_=None, start_date=None, end_date=None, search=None, limit=None, offset=None, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Fetches transactions with optional filtering and pagination."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        q = client.table("transactions").select("*").eq("user_id", str(user_id))
        if category and category != "all":
            q = q.eq("category", category)
        if type_ and type_ != "all":
            q = q.eq("type", type_)
        if start_date:
            q = q.gte("date", start_date)
        if end_date:
            q = q.lte("date", end_date)
        if search:
            q = q.ilike("description", f"%{search.strip()}%")

        q = q.order("date", desc=True).order("id", desc=True)
        if limit is not None:
            start = int(offset or 0)
            end = start + int(limit) - 1
            q = q.range(start, end)
        res = q.execute()
        rows = res.data or []
        for r in rows:
            r.setdefault("is_anomaly", 0)
            r.setdefault("description", r.get("note", ""))
        return rows

    # SQLite fallback
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


def get_transaction_by_id(transaction_id, user_id, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Gets a specific transaction by ID belonging to user_id."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        res = client.table("transactions").select("*").eq("id", transaction_id).eq("user_id", str(user_id)).execute()
        if res.data:
            row = res.data[0]
            row.setdefault("is_anomaly", 0)
            row.setdefault("description", row.get("note", ""))
            return row
        return None

    # SQLite fallback
    conn = get_db_connection(db_path)
    row = conn.execute(
        "SELECT * FROM transactions WHERE id = ? AND user_id = ?",
        (transaction_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_transaction(transaction_id, user_id, type_, amount, category, date, description="", is_anomaly=0, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Updates an existing transaction."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        payload = {
            "type": type_,
            "amount": float(amount),
            "category": category.strip(),
            "date": str(date),
            "description": (description or "").strip(),
        }
        try:
            res = client.table("transactions").update(payload).eq("id", transaction_id).eq("user_id", str(user_id)).execute()
            return bool(res.data)
        except Exception as e:
            err_str = str(e)
            if "description" in err_str:
                alt_payload = {
                    "type": type_,
                    "amount": float(amount),
                    "category": category.strip(),
                    "date": str(date),
                    "note": (description or "").strip(),
                }
                res = client.table("transactions").update(alt_payload).eq("id", transaction_id).eq("user_id", str(user_id)).execute()
                return bool(res.data)
            raise

    # SQLite fallback
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


def delete_transaction(transaction_id, user_id, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Deletes a transaction."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        res = client.table("transactions").delete().eq("id", transaction_id).eq("user_id", str(user_id)).execute()
        return bool(res.data)

    # SQLite fallback
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

def set_budget(user_id, category, monthly_limit, month_year=None, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Sets or updates a monthly budget for a category."""
    if not month_year:
        month_year = datetime.now().strftime("%Y-%m")

    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        payload = {
            "user_id": str(user_id),
            "category": category.strip(),
            "monthly_limit": float(monthly_limit),
            "month_year": month_year
        }
        res = client.table("budgets").upsert(payload, on_conflict="user_id,category,month_year").execute()
        return res.data[0].get("id") if res.data else True

    # SQLite fallback
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


def get_budgets(user_id, month_year=None, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Gets all budgets for a user in a given month, with actual spend calculated."""
    if not month_year:
        month_year = datetime.now().strftime("%Y-%m")

    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        b_res = client.table("budgets").select("*").eq("user_id", str(user_id)).eq("month_year", month_year).execute()
        # Expenses for this month
        t_query = client.table("transactions").select("category, amount").eq("user_id", str(user_id)).eq("type", "expense")
        if month_year and len(month_year) == 7:
            try:
                import calendar
                y, m = map(int, month_year.split("-"))
                last_day = calendar.monthrange(y, m)[1]
                t_query = t_query.gte("date", f"{month_year}-01").lte("date", f"{month_year}-{last_day:02d}")
            except Exception:
                pass
        t_res = t_query.execute()

        spend_map = {}
        for row in (t_res.data or []):
            cat = row["category"]
            spend_map[cat] = spend_map.get(cat, 0.0) + float(row["amount"])

        result = []
        for b in (b_res.data or []):
            cat = b["category"]
            limit = float(b["monthly_limit"])
            spent = spend_map.get(cat, 0.0)
            b["spent"] = spent
            b["remaining"] = max(0.0, limit - spent)
            b["percentage"] = round((spent / limit * 100), 1) if limit > 0 else 0
            b["is_exceeded"] = spent > limit
            result.append(b)
        return result

    # SQLite fallback
    conn = get_db_connection(db_path)
    budget_rows = conn.execute(
        "SELECT * FROM budgets WHERE user_id = ? AND month_year = ?",
        (user_id, month_year)
    ).fetchall()

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


def delete_budget(budget_id, user_id, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Deletes a budget entry."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        res = client.table("budgets").delete().eq("id", budget_id).eq("user_id", str(user_id)).execute()
        return bool(res.data)

    # SQLite fallback
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

def get_financial_summary(user_id, month_year=None, db_path: Optional[str] = None, jwt: Optional[str] = None):
    """Calculates overall totals, category distribution, and cash flow."""
    token = _get_current_jwt(jwt)
    if supabase_client.is_supabase_enabled() and token:
        client = supabase_client.get_supabase_client(token)
        q = client.table("transactions").select("*").eq("user_id", str(user_id))
        if month_year and len(month_year) == 7:
            try:
                import calendar
                y, m = map(int, month_year.split("-"))
                last_day = calendar.monthrange(y, m)[1]
                q = q.gte("date", f"{month_year}-01").lte("date", f"{month_year}-{last_day:02d}")
            except Exception:
                pass
        q = q.order("date", desc=False)
        res = q.execute()
        rows = res.data or []

        total_income = 0.0
        total_expenses = 0.0
        cat_map = {}
        daily_map = {}

        for r in rows:
            amt = float(r["amount"])
            d = str(r["date"])
            if d not in daily_map:
                daily_map[d] = {"income": 0.0, "expense": 0.0}

            if r["type"] == "income":
                total_income += amt
                daily_map[d]["income"] += amt
            else:
                total_expenses += amt
                daily_map[d]["expense"] += amt
                cat = r["category"]
                if cat not in cat_map:
                    cat_map[cat] = {"total": 0.0, "count": 0}
                cat_map[cat]["total"] += amt
                cat_map[cat]["count"] += 1

        balance = total_income - total_expenses
        savings_rate = round(((balance / total_income) * 100), 1) if total_income > 0 else 0.0

        category_breakdown = [
            {"category": k, "total": v["total"], "count": v["count"]}
            for k, v in sorted(cat_map.items(), key=lambda item: item[1]["total"], reverse=True)
        ]

        daily_timeline = [
            {"date": d, "income": v["income"], "expense": v["expense"]}
            for d, v in sorted(daily_map.items(), key=lambda item: item[0])
        ]

        return {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "balance": balance,
            "savings_rate": savings_rate,
            "transaction_count": len(rows),
            "category_breakdown": category_breakdown,
            "daily_timeline": daily_timeline
        }

    # SQLite fallback
    conn = get_db_connection(db_path)
    if month_year:
        date_filter = "AND date LIKE ?"
        date_params = (f"{month_year}%",)
    else:
        date_filter = ""
        date_params = ()

    totals = conn.execute(f"""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS total_income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS total_expenses,
            COUNT(*) AS transaction_count
        FROM transactions
        WHERE user_id = ? {date_filter}
    """, (user_id, *date_params)).fetchone()

    total_income = float(totals["total_income"])
    total_expenses = float(totals["total_expenses"])
    balance = total_income - total_expenses
    savings_rate = round(((balance / total_income) * 100), 1) if total_income > 0 else 0.0

    category_rows = conn.execute(f"""
        SELECT category, SUM(amount) as total, COUNT(*) as count
        FROM transactions
        WHERE user_id = ? AND type = 'expense' {date_filter}
        GROUP BY category
        ORDER BY total DESC
    """, (user_id, *date_params)).fetchall()

    category_breakdown = [
        {"category": r["category"], "total": float(r["total"]), "count": r["count"]}
        for r in category_rows
    ]

    daily_rows = conn.execute(f"""
        SELECT date,
               COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
               COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
        FROM transactions
        WHERE user_id = ? {date_filter}
        GROUP BY date
        ORDER BY date ASC
    """, (user_id, *date_params)).fetchall()

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
