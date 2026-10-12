/**
 * Main application logic for ArbitrageLab
 * Mirror copy of ODIN RESEARCH Arbitrage Screener & Backtester
 */

let currentView = "screener";
let currentCategory = "All";
let screenerRows = [];
let columnFilters = {};
let sortCol = "symbol";
let sortAsc = true;
let pairsList = [];
let selectedSymbol = "JP225";
let currentPairData = null;
let currentBacktestResult = null;
let currentTradePage = 1;
const TRADES_PER_PAGE = 15;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  fetchPairsList();
  fetchScreenerData();

  // Route by URL hash if present
  if (window.location.hash === "#pair-analysis") {
    showView("pair-analysis");
  } else {
    showView("screener");
  }

  window.addEventListener("hashchange", () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "pair-analysis") {
      showView("pair-analysis");
    } else {
      showView("screener");
    }
  });

  // Close searchable dropdown on click outside
  document.addEventListener("click", (e) => {
    const wrap = document.querySelector(".searchable-select-wrap");
    if (wrap && !wrap.contains(e.target)) {
      const menu = document.getElementById("pair-dropdown-menu");
      if (menu) menu.classList.remove("open");
    }
  });

  // Auto-refresh screener every 15s in background
  setInterval(() => {
    if (currentView === "screener") {
      fetchScreenerData(true);
    }
  }, 15000);
});

// View Navigation
function showView(viewName) {
  currentView = viewName;
  window.location.hash = viewName;
  document.querySelectorAll(".view-section").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));

  if (viewName === "screener") {
    document.getElementById("view-screener").classList.add("active");
    document.getElementById("nav-screener").classList.add("active");
  } else if (viewName === "pair-analysis") {
    document.getElementById("view-pair-analysis").classList.add("active");
    document.getElementById("nav-pair-analysis").classList.add("active");
    if (selectedSymbol && !currentPairData) {
      loadSelectedPair();
    }
  }
}

// -----------------------------------------------------------------------------
// Screener Functions (Image 1)
// -----------------------------------------------------------------------------

function setCategory(cat) {
  currentCategory = cat;
  document.querySelectorAll(".cat-tab").forEach(tab => {
    tab.classList.toggle("active", tab.innerText.includes(cat) || (cat === "Favorites" && tab.innerText.includes("Favorites")));
  });
  fetchScreenerData();
}

async function fetchScreenerData(isBackground = false) {
  try {
    const res = await fetch(`/api/screener?category=${encodeURIComponent(currentCategory)}`);
    const json = await res.json();
    if (json.success) {
      screenerRows = json.data;
      renderScreenerTable();
    }
  } catch (err) {
    console.error("Failed to fetch screener data:", err);
  }
}

