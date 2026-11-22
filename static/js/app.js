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
// SUPABASE CLIENT & OAUTH AUTHENTICATION
// ==========================================================================

const SUPABASE_PROJECT_URL = "https://arhfznmlbjxevsqstkcp.supabase.co";
const SUPABASE_ANON_KEY = "sb_publishable_EBri7mpKhoWGtj3Angz1og_mu70Oauh";
let _supabaseClient = null;

function getSupabaseClient() {
    if (!_supabaseClient && window.supabase && SUPABASE_PROJECT_URL && SUPABASE_ANON_KEY) {
        try {
            _supabaseClient = window.supabase.createClient(SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY);
        } catch (e) {
            console.error("Failed to initialize Supabase client", e);
        }
    }
    return _supabaseClient;
}

async function loginWithOAuth(provider) {
    const client = getSupabaseClient();
    if (!client) {
        showToast("Supabase client is not loaded. Please try again.", "error");
        return;
    }
    showToast(`Redirecting to ${provider.toUpperCase()}...`, "info");
    const { data, error } = await client.auth.signInWithOAuth({
        provider: provider,
        options: {
            redirectTo: window.location.origin
        }
    });
    if (error) {
        showToast(error.message, "error");
    }
}

// ==========================================================================
// INITIALIZATION
// ==========================================================================

document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initAuthListeners();
    initWealthSimulator();
    initKeyboardShortcuts();
    checkAuth();
});

// Theme Management
function initTheme() {
    const savedTheme = localStorage.getItem("moneymap_theme") || localStorage.getItem("expenseai_theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme") || "light";
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
            const isAuthEndpoint = endpoint.includes("/api/auth/login") || endpoint.includes("/api/auth/register") || endpoint.includes("/api/auth/me");
            if (!isAuthEndpoint) {
                handleLogout(false);
                throw new Error("Session expired. Please sign in again.");
            }
        }
        let data;
        const contentType = res.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            try {
                data = await res.json();
            } catch (_) {
                data = { error: "Invalid response format from server" };
            }
        } else {
            const text = await res.text();
            data = { error: res.ok ? text : `Server error (${res.status})` };
        }
        if (!res.ok) {
            throw new Error(data.error || "Request failed");
        }
        return data;
    } catch (err) {
        if (!options.silent) {
            showToast(err.message, "error");
        }
        throw err;
    }
}

// ==========================================================================
// AUTHENTICATION
// ==========================================================================

function initAuthListeners() {
    // No additional auth listeners needed — login and register forms use onsubmit handlers.
}

async function checkAuth() {
    // 1. Check for Supabase OAuth session (from redirect)
    const client = getSupabaseClient();
    if (client) {
        try {
            const { data: { session } } = await client.auth.getSession();
            if (session && session.access_token) {
                state.token = session.access_token;
                localStorage.setItem("moneymap_token", session.access_token);
                // Clean URL hash if returned from OAuth redirect
                if (window.location.hash && window.location.hash.includes("access_token")) {
                    history.replaceState(null, "", window.location.pathname + window.location.search);
                }
            }
        } catch (err) {
            console.warn("Supabase OAuth check:", err);
        }
    }

    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get("theme");
    if (themeParam) {
        document.documentElement.setAttribute("data-theme", themeParam);
        localStorage.setItem("moneymap_theme", themeParam);
    }

    if (!state.token) {
        showAuthScreen();
        return;
    }
    try {
        const data = await apiRequest("/api/auth/me", { silent: true });
        state.user = data.user;
        state.currency = data.user.currency || "₹";
        showMainApp();
        initAppDashboard();
        if (urlParams.get("chat") === "1") {
            setTimeout(toggleAIChat, 100);
        }
    } catch (e) {
        // Token was stored but server rejected it — clear it and show auth screen
        state.token = null;
        localStorage.removeItem("moneymap_token");
        localStorage.removeItem("expenseai_token");
        showAuthScreen();
        if (e.message && !e.message.includes("401")) {
            showToast("Connection error — please sign in again.", "error");
        }
    }
}

