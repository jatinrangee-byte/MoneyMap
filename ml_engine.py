"""
Machine Learning & Analytics Engine for Personal Expense Tracker.
Core Machine Learning Modules:
1. NLP Smart Categorizer (Multinomial Naive Bayes with Laplace smoothing)
2. Spending Forecast & Trend Predictor (Time-series burn rate & linear regression)
3. Statistical Outlier / Anomaly Detector (Z-Score and IQR thresholds)
4. AI Financial Health Score & Smart Advisor Engine
"""

import math
import re
from datetime import datetime
from collections import defaultdict

# Pre-defined category taxonomy
CATEGORIES = [
    "Food & Dining",
    "Transportation",
    "Education",
    "Housing & Utilities",
    "Entertainment",
    "Shopping",
    "Healthcare",
    "Salary / Allowance",
    "Freelance / Projects"
]

# Comprehensive training corpus for personal finances
TRAINING_DATA = [
    # Food & Dining
    ("college canteen lunch meal plate", "Food & Dining"),
    ("canteen samosa chai tea coffee snacks", "Food & Dining"),
    ("dominos cheese burst pizza order swiggy", "Food & Dining"),
    ("zomato food delivery dinner burger king", "Food & Dining"),
    ("starbucks cold brew cappuccino espresso", "Food & Dining"),
    ("mcdonalds burger fries coke meal", "Food & Dining"),
    ("subway sandwich salad lunch", "Food & Dining"),
    ("grocery store vegetables fruits milk bread eggs", "Food & Dining"),
    ("supermarket provisions snacks biscuits", "Food & Dining"),
    ("restaurant family dinner buffet dining", "Food & Dining"),
    ("hostel mess food monthly coupon bill", "Food & Dining"),
    ("ice cream parlor waffle dessert pastry", "Food & Dining"),
    ("juice bar fresh juice shake smoothie", "Food & Dining"),
    ("shawarma roll street food momos kathi roll", "Food & Dining"),
    ("dosa idli south indian restaurant breakfast", "Food & Dining"),
    ("biryani chicken rice feast hotel", "Food & Dining"),

    # Transportation
    ("monthly metro card smart recharge", "Transportation"),
    ("uber auto taxi cab ride to campus", "Transportation"),
    ("ola ride cab fare to railway station", "Transportation"),
    ("rapido bike taxi commute travel", "Transportation"),
    ("bus pass monthly ticket local city bus", "Transportation"),
    ("petrol fuel refill for scooter motorbike", "Transportation"),
    ("diesel car petrol station fuel refill", "Transportation"),
    ("train ticket irctc railway reservation journey", "Transportation"),
    ("flight air ticket booking travel", "Transportation"),
    ("auto rickshaw fare to college hostel", "Transportation"),
    ("parking fee toll plaza tollgate fastag", "Transportation"),
    ("bicycle repair bike tube tyre puncture", "Transportation"),

    # Education
    ("semester exam registration fee university", "Education"),
    ("tuition fees college term fees installment", "Education"),
    ("machine learning textbook python data science book", "Education"),
    ("engineering notebook practical record lab manual", "Education"),
    ("stationary pen pencil calculator graph sheet", "Education"),
    ("coursera deep learning specialization course certificate", "Education"),
    ("udemy web development course tutorial", "Education"),
    ("photocopy xerox printout study notes project binding", "Education"),
    ("ieee acm conference registration student fee", "Education"),
    ("hackathon entry fee team registration coding", "Education"),
    ("chatgpt plus subscription openai api credits student", "Education"),
    ("library fine book late submission", "Education"),
    ("college fest workshop robotics seminar", "Education"),

    # Housing & Utilities
    ("hostel room monthly rent accommodation", "Housing & Utilities"),
    ("apartment pg flat rent landlord security deposit", "Housing & Utilities"),
    ("electricity power bill bescom electricity board", "Housing & Utilities"),
    ("broadband wifi internet router fiber monthly bill", "Housing & Utilities"),
    ("mobile recharge 5g data pack jio airtel vi", "Housing & Utilities"),
    ("water bill drinking water can delivery", "Housing & Utilities"),
    ("laundry washing machine dry clean clothes", "Housing & Utilities"),
    ("hostel maintenance cleaning service room repairs", "Housing & Utilities"),
    ("lpg cooking gas cylinder refill", "Housing & Utilities"),

    # Entertainment
    ("netflix 4k monthly streaming subscription", "Entertainment"),
    ("spotify premium student music subscription", "Entertainment"),
    ("movie ticket pvr inox cinema theater multiplex", "Entertainment"),
    ("youtube premium family music plan", "Entertainment"),
    ("steam game purchase video game console", "Entertainment"),
    ("playstation plus xbox game pass", "Entertainment"),
    ("amusement park concert music festival ticket", "Entertainment"),
    ("bowling arcade gaming zone weekend hangout", "Entertainment"),
    ("disney hotstar prime video ott subscription", "Entertainment"),
    ("board games sports club weekend match", "Entertainment"),

    # Shopping
    ("amazon online order parcel delivery package", "Shopping"),
    ("flipkart sale shopping casual shoes sneakers", "Shopping"),
    ("zara h&m cotton tshirt jeans hoodie clothes apparel", "Shopping"),
    ("ergonomic laptop stand mechanical keyboard mouse pad", "Shopping"),
    ("fastrack watch sunglasses wallet leather belt", "Shopping"),
    ("bedsheet blanket hostel pillow bed linen", "Shopping"),
    ("electronics usb c cable charger power bank", "Shopping"),
    ("perfume deodorant skincare moisturizer face wash", "Shopping"),
    ("myntra fashion shopping festival clothes", "Shopping"),
    ("backpack college bag travel bag luggage", "Shopping"),

    # Healthcare
    ("pharmacy medical store tablets medicines pills", "Healthcare"),
    ("doctor consultation clinic physician fee prescription", "Healthcare"),
    ("dentist dental cavity tooth filling routine checkup", "Healthcare"),
    ("optometrist spectacles eye glasses contact lens", "Healthcare"),
    ("blood test pathology lab report medical check", "Healthcare"),
    ("first aid kit bandage antiseptic ointment balm", "Healthcare"),
    ("vitamin c multivitamin supplements health protein powder", "Healthcare"),
    ("gym membership fitness club health center monthly", "Healthcare"),

    # Income Categories
    ("monthly allowance money sent from parents family", "Salary / Allowance"),
    ("college teaching assistant ta stipend payment", "Salary / Allowance"),
    ("ai research internship stipend credited", "Salary / Allowance"),
    ("merit scholarship award grant university financial aid", "Salary / Allowance"),
    ("part time campus job library desk assistant wage", "Salary / Allowance"),

    ("freelance web development project client payment", "Freelance / Projects"),
    ("python data analysis freelance gig upwork fiverr", "Freelance / Projects"),
    ("graphic design logo banner freelance commission", "Freelance / Projects"),
    ("bug bounty prize cash contest award hackathon win", "Freelance / Projects"),
    ("sold old engineering books second hand notes", "Freelance / Projects"),
]