function formatCurrency(val) {
  if (val === null || val === undefined) return "--";
  if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(1)}k`;
  return `$${val.toFixed(0)}`;
}

function renderScreenerTable() {
  const tbody = document.getElementById("screener-tbody");
  tbody.innerHTML = "";

  // Filter rows
  let filtered = screenerRows.filter(r => {
    for (const [key, val] of Object.entries(columnFilters)) {
      if (!val) continue;
      const filterStr = val.trim().toLowerCase();

      if (filterStr.startsWith(">") || filterStr.startsWith("<")) {
        const op = filterStr[0];
        const targetVal = parseFloat(filterStr.slice(1).trim());
        const cellVal = parseFloat(r[key]);
        if (!isNaN(targetVal) && !isNaN(cellVal)) {
          if (op === ">" && cellVal <= targetVal) return false;
          if (op === "<" && cellVal >= targetVal) return false;
        }
      } else {
        const cellStr = String(r[key] || "").toLowerCase();
        if (!cellStr.includes(filterStr)) return false;
      }
    }
    return true;
  });

  // Sort rows
  filtered.sort((a, b) => {
    let va = a[sortCol];
    let vb = b[sortCol];
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    if (typeof va === "string") {
      return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    }
    return sortAsc ? va - vb : vb - va;
  });

  filtered.forEach(r => {
    const tr = document.createElement("tr");

    const spreadClass = r.current_spread > 0 ? "pos" : (r.current_spread < 0 ? "neg" : "");
    const spreadPctClass = r.current_spread_pct > 0 ? "pos" : (r.current_spread_pct < 0 ? "neg" : "");
    const oracleClass = r.oracle_spread > 0 ? "pos" : (r.oracle_spread < 0 ? "neg" : "");

    const spdStr = r.current_spread !== null ? `${r.current_spread > 0 ? "+" : ""}${r.current_spread.toFixed(2)}` : "--";
    const spdPctStr = r.current_spread_pct !== null ? `${r.current_spread_pct > 0 ? "+" : ""}${r.current_spread_pct.toFixed(2)}%` : "--";
    const orcStr = r.oracle_spread !== null ? `${r.oracle_spread > 0 ? "+" : ""}${r.oracle_spread.toFixed(2)}` : "--";
    const fundingLSStr = `${r.ann_funding_long > 0 ? "+" : ""}${r.ann_funding_long.toFixed(2)}% / ${r.ann_funding_short > 0 ? "+" : ""}${r.ann_funding_short.toFixed(2)}%`;
    const fundingArbStr = `${r.funding_arbitrage > 0 ? "+" : ""}${r.funding_arbitrage.toFixed(2)}%`;
    const fundingArbClass = r.funding_arbitrage > 0 ? "pos" : (r.funding_arbitrage < 0 ? "neg" : "");

    tr.innerHTML = `
      <td><span class="star-icon ${r.is_favorite ? 'active' : ''}" onclick="toggleFavorite('${r.symbol}')">★</span></td>
      <td style="font-weight: 600;">${r.symbol}</td>
      <td class="num-cell ${spreadClass}">${spdStr}</td>
      <td class="num-cell ${spreadPctClass}">${spdPctStr}</td>
      <td class="num-cell ${oracleClass}">${orcStr}</td>
      <td class="num-cell">${fundingLSStr}</td>
      <td class="num-cell ${fundingArbClass}">${fundingArbStr}</td>
      <td class="num-cell">${formatCurrency(r.volume_24h_usd)}</td>
      <td class="num-cell">${formatCurrency(r.open_interest_usd)}</td>
      <td style="text-align: right;">
        <button class="btn-view-details" onclick="openPairAnalysis('${r.symbol}')">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          View
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function applyFilters(column, value) {
  columnFilters[column] = value;
  renderScreenerTable();
}

function sortTable(column) {
  if (sortCol === column) {
    sortAsc = !sortAsc;
  } else {
    sortCol = column;
    sortAsc = false;
  }
  renderScreenerTable();
}

function toggleFavorite(symbol) {
  const row = screenerRows.find(r => r.symbol === symbol);
  if (row) {
    row.is_favorite = !row.is_favorite;
    renderScreenerTable();
  }
}

// -----------------------------------------------------------------------------
// Searchable Pair Select Dropdown (Image 2)
// -----------------------------------------------------------------------------

function togglePairDropdown() {
  const menu = document.getElementById("pair-dropdown-menu");
  menu.classList.toggle("open");
  if (menu.classList.contains("open")) {
    const input = document.getElementById("pair-search-input");
    input.value = "";
    filterPairDropdown("");
    setTimeout(() => input.focus(), 50);
  }
}

function filterPairDropdown(query) {
  const q = query.toLowerCase();
  const filtered = pairsList.filter(p => 
    p.label.toLowerCase().includes(q) || 
    p.symbol.toLowerCase().includes(q) ||
    p.hl_symbol.toLowerCase().includes(q) ||
    p.mt5_symbol.toLowerCase().includes(q)
  );
  renderDropdownOptions(filtered);
}

function renderDropdownOptions(pairs) {
  const container = document.getElementById("pair-options-container");
  container.innerHTML = "";
  if (pairs.length === 0) {
    container.innerHTML = `<div style="padding: 10px; color: var(--text-muted); font-size: 11.5px; text-align: center;">No symbols found</div>`;
    return;
  }

  pairs.forEach(p => {
    const div = document.createElement("div");
    div.className = "dropdown-option";
    div.innerText = p.label;
    div.onclick = () => selectPair(p.symbol, p.label);
    container.appendChild(div);
  });
}

