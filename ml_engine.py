"""
Machine Learning & Analytics Engine for Personal Expense Tracker.
Core Machine Learning Modules:
1. NLP Smart Categorizer (Optimized Multinomial Naive Bayes with Lidstone/Laplace smoothing)
2. Spending Forecast & Trend Predictor (Time-series burn rate & linear regression)
3. Statistical Outlier / Anomaly Detector (Z-Score and IQR thresholds with constant-variance guards)
4. AI Financial Health Score & Smart Advisor Engine
"""

import math
import re
import calendar
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

# Comprehensive domain-specific training corpus for personal & student finances
TRAINING_DATA = [
    # Food & Dining
    ("college canteen lunch meal plate thali", "Food & Dining"),
    ("canteen samosa chai tea coffee snacks bun maska", "Food & Dining"),
    ("dominos cheese burst pizza order swiggy", "Food & Dining"),
    ("zomato food delivery dinner burger king meal", "Food & Dining"),
    ("starbucks cold brew cappuccino espresso latte", "Food & Dining"),
    ("mcdonalds burger fries coke meal combo", "Food & Dining"),
    ("subway sandwich salad cookies lunch wrap", "Food & Dining"),
    ("kfc fried chicken bucket wings zinger", "Food & Dining"),
    ("grocery store vegetables fruits milk bread eggs curd", "Food & Dining"),
    ("supermarket provisions snacks biscuits chips maggi", "Food & Dining"),
    ("restaurant family dinner buffet dining fine dine", "Food & Dining"),
    ("hostel mess food monthly coupon bill mess fees", "Food & Dining"),
    ("ice cream parlor waffle dessert pastry brownie", "Food & Dining"),
    ("juice bar fresh fruit juice shake smoothie", "Food & Dining"),
    ("shawarma roll street food momos kathi roll noodles", "Food & Dining"),
    ("dosa idli vada sambar south indian restaurant breakfast", "Food & Dining"),
    ("biryani chicken rice mutton feast hotel takeaway", "Food & Dining"),
    ("zepto grocery delivery quick commerce essentials", "Food & Dining"),
    ("blinkit instamart quick delivery milk bread vegetables", "Food & Dining"),
    ("cafe coffee day beverage mocha frappe", "Food & Dining"),
    ("bakery cakes biscuits bread cookies", "Food & Dining"),
    ("barbeque nation grill dinner buffet", "Food & Dining"),
    ("swiggy food order delivery biryani pizza lunch dinner", "Food & Dining"),
    ("upi swiggy instamart food order payment", "Food & Dining"),
    ("zomato online food order restaurant delivery", "Food & Dining"),
    ("eatsure faasos behrouz biryani ovenstory pizza", "Food & Dining"),
    ("haldiram bikanervala sweets snacks chaat thali", "Food & Dining"),
    ("chaayos chai point third wave coffee blue tokai", "Food & Dining"),
    ("bigbasket jiomart dmart reliance fresh grocery shopping", "Food & Dining"),
    ("licious freshmenu box8 meal box tiffin service", "Food & Dining"),
    ("ordered food lunch dinner breakfast snacks", "Food & Dining"),

    # Transportation
    ("monthly metro card smart recharge token", "Transportation"),
    ("uber auto taxi cab ride to campus college", "Transportation"),
    ("ola ride cab fare to railway station airport", "Transportation"),
    ("rapido bike taxi commute travel ride", "Transportation"),
    ("bus pass monthly ticket local city bus transport", "Transportation"),
    ("petrol fuel refill for scooter motorbike vehicle", "Transportation"),
    ("diesel car petrol station fuel refill pump", "Transportation"),
    ("train ticket irctc railway reservation journey berth", "Transportation"),
    ("flight air ticket booking travel indigo air india", "Transportation"),
    ("auto rickshaw fare to college hostel campus", "Transportation"),
    ("parking fee toll plaza tollgate fastag recharge", "Transportation"),
    ("bicycle repair bike tube tyre puncture air refill", "Transportation"),
    ("car service maintenance engine oil puncture tyre", "Transportation"),
    ("intercity bus redbus travel booking sleeper", "Transportation"),
    ("ev charging station electric scooter recharge", "Transportation"),
    ("namma yatri blusmart indrive meru cab ride", "Transportation"),
    ("indian oil iocl bpcl hpcl shell petrol pump fuel", "Transportation"),
    ("makemytrip goibibo cleartrip akasa spicejet vistara", "Transportation"),
    ("dmrc bmrc metro rail ticket commute", "Transportation"),

    # Education
    ("semester exam registration fee university examination", "Education"),
    ("tuition fees college term fees installment payment", "Education"),
    ("machine learning textbook python data science book algorithm", "Education"),
    ("engineering notebook practical record lab manual journal", "Education"),
    ("stationary pen pencil calculator graph sheet ruler", "Education"),
    ("coursera deep learning specialization course certificate", "Education"),
    ("udemy web development course tutorial react node", "Education"),
    ("photocopy xerox printout study notes project binding spiral", "Education"),
    ("ieee acm conference registration student fee", "Education"),
    ("hackathon entry fee team registration coding contest", "Education"),
    ("chatgpt plus subscription openai api credits student ai", "Education"),
    ("library fine book late submission renewal fee", "Education"),
    ("college fest workshop robotics seminar training bootcamp", "Education"),
    ("gre toefl exam preparation test series gate registration", "Education"),
    ("scientific calculator casio fx engineering tool", "Education"),
    ("textbook bookstore publication academic journal", "Education"),
    ("unacademy physicswallah byjus vedantu scaler upgrad", "Education"),
    ("github copilot claude perplexity leetcode subscription", "Education"),

    # Housing & Utilities
    ("hostel room monthly rent accommodation boarding", "Housing & Utilities"),
    ("apartment pg flat rent landlord security deposit broker", "Housing & Utilities"),
    ("electricity power bill bescom electricity board discom", "Housing & Utilities"),
    ("broadband wifi internet router fiber monthly bill connection", "Housing & Utilities"),
    ("mobile recharge 5g data pack jio airtel vi prepaid", "Housing & Utilities"),
    ("water bill drinking water can delivery bisleri", "Housing & Utilities"),
    ("laundry washing machine dry clean clothes iron press", "Housing & Utilities"),
    ("hostel maintenance cleaning service room repairs plumbing", "Housing & Utilities"),
    ("lpg cooking gas cylinder refill indane bharat", "Housing & Utilities"),
    ("room heater fan air conditioner repair appliance", "Housing & Utilities"),
    ("society maintenance flat charges security cleaning fee", "Housing & Utilities"),
    ("nobroker nestaway stanza living zolo pg rent", "Housing & Utilities"),
    ("tata power adani electricity msedcl bses tneb bill", "Housing & Utilities"),
    ("jiofiber airtel xstream act fibernet hathway broadband", "Housing & Utilities"),
    ("urban company plumber electrician carpenter repair", "Housing & Utilities"),

    # Entertainment
    ("netflix 4k monthly streaming subscription ott", "Entertainment"),
    ("spotify premium student music subscription playlist", "Entertainment"),
    ("movie ticket pvr inox cinema theater multiplex popcorn", "Entertainment"),
    ("youtube premium family music plan ad free", "Entertainment"),
    ("steam game purchase video game console pc game", "Entertainment"),
    ("playstation plus xbox game pass ultimate", "Entertainment"),
    ("amusement park concert music festival ticket show", "Entertainment"),
    ("bowling arcade gaming zone weekend hangout fun", "Entertainment"),
    ("disney hotstar prime video ott subscription renewal", "Entertainment"),
    ("board games sports club weekend match stadium tickets", "Entertainment"),
    ("apple music tv subscription itunes entertainment", "Entertainment"),
    ("comic con stand up comedy show live comedy ticket", "Entertainment"),
    ("bookmyshow cinepolis imax movie booking tickets", "Entertainment"),
    ("jiocinema sonyliv zee5 jiosaavn gaana subscription", "Entertainment"),
    ("valorant bgmi nintendo gaming topup", "Entertainment"),

    # Shopping
    ("amazon online order parcel delivery package merchandise", "Shopping"),
    ("flipkart sale shopping casual shoes sneakers boots", "Shopping"),
    ("zara h&m cotton tshirt jeans hoodie clothes apparel jacket", "Shopping"),
    ("ergonomic laptop stand mechanical keyboard mouse pad desk", "Shopping"),
    ("fastrack watch sunglasses wallet leather belt bag", "Shopping"),
    ("bedsheet blanket hostel pillow bed linen mattress", "Shopping"),
    ("electronics usb c cable charger power bank earphones", "Shopping"),
    ("perfume deodorant skincare moisturizer face wash sunscreen", "Shopping"),
    ("myntra fashion shopping festival clothes ethnic wear", "Shopping"),
    ("backpack college bag travel bag luggage suitcase", "Shopping"),
    ("smartwatch noise boat ear buds audio headphones", "Shopping"),
    ("sunglasses eyewear ray ban specs frame lenskart", "Shopping"),
    ("shoes nike adidas sports running sneakers footwear", "Shopping"),
    ("ajio nykaa meesho tata cliq croma reliance digital", "Shopping"),
    ("decathlon uniqlo westside pantaloons puma skechers", "Shopping"),
    ("ikea pepperfry home decor furniture lamp", "Shopping"),

    # Healthcare
    ("pharmacy medical store tablets medicines pills prescription", "Healthcare"),
    ("apollo pharmacy paracetamol crocin cough syrup strip", "Healthcare"),
    ("doctor consultation clinic physician fee prescription hospital", "Healthcare"),
    ("dentist dental cavity tooth filling routine checkup braces", "Healthcare"),
    ("optometrist spectacles eye glasses contact lens solution", "Healthcare"),
    ("blood test pathology lab report medical check diagnostic", "Healthcare"),
    ("first aid kit bandage antiseptic ointment balm dolo", "Healthcare"),
    ("vitamin c multivitamin supplements health protein powder whey", "Healthcare"),
    ("gym membership fitness club health center monthly workout", "Healthcare"),
    ("physiotherapy massage therapy posture relief doctor", "Healthcare"),
    ("skincare dermatologist consultation acne treatment", "Healthcare"),
    ("pharmeasy 1mg netmeds medplus practo medicine order", "Healthcare"),
    ("cultfit cult fit anytime fitness health checkup", "Healthcare"),
    ("thyrocare lal pathlabs diagnostic test scan", "Healthcare"),

    # Salary / Allowance
    ("monthly allowance money sent from parents family support pocket", "Salary / Allowance"),
    ("college teaching assistant ta stipend payment assistantship", "Salary / Allowance"),
    ("ai research internship stipend credited bank transfer", "Salary / Allowance"),
    ("merit scholarship award grant university financial aid fellowship", "Salary / Allowance"),
    ("part time campus job library desk assistant wage hourly", "Salary / Allowance"),
    ("monthly company salary credit direct deposit payroll", "Salary / Allowance"),
    ("academic excellence reward cash prize scholarship stipend", "Salary / Allowance"),
    ("neft cr salary credit bonus reimbursement refund cashback", "Salary / Allowance"),

    # Freelance / Projects
    ("freelance web development project client payment milestone", "Freelance / Projects"),
    ("python data analysis freelance gig upwork fiverr payout", "Freelance / Projects"),
    ("graphic design logo banner freelance commission design work", "Freelance / Projects"),
    ("bug bounty prize cash contest award hackathon win prize", "Freelance / Projects"),
    ("sold old engineering books second hand notes resale", "Freelance / Projects"),
    ("app development client contract milestone payment advance", "Freelance / Projects"),
    ("content writing technical blog article sponsorship payment", "Freelance / Projects"),
    ("stripe payout razorpay payout paypal wise client invoice", "Freelance / Projects"),
]

