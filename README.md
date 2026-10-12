# ArbitrageLab — Cross-Venue Arbitrage Data Pipeline

Data pipeline and statistical backtesting engine powering the Arbitrage Screener between **Hyperliquid** (builder DEXes e.g. `xyz:`) and **MetaTrader 5** (broker CFDs, FX, commodities, equities).

## Pipeline Architecture

- `pipeline/config.py`: Complete universe mappings across 8 categories (Indices, FX, Metals, Commodities, Equities, ETFs) with automatic broker ticker resolution.
- `pipeline/hyperliquid_feed.py`: Hyperliquid Info API client fetching live mid, mark, oracle prices, funding rates, open interest, 24h volume, and 1m historical candles.
- `pipeline/mt5_feed.py`: MT5 Python bridge with automatic broker UTC offset detection, real-time bid/ask/mid spread polling, and M1 rate retrieval with off-market fallbacks.
- `pipeline/synchronizer.py`: Time-series bar alignment on UTC, mark spread calculation, and statistical distribution analytics ($\mu, \sigma, \mu \pm 1\sigma, \mu \pm 2\sigma$).
- `pipeline/cost_and_backtest.py`: Friction modeling (HL taker fee + MT5 spread & commission) and threshold-based mean-reversion trade simulator.
- `pipeline/screener_engine.py`: High-level orchestrator generating screener table snapshots and pair analysis payloads.

## Quick Start

### 1. Run Live Screener in Terminal
```powershell
python run_screener_cli.py
```
Or filter by category:
```powershell
python run_screener_cli.py Indices
python run_screener_cli.py FX
python run_screener_cli.py Metals
```

### 2. Run Test Suite
```powershell
python -m unittest tests/test_pipeline.py
```
