# 🗺️ MoneyMap — Intelligent Personal Wealth & Expense Analytics

> *An editorial, machine-learning-driven web application for personal finance intelligence, spending forecasting, and automated Bayesian transaction categorization.*

---

## 🌟 Key Highlights & Architecture

1. **Layered System Architecture**:
   - **Presentation Layer**: Editorial SPA built with HTML5, CSS3, modern Vanilla JavaScript, and Chart.js featuring the Awwwards-inspired Epple design system.
   - **Application Logic Layer**: Python & Flask REST API handling transaction CRUD, business validations, and budget calculations.
   - **Machine Learning Engine**: Custom transparent NLP and statistical AI models with real-time inference and online active learning.
   - **Data Layer**: SQLite persistent relational storage (`tracker.db`) with indexes and foreign keys.

2. **4 Built-in Machine Learning Modules**:
   - 🤖 **Model 1: NLP Smart Auto-Categorizer**: Real-time category prediction as you type transaction descriptions using *Multinomial Naive Bayes* with *Laplace Smoothing* ($+ \alpha$). Includes online active learning that adapts to personal spending habits.
   - 🔮 **Model 2: Spending Velocity & Regression Forecaster**: Analyzes day-by-day burn rate and weighted moving averages to project month-end expenditure ($y = mx + c$) against budget targets.
   - ⚠️ **Model 3: Statistical Anomaly & Outlier Detector**: Flags unusual spending spikes using *Statistical Z-Score* ($Z \ge +2.5\sigma$) and *Interquartile Range (IQR)* thresholds.
   - 🧠 **Model 4: AI Financial Health Coach**: Computes a 0–100 score based on savings ratio, budget adherence, and spending volatility, paired with personalized financial recommendations (e.g., 50/30/20 rule).

3. **Interactive Demonstration & Intelligence Sandbox**:
   - ⚡ **1-Click Quick Demo Account**: A dedicated button on the login screen that immediately logs into a live demonstration session populated with 30+ pre-seeded records and visual ML anomaly flags.
   - 🧪 **Interactive Intelligence Lab**: A dedicated tab allowing users to test the NLP model on custom text phrases and inspect model probabilities in real time.

---

## 📐 Algorithmic Formulations & Principles

### 1. NLP Naive Bayes Classifier
Given an expense description $D = \{w_1, w_2, \dots, w_n\}$, the predicted category $\hat{C}$ satisfies:

$$\hat{C} = \arg\max_{C \in \mathcal{C}} P(C) \prod_{i=1}^n P(w_i \mid C)$$

With Laplace smoothing ($\alpha = 1.0$):

$$P(w \mid C) = \frac{\text{count}(w, C) + \alpha}{\sum_{w' \in V} \text{count}(w', C) + \alpha \cdot |V|}$$

### 2. Time-Series Linear Spending Regression
Given cumulative spending $y_i$ on day $x_i \in [1, d_{\text{elapsed}}]$:

$$\text{Slope } m = \frac{n \sum (x_i y_i) - (\sum x_i)(\sum y_i)}{n \sum x_i^2 - (\sum x_i)^2}$$

$$\text{Projected Total Spend} = \text{Current Spend} + \text{Blended Daily Burn Rate} \times \text{Days Remaining}$$

### 3. Statistical Anomaly Detection (Z-Score & IQR)
For an expense amount $x$ in category $C$ with historical mean $\mu$ and standard deviation $\sigma$:

$$Z = \frac{x - \mu}{\sigma}$$

If $Z \ge 2.5$ or $x > Q_3 + 1.5 \times (Q_3 - Q_1)$, the transaction is flagged with an anomaly badge.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- Flask (`pip install flask`)
- NumPy & Scikit-Learn (`pip install numpy scikit-learn`)

### 1. Launch the Application
In your terminal, navigate to the project directory and run:

```bash
cd  "/Users/abc/Desktop/Expense tracker"
python3 app.py
```

### 2. Open in Browser
Open your browser and navigate to:
```
http://127.0.0.1:8080
```

### 3. Instant Demo Walkthrough
1. Click **"⚡ Launch Demo Session (1-Click)"** on the landing page.
2. Explore the **Overview**: View Net Balance, Income vs Expense bar charts, Category distribution donut chart, and the ML Spending Forecast.
3. Check the **Transactions** tab: Search, filter by date/category, and click **"+ Add Transaction"**. Notice how typing "Dominos pizza" or "Uber ride" triggers live ML category prediction!
4. Check the **Budgets** tab: Observe visual progress bars and limit alerts.
5. Visit the **Intelligence Lab** tab: Try typing any text into the interactive ML Sandbox to test the classifier live.

---

## 🧪 Running Automated Tests

A comprehensive unit and integration test suite is included:

```bash
python3 test_app.py
```

All 9 tests verify:
- Relational SQLite schema integrity and CRUD operations
- PBKDF2 password hashing and HMAC session security
- Naive Bayes text categorization accuracy
- Time series spending forecasting calculations
- Statistical anomaly detection on outlier amounts
- REST API endpoints and CSV export

---

## 📁 Project Structure

```
personal-expense-tracker/
├── app.py                  # Flask web server & REST API endpoints
├── database.py             # SQLite schemas, CRUD helpers, & demo data generator
├── auth.py                 # PBKDF2-HMAC-SHA256 hashing & HMAC session tokens
├── ml_engine.py            # Machine Learning engine (Naive Bayes, Forecast, Anomalies)
├── test_app.py             # Automated unit & integration test suite
├── README.md               # Project documentation
├── tracker.db              # SQLite persistent database (created automatically)
├── templates/
│   └── index.html          # Responsive single-page application shell
└── static/
    ├── css/
    │   └── style.css       # Epple editorial gallery palette & dark/light theme
    └── js/
        └── app.js          # Client-side state, Chart.js, & real-time ML integration
```

---

## 🏛️ Core Capabilities Matrix

| Functional Requirement | Implementation in MoneyMap |
|-------------------------|----------------------------|
| Income & Expense recording | Full CRUD with amount, date, category, and notes |
| Balance and totals calculation | Real-time calculations: Total Income, Total Expenses, Balance, Savings Rate |
| Category grouping | Categorized storage, Donut chart visualization, category-wise budgets |
| Persistent storage | Local SQLite relational database with proper foreign keys & indexing |
| Multi-user authentication | Secure registration, login, PBKDF2 password hashing, session tokens |
| Machine Learning extension | NLP Auto-Categorizer, Trend Forecaster, Anomaly Detector, Financial Health Score |
| Export capabilities | Formatted CSV export with 1-click download |