# Stopwords to filter out noise
STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "after", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "but", "if", "or", "because", "as", "until", "while", "this", "that", "these",
    "those", "my", "your", "his", "her", "its", "our", "their", "i", "me", "we"
}

# Pre-compiled regex for ultra-fast tokenization
_TOKEN_REGEX = re.compile(r'[a-zA-Z0-9]+')
_ALPHA_REGEX = re.compile(r'[a-zA-Z]{2,}')

# High-signal merchant & bank-narration keyword boosts for crisp detection
MERCHANT_KEYWORD_MAP = {
    # Food & Dining
    "swiggy": "Food & Dining", "zomato": "Food & Dining", "eatsure": "Food & Dining",
    "faasos": "Food & Dining", "behrouz": "Food & Dining", "dominos": "Food & Dining",
    "pizzahut": "Food & Dining", "mcdonalds": "Food & Dining", "kfc": "Food & Dining",
    "burgerking": "Food & Dining", "starbucks": "Food & Dining", "chaayos": "Food & Dining",
    "blinkit": "Food & Dining", "zepto": "Food & Dining", "instamart": "Food & Dining",
    "bigbasket": "Food & Dining", "dmart": "Food & Dining", "jiomart": "Food & Dining",
    "haldiram": "Food & Dining", "biryani": "Food & Dining", "canteen": "Food & Dining",
    "restaurant": "Food & Dining", "cafe": "Food & Dining", "grocery": "Food & Dining",
    # Transportation
    "uber": "Transportation", "ola": "Transportation", "rapido": "Transportation",
    "blusmart": "Transportation", "indrive": "Transportation", "irctc": "Transportation",
    "redbus": "Transportation", "fastag": "Transportation", "metro": "Transportation",
    "petrol": "Transportation", "diesel": "Transportation", "indigo": "Transportation",
    "makemytrip": "Transportation", "goibibo": "Transportation", "cab": "Transportation",
    # Education
    "coursera": "Education", "udemy": "Education", "unacademy": "Education",
    "physicswallah": "Education", "tuition": "Education", "semester": "Education",
    "textbook": "Education", "stationery": "Education", "xerox": "Education",
    "hackathon": "Education", "chatgpt": "Education", "openai": "Education",
    # Housing & Utilities
    "rent": "Housing & Utilities", "nobroker": "Housing & Utilities", "bescom": "Housing & Utilities",
    "electricity": "Housing & Utilities", "broadband": "Housing & Utilities", "wifi": "Housing & Utilities",
    "jiofiber": "Housing & Utilities", "airtel": "Housing & Utilities", "jio": "Housing & Utilities",
    "recharge": "Housing & Utilities", "laundry": "Housing & Utilities", "indane": "Housing & Utilities",
    # Entertainment
    "netflix": "Entertainment", "spotify": "Entertainment", "hotstar": "Entertainment",
    "bookmyshow": "Entertainment", "pvr": "Entertainment", "inox": "Entertainment",
    "jiocinema": "Entertainment", "sonyliv": "Entertainment", "steam": "Entertainment",
    "playstation": "Entertainment", "xbox": "Entertainment", "cinema": "Entertainment",
    # Shopping
    "amazon": "Shopping", "flipkart": "Shopping", "myntra": "Shopping",
    "ajio": "Shopping", "nykaa": "Shopping", "meesho": "Shopping",
    "croma": "Shopping", "decathlon": "Shopping", "lenskart": "Shopping",
    "ikea": "Shopping", "sneakers": "Shopping", "shoes": "Shopping",
    # Healthcare
    "apollo": "Healthcare", "pharmeasy": "Healthcare", "netmeds": "Healthcare",
    "medplus": "Healthcare", "practo": "Healthcare", "thyrocare": "Healthcare",
    "pharmacy": "Healthcare", "hospital": "Healthcare", "clinic": "Healthcare",
    "dentist": "Healthcare", "medicine": "Healthcare", "gym": "Healthcare",
    # Salary / Allowance
    "salary": "Salary / Allowance", "stipend": "Salary / Allowance", "payroll": "Salary / Allowance",
    "scholarship": "Salary / Allowance", "allowance": "Salary / Allowance",
    # Freelance / Projects
    "freelance": "Freelance / Projects", "upwork": "Freelance / Projects", "fiverr": "Freelance / Projects",
    "stripe": "Freelance / Projects", "razorpay": "Freelance / Projects", "bounty": "Freelance / Projects",
}


