"""
MoneyMap AI Financial Advisor Engine.
Context-aware conversational intelligence for expense reduction,
budget optimization, anomaly auditing, and wealth planning.
"""

import re
from datetime import datetime
import database
import ml_engine


def get_user_financial_context(user_id: int) -> dict:
    """Gathers comprehensive, real-time financial metrics for the AI advisor."""
    user = database.get_user_by_id(user_id)
    currency = user.get("currency", "₹") if user else "₹"

    summary = database.get_financial_summary(user_id)
    transactions = database.get_transactions(user_id)
    budgets = database.get_budgets(user_id)

    total_income = summary.get("total_income", 0.0)
    total_expenses = summary.get("total_expenses", 0.0)
    balance = summary.get("balance", 0.0)
    savings_rate = summary.get("savings_rate", 0.0)
    
    raw_categories = summary.get("category_breakdown", [])
    if isinstance(raw_categories, list):
        category_breakdown = {item["category"]: float(item.get("total", 0.0)) for item in raw_categories if "category" in item}
    elif isinstance(raw_categories, dict):
        category_breakdown = {k: float(v) for k, v in raw_categories.items()}
    else:
        category_breakdown = {}

    total_budget = sum(b.get("monthly_limit", 0.0) for b in budgets)
    forecast = ml_engine.forecast_monthly_spending(transactions, total_budget)
    health = ml_engine.compute_financial_health_score(summary, budgets)

    # Separate anomalies and largest expenses
    anomalies = [t for t in transactions if t.get("is_anomaly") or (t.get("type") == "expense" and t.get("amount", 0) >= 4000)]
    expenses_only = [t for t in transactions if t.get("type") == "expense"]
    top_expenses = sorted(expenses_only, key=lambda x: x.get("amount", 0.0), reverse=True)[:5]

    # Subscriptions & recurring items detection
    subscription_keywords = ["netflix", "spotify", "coursera", "wifi", "broadband", "prime", "recharge", "gym", "subscription"]
    subscriptions = [
        t for t in expenses_only
        if any(kw in (t.get("description") or "").lower() for kw in subscription_keywords)
    ]
    total_subscriptions = sum(s.get("amount", 0.0) for s in subscriptions)

    # Sort categories by total expenditure
    sorted_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)

    return {
        "currency": currency,
        "total_income": total_income,
        "total_expenses": total_expenses,
        "balance": balance,
        "savings_rate": savings_rate,
        "category_breakdown": category_breakdown,
        "sorted_categories": sorted_categories,
        "total_budget": total_budget,
        "forecast": forecast,
        "health": health,
        "anomalies": anomalies,
        "top_expenses": top_expenses,
        "subscriptions": subscriptions,
        "total_subscriptions": total_subscriptions,
        "transactions_count": len(transactions)
    }


