/**
 * High-Performance Chart Rendering Engine for ArbitrageLab
 * Mirror copy of ODIN RESEARCH ArbitrageLab using Plotly.js
 */

const BASE_CHART_THEME = {
  paper_bgcolor: "#12151c",
  plot_bgcolor: "#12151c",
  font: {
    family: "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
    size: 11,
    color: "#9ca3af"
  },
  margin: { t: 25, r: 25, b: 45, l: 65 },
  uirevision: "fixed",
  hovermode: "x unified",
  hoverlabel: {
    bgcolor: "#1a202c",
    bordercolor: "#2d3748",
    font: { color: "#ffffff", size: 11 }
  },
  xaxis: {
    title: { text: "Time (UTC)", font: { size: 10, color: "#64748b" } },
    gridcolor: "#1c2230",
    linecolor: "#202634",
    tickfont: { size: 10, color: "#64748b" },
    showgrid: true,
    zeroline: false
  },
  yaxis: {
    gridcolor: "#1c2230",
    linecolor: "#202634",
    tickfont: { size: 10, color: "#64748b" },
    showgrid: true,
    zeroline: false
  }
};

const PLOTLY_FAST_CONFIG = {
  responsive: true,
  displayModeBar: false,
  scrollZoom: false,
  showAxisDragHandles: false,
  doubleClick: "reset"
};

/**
 * Chart 1: Raw Close Prices (HL vs MT5)
 */
function renderClosePricesChart(containerId, times, hlClose, mt5Close, hlLabel, mt5Label) {
  const traceHL = {
    x: times,
    y: hlClose,
    name: hlLabel || "HyperLiquid",
    type: "scatter",
    mode: "lines",
    line: { color: "#38bdf8", width: 1.5 },
    hoverinfo: "y+name"
  };

  const traceMT5 = {
    x: times,
    y: mt5Close,
    name: mt5Label || "MT5",
    type: "scatter",
    mode: "lines",
    line: { color: "#c084fc", width: 1.5 },
    hoverinfo: "y+name"
  };

  const layout = {
    ...BASE_CHART_THEME,
    yaxis: {
      ...BASE_CHART_THEME.yaxis,
      title: { text: "Close price", font: { size: 10, color: "#64748b" } }
    },
    legend: {
      orientation: "h",
      y: -0.18,
      x: 0,
      font: { color: "#9ca3af", size: 11 },
      bgcolor: "transparent"
    }
  };

  Plotly.react(containerId, [traceHL, traceMT5], layout, PLOTLY_FAST_CONFIG);
}

/**
 * Chart 2: Spread Series & Statistical Bounds
 */
function renderSpreadChart(containerId, times, spread, stats) {
  const traces = [
    {
      x: times,
      y: spread,
      name: "HL — MT5",
      type: "scatter",
      mode: "lines",
      line: { color: "#ffd24a", width: 1.5 },
      hoverinfo: "y+name"
    }
  ];

  const shapes = [];

  if (stats && stats.count > 0 && times.length > 0) {
    const xStart = times[0];
    const xEnd = times[times.length - 1];

    // Mean line
    shapes.push({
      type: "line",
      x0: xStart,
      x1: xEnd,
      y0: stats.mean,
      y1: stats.mean,
      line: { color: "#9ca3af", width: 1, dash: "dash" }
    });

    // +/- 1 std
    shapes.push({
      type: "line",
      x0: xStart,
      x1: xEnd,
      y0: stats.u_plus_1s,
      y1: stats.u_plus_1s,
      line: { color: "rgba(156, 163, 175, 0.4)", width: 1, dash: "dot" }
    });
    shapes.push({
      type: "line",
      x0: xStart,
      x1: xEnd,
      y0: stats.u_minus_1s,
      y1: stats.u_minus_1s,
      line: { color: "rgba(156, 163, 175, 0.4)", width: 1, dash: "dot" }
    });

    // +/- 2 std
    shapes.push({
      type: "line",
      x0: xStart,
      x1: xEnd,
      y0: stats.u_plus_2s,
      y1: stats.u_plus_2s,
      line: { color: "rgba(239, 68, 68, 0.5)", width: 1, dash: "dashdot" }
    });
    shapes.push({
      type: "line",
      x0: xStart,
      x1: xEnd,
      y0: stats.u_minus_2s,
      y1: stats.u_minus_2s,
      line: { color: "rgba(239, 68, 68, 0.5)", width: 1, dash: "dashdot" }
    });
  }

  const layout = {
    ...BASE_CHART_THEME,
    yaxis: {
      ...BASE_CHART_THEME.yaxis,
      title: { text: "Spread (price units)", font: { size: 10, color: "#64748b" } }
    },
    shapes: shapes,
    legend: {
      orientation: "h",
      y: -0.18,
      x: 0,
      font: { color: "#9ca3af", size: 11 },
      bgcolor: "transparent"
    }
  };

  Plotly.react(containerId, traces, layout, PLOTLY_FAST_CONFIG);
}

/**
 * Chart 3: Oracle Basis
 */
function renderOracleBasisChart(containerId, times, oracleBasis) {
  const trace = {
    x: times,
    y: oracleBasis,
    name: "HL oracle — MT5",
    type: "scatter",
    mode: "lines",
    line: { color: "#2dd4bf", width: 1.5 },
    hoverinfo: "y+name"
  };

  const layout = {
    ...BASE_CHART_THEME,
    yaxis: {
      ...BASE_CHART_THEME.yaxis,
      title: { text: "Oracle basis (price units)", font: { size: 10, color: "#64748b" } }
    },
    legend: {
      orientation: "h",
      y: -0.18,
      x: 0,
      font: { color: "#9ca3af", size: 11 },
      bgcolor: "transparent"
    }
  };

  Plotly.react(containerId, [trace], layout, PLOTLY_FAST_CONFIG);
}