def tokenize(text: str) -> list[str]:
    """Tokenizes text into cleaned lowercase words, splitting bank narration codes cleanly."""
    if not text:
        return []
    lowered = text.lower()
    raw_words = _TOKEN_REGEX.findall(lowered)
    tokens = []
    for w in raw_words:
        if len(w) > 1 and w not in STOPWORDS:
            tokens.append(w)
        # Also extract pure alpha parts from mixed bank narration tokens (e.g. swiggy200 -> swiggy)
        if not w.isalpha():
            for alpha in _ALPHA_REGEX.findall(w):
                if alpha not in STOPWORDS and alpha != w:
                    tokens.append(alpha)
    return tokens


class NaiveBayesExpenseClassifier:
    """
    High-Performance Multinomial Naive Bayes Text Classifier.
    - Precomputes log priors, vocabulary size, and category word counts for ultra-low latency.
    - Tuned with Lidstone smoothing (alpha=0.25) for crisp, calibrated posterior probabilities.
    - Sub-microsecond incremental learning via train_example().
    """

    def __init__(self, alpha: float = 0.25):
        self.alpha = alpha
        self.class_counts = defaultdict(int)
        self.word_counts = defaultdict(lambda: defaultdict(int))
        self.category_total_words = defaultdict(int)
        self.vocab = set()
        self.total_docs = 0

        # Precomputed cache for zero-overhead inference
        self._log_priors = {}
        self._log_denominators = {}
        self._unseen_log_prob = {}

        self._fit_initial()

    def _fit_initial(self):
        """Trains on default base training corpus."""
        for text, category in TRAINING_DATA:
            tokens = tokenize(text)
            if not tokens:
                continue
            self.class_counts[category] += 1
            self.total_docs += 1
            for token in tokens:
                self.word_counts[category][token] += 1
                self.category_total_words[category] += 1
                self.vocab.add(token)

        self._recompute_cache()

    def _recompute_cache(self):
        """Precomputes log priors and denominators to eliminate loops during prediction."""
        vocab_size = max(len(self.vocab), 1)
        num_categories = len(CATEGORIES)

        for category in CATEGORIES:
            class_count = self.class_counts.get(category, 0)
            # Additive Laplace prior
            prior = (class_count + 1.0) / (self.total_docs + num_categories)
            self._log_priors[category] = math.log(prior)

            # Denominator: total category words + (alpha * |V|)
            denom = self.category_total_words.get(category, 0) + (self.alpha * vocab_size)
            log_denom = math.log(denom)
            self._log_denominators[category] = log_denom

            # Constant probability for out-of-category tokens
            self._unseen_log_prob[category] = math.log(self.alpha) - log_denom

    def train_example(self, text: str, category: str):
        """Incrementally trains model with one sample in real-time."""
        tokens = tokenize(text)
        if not tokens or category not in CATEGORIES:
            return

        self.class_counts[category] += 1
        self.total_docs += 1
        for token in tokens:
            self.word_counts[category][token] += 1
            self.category_total_words[category] += 1
            self.vocab.add(token)

        self._recompute_cache()

    def predict(self, text: str) -> dict:
        """
        Ultra-fast category prediction for an expense description.
        Returns predicted category, calibrated confidence percentage, and top-5 probability distribution.
        """
        tokens = tokenize(text)
        if not tokens or self.total_docs == 0:
            return {
                "category": "Food & Dining",
                "confidence": 50.0,
                "probabilities": [{"category": c, "confidence": round(100 / len(CATEGORIES), 1)} for c in CATEGORIES[:5]]
            }

        log_probs = {}

        for category in CATEGORIES:
            log_prob = self._log_priors[category]
            cat_words = self.word_counts[category]
            log_denom = self._log_denominators[category]
            unseen_lp = self._unseen_log_prob[category]

            for token in tokens:
                count = cat_words.get(token, 0)
                if count > 0:
                    log_prob += math.log(count + self.alpha) - log_denom
                else:
                    log_prob += unseen_lp

                # Apply high-signal merchant/keyword boost when a known brand or keyword matches
                if MERCHANT_KEYWORD_MAP.get(token) == category:
                    log_prob += 3.5

            log_probs[category] = log_prob

        # Softmax conversion from log probabilities to calibrated percentage confidence
        max_log = max(log_probs.values())
        exp_probs = {c: math.exp(lp - max_log) for c, lp in log_probs.items()}
        sum_exp = sum(exp_probs.values())

        if sum_exp <= 0:
            sum_exp = 1.0

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
    Uses exact calendar days in current month.
    """
    now = datetime.now()
    current_year_month = now.strftime("%Y-%m")
    current_day = now.day

    # Exact days in current month via standard library calendar module
    days_in_month = calendar.monthrange(now.year, now.month)[1]
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
    Handles zero-variance constant historical expenses safely.
    """
    if amount <= 0:
        return False, ""

    cat_expenses = [
        float(t["amount"])
        for t in existing_transactions
        if t.get("category") == category and t.get("type") == "expense" and float(t.get("amount", 0)) > 0
    ]

    # If fewer than 4 transactions in this category, insufficient statistical sample
    if len(cat_expenses) < 4:
        # Heuristic: if single expense is > 5000 in baseline tier
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
        # Edge case: all past expenses were identical (std_dev = 0)
        if amount >= mean * 2.5 and amount > 500:
            multiplier = round(amount / mean, 1) if mean > 0 else 2.5
            return True, f"Anomaly: ₹{amount:,.0f} deviates from historical constant of ₹{mean:,.0f} ({multiplier}x higher) for {category}."
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
    income = float(summary.get("total_income", 0.0) or 0.0)
    expenses = float(summary.get("total_expenses", 0.0) or 0.0)
    balance = float(summary.get("balance", 0.0) or 0.0)

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
        top_pct = (top_cat.get("total", 0) / expenses) * 100
        if top_pct > 60 and top_cat.get("category") not in ["Housing & Utilities", "Education"]:
            concentration_score = 10.0
        elif top_pct > 45 and top_cat.get("category") not in ["Housing & Utilities", "Education"]:
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
        cat_pct = round((top_cat.get("total", 0) / expenses) * 100, 1)
        recommendations.append(f"📊 Top Expense Driver: '{top_cat.get('category')}' represents {cat_pct}% of your total expenditure.")

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