def generate_advisor_response(user_id: int, message: str, history: list = None) -> dict:
    """
    Processes the user's inquiry against their personal financial ledger
    and returns a structured, actionable advisory report with savings calculations.
    """
    msg = message.strip().lower()
    ctx = get_user_financial_context(user_id)
    c = ctx["currency"]

    # Default quick actions for follow-up
    quick_actions = [
        "💡 How can I reduce expenses?",
        "🔍 Where am I overspending?",
        "⚠️ Analyze my spending leaks",
        "🎯 How to save 20% more?"
    ]

    # 1. INTENT: EXPENSE REDUCTION / HOW TO CUT SPENDING / SAVE MONEY
    if any(k in msg for k in ["reduce", "cut", "save money", "lower", "decrease", "lessen", "cut down", "how can i reduce", "stop spending"]):
        reply = build_expense_reduction_plan(ctx)
        suggested = [
            "🔍 Audit my top categories",
            "⚠️ Check for outlier leaks",
            "📊 Set new budget limits"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "expense_reduction"
        }

    # 2. INTENT: TOP EXPENSES / WHERE IS MY MONEY GOING
    elif any(k in msg for k in ["where", "most", "highest", "biggest", "breakdown", "category", "categories", "overspend"]):
        reply = build_spending_breakdown_analysis(ctx)
        suggested = [
            "💡 How can I reduce expenses?",
            "🎯 Create a 50/30/20 plan",
            "⚡ View predictive forecast"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "spending_breakdown"
        }

    # 3. INTENT: ANOMALIES / LEAKS / UNUSUAL SPENDING
    elif any(k in msg for k in ["anomaly", "anomalies", "leak", "leaks", "unusual", "outlier", "spike", "waste"]):
        reply = build_anomaly_audit_response(ctx)
        suggested = [
            "💡 How can I reduce expenses?",
            "📊 Review monthly budgets",
            "💰 How is my savings rate?"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "anomaly_audit"
        }

    # 4. INTENT: SAVINGS GOAL / TARGET (e.g., save 5000, save 20%)
    elif any(k in msg for k in ["target", "goal", "save 5000", "save 20%", "save 10000", "emergency fund", "wealth"]):
        reply = build_savings_goal_response(ctx, msg)
        suggested = [
            "💡 How can I reduce expenses?",
            "🔍 Where am I overspending?",
            "📈 Forecast month-end balance"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "savings_target"
        }

    # 5. INTENT: 50/30/20 BUDGET RULE
    elif any(k in msg for k in ["50/30/20", "rule", "framework", "ratio", "budget rule"]):
        reply = build_50_30_20_response(ctx)
        suggested = [
            "💡 How can I reduce expenses?",
            "🎯 Adjust category budgets",
            "🔍 Show spending breakdown"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "budget_framework"
        }

    # 6. INTENT: FOOD & DINING SPECIFIC
    elif any(k in msg for k in ["food", "dining", "canteen", "restaurant", "zomato", "swiggy", "groceries"]):
        reply = build_food_reduction_response(ctx)
        suggested = [
            "💡 General expense reduction plan",
            "🚗 Transportation savings",
            "🏠 Housing & fixed costs"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "food_analysis"
        }

    # 7. INTENT: SUBSCRIPTIONS
    elif any(k in msg for k in ["subscription", "subscriptions", "netflix", "spotify", "recurring", "bills"]):
        reply = build_subscription_response(ctx)
        suggested = [
            "💡 How can I reduce expenses?",
            "🔍 Show all outliers",
            "📊 Set category limits"
        ]
        return {
            "reply": reply,
            "suggested_actions": suggested,
            "intent": "subscription_audit"
        }

    # 8. DEFAULT / GENERAL ADVICE
    else:
        reply = build_general_advisor_response(ctx, message)
        return {
            "reply": reply,
            "suggested_actions": quick_actions,
            "intent": "general_inquiry"
        }


# ==============================================================================
# SPECIALIZED REPORT BUILDERS
# ==============================================================================