function openAuthModal(tab = "login") {
    const modal = document.getElementById("auth-modal");
    if (modal) {
        modal.classList.remove("hidden");
    }
    switchAuthTab(tab);
}

function closeAuthModal() {
    const modal = document.getElementById("auth-modal");
    if (modal) {
        modal.classList.add("hidden");
    }
}

function handleAuthModalBackdropClick(e) {
    if (e.target.id === "auth-modal") {
        closeAuthModal();
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
        showToast(`Welcome, ${res.user.name}! Your account is ready.`, "success");
        showMainApp();
        initAppDashboard();
    } catch (err) {}
}

function handleLogout(showToastMsg = true) {
    state.token = null;
    state.user = null;
    localStorage.removeItem("moneymap_token");
    localStorage.removeItem("expenseai_token");
    fetch("/api/auth/logout", { method: "POST" });
    showAuthScreen();
    if (showToastMsg) {
        showToast("Signed out", "info");
    }
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
    closeAuthModal();
    document.getElementById("auth-screen").classList.add("hidden");
    document.getElementById("main-app").classList.remove("hidden");
    const launcher = document.getElementById("ai-chat-launcher");
    if (launcher) launcher.classList.remove("hidden");
    initAIChatIfEmpty();

    if (state.user) {
        const initials = state.user.name.split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);
        const initialsEl = document.getElementById("nav-user-initials");
        if (initialsEl) initialsEl.textContent = initials || "Me";
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

function toggleSidebar(forceState) {
    const sidebar = document.getElementById("app-sidebar");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (!sidebar) return;
    const shouldOpen = typeof forceState === "boolean" ? forceState : !sidebar.classList.contains("sidebar-open");
    if (shouldOpen) {
        sidebar.classList.add("sidebar-open");
        if (backdrop) backdrop.classList.add("active");
    } else {
        sidebar.classList.remove("sidebar-open");
        if (backdrop) backdrop.classList.remove("active");
    }
}

function closeSidebarOnMobile() {
    if (window.innerWidth <= 1024) {
        toggleSidebar(false);
    }
}

function switchView(viewName) {
    state.currentView = viewName;
    if (window.location.hash !== `#${viewName}`) {
        history.replaceState(null, "", `#${viewName}`);
    }
    closeSidebarOnMobile();
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
    const monthEl = document.getElementById("dash-current-month");
    if (monthEl) monthEl.textContent = `${monthNames[now.getMonth()]} ${now.getFullYear()}`;
    
    const hash = window.location.hash.replace("#", "");
    if (["transactions", "budgets", "ml-lab"].includes(hash)) {
        switchView(hash);
    } else {
        loadDashboardData();
    }
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
    // Set loading placeholders on KPI elements before fetching
    const kpiIds = ["kpi-balance", "kpi-income", "kpi-expense"];
    kpiIds.forEach(id => { const el = document.getElementById(id); if (el) el.textContent = "Loading…"; });
    const scoreEl = document.getElementById("kpi-health-score");
    if (scoreEl) scoreEl.textContent = "…";
    const healthBadge = document.getElementById("kpi-health-badge");
    if (healthBadge) { healthBadge.textContent = ""; healthBadge.className = "health-score-badge"; }

    // Use allSettled so a single failing endpoint never crashes the whole dashboard
    const [sumResult, mlResult, txResult] = await Promise.allSettled([
        apiRequest("/api/summary", { silent: true }),
        apiRequest("/api/ml/insights", { silent: true }),
        apiRequest("/api/transactions?limit=6", { silent: true })
    ]);

    // --- Summary / KPI block ---
    if (sumResult.status === "fulfilled") {
        const summary = sumResult.value.summary;

        document.getElementById("kpi-balance").textContent = `${state.currency}${summary.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("kpi-income").textContent = `${state.currency}${summary.total_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
        document.getElementById("kpi-expense").textContent = `${state.currency}${summary.total_expenses.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

        // Update Category Photo Grid spends
        const catMap = {};
        (summary.category_breakdown || []).forEach(c => catMap[c.category] = c.total);
        if (document.getElementById("cat-spend-food")) document.getElementById("cat-spend-food").textContent = `${state.currency}${(catMap["Food & Dining"] || 0).toLocaleString('en-IN')}`;
        if (document.getElementById("cat-spend-edu")) document.getElementById("cat-spend-edu").textContent = `${state.currency}${(catMap["Education"] || 0).toLocaleString('en-IN')}`;
        if (document.getElementById("cat-spend-transit")) document.getElementById("cat-spend-transit").textContent = `${state.currency}${(catMap["Transportation"] || 0).toLocaleString('en-IN')}`;
        if (document.getElementById("cat-spend-housing")) document.getElementById("cat-spend-housing").textContent = `${state.currency}${(catMap["Housing & Utilities"] || 0).toLocaleString('en-IN')}`;

        renderCashflowChart(summary.daily_timeline || []);
        renderCategoryChart(summary.category_breakdown || []);
    } else {
        console.error("Summary load failed:", sumResult.reason);
        // Show meaningful error on KPI elements instead of leaving "Loading…"
        ["kpi-balance", "kpi-income", "kpi-expense"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = "Error — retry";
        });
        showToast("Could not load financial summary. Check your connection.", "error");
    }

    // --- ML Insights / Health Score / Forecast block ---
    if (mlResult.status === "fulfilled") {
        const ml = mlResult.value;
        const health = ml.health || {};
        const healthScore = (health.score !== null && health.score !== undefined) ? health.score : null;

        const scoreEl2 = document.getElementById("kpi-health-score");
        if (scoreEl2) scoreEl2.textContent = healthScore !== null ? `${healthScore}` : "N/A";

        const healthBadge2 = document.getElementById("kpi-health-badge");
        if (healthBadge2) {
            healthBadge2.textContent = health.grade || "Unavailable";
            healthBadge2.className = "health-score-badge";
        }

        const healthFill = document.getElementById("kpi-health-fill");
        if (healthFill && healthScore !== null) {
            if (healthFill.tagName && healthFill.tagName.toLowerCase() === "circle") {
                const circumference = 251.2;
                healthFill.style.strokeDashoffset = circumference * (1 - (healthScore / 100));
            } else {
                healthFill.style.width = `${healthScore}%`;
            }
        }

        const forecast = ml.forecast || {};
        const fMsg = document.getElementById("forecast-status-msg"); if (fMsg) fMsg.textContent = forecast.status_message || "";
        const fBurn = document.getElementById("forecast-burn-rate"); if (fBurn) fBurn.textContent = `${state.currency}${Math.round(forecast.daily_burn_rate || 0)}/day`;
        const fProj = document.getElementById("forecast-projected-total"); if (fProj) fProj.textContent = `${state.currency}${Math.round(forecast.projected_total || 0).toLocaleString('en-IN')}`;
        const fBudg = document.getElementById("forecast-total-budget"); if (fBudg) fBudg.textContent = `${state.currency}${Math.round(ml.total_budget || 0).toLocaleString('en-IN')}`;
    } else {
        console.error("ML insights load failed:", mlResult.reason);
        const scoreEl2 = document.getElementById("kpi-health-score");
        if (scoreEl2) scoreEl2.textContent = "N/A";
        const healthBadge2 = document.getElementById("kpi-health-badge");
        if (healthBadge2) healthBadge2.textContent = "Unavailable";
    }

    // --- Recent Transactions block ---
    if (txResult.status === "fulfilled") {
        renderRecentTransactions(txResult.value.transactions || []);
    } else {
        console.error("Transactions load failed:", txResult.reason);
        // Show empty state with retry rather than silent blank
        const tbody = document.getElementById("recent-transactions-tbody");
        if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="color:var(--text-muted)">
            Could not load transactions.
            <button onclick="loadDashboardData()" style="margin-left:8px;text-decoration:underline;cursor:pointer;background:none;border:none;color:inherit;">Retry</button>
        </td></tr>`;
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

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textMuted = isDark ? "#97a69f" : "#717d77";
    const gridColor = isDark ? "rgba(255, 255, 255, 0.06)" : "rgba(10, 31, 24, 0.05)";

    state.charts.cashflow = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels.length ? labels : ["No data"],
            datasets: [
                {
                    label: "Inflows (Credits)",
                    data: incomeData.length ? incomeData : [0],
                    backgroundColor: "#15623e", // Deep Hunter Emerald
                    borderRadius: 3,
                    maxBarThickness: 20
                },
                {
                    label: "Outflows (Debits)",
                    data: expenseData.length ? expenseData : [0],
                    backgroundColor: "#9e2a2b", // Editorial Burgundy
                    borderRadius: 3,
                    maxBarThickness: 20
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "top",
                    labels: { color: textMuted, font: { family: "Inter", weight: "600", size: 12 } }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: textMuted, font: { family: "Inter", size: 11 } }
                },
                y: {
                    grid: { color: gridColor },
                    ticks: {
                        color: textMuted,
                        font: { family: "JetBrains Mono", size: 11 },
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

    // Editorial Fintech Curated Palette: Forest, Emerald, Sage, Amber, Burgundy, Spruce
    const palette = [
        "#0f2d23", "#15623e", "#3d7a63", "#9e7a2b",
        "#9e2a2b", "#2a3b34", "#4b6b5e", "#b88628", "#1e3b2e"
    ];

    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const textMuted = isDark ? "#97a69f" : "#717d77";
    const borderColor = isDark ? "#121815" : "#ffffff";

    state.charts.category = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels.length ? labels : ["No Expenses"],
            datasets: [{
                data: values.length ? values : [1],
                backgroundColor: palette.slice(0, Math.max(labels.length, 1)),
                borderWidth: 2,
                borderColor: borderColor
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: textMuted, font: { family: "Inter", size: 11, weight: "500" } }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${state.currency}${ctx.raw.toLocaleString('en-IN')}`
                    }
                }
            },
            cutout: "68%"
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
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4" style="color: var(--text-muted); font-size: 0.9rem;">No matching transactions found. Try adjusting your search query or filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = transactions.map(t => `
        <tr>
            <td class="font-mono" style="font-size: 0.85rem; color: var(--text-muted);">${t.date}</td>
            <td><span class="type-pill ${t.type}">${t.type === 'income' ? '+ Income' : '- Expense'}</span></td>
            <td><span class="cat-pill">${t.category}</span></td>
            <td><strong style="font-weight: 600; color: var(--text-primary);">${escapeHtml(t.description || '-')}</strong></td>
            <td class="amount-cell ${t.type === 'income' ? 'income-text' : 'expense-text'} font-mono">
                ${t.type === 'income' ? '+' : '-'}${state.currency}${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </td>
            <td>
                ${t.is_anomaly ? '<span class="anomaly-badge" title="Statistical outlier: Amount significantly deviates from category distribution">Outlier (+2.5σ)</span>' : '<span class="anomaly-badge normal">Normal</span>'}
            </td>
            <td class="text-right">
                <button class="table-action-btn" onclick="openEditTransactionModal(${t.id})" title="Edit transaction">Edit</button>
                <button class="table-action-btn delete-btn" onclick="deleteTransaction(${t.id})" title="Delete transaction">Delete</button>
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
            if (type === "income") {
                triggerCelebrationConfetti();
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
            <div class="glass-panel text-center" style="grid-column: 1 / -1; padding: 48px 24px;">
                <div style="font-size: 2.2rem; margin-bottom: 12px;">🎯</div>
                <h4 style="font-size: 1.15rem; font-weight: 600; margin-bottom: 6px; color: var(--text-primary);">No Category Budgets Configured</h4>
                <p style="color: var(--text-muted); font-size: 0.88rem; max-width: 440px; margin: 0 auto 18px auto; line-height: 1.5;">Establish monthly spending thresholds per functional category to track velocity, maintain cash flow buffers, and prevent deficits.</p>
                <button class="btn btn-primary btn-sm" onclick="openBudgetModal()">+ Set Budget Limit</button>
            </div>
        `;
        return;
    }

    container.innerHTML = budgets.map(b => {
        const pct = Math.min(b.percentage, 100);
        let barClass = "normal";
        let statusBadge = '<span class="budget-status-pill normal">On Track</span>';

        if (b.percentage >= 100) {
            barClass = "exceeded";
            statusBadge = '<span class="budget-status-pill exceeded">Exceeded</span>';
        } else if (b.percentage >= 80) {
            barClass = "warning";
            statusBadge = '<span class="budget-status-pill warning">Near Limit</span>';
        }

        return `
            <div class="budget-card glass-panel">
                <div class="budget-card-header">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="budget-cat-name">${b.category}</span>
                        ${statusBadge}
                    </div>
                    <button class="budget-del-btn" onclick="deleteBudget(${b.id})" title="Delete Budget" aria-label="Delete Budget">✕</button>
                </div>

                <div class="budget-amounts">
                    <div>
                        Spent: <span class="budget-spent-strong font-mono">${state.currency}${b.spent.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div>
                        Limit: <strong class="font-mono">${state.currency}${b.monthly_limit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong>
                    </div>
                </div>

                <div class="budget-bar-track">
                    <div class="budget-bar-fill ${barClass}" style="width: ${pct}%;"></div>
                </div>

                <div class="budget-card-footer">
                    <span class="font-mono">${b.percentage}% utilized</span>
                    <span>Cushion: <strong class="font-mono ${b.is_exceeded ? 'expense-text' : 'income-text'}">${state.currency}${b.remaining.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></span>
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
        triggerCelebrationConfetti();
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
        const currSpendEl = document.getElementById("lab-curr-spend");
        if (currSpendEl) currSpendEl.textContent = `${state.currency}${f.current_spent.toLocaleString('en-IN')}`;
        
        const daysEl = document.getElementById("lab-days-elapsed");
        if (daysEl) daysEl.textContent = `Day ${f.days_elapsed} of ${f.days_in_month}`;
        
        const burnEl = document.getElementById("lab-burn-rate");
        if (burnEl) burnEl.textContent = `${state.currency}${Math.round(f.daily_burn_rate)} / day`;
        
        const projEl = document.getElementById("lab-projected-spend");
        if (projEl) {
            projEl.textContent = `${state.currency}${Math.round(f.projected_total).toLocaleString('en-IN')}`;
            if (f.projected_total > ml.total_budget && ml.total_budget > 0) {
                projEl.className = "f-val font-mono expense-text";
            } else {
                projEl.className = "f-val font-mono income-text";
            }
        }
        
        const targetEl = document.getElementById("lab-budget-target");
        if (targetEl) targetEl.textContent = `Target: ${state.currency}${Math.round(ml.total_budget).toLocaleString('en-IN')}`;
        
        const slopeEl = document.getElementById("lab-slope");
        if (slopeEl) {
            const prefix = f.spending_slope >= 0 ? "+" : "";
            slopeEl.textContent = `${prefix}${state.currency}${f.spending_slope.toFixed(2)}`;
        }

        const alertBox = document.getElementById("lab-forecast-alert");
        if (alertBox) {
            const isExceeded = f.projected_total > ml.total_budget && ml.total_budget > 0;
            alertBox.className = `forecast-status-box ${isExceeded ? 'alert-warning' : 'alert-normal'}`;
            alertBox.innerHTML = `
                <span class="forecast-status-icon">${isExceeded ? '⚠️' : '✓'}</span>
                <div>
                    <strong>Velocity Status:</strong> ${escapeHtml(f.status_message)}
                </div>
            `;
        }

        // Anomalies List
        const anomalyContainer = document.getElementById("lab-anomalies-container");
        if (anomalyContainer) {
            if (!ml.anomalies || ml.anomalies.length === 0) {
                anomalyContainer.innerHTML = `
                    <div class="empty-state-notice">
                        <span class="notice-icon">✓</span>
                        <div>
                            <strong>No Statistical Outliers Detected</strong>
                            <p>All recorded transactions fall within expected category distribution limits (Z-score &lt; +2.5σ and 1.5× IQR).</p>
                        </div>
                    </div>
                `;
            } else {
                anomalyContainer.innerHTML = ml.anomalies.map(a => `
                    <div class="anomaly-item">
                        <div class="anomaly-desc">
                            <strong>${escapeHtml(a.description || 'Expense')} • <span class="cat-pill">${a.category}</span></strong>
                            <span class="anomaly-meta font-mono">Date: ${a.date} | Statistical Outlier (Z-score ≥ +2.5σ)</span>
                        </div>
                        <div class="anomaly-amount font-mono expense-text">${state.currency}${a.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    </div>
                `).join("");
            }
        }

        // Recommendations List
        const recContainer = document.getElementById("lab-recommendations-list");
        if (recContainer) {
            if (!ml.health || !ml.health.recommendations || ml.health.recommendations.length === 0) {
                recContainer.innerHTML = `
                    <div class="empty-state-notice">
                        <span class="notice-icon">ℹ️</span>
                        <div>
                            <strong>No Recommendations Yet</strong>
                            <p>Record additional transactions and set monthly budgets to unlock tailored fiscal guidance.</p>
                        </div>
                    </div>
                `;
            } else {
                recContainer.innerHTML = ml.health.recommendations.map(r => `
                    <div class="rec-item">
                        <span class="rec-bullet">◆</span>
                        <div class="rec-text">${escapeHtml(r)}</div>
                    </div>
                `).join("");
            }
        }

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

        const catEl = document.getElementById("sandbox-predicted-cat");
        if (catEl) catEl.textContent = data.category;
        const confEl = document.getElementById("sandbox-predicted-conf");
        if (confEl) confEl.textContent = `${data.confidence}% Confidence`;

        const barsContainer = document.getElementById("sandbox-prob-bars");
        if (barsContainer && data.probabilities) {
            barsContainer.innerHTML = data.probabilities.map(p => `
                <div class="prob-row">
                    <span class="prob-cat-name">${p.category}</span>
                    <div class="prob-bar-container">
                        <div class="prob-bar-fill" style="width: ${Math.max(p.confidence, 4)}%;"></div>
                    </div>
                    <span class="prob-pct-val font-mono">${p.confidence}%</span>
                </div>
            `).join("");
        }
    } catch (err) {
        console.error(err);
    }
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

// ==========================================================================
// CELEBRATION CONFETTI & UX ENHANCEMENTS
// ==========================================================================

function triggerCelebrationConfetti() {
    if (typeof window.confetti === "function") {
        window.confetti({
            particleCount: 80,
            spread: 70,
            origin: { y: 0.65 },
            colors: ['#15623e', '#0d9488', '#9e7a2b', '#7c3aed', '#34d399']
        });
    }
}

// Transaction Modal Quick Chips
function addTxQuickAmount(val) {
    const el = document.getElementById("tx-amount");
    if (!el) return;
    const current = parseFloat(el.value) || 0;
    el.value = (current + val).toFixed(2);
}

function setTxQuickDate(preset) {
    const el = document.getElementById("tx-date");
    if (!el) return;
    const now = new Date();
    if (preset === "today") {
        el.value = now.toISOString().split("T")[0];
    } else if (preset === "yesterday") {
        const y = new Date(now);
        y.setDate(y.getDate() - 1);
        el.value = y.toISOString().split("T")[0];
    } else if (preset === "first") {
        const y = now.getFullYear();
        const m = String(now.getMonth() + 1).padStart(2, "0");
        el.value = `${y}-${m}-01`;
    }
}

// ==========================================================================
// INTERACTIVE 50/30/20 WEALTH & SAFE SPEND SIMULATOR
// ==========================================================================

function initWealthSimulator() {
    const input = document.getElementById("sim-income-input");
    const slider = document.getElementById("sim-income-slider");
    if (input && slider) {
        recalcWealthSimulator(parseFloat(input.value) || 60000);
    }
}

function handleSimInputChange(e) {
    let val = parseFloat(e.target.value) || 0;
    val = Math.max(0, val);
    const slider = document.getElementById("sim-income-slider");
    if (slider) slider.value = Math.min(val, 500000);
    recalcWealthSimulator(val);
}

function handleSimSliderChange(e) {
    const val = parseFloat(e.target.value) || 0;
    const input = document.getElementById("sim-income-input");
    if (input) input.value = val;
    recalcWealthSimulator(val);
}

function recalcWealthSimulator(income) {
    const label = document.getElementById("sim-slider-val-label");
    if (label) label.textContent = `₹${Math.round(income).toLocaleString('en-IN')} / month`;

    const needs = income * 0.50;
    const wants = income * 0.30;
    const savings = income * 0.20;
    const safeDailyBurn = (needs + wants) / 30;

    const needsEl = document.getElementById("sim-needs-amt");
    if (needsEl) needsEl.textContent = `₹${Math.round(needs).toLocaleString('en-IN')}`;

    const wantsEl = document.getElementById("sim-wants-amt");
    if (wantsEl) wantsEl.textContent = `₹${Math.round(wants).toLocaleString('en-IN')}`;

    const savingsEl = document.getElementById("sim-savings-amt");
    if (savingsEl) savingsEl.textContent = `₹${Math.round(savings).toLocaleString('en-IN')}`;

    const burnEl = document.getElementById("sim-daily-burn");
    if (burnEl) burnEl.textContent = `₹${Math.round(safeDailyBurn).toLocaleString('en-IN')} / day`;
}

function triggerSimulatorCelebration() {
    triggerCelebrationConfetti();
    showToast("50/30/20 Safe Cushion Calculated! ₹12,000+ compounding monthly.", "success");
}

// ==========================================================================
// KEYBOARD SHORTCUTS & MODAL (UX)
// ==========================================================================

function toggleShortcutsModal() {
    const modal = document.getElementById("shortcuts-modal");
    if (!modal) return;
    if (modal.classList.contains("hidden")) {
        modal.classList.remove("hidden");
    } else {
        modal.classList.add("hidden");
    }
}

function initKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
        // If typing in form input / textarea / select, ignore single key shortcuts
        const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : "";
        const isEditing = tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable;

        if (e.key === "Escape") {
            // Close open modals
            const openModals = document.querySelectorAll(".modal-overlay:not(.hidden), .auth-modal-backdrop:not(.hidden)");
            openModals.forEach(m => m.classList.add("hidden"));
            return;
        }

        if (isEditing) return;

        if (e.key === "?" || (e.shiftKey && e.key === "/")) {
            e.preventDefault();
            toggleShortcutsModal();
        } else if (e.key === "n" || e.key === "N") {
            e.preventDefault();
            if (state.token) openAddTransactionModal();
        } else if (e.key === "b" || e.key === "B") {
            e.preventDefault();
            if (state.token) openBudgetModal();
        } else if (e.key === "d" || e.key === "D") {
            e.preventDefault();
            if (state.token) switchView("dashboard");
        } else if (e.key === "t" || e.key === "T") {
            e.preventDefault();
            if (state.token) switchView("transactions");
        } else if (e.key === "l" || e.key === "L") {
            e.preventDefault();
            if (state.token) switchView("ml-lab");
        } else if (e.key === "a" || e.key === "A") {
            e.preventDefault();
            if (state.token) toggleAIChat();
        } else if (e.key === "m" || e.key === "M") {
            e.preventDefault();
            toggleTheme();
        }
    });
}
