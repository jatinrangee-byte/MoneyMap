/**
 * MoneyMap - Frontend Client Logic
 * Epple Editorial Design System (Awwwards Inspired)
 * High-Res Photography & Category Photo Grid integration
 */

// Application State
const state = {
    user: null,
    token: localStorage.getItem("moneymap_token") || localStorage.getItem("expenseai_token") || null,
    currency: "₹",
    currentView: "dashboard",
    activeTxType: "expense",
    charts: {
        cashflow: null,
        category: null
    },
    suggestedCategory: null,
    debounceTimers: {}
};

// ==========================================================================
// INITIALIZATION
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initAuthListeners();
    checkAuth();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem("moneymap_theme") || localStorage.getItem("expenseai_theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("moneymap_theme", next);
    updateThemeIcon(next);
    // Re-render charts with theme colors
    if (state.charts.cashflow) state.charts.cashflow.update();
    if (state.charts.category) state.charts.category.update();
}

function updateThemeIcon(theme) {
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) btn.textContent = theme === "dark" ? "🌙" : "☀️";
}

// Toast Notifications
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icon = type === "success" ? "✓" : (type === "error" ? "✕" : "ℹ");
    toast.innerHTML = `<span style="font-weight:700;">${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(15px)";
        setTimeout(() => toast.remove(), 250);
    }, 3500);
}

// API Helper with Auth Bearer Token
async function apiRequest(endpoint, options = {}) {
    const headers = options.headers || {};
    if (state.token) {
        headers["Authorization"] = `Bearer ${state.token}`;
    }
    if (options.body && typeof options.body === "object" && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(options.body);
    }
    options.headers = headers;

    try {
        const res = await fetch(endpoint, options);
        if (res.status === 401) {
            handleLogout();
            throw new Error("Session expired. Please sign in again.");
        }
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || "Request failed");
        }
        return data;
    } catch (err) {
        showToast(err.message, "error");
        throw err;
    }
}

// ==========================================================================
// AUTHENTICATION
// ==========================================================================

function initAuthListeners() {
    const quickDemoBtn = document.getElementById("quick-demo-btn");
    if (quickDemoBtn) {
        quickDemoBtn.addEventListener("click", quickDemoLogin);
    }
}

async function checkAuth() {
    if (!state.token) {
        showAuthScreen();
        return;
    }
    try {
        const data = await apiRequest("/api/auth/me");
        state.user = data.user;
        state.currency = data.user.currency || "₹";
        showMainApp();
        initAppDashboard();
    } catch (e) {
        showAuthScreen();
    }
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById("login-form");
    const regForm = document.getElementById("register-form");
    const tabLogin = document.getElementById("tab-login-btn");
    const tabReg = document.getElementById("tab-register-btn");

    if (tab === "login") {
        loginForm.classList.remove("hidden");
        regForm.classList.add("hidden");
        tabLogin.classList.add("active");
        tabReg.classList.remove("active");
    } else {
        loginForm.classList.add("hidden");
        regForm.classList.remove("hidden");
        tabLogin.classList.remove("active");
        tabReg.classList.add("active");
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
        const res = await apiRequest("/api/auth/login", {
            method: "POST",
            body: { email, password }
        });
        state.token = res.token;
        state.user = res.user;
        state.currency = res.user.currency || "₹";
        localStorage.setItem("moneymap_token", res.token);
        showToast(`Signed in as ${res.user.name}`, "success");
        showMainApp();
        initAppDashboard();
    } catch (err) {}
}

async function handleRegister(e) {
    e.preventDefault();
    const name = document.getElementById("reg-name").value;
    const email = document.getElementById("reg-email").value;
    const password = document.getElementById("reg-password").value;
    const currency = document.getElementById("reg-currency").value;

    try {
        const res = await apiRequest("/api/auth/register", {
            method: "POST",
            body: { name, email, password, currency }
        });
        state.token = res.token;
        state.user = res.user;
        state.currency = res.user.currency || "₹";
        localStorage.setItem("moneymap_token", res.token);
        showToast("Account created successfully with demo records", "success");
        showMainApp();
        initAppDashboard();
    } catch (err) {}
}

async function quickDemoLogin() {
    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: "demo@moneymap.io", password: "demoPassword123" })
        });
        if (res.ok) {
            const data = await res.json();
            state.token = data.token;
            state.user = data.user;
            state.currency = data.user.currency || "₹";
            localStorage.setItem("moneymap_token", data.token);
            showToast("Demo session loaded", "success");
            showMainApp();
            initAppDashboard();
            return;
        }

        const regRes = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: "Alex Sharma",
                email: "demo@moneymap.io",
                password: "demoPassword123",
                currency: "₹"
            })
        });
        const regData = await regRes.json();
        if (regRes.ok) {
            state.token = regData.token;
            state.user = regData.user;
            state.currency = regData.user.currency || "₹";
            localStorage.setItem("moneymap_token", regData.token);
            showToast("Demo session initialized", "success");
            showMainApp();
            initAppDashboard();
        } else {
            showToast(regData.error || "Failed to initialize demo", "error");
        }
    } catch (err) {
        showToast("Error connecting to server", "error");
    }
}

function handleLogout() {
    state.token = null;
    state.user = null;
    localStorage.removeItem("moneymap_token");
    localStorage.removeItem("expenseai_token");
    fetch("/api/auth/logout", { method: "POST" });
    showAuthScreen();
    showToast("Signed out", "info");
}

function showAuthScreen() {
    document.getElementById("auth-screen").classList.remove("hidden");
    document.getElementById("main-app").classList.add("hidden");
    const launcher = document.getElementById("ai-chat-launcher");
    if (launcher) launcher.classList.add("hidden");
    const widget = document.getElementById("ai-chat-widget");
    if (widget) widget.classList.add("hidden");
}

function showMainApp() {
    document.getElementById("auth-screen").classList.add("hidden");
    document.getElementById("main-app").classList.remove("hidden");
    const launcher = document.getElementById("ai-chat-launcher");
    if (launcher) launcher.classList.remove("hidden");
    initAIChatIfEmpty();

    if (state.user) {
        const initials = state.user.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
        const initialsEl = document.getElementById("nav-user-initials");
        if (initialsEl) initialsEl.textContent = initials || "AS";
        const nameEl = document.getElementById("nav-user-name");
        if (nameEl) nameEl.textContent = state.user.name;
        const greetingEl = document.getElementById("dash-greeting-name");
        if (greetingEl) greetingEl.textContent = state.user.name.split(" ")[0];
        document.querySelectorAll(".currency-label").forEach(el => el.textContent = state.currency);
    }
}

// ==========================================================================
// NAVIGATION & VIEWS
// ==========================================================================

function switchView(viewName) {
    state.currentView = viewName;
    document.querySelectorAll(".app-view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));

    const targetView = document.getElementById(`view-${viewName}`);
    if (targetView) targetView.classList.add("active");

    const navItems = document.querySelectorAll(".nav-item");
    if (viewName === "dashboard" && navItems[0]) navItems[0].classList.add("active");
    if (viewName === "transactions" && navItems[1]) navItems[1].classList.add("active");
    if (viewName === "budgets" && navItems[2]) navItems[2].classList.add("active");
    if (viewName === "ml-lab" && navItems[3]) navItems[3].classList.add("active");

    if (viewName === "dashboard") loadDashboardData();
    if (viewName === "transactions") fetchTransactions();
    if (viewName === "budgets") loadBudgets();
    if (viewName === "ml-lab") loadMLLabData();
}

function initAppDashboard() {
    const now = new Date();
    const monthNames = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    document.getElementById("dash-current-month").textContent = `${monthNames[now.getMonth()]} ${now.getFullYear()}`;
    loadDashboardData();
}

function filterByCategory(category) {
    switchView("transactions");
    const catSelect = document.getElementById("filter-category");
    if (catSelect) {
        catSelect.value = category;
        fetchTransactions();
    }
}

// ==========================================================================
// DASHBOARD & SCIENTIFIC CHARTS
// ==========================================================================

async function loadDashboardData() {
    try {
        const [sumRes, mlRes, txRes] = await Promise.all([
            apiRequest("/api/summary"),
            apiRequest("/api/ml/insights"),
            apiRequest("/api/transactions?limit=6")
        ]);

        const summary = sumRes.summary;
        const ml = mlRes;

        // KPI Updates
        document.getElementById("kpi-balance").textContent = `${state.currency}${summary.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("kpi-income").textContent = `${state.currency}${summary.total_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("kpi-expense").textContent = `${state.currency}${summary.total_expenses.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

        // Health Score
        const healthScore = ml.health.score;
        document.getElementById("kpi-health-score").textContent = `${healthScore}/100`;
        const healthBadge = document.getElementById("kpi-health-badge");
        healthBadge.textContent = ml.health.grade;
        healthBadge.className = `health-score-badge`;
        document.getElementById("kpi-health-fill").style.width = `${healthScore}%`;

        // Update Category Photo Grid spends
        const catMap = {};
        summary.category_breakdown.forEach(c => catMap[c.category] = c.total);
        if (document.getElementById("cat-spend-food")) {
            document.getElementById("cat-spend-food").textContent = `${state.currency}${(catMap["Food & Dining"] || 0).toLocaleString('en-IN')}`;
        }
        if (document.getElementById("cat-spend-edu")) {
            document.getElementById("cat-spend-edu").textContent = `${state.currency}${(catMap["Education"] || 0).toLocaleString('en-IN')}`;
        }
        if (document.getElementById("cat-spend-transit")) {
            document.getElementById("cat-spend-transit").textContent = `${state.currency}${(catMap["Transportation"] || 0).toLocaleString('en-IN')}`;
        }
        if (document.getElementById("cat-spend-housing")) {
            document.getElementById("cat-spend-housing").textContent = `${state.currency}${(catMap["Housing & Utilities"] || 0).toLocaleString('en-IN')}`;
        }

        // Forecast Card
        const forecast = ml.forecast;
        document.getElementById("forecast-status-msg").textContent = forecast.status_message;
        document.getElementById("forecast-burn-rate").textContent = `${state.currency}${Math.round(forecast.daily_burn_rate)}/day`;
        document.getElementById("forecast-projected-total").textContent = `${state.currency}${Math.round(forecast.projected_total).toLocaleString('en-IN')}`;
        document.getElementById("forecast-total-budget").textContent = `${state.currency}${Math.round(ml.total_budget).toLocaleString('en-IN')}`;

        // Render Charts with Epple Palette
        renderCashflowChart(summary.daily_timeline);
        renderCategoryChart(summary.category_breakdown);

        // Render Recent Transactions
        renderRecentTransactions(txRes.transactions);
    } catch (err) {
        console.error("Dashboard load failed", err);
    }
}