def build_expense_reduction_plan(ctx: dict) -> str:
    c = ctx["currency"]
    total_exp = ctx["total_expenses"]
    income = ctx["total_income"]
    cats = ctx["sorted_categories"]

    lines = []
    lines.append(f"### 🎯 Actionable Expense Reduction Blueprint")
    lines.append(f"Based on your active records, your current monthly outflows are **{c}{total_exp:,.2f}** against inflows of **{c}{income:,.2f}** (Savings Rate: **{ctx['savings_rate']:.1f}%**).")
    lines.append("")

    potential_savings = 0.0

    # 1. Top Category Target
    if cats:
        top_cat, top_amt = cats[0]
        pct = (top_amt / total_exp * 100) if total_exp > 0 else 0
        target_cut = round(top_amt * 0.25, 0)
        potential_savings += target_cut

        lines.append(f"#### 1. Restructure Your Largest Outflow: **{top_cat}**")
        lines.append(f"- **Current Spend**: **{c}{top_amt:,.2f}** ({pct:.1f}% of total expenditures).")
        lines.append(f"- **The Strategy**: This is your highest financial lever. Applying a **25% efficiency target** will save you approximately **{c}{target_cut:,.0f}/month**.")
        if top_cat == "Food & Dining":
            lines.append(f"- **Action Step**: Cap delivery app orders (Swiggy/Zomato) to once per week and meal-prep breakfasts. Replace premium cafe trips with brewed coffee.")
        elif top_cat == "Housing & Utilities":
            lines.append(f"- **Action Step**: Audit utility electricity usage and review shared broadband plans with flatmates to split fixed overhead.")
        elif top_cat == "Education":
            lines.append(f"- **Action Step**: Utilize open-access digital libraries, shared subscription accounts, and free student developer packs.")
        else:
            lines.append(f"- **Action Step**: Implement a strict 3-day buffer before any discretionary purchase above {c}1,000 in this category.")
        lines.append("")

    # 2. Second Category Target
    if len(cats) > 1:
        sec_cat, sec_amt = cats[1]
        sec_cut = round(sec_amt * 0.20, 0)
        potential_savings += sec_cut
        lines.append(f"#### 2. Optimize Secondary Spend: **{sec_cat}**")
        lines.append(f"- **Current Spend**: **{c}{sec_amt:,.2f}**.")
        lines.append(f"- **The Strategy**: Trimming non-essential volume by **20%** unlocks an additional **+{c}{sec_cut:,.0f}/month** in liquidity.")
        lines.append("")

    # 3. Anomaly / Outlier Leaks
    if ctx["anomalies"]:
        leak = ctx["anomalies"][0]
        leak_amt = leak.get("amount", 0.0)
        leak_desc = leak.get("description", "Large expense")
        potential_savings += round(leak_amt * 0.5, 0)
        lines.append(f"#### 3. Eliminate Statistical Spending Leaks (Outliers)")
        lines.append(f"- **Identified Spike**: '{leak_desc}' of **{c}{leak_amt:,.2f}**.")
        lines.append(f"- **The Strategy**: Single-event impulse splurges severely accelerate your burn rate. Establishing an event cap of {c}{round(leak_amt*0.4, 0):,.0f} protects **+{c}{round(leak_amt*0.5, 0):,.0f}**.")
        lines.append("")

    # 4. Subscriptions Audit
    if ctx["subscriptions"]:
        sub_total = ctx["total_subscriptions"]
        sub_cut = round(sub_total * 0.4, 0)
        potential_savings += sub_cut
        lines.append(f"#### 4. Audit Recurring Subscriptions")
        lines.append(f"- **Active Subscriptions**: {len(ctx['subscriptions'])} recurring services totaling **{c}{sub_total:,.2f}/month**.")
        lines.append(f"- **Action Step**: Pause or cancel unused platforms (e.g. streaming or premium add-ons). Estimated recovery: **+{c}{sub_cut:,.0f}/month**.")
        lines.append("")

    # Summary Box
    lines.append("---")
    lines.append(f"### 💡 Total Monthly Savings Potential: **{c}{potential_savings:,.0f}**")
    new_balance = ctx["balance"] + potential_savings
    new_savings_rate = (new_balance / income * 100) if income > 0 else 0
    lines.append(f"- **Projected Net Savings Rate**: **{ctx['savings_rate']:.1f}% ➔ {new_savings_rate:.1f}%**.")
    lines.append(f"- **Annual Wealth Accumulation**: **{c}{potential_savings * 12:,.0f}/year** redirected to investments or emergency buffer.")

    return "\n".join(lines)


