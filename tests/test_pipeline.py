"""
Unit and integration tests for the ArbitrageLab pipeline.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta

from pipeline.config import RAW_PAIRS_UNIVERSE, resolve_symbol_pair
from pipeline.cost_and_backtest import CostEstimator, SpreadBacktester
from pipeline.synchronizer import DataSynchronizer
from pipeline.hyperliquid_feed import HyperliquidFeed
from pipeline.mt5_feed import MT5Feed


class TestArbitragePipeline(unittest.TestCase):

    def test_cost_estimator(self):
        # Example: HL fee 0.01%, ref price 48207, MT5 spread 4.0, MT5 fee 0.0
        cost = CostEstimator.estimate_cost_per_side(
            hl_fee_pct=0.010,
            reference_price=48207.0,
            mt5_avg_spread=4.0,
            mt5_fee=0.0
        )
        self.assertAlmostEqual(cost["hl_fee_cost"], 4.8207, places=4)
        self.assertAlmostEqual(cost["mt5_half_spread"], 2.0, places=4)
        self.assertAlmostEqual(cost["total_cost_per_side"], 6.8207, places=4)

    def test_spread_backtester(self):
        times = pd.date_range("2026-10-10 00:00", periods=10, freq="1min", tz="UTC")
        # Spread values oscillates: -5, 10, -2, 25, -6, 30, ...
        spread_vals = [-5.0, -10.0, 5.0, 25.0, 30.0, 55.0, 20.0, -1.0, 15.0, 5.0]
        df = pd.DataFrame({"spread": spread_vals}, index=times)

        # Long entry <= 0, Long exit >= 20. Sell entry >= 50, Sell exit <= 25. Cost = 1.0/side
        res = SpreadBacktester.run_backtest(
            df_spread=df,
            buy_entry=0.0,
            buy_exit=20.0,
            sell_entry=50.0,
            sell_exit=25.0,
            cost_per_side=1.0
        )
        summary = res["summary"]
        self.assertGreater(summary["total_trades"], 0)
        self.assertTrue("trades" in res)
        self.assertTrue("equity_curve" in res)

    def test_synchronizer_statistics(self):
        series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
        stats = DataSynchronizer.compute_statistics(series)
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["mean"], 30.0)
        self.assertAlmostEqual(stats["u_plus_1s"], 30.0 + stats["std"])
        self.assertAlmostEqual(stats["u_minus_1s"], 30.0 - stats["std"])

    def test_hyperliquid_live_feed(self):
        hl = HyperliquidFeed()
        ctxs = hl.get_meta_and_contexts(dex="xyz")
        self.assertGreater(len(ctxs), 0)
        self.assertTrue("xyz:JP225" in ctxs or "JP225" in ctxs)
        jp_ctx = ctxs.get("xyz:JP225") or ctxs.get("JP225")
        self.assertIsNotNone(jp_ctx["mid_px"])
        self.assertIsNotNone(jp_ctx["oracle_px"])

    def test_autonomous_cloud_fallback(self):
        import pipeline.mt5_feed as mf
        from pipeline.screener_engine import ScreenerEngine

        orig_mt5 = mf.mt5
        try:
            mf.mt5 = None  # Mock cloud environment where MT5 is unavailable
            engine = ScreenerEngine()
            engine.initialize()

            # Test screener table in cloud mode
            rows = engine.get_screener_table()
            self.assertGreater(len(rows), 0)
            row_0 = rows[0]
            self.assertIsNotNone(row_0["current_spread"])
            self.assertIn(row_0["feed_source"], ["Oracle", "MT5", "DEX"])

            # Test pair analysis in cloud mode
            analysis = engine.get_pair_analysis("JP225", "1m", 24)
            df = analysis["aligned_df"]
            self.assertFalse(df.empty)
            self.assertGreater(len(df), 100)
            self.assertEqual(analysis["data_source"], "AUTONOMOUS_ORACLE")
            self.assertGreater(analysis["stats"]["count"], 100)
            self.assertIsNotNone(analysis["metrics"]["current_spread"])
        finally:
            mf.mt5 = orig_mt5

    def test_remote_candles_sync(self):
        from pipeline.screener_engine import ScreenerEngine
        engine = ScreenerEngine()
        engine.initialize()

        sample_candles = [
            {"time": "2026-10-13 00:00:00+00:00", "open": 67000.0, "high": 67050.0, "low": 66980.0, "close": 67010.0, "volume": 10.0},
            {"time": "2026-10-13 00:01:00+00:00", "open": 67010.0, "high": 67060.0, "low": 66990.0, "close": 67020.0, "volume": 12.0}
        ]
        count = engine.update_remote_candles("JP225", sample_candles)
        self.assertEqual(count, 2)
        self.assertIn("JP225", engine._remote_candles)


if __name__ == "__main__":
    unittest.main()
