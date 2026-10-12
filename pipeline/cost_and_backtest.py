"""
Spread Cost Estimator & Mean-Reversion Backtest Engine
Simulates static threshold trading rules on historical spread series,
models multi-venue transaction costs (Hyperliquid taker fee + MT5 spread & commissions),
and calculates full performance analytics and equity curves.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np


class CostEstimator:
    """Calculates realistic transaction costs per side across Hyperliquid and MT5."""

    @staticmethod
    def estimate_cost_per_side(
        hl_fee_pct: float,
        reference_price: float,
        mt5_avg_spread: float,
        mt5_fee: float = 0.0
    ) -> Dict[str, float]:
        """
        Estimates the per-side friction in spread price units:
        - hl_cost = (hl_fee_pct / 100.0) * reference_price
        - mt5_spread_cost = mt5_avg_spread / 2.0 (half-spread)
        - mt5_commission = mt5_fee
        - total_cost_per_side = hl_cost + mt5_spread_cost + mt5_commission
        """
        hl_fee_cost = (hl_fee_pct / 100.0) * reference_price
        mt5_half_spread = mt5_avg_spread / 2.0
        total_cost = hl_fee_cost + mt5_half_spread + mt5_fee

        return {
            "hl_fee_cost": hl_fee_cost,
            "mt5_half_spread": mt5_half_spread,
            "mt5_fee": mt5_fee,
            "total_cost_per_side": total_cost
        }


class SpreadBacktester:
    """Backtests spread trading levels on historical series."""

    @staticmethod
    def run_backtest(
        df_spread: pd.DataFrame,
        buy_entry: Optional[float] = None,
        buy_exit: Optional[float] = None,
        sell_entry: Optional[float] = None,
        sell_exit: Optional[float] = None,
        cost_per_side: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes a static threshold backtest on the spread series.

        Rules:
        - Buy side goes long spread (spread <= Buy Entry), exits when (spread >= Buy Exit).
        - Sell side goes short spread (spread >= Sell Entry), exits when (spread <= Sell Exit).
        - Cost charged per side (entry and exit) = 2 * cost_per_side per round-trip trade.
        """
        if df_spread.empty or "spread" not in df_spread.columns:
            return {
                "trades": [],
                "summary": {
                    "total_trades": 0,
                    "win_rate_pct": 0.0,
                    "gross_pnl": 0.0,
                    "total_commission": 0.0,
                    "net_pnl": 0.0,
                    "avg_trade_pnl": 0.0,
                    "max_drawdown": 0.0,
                    "is_profitable": False
                },
                "equity_curve": []
            }

        position = 0  # +1 = Long spread, -1 = Short spread, 0 = Flat
        entry_idx = None
        entry_time = None
        entry_price = 0.0

        trades: List[Dict[str, Any]] = []
        equity_points: List[Dict[str, Any]] = []
        cum_pnl = 0.0

        times = df_spread.index
        spreads = df_spread["spread"].values

        for i in range(len(spreads)):
            current_time = times[i]
            s = spreads[i]

            if position == 0:
                # Flat: check for entries
                if buy_entry is not None and s <= buy_entry:
                    position = 1
                    entry_idx = i
                    entry_time = current_time
                    entry_price = s
                elif sell_entry is not None and s >= sell_entry:
                    position = -1
                    entry_idx = i
                    entry_time = current_time
                    entry_price = s

            elif position == 1:
                # Long: check for exit
                if buy_exit is not None and s >= buy_exit:
                    exit_price = s
                    gross = exit_price - entry_price
                    commission = 2.0 * cost_per_side
                    net = gross - commission
                    cum_pnl += net

                    entry_iso = str(entry_time)
                    exit_iso = str(current_time)
                    entry_disp = entry_time.strftime("%m-%d %H:%M") if hasattr(entry_time, "strftime") else str(entry_time)[5:16]
                    exit_disp = current_time.strftime("%m-%d %H:%M") if hasattr(current_time, "strftime") else str(current_time)[5:16]

                    trades.append({
                        "trade_num": len(trades) + 1,
                        "side": "Long",
                        "entry_time": entry_iso,
                        "exit_time": exit_iso,
                        "entry_time_display": entry_disp,
                        "exit_time_display": exit_disp,
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "gross": round(gross, 4),
                        "commission": round(commission, 4),
                        "net": round(net, 4),
                        "is_open": False
                    })
                    position = 0

            elif position == -1:
                # Short: check for exit
                if sell_exit is not None and s <= sell_exit:
                    exit_price = s
                    gross = entry_price - exit_price
                    commission = 2.0 * cost_per_side
                    net = gross - commission
                    cum_pnl += net

                    entry_iso = str(entry_time)
                    exit_iso = str(current_time)
                    entry_disp = entry_time.strftime("%m-%d %H:%M") if hasattr(entry_time, "strftime") else str(entry_time)[5:16]
                    exit_disp = current_time.strftime("%m-%d %H:%M") if hasattr(current_time, "strftime") else str(current_time)[5:16]

                    trades.append({
                        "trade_num": len(trades) + 1,
                        "side": "Short",
                        "entry_time": entry_iso,
                        "exit_time": exit_iso,
                        "entry_time_display": entry_disp,
                        "exit_time_display": exit_disp,
                        "entry_price": round(entry_price, 4),
                        "exit_price": round(exit_price, 4),
                        "gross": round(gross, 4),
                        "commission": round(commission, 4),
                        "net": round(net, 4),
                        "is_open": False
                    })
                    position = 0

            # Record running equity
            equity_points.append({
                "time": str(current_time),
                "cum_pnl": round(cum_pnl, 4)
            })

        # Handle open position at end of window
        if position != 0 and entry_time is not None:
            last_price = spreads[-1]
            if position == 1:
                gross = last_price - entry_price
            else:
                gross = entry_price - last_price
            commission = 2.0 * cost_per_side
            net = gross - commission
            entry_iso = str(entry_time)
            exit_iso = str(times[-1])
            entry_disp = entry_time.strftime("%m-%d %H:%M") if hasattr(entry_time, "strftime") else str(entry_time)[5:16]
            exit_disp = times[-1].strftime("%m-%d %H:%M") if hasattr(times[-1], "strftime") else str(times[-1])[5:16]

            trades.append({
                "trade_num": len(trades) + 1,
                "side": "Long" if position == 1 else "Short",
                "entry_time": entry_iso,
                "exit_time": exit_iso,
                "entry_time_display": entry_disp,
                "exit_time_display": exit_disp,
                "entry_price": round(entry_price, 4),
                "exit_price": round(last_price, 4),
                "gross": round(gross, 4),
                "commission": round(commission, 4),
                "net": round(net, 4),
                "is_open": True
            })

        # Summary statistics
        total_trades = len(trades)
        won_trades = sum(1 for t in trades if t["net"] > 0)
        lost_trades = sum(1 for t in trades if t["net"] < 0)
        flat_trades = sum(1 for t in trades if t["net"] == 0)
        win_rate = float(won_trades / total_trades * 100.0) if total_trades > 0 else 0.0
        total_gross = float(sum(t["gross"] for t in trades))
        total_comm = float(sum(t["commission"] for t in trades))
        net_total = float(sum(t["net"] for t in trades))
        avg_trade = float(net_total / total_trades) if total_trades > 0 else 0.0

        # Calculate Max Drawdown from equity series
        cum_series = np.array([p["cum_pnl"] for p in equity_points])
        if len(cum_series) > 0:
            running_max = np.maximum.accumulate(cum_series)
            drawdown = cum_series - running_max
            max_drawdown = float(drawdown.min())
        else:
            max_drawdown = 0.0

        return {
            "trades": trades,
            "summary": {
                "total_trades": int(total_trades),
                "won_trades": int(won_trades),
                "lost_trades": int(lost_trades),
                "flat_trades": int(flat_trades),
                "win_rate_pct": round(win_rate, 1),
                "win_rate_detail": f"({won_trades} won / {lost_trades} lost / {flat_trades} fl)",
                "gross_pnl": round(total_gross, 4),
                "total_commission": round(total_comm, 4),
                "net_pnl": round(net_total, 4),
                "avg_trade_pnl": round(avg_trade, 4),
                "max_drawdown": round(max_drawdown, 4),
                "is_profitable": bool(net_total > 0)
            },
            "equity_curve": equity_points
        }