function selectPair(symbol, label) {
  selectedSymbol = symbol;
  document.getElementById("pair-selected-label").innerText = label;
  document.getElementById("pair-dropdown-menu").classList.remove("open");
  loadSelectedPair();
}

async function fetchPairsList() {
  try {
    const res = await fetch("/api/pairs");
    const json = await res.json();
    if (json.pairs) {
      pairsList = json.pairs;
      renderDropdownOptions(pairsList);

      const defaultPair = pairsList.find(p => p.symbol === "JP225") || pairsList[0];
      if (defaultPair) {
        selectedSymbol = defaultPair.symbol;
        document.getElementById("pair-selected-label").innerText = defaultPair.label;
      }
    }
  } catch (err) {
    console.error("Failed to load pairs list:", err);
  }
}

function openPairAnalysis(symbol) {
  selectedSymbol = symbol;
  const p = pairsList.find(x => x.symbol === symbol);
  if (p) {
    document.getElementById("pair-selected-label").innerText = p.label;
  }
  showView("pair-analysis");
  loadSelectedPair();
}

// -----------------------------------------------------------------------------
// Pair Analysis Loader & Renderer (Images 2, 3, 4, 5)
// -----------------------------------------------------------------------------

async function loadSelectedPair() {
  if (!selectedSymbol) return;

  const reloadBtn = document.getElementById("btn-reload-pair");
  const origBtnContent = reloadBtn.innerHTML;
  reloadBtn.innerHTML = `
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="spin">
      <path d="M23 4v6h-6"></path>
      <path d="M1 20v-6h6"></path>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
    </svg> Loading...
  `;
  reloadBtn.style.opacity = "0.75";
  reloadBtn.disabled = true;

  const tf = document.getElementById("timeframe-select").value;
  const lookback = document.getElementById("lookback-select").value;

  try {
    const res = await fetch(`/api/pair-analysis?symbol=${encodeURIComponent(selectedSymbol)}&timeframe=${tf}&lookback_hours=${lookback}`);
    const json = await res.json();
    if (!json.success) return;

    currentPairData = json;
    const p = json.pair;
    const m = json.metrics;
    const s = json.stats;
    const c = json.chart_data;

    // Header title matching Image 3: "JP225 — xyz:JP225 vs JP225"
    document.getElementById("pair-analysis-header").innerText = `${p.symbol} — ${p.hl_symbol} vs ${p.mt5_symbol}`;

    // KPI ribbon (horizontal strip)
    const spdStr = m.current_spread !== null ? `${m.current_spread > 0 ? "+" : ""}${m.current_spread.toFixed(2)}` : "--";
    const spdPctStr = m.current_spread_pct !== null ? `${m.current_spread_pct > 0 ? "+" : ""}${m.current_spread_pct.toFixed(2)}%` : "--";
    const orcStr = m.oracle_spread !== null ? `${m.oracle_spread > 0 ? "+" : ""}${m.oracle_spread.toFixed(2)}` : "--";
    const fundingLSStr = `${m.ann_funding_long > 0 ? "+" : ""}${m.ann_funding_long.toFixed(2)}% / ${m.ann_funding_short > 0 ? "+" : ""}${m.ann_funding_short.toFixed(2)}%`;
    const fundingArbStr = `${m.funding_arbitrage > 0 ? "+" : ""}${m.funding_arbitrage.toFixed(2)}%`;

    const kpiSpreadEl = document.getElementById("kpi-spread");
    kpiSpreadEl.innerText = spdStr;
    kpiSpreadEl.className = `kpi-value ${m.current_spread > 0 ? "pos" : (m.current_spread < 0 ? "neg" : "")}`;

    const kpiSpreadPctEl = document.getElementById("kpi-spread-pct");
    kpiSpreadPctEl.innerText = spdPctStr;
    kpiSpreadPctEl.className = `kpi-value ${m.current_spread_pct > 0 ? "pos" : (m.current_spread_pct < 0 ? "neg" : "")}`;

    const kpiOracleEl = document.getElementById("kpi-oracle-spread");
    kpiOracleEl.innerText = orcStr;
    kpiOracleEl.className = `kpi-value ${m.oracle_spread > 0 ? "pos" : (m.oracle_spread < 0 ? "neg" : "")}`;

    document.getElementById("kpi-funding-ls").innerText = fundingLSStr;
    
    const kpiArbEl = document.getElementById("kpi-funding-arb");
    kpiArbEl.innerText = fundingArbStr;
    kpiArbEl.className = `kpi-value ${m.funding_arbitrage > 0 ? "pos" : (m.funding_arbitrage < 0 ? "neg" : "")}`;

    document.getElementById("kpi-volume").innerText = formatCurrency(m.volume_24h_usd);
    document.getElementById("kpi-oi").innerText = formatCurrency(m.open_interest_usd);

    // Chart titles matching Image 3
    document.getElementById("chart-1-title").innerText = `${p.hl_symbol} vs ${p.mt5_symbol} — close price`;
    document.getElementById("chart-2-title").innerText = `Spread: ${p.hl_symbol} — ${p.mt5_symbol}`;
    document.getElementById("chart-3-title").innerText = `Oracle basis: ${p.hl_symbol} oracle — ${p.mt5_symbol} (${tf}, recent window)`;

    // Aligned bars footer text: "5,423 aligned 1m bars | 2024-10-07 13:17 -> 2024-10-12 10:24 UTC"
    const startTimeStr = c.times[0] ? c.times[0].replace("T", " ").slice(0, 16) : "";
    const endTimeStr = c.times[c.count - 1] ? c.times[c.count - 1].replace("T", " ").slice(0, 16) : "";
    document.getElementById("aligned-bars-info").innerText = `${c.count.toLocaleString()} aligned ${tf} bars | ${startTimeStr} -> ${endTimeStr} UTC`;

    // Render 3 Charts (using high-performance Plotly)
    renderClosePricesChart("chart-close-prices", c.times, c.hl_close, c.mt5_close, p.hl_symbol, p.mt5_symbol);
    renderSpreadChart("chart-spread", c.times, c.spread, s);
    renderOracleBasisChart("chart-oracle-basis", c.times, c.oracle_basis);

    // Update Statistical Summary Table below Chart 2
    document.getElementById("stat-std").innerText = s.std !== undefined ? s.std.toFixed(4) : "--";
    document.getElementById("stat-mean").innerText = s.mean !== undefined ? s.mean.toFixed(4) : "--";
    document.getElementById("stat-u-1s-plus").innerText = s.u_plus_1s !== undefined ? s.u_plus_1s.toFixed(4) : "--";
    document.getElementById("stat-u-1s").innerText = s.u_minus_1s !== undefined ? s.u_minus_1s.toFixed(4) : "--";
    document.getElementById("stat-u-2s-plus").innerText = s.u_plus_2s !== undefined ? s.u_plus_2s.toFixed(4) : "--";
    document.getElementById("stat-u-2s-minus").innerText = s.u_minus_2s !== undefined ? s.u_minus_2s.toFixed(4) : "--";

    // Auto-populate Cost Estimator inputs matching pair
    const refPx = (c.hl_close.length > 0 ? c.hl_close[c.hl_close.length - 1] : 48207);
    document.getElementById("cost-ref-price").value = Math.round(refPx);
    document.getElementById("cost-mt5-spread").value = Math.round(m.mt5_spread || 4);
    await applyCostEstimation();

    // Auto-populate default spread entry/exit levels if empty
    if (s.std > 0) {
      const buyEnt = Math.round(s.mean - (1.0 * s.std));
      const buyEx = Math.round(s.mean);
      const sellEnt = Math.round(s.mean + (1.0 * s.std));
      const sellEx = Math.round(s.mean);

      document.getElementById("bt-buy-entry").value = buyEnt;
      document.getElementById("bt-buy-exit").value = buyEx;
      document.getElementById("bt-sell-entry").value = sellEnt;
      document.getElementById("bt-sell-exit").value = sellEx;
    }

    // Run instant backtest
    await runBacktest();

  } catch (err) {
    console.error("Failed to load pair analysis:", err);
  } finally {
    reloadBtn.innerHTML = origBtnContent;
    reloadBtn.style.opacity = "1";
    reloadBtn.disabled = false;
  }
}