function renderCashflowChart(dailyTimeline) {
    const ctx = document.getElementById("cashflow-chart");
    if (!ctx) return;

    if (state.charts.cashflow) {
        state.charts.cashflow.destroy();
    }

    const labels = dailyTimeline.map(d => d.date.slice(5)); // 'MM-DD'
    const incomeData = dailyTimeline.map(d => d.income);
    const expenseData = dailyTimeline.map(d => d.expense);

    state.charts.cashflow = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels.length ? labels : ["No data"],
            datasets: [
                {
                    label: "Inflows (Credits)",
                    data: incomeData.length ? incomeData : [0],
                    backgroundColor: "#15803d", // Deep Forest Green
                    borderRadius: 4,
                    maxBarThickness: 22
                },
                {
                    label: "Outflows (Debits)",
                    data: expenseData.length ? expenseData : [0],
                    backgroundColor: "#eb4d28", // Epple Precision Vermilion
                    borderRadius: 4,
                    maxBarThickness: 22
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: { color: "#8b8d96", font: { family: "Inter Tight", weight: "600" } }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: "#8b8d96", font: { family: "Inter Tight" } }
                },
                y: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: {
                        color: "#8b8d96",
                        font: { family: "JetBrains Mono" },
                        callback: val => `${state.currency}${val}`
                    }
                }
            }
        }
    });
}