/**
 * Chart 4: Cumulative Equity Curve (Backtester)
 */
function renderEquityCurveChart(containerId, equityPoints) {
  if (!equityPoints || equityPoints.length === 0) return;

  const times = equityPoints.map(p => p.time);
  const pnl = equityPoints.map(p => p.cum_pnl);

  const trace = {
    x: times,
    y: pnl,
    name: "Cumulative net PnL",
    type: "scatter",
    mode: "lines",
    line: { color: "#38bdf8", width: 2 },
    hoverinfo: "y+name"
  };

  const layout = {
    ...BASE_CHART_THEME,
    yaxis: {
      ...BASE_CHART_THEME.yaxis,
      title: { text: "Net PnL", font: { size: 10, color: "#64748b" } }
    },
    legend: {
      orientation: "h",
      y: -0.18,
      x: 0,
      font: { color: "#9ca3af", size: 11 },
      bgcolor: "transparent"
    }
  };

  Plotly.react(containerId, [trace], layout, PLOTLY_FAST_CONFIG);
}

/**
 * Chart 5: Spread with Trading Levels and Trade Entry/Exit Markers
 */
function renderSpreadWithTradesChart(containerId, times, spread, levels, trades) {
  if (!times || times.length === 0) return;

  const xStart = times[0];
  const xEnd = times[times.length - 1];

  const traces = [
    {
      x: times,
      y: spread,
      name: "Spread",
      type: "scatter",
      mode: "lines",
      line: { color: "#ffd24a", width: 1.2 },
      hoverinfo: "y+name"
    }
  ];

  // Strategy Level Traces (appear in bottom legend matching Image 5)
  if (levels.buy_entry !== null && !isNaN(levels.buy_entry)) {
    traces.push({
      x: [xStart, xEnd],
      y: [levels.buy_entry, levels.buy_entry],
      name: "Buy entry",
      mode: "lines",
      line: { color: "#10b981", width: 1.2, dash: "dash" },
      hoverinfo: "none"
    });
  }

  if (levels.buy_exit !== null && !isNaN(levels.buy_exit)) {
    traces.push({
      x: [xStart, xEnd],
      y: [levels.buy_exit, levels.buy_exit],
      name: "Buy exit",
      mode: "lines",
      line: { color: "#34d399", width: 1.2, dash: "dot" },
      hoverinfo: "none"
    });
  }

  if (levels.sell_entry !== null && !isNaN(levels.sell_entry)) {
    traces.push({
      x: [xStart, xEnd],
      y: [levels.sell_entry, levels.sell_entry],
      name: "Sell entry",
      mode: "lines",
      line: { color: "#ef4444", width: 1.2, dash: "dash" },
      hoverinfo: "none"
    });
  }

  if (levels.sell_exit !== null && !isNaN(levels.sell_exit)) {
    traces.push({
      x: [xStart, xEnd],
      y: [levels.sell_exit, levels.sell_exit],
      name: "Sell exit",
      mode: "lines",
      line: { color: "#f87171", width: 1.2, dash: "dot" },
      hoverinfo: "none"
    });
  }

  // Trade Execution Markers (Long Entry, Long Exit, Short Entry, Short Exit)
  if (trades && trades.length > 0) {
    const longEntries = trades.filter(t => t.side === "Long");
    const longExits = trades.filter(t => t.side === "Long" && !t.is_open);
    const shortEntries = trades.filter(t => t.side === "Short");
    const shortExits = trades.filter(t => t.side === "Short" && !t.is_open);

    if (longEntries.length > 0) {
      traces.push({
        x: longEntries.map(t => t.entry_time),
        y: longEntries.map(t => t.entry_price),
        name: "Long entry",
        mode: "markers",
        marker: { symbol: "triangle-up", size: 8, color: "#10b981" },
        hoverinfo: "x+y+name"
      });
    }

    if (longExits.length > 0) {
      traces.push({
        x: longExits.map(t => t.exit_time),
        y: longExits.map(t => t.exit_price),
        name: "Long exit",
        mode: "markers",
        marker: { symbol: "triangle-down", size: 8, color: "#34d399" },
        hoverinfo: "x+y+name"
      });
    }

    if (shortEntries.length > 0) {
      traces.push({
        x: shortEntries.map(t => t.entry_time),
        y: shortEntries.map(t => t.entry_price),
        name: "Short entry",
        mode: "markers",
        marker: { symbol: "triangle-down", size: 8, color: "#ef4444" },
        hoverinfo: "x+y+name"
      });
    }

    if (shortExits.length > 0) {
      traces.push({
        x: shortExits.map(t => t.exit_time),
        y: shortExits.map(t => t.exit_price),
        name: "Short exit",
        mode: "markers",
        marker: { symbol: "triangle-up", size: 8, color: "#f87171" },
        hoverinfo: "x+y+name"
      });
    }
  }

  const layout = {
    ...BASE_CHART_THEME,
    yaxis: {
      ...BASE_CHART_THEME.yaxis,
      title: { text: "Spread (price units)", font: { size: 10, color: "#64748b" } }
    },
    legend: {
      orientation: "h",
      y: -0.18,
      x: 0,
      font: { color: "#9ca3af", size: 11 },
      bgcolor: "transparent"
    }
  };

  Plotly.react(containerId, traces, layout, PLOTLY_FAST_CONFIG);
}
