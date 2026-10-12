"""
ArbitrageLab Web API & Application Server
FastAPI backend powering the real-time Arbitrage Screener, Pair Analysis charts,
and the Mean-Reversion Backtester. Fully deployable on DigitalOcean App Platform.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Query, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.screener_engine import ScreenerEngine
from pipeline.cost_and_backtest import CostEstimator, SpreadBacktester
from pipeline.config import RAW_PAIRS_UNIVERSE, CATEGORIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("server")

app = FastAPI(title="ArbitrageLab API", version="1.0.0")

# Enable CORS for cross-origin or development setups
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instance
engine = ScreenerEngine()


@app.on_event("startup")
def startup_event():
    logger.info("Initializing ScreenerEngine...")
    engine.initialize()
    logger.info("ArbitrageLab Engine initialized.")


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "mt5_connected": engine.mt5_feed._is_initialized,
        "remote_ticks_count": len(engine._remote_ticks),
        "server_time_utc": datetime.now(timezone.utc).isoformat()
    }


class SyncFeedRequest(BaseModel):
    ticks: Dict[str, Dict[str, Any]]


@app.post("/api/sync-feed")
def sync_feed(req: SyncFeedRequest):
    engine.update_remote_ticks(req.ticks)
    return {"success": True, "count": len(req.ticks)}


@app.get("/api/categories")
def get_categories():
    return {"categories": CATEGORIES}


@app.get("/api/pairs")
def get_pairs():
    if not engine._initialized:
        engine.initialize()
    return {"pairs": engine._resolved_universe}


@app.get("/api/screener")
def get_screener_data(category: str = Query("All")):
    try:
        rows = engine.get_screener_table(category=category)
        return {
            "success": True,
            "category": category,
            "count": len(rows),
            "updated_at": datetime.now(timezone.utc).strftime("%H:%M:%S UTC"),
            "data": rows
        }
    except Exception as e:
        logger.error(f"Error fetching screener table: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pair-analysis")
def get_pair_analysis_data(
    symbol: str = Query(..., description="Symbol (e.g. JP225, SP500, GOLD)"),
    timeframe: str = Query("1m", description="Candle timeframe e.g. 1m, 5m, 15m, 1h, 1d"),
    lookback_hours: int = Query(48, description="Lookback window in hours")
):
    try:
        analysis = engine.get_pair_analysis(
            symbol=symbol,
            timeframe=timeframe,
            lookback_hours=lookback_hours
        )

        df = analysis["aligned_df"]
        times = []
        hl_close = []
        mt5_close = []
        spread = []
        oracle_basis = []

        if not df.empty:
            times = [str(t) for t in df.index]
            hl_close = [float(x) for x in df["hl_close"].tolist()]
            mt5_close = [float(x) for x in df["mt5_close"].tolist()]
            spread = [float(x) for x in df["spread"].tolist()]
            # Oracle basis: estimate or live basis
            ref_oracle_diff = analysis["metrics"]["oracle_spread"] or 0.0
            oracle_basis = [float(s - (analysis["metrics"]["current_spread"] or 0.0) + ref_oracle_diff) for s in spread]

        return {
            "success": True,
            "pair": analysis["pair"],
            "metrics": analysis["metrics"],
            "stats": analysis["stats"],
            "chart_data": {
                "count": len(times),
                "times": times,
                "hl_close": hl_close,
                "mt5_close": mt5_close,
                "spread": spread,
                "oracle_basis": oracle_basis
            }
        }
    except Exception as e:
        logger.error(f"Error getting pair analysis for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CostEstimateRequest(BaseModel):
    hl_fee_pct: float
    reference_price: float
    mt5_avg_spread: float
    mt5_fee: float = 0.0


@app.post("/api/cost-estimate")
def estimate_cost(req: CostEstimateRequest):
    result = CostEstimator.estimate_cost_per_side(
        hl_fee_pct=req.hl_fee_pct,
        reference_price=req.reference_price,
        mt5_avg_spread=req.mt5_avg_spread,
        mt5_fee=req.mt5_fee
    )
    return {"success": True, "data": result}


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1m"
    lookback_hours: int = 48
    buy_entry: Optional[float] = None
    buy_exit: Optional[float] = None
    sell_entry: Optional[float] = None
    sell_exit: Optional[float] = None
    cost_per_side: float = 0.0


@app.post("/api/backtest")
def run_backtest(req: BacktestRequest):
    try:
        analysis = engine.get_pair_analysis(
            symbol=req.symbol,
            timeframe=req.timeframe,
            lookback_hours=req.lookback_hours
        )
        df = analysis["aligned_df"]
        result = SpreadBacktester.run_backtest(
            df_spread=df,
            buy_entry=req.buy_entry,
            buy_exit=req.buy_exit,
            sell_entry=req.sell_entry,
            sell_exit=req.sell_exit,
            cost_per_side=req.cost_per_side
        )
        return {
            "success": True,
            "summary": result["summary"],
            "trades": result["trades"],
            "equity_curve": result["equity_curve"]
        }
    except Exception as e:
        logger.error(f"Error executing backtest: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Mount static assets for web UI
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting ArbitrageLab server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