function renderCategoryChart(categories) {
    const ctx = document.getElementById("category-chart");
    if (!ctx) return;

    if (state.charts.category) {
        state.charts.category.destroy();
    }

    const labels = categories.map(c => c.category);
    const values = categories.map(c => c.total);

    // Epple Architectural Category Palette
    const palette = [
        "#eb4d28", "#121316", "#5a5c63", "#0d9488",
        "#d97706", "#2563eb", "#15803d", "#7c3aed", "#b45309"
    ];

    state.charts.category = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels.length ? labels : ["No Expenses"],
            datasets: [{
                data: values.length ? values : [1],
                backgroundColor: palette.slice(0, Math.max(labels.length, 1)),
                borderWidth: 2,
                borderColor: "#18191d"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: "#8b8d96", font: { family: "Inter Tight", size: 11, weight: "500" } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${state.currency}${ctx.raw.toLocaleString('en-IN')}`
                    }
                }
            },
            cutout: "66%"
        }
    });
}

function renderRecentTransactions(transactions) {
    const tbody = document.getElementById("recent-transactions-tbody");
    if (!tbody) return;

    if (!transactions.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4">No transactions recorded yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = transactions.map(t => `
        <tr>
            <td>${t.date}</td>
            <td><span class="type-pill ${t.type}">${t.type === 'income' ? 'Income' : 'Expense'}</span></td>
            <td><span class="cat-pill">${t.category}</span></td>
            <td><strong>${escapeHtml(t.description || '-')}</strong></td>
            <td class="amount-cell ${t.type === 'income' ? 'income-text' : 'expense-text'}">
                ${t.type === 'income' ? '+' : '-'}${state.currency}${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </td>
            <td>
                ${t.is_anomaly ? '<span class="anomaly-badge">Outlier (+2.5σ)</span>' : '<span class="anomaly-badge normal">Normal</span>'}
            </td>
        </tr>
    `).join("");
}

// ==========================================================================
// TRANSACTIONS VIEW (CRUD)
// ==========================================================================

function debounceFilterTransactions() {
    clearTimeout(state.debounceTimers.txFilter);
    state.debounceTimers.txFilter = setTimeout(() => {
        fetchTransactions();
    }, 200);
}

async function fetchTransactions() {
    const search = document.getElementById("filter-search")?.value || "";
    const type = document.getElementById("filter-type")?.value || "all";
    const category = document.getElementById("filter-category")?.value || "all";
    const startDate = document.getElementById("filter-start-date")?.value || "";
    const endDate = document.getElementById("filter-end-date")?.value || "";

    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (type !== "all") params.append("type", type);
    if (category !== "all") params.append("category", category);
    if (startDate) params.append("start_date", startDate);
    if (endDate) params.append("end_date", endDate);

    try {
        const data = await apiRequest(`/api/transactions?${params.toString()}`);
        renderFullTransactions(data.transactions);
    } catch (err) {
        console.error("Fetch transactions error", err);
    }
}

function renderFullTransactions(transactions) {
    const tbody = document.getElementById("full-transactions-tbody");
    if (!tbody) return;

    if (!transactions.length) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4">No matching transactions found.</td></tr>`;
        return;
    }

    tbody.innerHTML = transactions.map(t => `
        <tr>
            <td>${t.date}</td>
            <td><span class="type-pill ${t.type}">${t.type === 'income' ? 'Income' : 'Expense'}</span></td>
            <td><span class="cat-pill">${t.category}</span></td>
            <td><strong>${escapeHtml(t.description || '-')}</strong></td>
            <td class="amount-cell ${t.type === 'income' ? 'income-text' : 'expense-text'}">
                ${t.type === 'income' ? '+' : '-'}${state.currency}${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </td>
            <td>
                ${t.is_anomaly ? '<span class="anomaly-badge" title="Statistical outlier: Amount significantly higher than normal">Outlier</span>' : '<span class="anomaly-badge normal">Normal</span>'}
            </td>
            <td class="text-right">
                <button class="table-action-btn" onclick="openEditTransactionModal(${t.id})" title="Edit">Edit</button>
                <button class="table-action-btn delete-btn" onclick="deleteTransaction(${t.id})" title="Delete">Delete</button>
            </td>
        </tr>
    `).join("");
}

function resetFilters() {
    if (document.getElementById("filter-search")) document.getElementById("filter-search").value = "";
    if (document.getElementById("filter-type")) document.getElementById("filter-type").value = "all";
    if (document.getElementById("filter-category")) document.getElementById("filter-category").value = "all";
    if (document.getElementById("filter-start-date")) document.getElementById("filter-start-date").value = "";
    if (document.getElementById("filter-end-date")) document.getElementById("filter-end-date").value = "";
    fetchTransactions();
}

// Modal Handlers
function openAddTransactionModal(presetType = null) {
    document.getElementById("tx-id").value = "";
    document.getElementById("modal-title").textContent = "Record Transaction";
    document.getElementById("btn-save-tx").textContent = "Save";
    document.getElementById("tx-amount").value = "";
    document.getElementById("tx-description").value = "";
    document.getElementById("tx-date").value = new Date().toISOString().split("T")[0];
    document.getElementById("ml-suggestion-bubble").classList.add("hidden");

    selectTxType(presetType || "expense");
    openModal("transaction-modal");
}

async function openEditTransactionModal(id) {
    try {
        const data = await apiRequest(`/api/transactions/${id}`);
        const t = data.transaction;

        document.getElementById("tx-id").value = t.id;
        document.getElementById("modal-title").textContent = "Edit Transaction";
        document.getElementById("btn-save-tx").textContent = "Update";
        document.getElementById("tx-amount").value = t.amount;
        document.getElementById("tx-description").value = t.description;
        document.getElementById("tx-date").value = t.date;
        document.getElementById("tx-category").value = t.category;
        document.getElementById("ml-suggestion-bubble").classList.add("hidden");

        selectTxType(t.type);
        openModal("transaction-modal");
    } catch (err) {
        showToast("Failed to load transaction", "error");
    }
}

function selectTxType(type) {
    state.activeTxType = type;
    const expBtn = document.getElementById("tx-type-expense");
    const incBtn = document.getElementById("tx-type-income");

    if (type === "expense") {
        expBtn.classList.add("active");
        incBtn.classList.remove("active");
    } else {
        expBtn.classList.remove("active");
        incBtn.classList.add("active");
    }
}

// Live ML Suggestion as user types note
function handleDescriptionInput(e) {
    const text = e.target.value.trim();
    const bubble = document.getElementById("ml-suggestion-bubble");

    if (text.length < 3) {
        bubble.classList.add("hidden");
        return;
    }

    clearTimeout(state.debounceTimers.mlPredict);
    state.debounceTimers.mlPredict = setTimeout(async () => {
        try {
            const res = await fetch("/api/ml/predict-category", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ description: text })
            });
            const data = await res.json();
            if (data && data.category && data.confidence > 25) {
                state.suggestedCategory = data.category;
                document.getElementById("ml-suggested-category").textContent = data.category;
                document.getElementById("ml-suggested-conf").textContent = `(${data.confidence}% confidence)`;
                bubble.classList.remove("hidden");
            }
        } catch (err) {
            console.error(err);
        }
    }, 180);
}

