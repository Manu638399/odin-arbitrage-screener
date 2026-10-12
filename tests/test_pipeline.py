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


if __name__ == "__main__":
    unittest.main()
