"""
Local MT5 Publisher Agent for DigitalOcean App Platform
Streams real-time ticks and quotes from your local MT5 terminal to your
deployed DigitalOcean web app instance.
"""

import time
import logging
import argparse
import threading
from typing import List, Dict, Any
import requests
from pipeline.mt5_feed import MT5Feed
from pipeline.config import RAW_PAIRS_UNIVERSE, resolve_symbol_pair

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("publish_agent")


def sync_candles_loop(feed: MT5Feed, pairs: List[Dict[str, Any]], cloud_url: str, interval_sec: float = 60.0):
    """Periodically syncs recent 48h M1 candles for universe symbols to cloud app."""
    endpoint = f"{cloud_url.rstrip('/')}/api/sync-candles"
    while True:
        try:
            logger.info(f"Starting candle synchronization for {len(pairs)} symbols...")
            for p in pairs:
                try:
                    df = feed.get_candles(p["mt5_symbol"], timeframe="1m", lookback_hours=48)
                    if not df.empty:
                        df_export = df.reset_index()
                        df_export["time"] = df_export["time"].astype(str)
                        records = df_export.to_dict(orient="records")
                        resp = requests.post(endpoint, json={"symbol": p["symbol"], "candles": records}, timeout=10)
                        if resp.status_code == 200:
                            logger.info(f"Synced {len(records)} candles for {p['symbol']} ({p['mt5_symbol']})")
                except Exception as e:
                    logger.warning(f"Failed syncing candles for {p['symbol']}: {e}")
                time.sleep(0.5)
            logger.info("Candle synchronization round complete.")
        except Exception as e:
            logger.error(f"Error in candle sync loop: {e}")
        time.sleep(interval_sec)


def main():
    parser = argparse.ArgumentParser(description="Publish local MT5 data to cloud ArbitrageLab app")
    parser.add_argument("--cloud-url", type=str, default="https://odin-arbitrage-screener.onrender.com", help="Render/Cloud App URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Tick polling interval in seconds")
    args = parser.parse_args()

    feed = MT5Feed()
    if not feed.initialize():
        logger.error("Failed to connect to local MT5 terminal. Make sure MT5 is running.")
        return

    available = feed.get_available_symbols()
    pairs = [resolve_symbol_pair(p, available) for p in RAW_PAIRS_UNIVERSE]
    logger.info(f"Connected to MT5. Streaming {len(pairs)} pairs to {args.cloud_url}...")

    # Launch background thread for candle synchronization
    candle_thread = threading.Thread(
        target=sync_candles_loop,
        args=(feed, pairs, args.cloud_url, 60.0),
        daemon=True
    )
    candle_thread.start()

    endpoint = f"{args.cloud_url.rstrip('/')}/api/sync-feed"

    while True:
        try:
            ticks = {}
            for p in pairs:
                tick = feed.get_tick(p["mt5_symbol"])
                if tick:
                    ticks[p["symbol"]] = tick

            if ticks:
                try:
                    resp = requests.post(endpoint, json={"ticks": ticks}, timeout=5)
                    if resp.status_code == 200:
                        logger.info(f"Synced {len(ticks)} ticks to cloud app.")
                except requests.RequestException as e:
                    logger.warning(f"Could not reach cloud app: {e}")

        except Exception as e:
            logger.error(f"Error in publisher loop: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
