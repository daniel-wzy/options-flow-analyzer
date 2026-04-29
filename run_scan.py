#!/usr/bin/env python3
"""Quick multi-ticker scan runner"""
import sys
sys.path.insert(0, '/Users/danielwan/Projects/options-flow-analyzer')

import json
import time
from backtest import OptionsBacktester

tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD']
threshold = 2.0
min_premium = 100000

all_signals = []

for ticker in tickers:
    backtester = OptionsBacktester(volume_multiplier=threshold, min_premium=min_premium)
    results = backtester.run(ticker, 30)
    backtester.print_report(results, ticker)
    
    for r in results[:5]:  # top 5 per ticker
        s = r.signal
        all_signals.append({
            'ticker': s.ticker,
            'direction': s.direction,
            'option_type': s.option_type,
            'strike': s.strike,
            'expiration': s.expiration,
            'volume_ratio': s.volume_ratio,
            'premium': s.premium_estimate,
            'stock_price': s.stock_price_at_signal,
        })
    
    if ticker != tickers[-1]:
        time.sleep(2)

print("\n\n===JSON_SIGNALS_START===")
print(json.dumps(all_signals, indent=2))
print("===JSON_SIGNALS_END===")
