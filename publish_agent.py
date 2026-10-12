"""
Local MT5 Publisher Agent for DigitalOcean App Platform
Streams real-time ticks and quotes from your local MT5 terminal to your
deployed DigitalOcean web app instance.
"""

import time
import logging
import argparse
import requests
from pipeline.mt5_feed import MT5Feed
from pipeline.config import RAW_PAIRS_UNIVERSE, resolve_symbol_pair

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("publish_agent")


def main():
    parser = argparse.ArgumentParser(description="Publish local MT5 data to cloud ArbitrageLab app")
    parser.add_argument("--cloud-url", type=str, default="http://localhost:8000", help="DigitalOcean App URL (e.g. https://your-app.ondigitalocean.app)")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds")
    args = parser.parse_args()

    feed = MT5Feed()
    if not feed.initialize():
        logger.error("Failed to connect to local MT5 terminal. Make sure MT5 is running.")
        return

    available = feed.get_available_symbols()
    pairs = [resolve_symbol_pair(p, available) for p in RAW_PAIRS_UNIVERSE]
    logger.info(f"Connected to MT5. Streaming {len(pairs)} pairs to {args.cloud_url}...")

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
