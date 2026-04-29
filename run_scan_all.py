#!/usr/bin/env python3
"""Run options flow scan for multiple tickers and output JSON results."""
import sys
import json
sys.path.insert(0, '/Users/danielwan/Projects/options-flow-analyzer')

from backtest import OptionsBacktester

tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD']
threshold = 2.0
min_premium = 100000

scanner = OptionsBacktester(volume_multiplier=threshold, min_premium=min_premium)
all_signals = []

for ticker in tickers:
    try:
        results = scanner.run(ticker, lookback_days=1)
        for r in results:
            s = r.signal
            all_signals.append({
                'ticker': s.ticker,
                'option_type': s.option_type,
                'strike': s.strike,
                'expiration': s.expiration,
                'volume_ratio': s.volume_ratio,
                'premium_estimate': s.premium_estimate,
                'stock_price': s.stock_price_at_signal,
                'direction': s.direction,
                'date': s.date,
            })
    except Exception as e:
        print(f"ERROR scanning {ticker}: {e}", file=sys.stderr)

print("===JSON_OUTPUT===")
print(json.dumps(all_signals))