def build_spending_breakdown_analysis(ctx: dict) -> str:
    c = ctx["currency"]
    total = ctx["total_expenses"]
    cats = ctx["sorted_categories"]

    lines = [
        f"### 📊 Comprehensive Spending Breakdown",
        f"Here is how your total expenditure of **{c}{total:,.2f}** is distributed across categories:",
        ""
    ]

    for cat, amt in cats:
        pct = (amt / total * 100) if total > 0 else 0
        bar = "█" * int(pct // 5) + "░" * (20 - int(pct // 5))
        status = "🔴 High Outflow" if pct >= 30 else ("🟡 Moderate" if pct >= 15 else "🟢 Controlled")
        lines.append(f"- **{cat}**: **{c}{amt:,.2f}** ({pct:.1f}%) — {status}")
        lines.append(f"  `{bar}`")

    lines.append("")
    lines.append("#### 🧠 Advisor Takeaway:")
    if cats:
        top_cat, top_amt = cats[0]
        lines.append(f"Your #1 cost driver is **{top_cat}** at **{c}{top_amt:,.2f}**. Controlling this single bucket provides the fastest path to positive cash flow.")

    return "\n".join(lines)


def build_anomaly_audit_response(ctx: dict) -> str:
    c = ctx["currency"]
    anomalies = ctx["anomalies"]

    if not anomalies:
        return (
            f"### ✅ No Statistical Spending Anomaly Detected\n\n"
            f"All your recorded transactions currently fall within normal statistical thresholds "
            f"(Z-score < +2.5σ and within 1.5× IQR boundaries). Your spending distribution is consistent.\n\n"
            f"- **Recommendation**: Continue maintaining steady category spending and avoid spontaneous single-event purchases above {c}3,000."
        )

    lines = [
        f"### ⚠️ Anomaly & Leak Audit ({len(anomalies)} Flagged Spikes)",
        f"Our machine learning outlier model has flagged the following high-variance transactions:",
        ""
    ]

    for a in anomalies:
        desc = a.get("description", "Expense")
        amt = a.get("amount", 0.0)
        cat = a.get("category", "General")
        date = a.get("date", "")
        lines.append(f"- **{c}{amt:,.2f}** on **{desc}** ({cat}, {date})")
        lines.append(f"  *Reason*: Single expense significantly exceeds the historical mean for this category.")

    lines.append("")
    lines.append("#### 🛡️ How to Plug These Leaks:")
    lines.append(f"1. **Enforce Hard Event Budgets**: Before hosting dinners or making major electronics purchases, establish an absolute ceiling.")
    lines.append(f"2. **Separate Emergency Reserves**: Move high-ticket items into a dedicated savings reserve rather than spending out of primary operating liquidity.")

    return "\n".join(lines)


def build_savings_goal_response(ctx: dict, msg: str) -> str:
    c = ctx["currency"]
    income = ctx["total_income"]
    expenses = ctx["total_expenses"]
    balance = ctx["balance"]

    # Extract target number if user specified (e.g. "save 5000")
    target_match = re.search(r"(\d+[\d,]*)", msg)
    target = float(target_match.group(1).replace(",", "")) if target_match else 5000.0

    days_remaining = max(1, ctx["forecast"].get("days_in_month", 30) - ctx["forecast"].get("days_elapsed", 15))
    daily_budget_reduction = round(target / days_remaining, 0)

    lines = [
        f"### 🎯 Roadmap to Save **{c}{target:,.0f}**",
        f"To add **{c}{target:,.0f}** to your net reserves across the next **{days_remaining} days**:",
        "",
        f"- **Current Balance**: **{c}{balance:,.2f}**",
        f"- **Daily Reduction Target**: Cut discretionary spending by **{c}{daily_budget_reduction:,.0f} per day**.",
        "",
        "#### Priority Cut Checklist:",
        f"1. **Food Deliveries**: Switch 3 app orders to home cooking (-{c}{round(target*0.4, 0):,.0f}).",
        f"2. **Transport Swaps**: Take metro/bus instead of surge pricing cabs (-{c}{round(target*0.25, 0):,.0f}).",
        f"3. **Subscription Pause**: Temporarily freeze 1 entertainment streaming account (-{c}{round(target*0.15, 0):,.0f}).",
        f"4. **Shopping Freeze**: 14-day zero non-essential shopping rule (-{c}{round(target*0.20, 0):,.0f})."
    ]

    return "\n".join(lines)


def build_50_30_20_response(ctx: dict) -> str:
    c = ctx["currency"]
    income = ctx["total_income"]
    expenses = ctx["total_expenses"]

    if income <= 0:
        return f"Please record monthly income to compute the 50/30/20 financial framework."

    ideal_needs = income * 0.50
    ideal_wants = income * 0.30
    ideal_savings = income * 0.20

    # Categorize
    cats = ctx["category_breakdown"]
    needs_spend = cats.get("Housing & Utilities", 0) + (cats.get("Food & Dining", 0) * 0.6) + cats.get("Transportation", 0)
    wants_spend = (cats.get("Food & Dining", 0) * 0.4) + cats.get("Entertainment", 0) + cats.get("Shopping", 0)
    actual_savings = ctx["balance"]

    lines = [
        f"### 🏛️ 50/30/20 Personal Wealth Audit",
        f"Benchmarked against your total monthly inflows of **{c}{income:,.2f}**:",
        "",
        f"| Category | Ideal (Target) | Your Current Spending | Status |",
        f"|---|---|---|---|",
        f"| **Needs (50%)** | {c}{ideal_needs:,.0f} | {c}{needs_spend:,.0f} ({(needs_spend/income*100):.1f}%) | {'🟢 Healthy' if needs_spend <= ideal_needs else '🔴 Exceeding'} |",
        f"| **Wants (30%)** | {c}{ideal_wants:,.0f} | {c}{wants_spend:,.0f} ({(wants_spend/income*100):.1f}%) | {'🟢 Controlled' if wants_spend <= ideal_wants else '🟡 Trim Discretionary'} |",
        f"| **Savings (20%)** | {c}{ideal_savings:,.0f} | {c}{actual_savings:,.0f} ({(actual_savings/income*100):.1f}%) | {'🟢 Strong Buffer' if actual_savings >= ideal_savings else '🔴 Below Target'} |",
        "",
        "#### 💡 Strategic Adjustment:",
        f"To hit the 20% savings threshold, target a total monthly expense ceiling of **{c}{income * 0.80:,.0f}**."
    ]

    return "\n".join(lines)


def build_food_reduction_response(ctx: dict) -> str:
    c = ctx["currency"]
    food_spend = ctx["category_breakdown"].get("Food & Dining", 0.0)

    lines = [
        f"### 🥗 Food & Dining Spending Optimization",
        f"You have spent **{c}{food_spend:,.2f}** on Food & Dining this month.",
        "",
        "#### 3 High-Yield Reduction Tactics:",
        f"1. **The '2-Delivery Rule'**: Online food delivery apps (Swiggy/Zomato) carry 35–45% markups with delivery & convenience fees. Capping app deliveries to twice a week immediately saves ~**{c}{round(food_spend*0.35, 0):,.0f}/month**.",
        f"2. **Home Brew vs Cafe**: Replacing daily cafe runs with a French press or thermos saves ~**{c}1,800/month**.",
        f"3. **Weekly Grocery Batching**: Buy staple provisions in bulk rather than frequent micro-mart purchases.",
        "",
        f"- **Recommended Monthly Food Budget**: **{c}{round(food_spend * 0.70, 0):,.0f}** (Saves {c}{round(food_spend * 0.30, 0):,.0f})."
    ]
    return "\n".join(lines)


def build_subscription_response(ctx: dict) -> str:
    c = ctx["currency"]
    subs = ctx["subscriptions"]
    total = ctx["total_subscriptions"]

    lines = [
        f"### 📱 Subscription & Recurring Billing Audit",
        f"You currently have **{len(subs)} recurring subscriptions** totaling **{c}{total:,.2f}/month** ({c}{total * 12:,.2f}/year):",
        ""
    ]

    for s in subs:
        lines.append(f"- **{s.get('description')}**: {c}{s.get('amount', 0.0):,.2f}")

    lines.append("")
    lines.append("#### Recommended Action:")
    lines.append("1. **Cancel the 'Zombie' Subscriptions**: If you haven't used a service in the past 14 days, pause it immediately.")
    lines.append("2. **Opt for Annual/Family Bundles**: Switching from monthly to annual billing typically offers a 20-25% discount.")

    return "\n".join(lines)


def build_general_advisor_response(ctx: dict, user_msg: str) -> str:
    c = ctx["currency"]
    lines = [
        f"### 🤖 MoneyMap Financial Intelligence",
        f"I've analyzed your financial situation for this month:",
        f"- **Current Balance**: **{c}{ctx['balance']:,.2f}**",
        f"- **Inflows**: **{c}{ctx['total_income']:,.2f}** | **Outflows**: **{c}{ctx['total_expenses']:,.2f}**",
        f"- **Savings Rate**: **{ctx['savings_rate']:.1f}%** (Health Score: **{ctx['health']['score']}/100**)",
        f"- **Forecast**: {ctx['forecast']['status_message']}",
        "",
        "How can I best assist you today? You can ask me:",
        "- 💡 **'How can I reduce expenses?'** for a personalized reduction blueprint",
        "- 🔍 **'Where am I overspending?'** for category distribution analysis",
        "- ⚠️ **'Audit my anomalies'** to identify financial leaks and spikes",
        "- 🎯 **'How do I save {c}5,000 this month?'** for a custom daily roadmap"
    ]
    return "\n".join(lines)
