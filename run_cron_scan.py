#!/usr/bin/env python3
"""Cron scan wrapper: runs backtest for multiple tickers and outputs JSON results."""
import sys
import json
import time
sys.path.insert(0, '/Users/danielwan/Projects/options-flow-analyzer')

from backtest import OptionsBacktester

TICKERS = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD"]
THRESHOLD = 2.0
MIN_PREMIUM = 100000

all_signals = []

for ticker in TICKERS:
    try:
        bt = OptionsBacktester(volume_multiplier=THRESHOLD, min_premium=MIN_PREMIUM)
        results = bt.run(ticker, lookback_days=1)
        for r in results:
            s = r.signal
            current_price = s.stock_price_at_signal
            strike = s.strike
            if current_price > 0:
                pct_diff = (strike - current_price) / current_price * 100
                if abs(pct_diff) < 1.0:
                    moneyness = "ATM"
                elif s.option_type == "call":
                    moneyness = "ITM" if strike < current_price else "OTM"
                else:
                    moneyness = "ITM" if strike > current_price else "OTM"
            else:
                moneyness = "Unknown"

            all_signals.append({
                "ticker": s.ticker,
                "option_type": s.option_type,
                "direction": s.direction,
                "strike": s.strike,
                "expiration": s.expiration,
                "volume_ratio": s.volume_ratio,
                "premium": s.premium_estimate,
                "stock_price": current_price,
                "moneyness": moneyness
            })
        time.sleep(1)
    except Exception as e:
        print(f"ERROR scanning {ticker}: {e}", file=sys.stderr)

print(json.dumps(all_signals))