# Stopwords to filter out noise
STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "but", "if", "or", "because", "as", "until", "while", "this", "that", "these",
    "those", "my", "your", "his", "her", "its", "our", "their", "i", "me", "we"
}


def tokenize(text: str) -> list[str]:
    """Tokenizes text into cleaned lowercase words without punctuation and stopwords."""
    if not text:
        return []
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


class NaiveBayesExpenseClassifier:
    """
    Multinomial Naive Bayes Text Classifier for Expense Auto-Categorization.
    Computes class prior probabilities and token likelihoods with Laplace smoothing (+alpha).
    """

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.class_counts = defaultdict(int)
        self.word_counts = defaultdict(lambda: defaultdict(int))
        self.vocab = set()
        self.total_docs = 0
        self._fit_initial()

    def _fit_initial(self):
        """Trains on default base training corpus."""
        for text, category in TRAINING_DATA:
            self.train_example(text, category)

    def train_example(self, text: str, category: str):
        """Incrementally trains model with one sample."""
        tokens = tokenize(text)
        if not tokens:
            return
        self.class_counts[category] += 1
        self.total_docs += 1
        for token in tokens:
            self.word_counts[category][token] += 1
            self.vocab.add(token)

    def predict(self, text: str) -> dict:
        """
        Predicts category for an expense description.
        Returns predicted category, confidence percentage, and full probability distribution.
        """
        tokens = tokenize(text)
        if not tokens or self.total_docs == 0:
            return {
                "category": "Food & Dining",
                "confidence": 50.0,
                "probabilities": [{"category": c, "confidence": round(100 / len(CATEGORIES), 1)} for c in CATEGORIES[:5]]
            }

        vocab_size = max(len(self.vocab), 1)
        log_probs = {}

        for category in CATEGORIES:
            class_count = self.class_counts.get(category, 0)
            # Prior P(C) with additive smoothing
            prior = (class_count + 1.0) / (self.total_docs + len(CATEGORIES))
            log_prob = math.log(prior)

            # Total words in this category
            total_words_in_cat = sum(self.word_counts[category].values()) + (self.alpha * vocab_size)

            for token in tokens:
                count = self.word_counts[category].get(token, 0)
                # Likelihood P(word | category) with Laplace smoothing
                prob_w_given_c = (count + self.alpha) / total_words_in_cat
                log_prob += math.log(prob_w_given_c)

            log_probs[category] = log_prob

        # Softmax conversion from log probabilities to percentage confidence
        max_log = max(log_probs.values())
        exp_probs = {c: math.exp(lp - max_log) for c, lp in log_probs.items()}
        sum_exp = sum(exp_probs.values())

        scores = [
            {"category": cat, "confidence": round((val / sum_exp) * 100, 1)}
            for cat, val in sorted(exp_probs.items(), key=lambda x: x[1], reverse=True)
        ]

        best = scores[0]
        return {
            "category": best["category"],
            "confidence": best["confidence"],
            "probabilities": scores[:5]
        }