// -----------------------------------------------------------------------------
// Backtester Functions (Image 5)
// -----------------------------------------------------------------------------

async function applyCostEstimation() {
  const hlFeePct = parseFloat(document.getElementById("cost-hl-fee").value) || 0.01;
  const mt5Spread = parseFloat(document.getElementById("cost-mt5-spread").value) || 0.0;
  const mt5Fee = parseFloat(document.getElementById("cost-mt5-fee").value) || 0.0;
  const refPrice = parseFloat(document.getElementById("cost-ref-price").value) || 1.0;

  try {
    const res = await fetch("/api/cost-estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hl_fee_pct: hlFeePct,
        reference_price: refPrice,
        mt5_avg_spread: mt5Spread,
        mt5_fee: mt5Fee
      })
    });
    const json = await res.json();
    if (json.success) {
      const d = json.data;
      // Exact formula format matching Image 5:
      // "Estimated cost / side = 4.5848 = HL fee 2.5848 + MT5 spread 2.0000 + MT5 fee 0.0000"
      document.getElementById("cost-formula-display").innerText = 
        `Estimated cost / side = ${d.total_cost_per_side.toFixed(4)} = HL fee ${d.hl_fee_cost.toFixed(4)} + MT5 spread ${d.mt5_half_spread.toFixed(4)} + MT5 fee ${d.mt5_fee.toFixed(4)}`;
      document.getElementById("bt-cost-side").value = d.total_cost_per_side.toFixed(4);
    }
  } catch (err) {
    console.error("Cost estimation error:", err);
  }
}