function applySuggestedCategory() {
    if (state.suggestedCategory) {
        document.getElementById("tx-category").value = state.suggestedCategory;
        document.getElementById("ml-suggestion-bubble").classList.add("hidden");
        showToast(`Category applied: ${state.suggestedCategory}`, "info");
    }
}

async function handleTransactionSubmit(e) {
    e.preventDefault();
    const id = document.getElementById("tx-id").value;
    const type = state.activeTxType;
    const amount = document.getElementById("tx-amount").value;
    const date = document.getElementById("tx-date").value;
    const category = document.getElementById("tx-category").value;
    const description = document.getElementById("tx-description").value;

    const payload = { type, amount, date, category, description };

    try {
        if (id) {
            await apiRequest(`/api/transactions/${id}`, {
                method: "PUT",
                body: payload
            });
            showToast("Transaction updated", "success");
        } else {
            const res = await apiRequest("/api/transactions", {
                method: "POST",
                body: payload
            });
            if (res.is_anomaly) {
                showToast(`Recorded (Outlier: ${res.anomaly_reason})`, "info");
            } else {
                showToast("Transaction recorded", "success");
            }
        }

        closeModal("transaction-modal");
        if (state.currentView === "dashboard") loadDashboardData();
        if (state.currentView === "transactions") fetchTransactions();
        if (state.currentView === "budgets") loadBudgets();
        if (state.currentView === "ml-lab") loadMLLabData();
    } catch (err) {}
}