# Global singleton instance of classifier
classifier = NaiveBayesExpenseClassifier()


def predict_category(description: str) -> dict:
    """Public helper to predict category for an expense description."""
    return classifier.predict(description)


def train_user_transaction(description: str, category: str):
    """Enables online active learning when user logs or edits a transaction."""
    if description and category in CATEGORIES:
        classifier.train_example(description, category)


# ---------------- SPENDING FORECASTER ----------------

def forecast_monthly_spending(transactions: list[dict], monthly_budget: float = 0.0) -> dict:
    """
    Time-series trend analysis & linear projection of monthly spending.
    Computes daily burn rate, velocity, and projected month-end expenditure.
    """
    now = datetime.now()
    current_year_month = now.strftime("%Y-%m")
    current_day = now.day

    # Calculate days in current month (rough estimate 30 or 31)
    if now.month in [1, 3, 5, 7, 8, 10, 12]:
        days_in_month = 31
    elif now.month == 2:
        days_in_month = 29 if (now.year % 4 == 0 and (now.year % 100 != 0 or now.year % 400 == 0)) else 28
    else:
        days_in_month = 30

    days_remaining = max(0, days_in_month - current_day)

    # Filter expenses for current month
    current_month_expenses = [
        t for t in transactions
        if t.get("type") == "expense" and str(t.get("date", "")).startswith(current_year_month)
    ]

    total_spent_so_far = sum(float(t.get("amount", 0)) for t in current_month_expenses)

    # Daily distribution
    daily_spent = defaultdict(float)
    for t in current_month_expenses:
        try:
            day = int(str(t.get("date")).split("-")[2])
            daily_spent[day] += float(t.get("amount", 0))
        except (IndexError, ValueError):
            pass

    # Simple burn rate
    days_elapsed = max(1, current_day)
    avg_daily_burn = total_spent_so_far / days_elapsed

    # Weighted recent velocity (last 7 days get higher weight)
    recent_days = range(max(1, current_day - 6), current_day + 1)
    recent_total = sum(daily_spent.get(d, 0.0) for d in recent_days)
    recent_daily_velocity = recent_total / len(recent_days)

    # Blended velocity: 60% historical average + 40% recent velocity
    blended_rate = (0.6 * avg_daily_burn) + (0.4 * recent_daily_velocity)

    projected_additional_spend = blended_rate * days_remaining
    projected_total_month_end = round(total_spent_so_far + projected_additional_spend, 2)

    # Linear regression slope (m) over elapsed days
    # y = cumulative spending, x = day
    x_vals = list(range(1, current_day + 1))
    cum_y = 0.0
    y_vals = []
    for d in x_vals:
        cum_y += daily_spent.get(d, 0.0)
        y_vals.append(cum_y)

    n = len(x_vals)
    if n > 1:
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)
        denominator = (n * sum_x2 - sum_x * sum_x)
        slope = ((n * sum_xy - sum_x * sum_y) / denominator) if denominator != 0 else avg_daily_burn
    else:
        slope = avg_daily_burn

    # Budget risk assessment
    status = "healthy"
    status_message = "Your spending velocity is within healthy limits."
    pct_of_budget = 0.0

    if monthly_budget > 0:
        pct_of_budget = round((projected_total_month_end / monthly_budget) * 100, 1)
        if projected_total_month_end > monthly_budget:
            status = "critical"
            status_message = f"Warning: At current burn rate (₹{round(blended_rate, 0)}/day), you will exceed your monthly budget by ₹{round(projected_total_month_end - monthly_budget, 0)}!"
        elif pct_of_budget >= 85:
            status = "caution"
            status_message = f"Caution: Projected to reach {pct_of_budget}% of your monthly budget. Watch non-essential expenses."
        else:
            status = "safe"
            status_message = f"Great pacing! Projected to finish month with ₹{round(monthly_budget - projected_total_month_end, 0)} surplus."

    return {
        "current_spent": round(total_spent_so_far, 2),
        "projected_total": projected_total_month_end,
        "daily_burn_rate": round(blended_rate, 2),
        "days_elapsed": days_elapsed,
        "days_remaining": days_remaining,
        "days_in_month": days_in_month,
        "spending_slope": round(slope, 2),
        "status": status,
        "status_message": status_message,
        "budget_usage_pct": pct_of_budget
    }