async function runBacktest() {
  if (!selectedSymbol) return;

  const btn = document.querySelector(".btn-run-backtest");
  if (btn) btn.style.opacity = "0.7";

  const tf = document.getElementById("timeframe-select").value;
  const lookback = parseInt(document.getElementById("lookback-select").value);

  const buyEntry = parseFloat(document.getElementById("bt-buy-entry").value);
  const buyExit = parseFloat(document.getElementById("bt-buy-exit").value);
  const sellEntry = parseFloat(document.getElementById("bt-sell-entry").value);
  const sellExit = parseFloat(document.getElementById("bt-sell-exit").value);
  const costSide = parseFloat(document.getElementById("bt-cost-side").value) || 0.0;

  try {
    const res = await fetch("/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        symbol: selectedSymbol,
        timeframe: tf,
        lookback_hours: lookback,
        buy_entry: isNaN(buyEntry) ? null : buyEntry,
        buy_exit: isNaN(buyExit) ? null : buyExit,
        sell_entry: isNaN(sellEntry) ? null : sellEntry,
        sell_exit: isNaN(sellExit) ? null : sellExit,
        cost_per_side: costSide
      })
    });

    const json = await res.json();
    if (!json.success) return;

    currentBacktestResult = json;
    const s = json.summary;

    // Outcome Banner matching Image 5:
    // Green/Red pill + "285 trades | net +7204.0000 spread units (after +0.0000 commission)"
    const badge = document.getElementById("bt-status-badge");
    const netSign = s.net_pnl > 0 ? "+" : "";
    const commSign = s.total_commission >= 0 ? "+" : "";

    if (s.is_profitable) {
      badge.innerHTML = `
        <span class="badge-status badge-profitable">Profitable</span>
        <span class="bt-summary-stats-text">${s.total_trades} trades | net ${netSign}${s.net_pnl.toFixed(4)} spread units (after ${commSign}${s.total_commission.toFixed(4)} commission)</span>
      `;
    } else {
      badge.innerHTML = `
        <span class="badge-status badge-unprofitable">Unprofitable</span>
        <span class="bt-summary-stats-text">${s.total_trades} trades | net ${netSign}${s.net_pnl.toFixed(4)} spread units (after ${commSign}${s.total_commission.toFixed(4)} commission)</span>
      `;
    }

    // 6 Backtest KPI Cards matching Image 5
    document.getElementById("bt-kpi-trades").innerText = s.total_trades;

    // Win Rate with detail "(142 won / 143 lost / 0 fl)"
    document.getElementById("bt-kpi-winrate").innerText = `+${s.win_rate_pct.toFixed(1)}%`;
    const winrateSubEl = document.getElementById("bt-kpi-winrate-sub");
    if (winrateSubEl) {
      winrateSubEl.innerText = s.win_rate_detail || "";
    }

    // Return on Spread
    document.getElementById("bt-kpi-gross").innerText = s.gross_pnl !== undefined ? `${s.gross_pnl > 0 ? "+" : ""}${s.gross_pnl.toFixed(4)}` : "n/a (no limit units)";
    
    // Commission
    document.getElementById("bt-kpi-comm").innerText = `-${s.total_commission.toFixed(4)}`;

    // Avg / Trade
    document.getElementById("bt-kpi-avg").innerText = `${s.avg_trade_pnl > 0 ? "+" : ""}${s.avg_trade_pnl.toFixed(4)}`;

    // Max Drawdown
    document.getElementById("bt-kpi-dd").innerText = s.max_drawdown.toFixed(4);

    // Render Equity Curve Chart
    renderEquityCurveChart("chart-equity-curve", json.equity_curve);

    // Render Spread with Trades Chart (all 4 markers & levels)
    if (currentPairData && currentPairData.chart_data) {
      const c = currentPairData.chart_data;
      renderSpreadWithTradesChart(
        "chart-spread-trades",
        c.times,
        c.spread,
        { buy_entry: buyEntry, buy_exit: buyExit, sell_entry: sellEntry, sell_exit: sellExit },
        json.trades
      );
    }

    // Render Trades Table
    currentTradePage = 1;
    renderTradesTable();

  } catch (err) {
    console.error("Backtest execution failed:", err);
  } finally {
    if (btn) btn.style.opacity = "1";
  }
}