async function deleteTransaction(id) {
    if (!confirm("Delete this transaction entry?")) return;
    try {
        await apiRequest(`/api/transactions/${id}`, { method: "DELETE" });
        showToast("Transaction removed", "success");
        fetchTransactions();
        if (state.currentView === "dashboard") loadDashboardData();
    } catch (err) {}
}

function exportCSV() {
    window.location.href = `/api/export/csv`;
}

// ==========================================================================
// BUDGETS VIEW
// ==========================================================================

async function loadBudgets() {
    try {
        const data = await apiRequest("/api/budgets");
        const budgets = data.budgets;

        let totalAllocated = 0;
        let totalSpent = 0;

        budgets.forEach(b => {
            totalAllocated += b.monthly_limit;
            totalSpent += b.spent;
        });

        const remaining = Math.max(0, totalAllocated - totalSpent);

        document.getElementById("budget-sum-allocated").textContent = `${state.currency}${totalAllocated.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("budget-sum-spent").textContent = `${state.currency}${totalSpent.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("budget-sum-remaining").textContent = `${state.currency}${remaining.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

        renderBudgetCards(budgets);
    } catch (err) {
        console.error("Budget load error", err);
    }
}

function renderBudgetCards(budgets) {
    const container = document.getElementById("budget-cards-container");
    if (!container) return;

    if (!budgets.length) {
        container.innerHTML = `
            <div class="glass-panel text-center py-4" style="grid-column: 1 / -1;">
                <p>No category budgets defined yet. Click "+ Set Budget Limit" to configure.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = budgets.map(b => {
        const pct = Math.min(b.percentage, 100);
        let barClass = "normal";
        if (b.percentage >= 100) barClass = "exceeded";
        else if (b.percentage >= 80) barClass = "warning";

        return `
            <div class="budget-card glass-panel">
                <div class="budget-card-header">
                    <div>
                        <span class="budget-cat-name">${b.category}</span>
                        ${b.is_exceeded ? '<span class="anomaly-badge" style="margin-left: 8px;">Exceeded</span>' : ''}
                    </div>
                    <button class="budget-del-btn" onclick="deleteBudget(${b.id})" title="Delete Budget">✕</button>
                </div>

                <div class="budget-amounts">
                    <div>
                        Spent: <span class="budget-spent-strong">${state.currency}${b.spent.toLocaleString('en-IN')}</span>
                    </div>
                    <div>
                        Limit: <strong>${state.currency}${b.monthly_limit.toLocaleString('en-IN')}</strong>
                    </div>
                </div>

                <div class="budget-bar-track">
                    <div class="budget-bar-fill ${barClass}" style="width: ${pct}%;"></div>
                </div>

                <div class="budget-card-footer">
                    <span>${b.percentage}% utilized</span>
                    <span>Remaining: ${state.currency}${b.remaining.toLocaleString('en-IN')}</span>
                </div>
            </div>
        `;
    }).join("");
}

function openBudgetModal() {
    document.getElementById("budget-limit").value = "";
    openModal("budget-modal");
}

async function handleBudgetSubmit(e) {
    e.preventDefault();
    const category = document.getElementById("budget-category").value;
    const monthly_limit = document.getElementById("budget-limit").value;

    try {
        await apiRequest("/api/budgets", {
            method: "POST",
            body: { category, monthly_limit }
        });
        showToast(`Budget for ${category} saved`, "success");
        closeModal("budget-modal");
        loadBudgets();
    } catch (err) {}
}

async function deleteBudget(id) {
    if (!confirm("Remove this category budget?")) return;
    try {
        await apiRequest(`/api/budgets/${id}`, { method: "DELETE" });
        showToast("Budget removed", "info");
        loadBudgets();
    } catch (err) {}
}

// ==========================================================================
// INTELLIGENCE LAB
// ==========================================================================

async function loadMLLabData() {
    try {
        const ml = await apiRequest("/api/ml/insights");

        const f = ml.forecast;
        document.getElementById("lab-curr-spend").textContent = `${state.currency}${f.current_spent.toLocaleString('en-IN')}`;
        document.getElementById("lab-days-elapsed").textContent = `Day ${f.days_elapsed} of ${f.days_in_month}`;
        document.getElementById("lab-burn-rate").textContent = `${state.currency}${Math.round(f.daily_burn_rate)} / day`;
        document.getElementById("lab-projected-spend").textContent = `${state.currency}${Math.round(f.projected_total).toLocaleString('en-IN')}`;
        document.getElementById("lab-budget-target").textContent = `Target: ${state.currency}${Math.round(ml.total_budget).toLocaleString('en-IN')}`;
        document.getElementById("lab-slope").textContent = `+${state.currency}${f.spending_slope.toFixed(2)}`;

        const alertBox = document.getElementById("lab-forecast-alert");
        alertBox.innerHTML = `<strong>Pacing:</strong> ${f.status_message}`;

        // Anomalies List
        const anomalyContainer = document.getElementById("lab-anomalies-container");
        if (ml.anomalies.length === 0) {
            anomalyContainer.innerHTML = `<div class="rec-item">All recorded transactions fall within normal statistical bounds.</div>`;
        } else {
            anomalyContainer.innerHTML = ml.anomalies.map(a => `
                <div class="anomaly-item">
                    <div class="anomaly-desc">
                        <strong>${escapeHtml(a.description || 'Expense')} • ${a.category}</strong>
                        <span>Date: ${a.date} | Deviation: Statistical Outlier (Z-score ≥ +2.5σ)</span>
                    </div>
                    <div class="anomaly-amount">${state.currency}${a.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                </div>
            `).join("");
        }

        // Recommendations List
        const recContainer = document.getElementById("lab-recommendations-list");
        recContainer.innerHTML = ml.health.recommendations.map(r => `
            <div class="rec-item">${r}</div>
        `).join("");

        handleMLSandboxInput();
    } catch (err) {
        console.error("ML Lab load error", err);
    }
}

// Interactive ML Categorizer Sandbox
async function handleMLSandboxInput() {
    const input = document.getElementById("ml-test-input");
    const text = (input && input.value.trim()) || "Dominos pizza study meetup with friends";

    try {
        const res = await fetch("/api/ml/predict-category", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description: text })
        });
        const data = await res.json();

        document.getElementById("sandbox-predicted-cat").textContent = data.category;
        document.getElementById("sandbox-predicted-conf").textContent = `${data.confidence}% Confidence`;

        const barsContainer = document.getElementById("sandbox-prob-bars");
        if (barsContainer && data.probabilities) {
            barsContainer.innerHTML = data.probabilities.map(p => `
                <div class="prob-row">
                    <span class="prob-cat-name">${p.category}</span>
                    <div class="prob-bar-container">
                        <div class="prob-bar-fill" style="width: ${Math.max(p.confidence, 4)}%;"></div>
                    </div>
                    <span class="prob-pct-val">${p.confidence}%</span>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error(err);
    }
}

// ==========================================================================
// SEED DEMO DATA
// ==========================================================================

async function triggerSeedData() {
    if (!confirm("Reload sample demonstration transactions and category budgets?")) return;
    try {
        await apiRequest("/api/demo/seed", { method: "POST" });
        showToast("Demo data loaded", "success");
        if (state.currentView === "dashboard") loadDashboardData();
        if (state.currentView === "transactions") fetchTransactions();
        if (state.currentView === "budgets") loadBudgets();
        if (state.currentView === "ml-lab") loadMLLabData();
    } catch (err) {}
}

// ==========================================================================
// MODAL & UTILITIES
// ==========================================================================

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove("hidden");
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add("hidden");
}

function handleModalBackdropClick(e, id) {
    if (e.target.id === id) closeModal(id);
}

function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// ==========================================================================
// AI FINANCIAL ADVISOR CHATBOT
// ==========================================================================

const chatState = {
    isOpen: false,
    history: [],
    isTyping: false
};

function toggleAIChat() {
    chatState.isOpen = !chatState.isOpen;
    const widget = document.getElementById("ai-chat-widget");
    if (!widget) return;

    if (chatState.isOpen) {
        widget.classList.remove("hidden");
        initAIChatIfEmpty();
        setTimeout(() => {
            const input = document.getElementById("chat-input-field");
            if (input) input.focus();
        }, 150);
    } else {
        widget.classList.add("hidden");
    }
}

function initAIChatIfEmpty() {
    const container = document.getElementById("chat-messages-container");
    if (!container || container.children.length > 0) return;

    // Initial greeting from MoneyMap AI
    appendBotMessage(
        `### 👋 Hello, I am your MoneyMap AI Advisor.\n\n` +
        `I continuously analyze your transactions, spending velocity, and budget pacing in real time. ` +
        `My purpose is to help you **eliminate spending leaks, optimize category budgets, and reduce expenses**.\n\n` +
        `Tap any recommendation chip below or ask: *"How can I reduce my expenses?"*`
    );
}

function resetAIChat() {
    chatState.history = [];
    const container = document.getElementById("chat-messages-container");
    if (container) container.innerHTML = "";
    initAIChatIfEmpty();
    showToast("Chat reset", "info");
}

function sendQuickPrompt(promptText) {
    if (chatState.isTyping) return;
    if (!chatState.isOpen) toggleAIChat();
    submitUserChatMessage(promptText);
}

async function handleSendChatMessage(e) {
    e.preventDefault();
    const input = document.getElementById("chat-input-field");
    if (!input) return;
    const text = input.value.trim();
    if (!text || chatState.isTyping) return;
    input.value = "";
    await submitUserChatMessage(text);
}

async function submitUserChatMessage(text) {
    appendUserMessage(text);
    chatState.history.push({ role: "user", content: text });
    showTypingIndicator();

    try {
        const res = await apiRequest("/api/ai/chat", {
            method: "POST",
            body: {
                message: text,
                history: chatState.history.slice(-6)
            }
        });

        hideTypingIndicator();
        appendBotMessage(res.reply);
        chatState.history.push({ role: "assistant", content: res.reply });

        // Update chips if suggested actions exist
        if (res.suggested_actions && res.suggested_actions.length > 0) {
            updateChatChips(res.suggested_actions);
        }
    } catch (err) {
        hideTypingIndicator();
        appendBotMessage(`⚠️ Unable to connect to AI Advisor: ${err.message || 'Server error'}. Please try again.`);
    }
}

function appendUserMessage(text) {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;
    const msg = document.createElement("div");
    msg.className = "chat-msg chat-msg-user";
    msg.textContent = text;
    container.appendChild(msg);
    scrollChatToBottom();
}

function appendBotMessage(markdownText) {
    const container = document.getElementById("chat-messages-container");
    if (!container) return;
    const msg = document.createElement("div");
    msg.className = "chat-msg chat-msg-bot";
    msg.innerHTML = formatChatMarkdown(markdownText);
    container.appendChild(msg);
    scrollChatToBottom();
}

function showTypingIndicator() {
    chatState.isTyping = true;
    const sendBtn = document.getElementById("chat-send-btn");
    if (sendBtn) sendBtn.disabled = true;

    const container = document.getElementById("chat-messages-container");
    if (!container) return;
    const typing = document.createElement("div");
    typing.id = "chat-typing-indicator";
    typing.className = "chat-typing";
    typing.innerHTML = `<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>`;
    container.appendChild(typing);
    scrollChatToBottom();
}

function hideTypingIndicator() {
    chatState.isTyping = false;
    const sendBtn = document.getElementById("chat-send-btn");
    if (sendBtn) sendBtn.disabled = false;

    const el = document.getElementById("chat-typing-indicator");
    if (el) el.remove();
}

function scrollChatToBottom() {
    const container = document.getElementById("chat-messages-container");
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

function updateChatChips(actions) {
    const bar = document.getElementById("chat-chips-bar");
    if (!bar || !actions) return;
    bar.innerHTML = actions.map(act => {
        const clean = act.replace(/'/g, "\\'");
        return `<button class="chat-chip" onclick="sendQuickPrompt('${clean}')">${escapeHtml(act)}</button>`;
    }).join("");
}

function formatChatMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);

    // Headers
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^#### (.*$)/gim, "<h4>$1</h4>");

    // Bold & italic
    html = html.replace(/\*\*(.*?)\*\*/gim, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/gim, "<em>$1</em>");

    // Inline code
    html = html.replace(/`(.*?)`/gim, "<code>$1</code>");

    // Dividers
    html = html.replace(/^---$/gim, "<hr>");

    // Unordered lists
    html = html.replace(/^- (.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gims, "<ul>$1</ul>");

    // Line breaks to paragraphs
    html = html.split("\n\n").map(p => {
        p = p.trim();
        if (!p) return "";
        if (p.startsWith("<h") || p.startsWith("<ul") || p.startsWith("<hr") || p.startsWith("<table")) return p;
        return `<p>${p.replace(/\n/g, "<br>")}</p>`;
    }).join("");

    return html;
}