# ---------------- ANOMALY & OUTLIER DETECTION ----------------

def detect_anomaly(amount: float, category: str, existing_transactions: list[dict]) -> tuple[bool, str]:
    """
    Evaluates if a new transaction amount is an outlier for its category using
    Statistical Z-Score (standard deviation from mean) and IQR.
    Returns (is_anomaly, explanation).
    """
    cat_expenses = [
        float(t["amount"])
        for t in existing_transactions
        if t.get("category") == category and t.get("type") == "expense"
    ]

    # If fewer than 4 transactions in this category, insufficient statistical sample
    if len(cat_expenses) < 4:
        # Generic heuristic: if single expense is > 5000 in baseline tier
        if amount > 5000:
            return True, f"High value expense for new category {category}."
        return False, ""

    mean = sum(cat_expenses) / len(cat_expenses)
    variance = sum((x - mean) ** 2 for x in cat_expenses) / len(cat_expenses)
    std_dev = math.sqrt(variance)

    # Statistical Z-score: (X - mean) / std_dev
    if std_dev > 0:
        z_score = (amount - mean) / std_dev
    else:
        z_score = 0.0

    # Also compute 75th percentile (Q3) and IQR
    sorted_exp = sorted(cat_expenses)
    q1 = sorted_exp[len(sorted_exp) // 4]
    q3 = sorted_exp[(3 * len(sorted_exp)) // 4]
    iqr = q3 - q1
    iqr_cutoff = q3 + (1.5 * iqr)

    # Flag as anomaly if Z-score >= 2.5 and amount > 500, or amount > IQR cutoff * 1.5
    if (z_score >= 2.5 and amount > 500) or (iqr > 0 and amount > iqr_cutoff and z_score >= 2.0):
        multiplier = round(amount / mean, 1) if mean > 0 else 2.0
        explanation = f"Anomaly: ₹{amount:,.0f} is {multiplier}x higher than your average of ₹{mean:,.0f} (Z-score: +{round(z_score, 1)}σ) for {category}."
        return True, explanation

    return False, ""


# ---------------- AI FINANCIAL HEALTH SCORE & ADVISOR ----------------

def compute_financial_health_score(summary: dict, budgets: list[dict]) -> dict:
    """
    Computes a comprehensive 0-100 AI Financial Health Score based on 4 pillars:
    1. Savings Ratio (35 points)
    2. Budget Adherence (30 points)
    3. Category Concentration / Diversification (20 points)
    4. Net Cash Flow Positive Buffer (15 points)
    Also generates actionable intelligent tips.
    """
    income = summary.get("total_income", 0.0)
    expenses = summary.get("total_expenses", 0.0)
    balance = summary.get("balance", 0.0)

    # Pillar 1: Savings Ratio (Max 35 points)
    # Target: 20-30% personal savings ratio
    savings_score = 0.0
    if income > 0:
        savings_ratio = balance / income
        if savings_ratio >= 0.30:
            savings_score = 35.0
        elif savings_ratio >= 0.20:
            savings_score = 30.0
        elif savings_ratio >= 0.10:
            savings_score = 22.0
        elif savings_ratio >= 0.0:
            savings_score = 15.0
        else:
            savings_score = max(0.0, 10.0 + (savings_ratio * 20))  # negative savings penalty
    else:
        savings_score = 15.0 if expenses == 0 else 5.0

    # Pillar 2: Budget Discipline (Max 30 points)
    budget_score = 30.0
    exceeded_count = 0
    if budgets:
        for b in budgets:
            if b.get("is_exceeded"):
                exceeded_count += 1
        deduction_per_breach = 30.0 / max(1, len(budgets))
        budget_score = max(0.0, 30.0 - (exceeded_count * deduction_per_breach))

    # Pillar 3: Spending Balance / Category concentration (Max 20 points)
    # Check if a single discretionary category swallows > 50% of all expenses
    breakdown = summary.get("category_breakdown", [])
    concentration_score = 20.0
    top_cat = None
    if breakdown and expenses > 0:
        top_cat = breakdown[0]
        top_pct = (top_cat["total"] / expenses) * 100
        if top_pct > 60 and top_cat["category"] not in ["Housing & Utilities", "Education"]:
            concentration_score = 10.0
        elif top_pct > 45 and top_cat["category"] not in ["Housing & Utilities", "Education"]:
            concentration_score = 15.0

    # Pillar 4: Buffer & Liquidity (Max 15 points)
    buffer_score = 15.0 if balance > 2000 else (10.0 if balance >= 0 else 0.0)

    total_score = round(savings_score + budget_score + concentration_score + buffer_score)
    total_score = max(5, min(100, total_score))

    # Rating badge
    if total_score >= 85:
        grade = "Excellent (A+)"
        badge_color = "emerald"
    elif total_score >= 70:
        grade = "Good (B+)"
        badge_color = "blue"
    elif total_score >= 50:
        grade = "Moderate (C)"
        badge_color = "amber"
    else:
        grade = "Needs Attention (D)"
        badge_color = "rose"

    # AI Recommendations Generator
    recommendations = []
    if income > 0 and balance < 0:
        recommendations.append("🚨 Deficit Alert: Current monthly expenses exceed your income. Review optional subscriptions and dining out.")
    elif income > 0 and (balance / income) < 0.15:
        recommendations.append("💡 Boost Savings: Aim for the 50/30/20 rule (50% Needs, 30% Wants, 20% Savings). Currently your savings rate is below 15%.")

    if exceeded_count > 0:
        recommendations.append(f"⚠️ Budget Breach: {exceeded_count} categories have surpassed their monthly targets. Consider adjusting your limits.")
    else:
        recommendations.append("🎯 Great Budget Discipline: All category budgets are currently under control.")

    if top_cat and expenses > 0:
        cat_pct = round((top_cat['total'] / expenses) * 100, 1)
        recommendations.append(f"📊 Top Expense Driver: '{top_cat['category']}' represents {cat_pct}% of your total expenditure.")

    recommendations.append("🤖 ML Auto-Categorization: As you log more personal notes, the Naive Bayes model refines its predictions.")

    return {
        "score": total_score,
        "grade": grade,
        "badge_color": badge_color,
        "breakdown": {
            "savings_discipline": round(savings_score, 1),
            "budget_adherence": round(budget_score, 1),
            "spending_balance": round(concentration_score, 1),
            "cash_buffer": round(buffer_score, 1)
        },
        "recommendations": recommendations
    }