function renderTradesTable() {
  if (!currentBacktestResult || !currentBacktestResult.trades) return;
  const trades = currentBacktestResult.trades;
  const tbody = document.getElementById("bt-trades-tbody");
  if (trades.length === 0) {
    document.getElementById("bt-page-info").innerText = "0 / 0";
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--text-muted); padding: 18px;">No trades triggered for the specified threshold levels.</td></tr>`;
    return;
  }

  const totalPages = Math.max(1, Math.ceil(trades.length / TRADES_PER_PAGE));
  document.getElementById("bt-page-info").innerText = `${currentTradePage} / ${totalPages}`;

  const startIdx = (currentTradePage - 1) * TRADES_PER_PAGE;
  const pageTrades = trades.slice(startIdx, startIdx + TRADES_PER_PAGE);

  pageTrades.forEach(t => {
    const tr = document.createElement("tr");
    const netClass = t.net > 0 ? "pos" : (t.net < 0 ? "neg" : "");
    const grossClass = t.gross > 0 ? "pos" : (t.gross < 0 ? "neg" : "");
    const openTag = t.is_open ? "*" : "";

    const entryTimeStr = t.entry_time_display || t.entry_time;
    const exitTimeStr = t.exit_time_display || t.exit_time;

    tr.innerHTML = `
      <td>${t.trade_num}${openTag}</td>
      <td style="font-weight: 600; color: ${t.side === 'Long' ? '#10b981' : '#ef4444'};">${t.side}</td>
      <td class="num-cell">${entryTimeStr}</td>
      <td class="num-cell">${exitTimeStr}</td>
      <td class="num-cell">${t.entry_price > 0 ? "+" : ""}${t.entry_price.toFixed(4)}</td>
      <td class="num-cell">${t.exit_price > 0 ? "+" : ""}${t.exit_price.toFixed(4)}</td>
      <td class="num-cell ${grossClass}">${t.gross > 0 ? "+" : ""}${t.gross.toFixed(4)}</td>
      <td class="num-cell">-${t.commission.toFixed(4)}</td>
      <td class="num-cell ${netClass}">${t.net > 0 ? "+" : ""}${t.net.toFixed(4)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function changeTradePage(delta) {
  if (!currentBacktestResult || !currentBacktestResult.trades) return;
  const totalPages = Math.ceil(currentBacktestResult.trades.length / TRADES_PER_PAGE);
  const newPage = currentTradePage + delta;
  if (newPage >= 1 && newPage <= totalPages) {
    currentTradePage = newPage;
    renderTradesTable();
  }
}