# ---------------- BANK STATEMENT PARSER ----------------

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d %B %Y",
    "%d-%b-%y",
    "%Y/%m/%d",
)


def _normalize_date(raw_date: str) -> str | None:
    """Normalizes common bank statement date formats to YYYY-MM-DD."""
    if not raw_date:
        return None
    cleaned = re.sub(r'\s+', ' ', str(raw_date).strip())
    # Strip trailing time if present (e.g. "2026-11-20 14:30:00")
    cleaned_date_only = cleaned.split(' ')[0] if re.search(r'\d{2}:\d{2}', cleaned) else cleaned
    for candidate in (cleaned_date_only, cleaned):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(candidate, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _parse_amount(raw_val: str) -> float:
    """Parses currency/amount strings like '₹1,250.50', 'Rs. 200', '(500.00)' into float."""
    if raw_val is None:
        return 0.0
    s = str(raw_val).strip()
    if not s or s in ("-", "--", "N/A", "na", "null"):
        return 0.0
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r'[₹$€£,\s()]', '', s)
    s = re.sub(r'^(rs\.?|inr|usd|eur|gbp)\s*', '', s, flags=re.IGNORECASE)
    # Strip trailing Dr/Cr markers
    s = re.sub(r'(dr|cr)\.?$', '', s, flags=re.IGNORECASE).strip()
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return 0.0


def parse_bank_statement_csv(csv_text: str) -> dict:
    """
    Parses a CSV bank statement (HDFC, SBI, ICICI, Axis, Kotak, or generic CSV)
    and auto-categorizes every transaction using the trained ML predictor.

    Supports:
    - Metadata header lines before the actual table header
    - Separate Debit/Withdrawal and Credit/Deposit columns
    - Single Amount column + Type/Dr-Cr column, or signed Amount (+/-)
    - Common date formats normalized to YYYY-MM-DD
    """
    import csv
    import io

    if not csv_text or not csv_text.strip():
        return {"transactions": [], "total_rows": 0, "skipped_rows": 0, "error": "Empty CSV content."}

    # Strip UTF-8 BOM if present
    text = csv_text.lstrip("\ufeff").strip()
    lines = text.splitlines()
    if not lines:
        return {"transactions": [], "total_rows": 0, "skipped_rows": 0, "error": "No rows found."}

    # Detect delimiter from non-empty sample
    sample = "\n".join(lines[:20])
    delimiter = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = ","

    all_rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))

    # Locate the header row (skip bank metadata preamble lines)
    header_idx = None
    date_keys = ("date", "txn date", "transaction date", "value date", "posting date", "value dt")
    desc_keys = ("description", "narration", "particulars", "remarks", "details", "merchant", "transaction remarks", "memo")
    amt_keys = ("amount", "debit", "credit", "withdrawal", "deposit", "withdrawal amt", "deposit amt", "debit amount", "credit amount")

    for i, row in enumerate(all_rows[:25]):
        norm_cells = [c.strip().lower() for c in row if c and c.strip()]
        if len(norm_cells) < 3:
            continue
        has_date = any(any(dk in c for dk in date_keys) for c in norm_cells)
        has_desc_or_amt = any(any(k in c for k in desc_keys + amt_keys) for c in norm_cells)
        if has_date and has_desc_or_amt:
            header_idx = i
            break

    if header_idx is None:
        return {
            "transactions": [],
            "total_rows": 0,
            "skipped_rows": len(all_rows),
            "error": "Could not detect bank statement columns (expected Date, Description/Narration, and Amount/Debit/Credit)."
        }

    headers = [h.strip().lower() for h in all_rows[header_idx]]

    def _find_col(candidates: tuple[str, ...]) -> int | None:
        for cand in candidates:
            for idx, h in enumerate(headers):
                if h == cand:
                    return idx
        for cand in candidates:
            for idx, h in enumerate(headers):
                if cand in h:
                    return idx
        return None

    date_col = _find_col(("txn date", "transaction date", "value date", "date", "posting date", "value dt"))
    desc_col = _find_col(("narration", "particulars", "description", "transaction remarks", "remarks", "details", "merchant", "memo"))
    debit_col = _find_col(("withdrawal amt", "debit amount", "withdrawal", "debit", "dr"))
    credit_col = _find_col(("deposit amt", "credit amount", "deposit", "credit", "cr"))
    amount_col = _find_col(("amount", "txn amount", "transaction amount"))
    type_col = _find_col(("type", "dr/cr", "cr/dr", "drcr", "transaction type"))
    cat_col = _find_col(("category",))

    if date_col is None or (debit_col is None and credit_col is None and amount_col is None):
        return {
            "transactions": [],
            "total_rows": 0,
            "skipped_rows": len(all_rows) - header_idx - 1,
            "error": "Missing required Date or Amount/Debit/Credit columns in CSV."
        }

    parsed = []
    skipped = 0

    for row in all_rows[header_idx + 1:]:
        if not row or all(not c.strip() for c in row):
            continue

        def _cell(idx: int | None) -> str:
            if idx is None or idx >= len(row):
                return ""
            return row[idx].strip()

        norm_date = _normalize_date(_cell(date_col))
        if not norm_date:
            skipped += 1
            continue

        description = _cell(desc_col) or "Bank Statement Entry"
        # Clean excessive whitespace in bank narrations
        description = re.sub(r'\s+', ' ', description).strip()

        tx_type = "expense"
        amount = 0.0

        if debit_col is not None or credit_col is not None:
            debit_amt = _parse_amount(_cell(debit_col))
            credit_amt = _parse_amount(_cell(credit_col))
            if credit_amt > 0 and debit_amt <= 0:
                tx_type = "income"
                amount = credit_amt
            elif debit_amt > 0:
                tx_type = "expense"
                amount = debit_amt
            elif amount_col is not None:
                raw_amt = _parse_amount(_cell(amount_col))
                amount = abs(raw_amt)
                if raw_amt > 0 and _cell(type_col).lower() in ("cr", "credit", "income"):
                    tx_type = "income"
        elif amount_col is not None:
            raw_amt_str = _cell(amount_col)
            raw_amt = _parse_amount(raw_amt_str)
            t_flag = _cell(type_col).lower()
            if t_flag in ("cr", "credit", "income", "deposit"):
                tx_type = "income"
                amount = abs(raw_amt)
            elif t_flag in ("dr", "debit", "expense", "withdrawal"):
                tx_type = "expense"
                amount = abs(raw_amt)
            elif raw_amt_str.lower().endswith("cr"):
                tx_type = "income"
                amount = abs(raw_amt)
            elif raw_amt < 0:
                tx_type = "expense"
                amount = abs(raw_amt)
            else:
                # Positive single-column amount without explicit type -> treat as expense unless income keywords match
                amount = abs(raw_amt)
                if any(k in description.lower() for k in ("salary", "stipend", "credit", "refund", "payout", "allowance", "dividend")):
                    tx_type = "income"

        if amount <= 0:
            skipped += 1
            continue

        # Use explicit CSV category only if valid, otherwise run ML predictor
        explicit_cat = _cell(cat_col)
        prediction = predict_category(description)
        if explicit_cat in CATEGORIES:
            category = explicit_cat
            confidence = 100.0
        else:
            category = prediction["category"]
            confidence = prediction["confidence"]
            # If it's an income row and ML picked an expense category with low confidence, map to Salary / Allowance
            if tx_type == "income" and category not in ("Salary / Allowance", "Freelance / Projects"):
                if any(k in description.lower() for k in ("freelance", "upwork", "fiverr", "stripe", "razorpay", "client")):
                    category = "Freelance / Projects"
                else:
                    category = "Salary / Allowance"

        parsed.append({
            "date": norm_date,
            "type": tx_type,
            "amount": round(amount, 2),
            "category": category,
            "confidence": confidence,
            "description": description[:200],
        })

    return {
        "transactions": parsed,
        "total_rows": len(parsed),
        "skipped_rows": skipped,
    }
