#!/usr/bin/env python3
"""Options flow scanner for NVDA, TSLA, AAPL, MSFT, AMD"""
import sys
import os
sys.path.insert(0, '/Users/danielwan/Projects/options-flow-analyzer')

# We'll replicate what backtest.py does but for multiple tickers
import yfinance as yf
import pandas as pd
from datetime import datetime

TICKERS = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD']
THRESHOLD = 2.0
MIN_PREMIUM = 100000

def scan_ticker(ticker_symbol):
    print(f"\n{'='*60}")
    print(f"SCANNING: {ticker_symbol}")
    print('='*60)
    
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # Get current price
        info = stock.info
        current_price = info.get('regularMarketPrice') or info.get('currentPrice', 0)
        if not current_price:
            hist = stock.history(period='1d')
            current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
        
        print(f"Current price: ${current_price:.2f}")
        
        # Get options expirations
        expirations = stock.options
        if not expirations:
            print("No options data available")
            return []
        
        print(f"Available expirations: {list(expirations[:6])}")
        
        signals = []
        now = datetime.now()
        
        for exp in expirations[:6]:
            try:
                chain = stock.option_chain(exp)
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                days_to_exp = (exp_date - now).days
                
                # Process calls
                calls = chain.calls.copy()
                puts = chain.puts.copy()
                
                for option_type, df in [('CALL', calls), ('PUT', puts)]:
                    if df.empty:
                        continue
                    
                    # Calculate vol/OI ratio
                    df = df[df['openInterest'] > 0].copy()
                    df['vol_oi_ratio'] = df['volume'] / df['openInterest']
                    
                    # Estimate premium (mid price * 100 * volume)
                    df['mid_price'] = (df['bid'] + df['ask']) / 2
                    df['est_premium'] = df['mid_price'] * 100 * df['volume']
                    
                    # Filter for unusual activity
                    unusual = df[
                        (df['vol_oi_ratio'] >= THRESHOLD) & 
                        (df['est_premium'] >= MIN_PREMIUM) &
                        (df['volume'] > 100)
                    ].copy()
                    
                    if unusual.empty:
                        continue
                    
                    # Sort by premium
                    unusual = unusual.sort_values('est_premium', ascending=False)
                    
                    for _, row in unusual.head(3).iterrows():
                        strike = row['strike']
                        
                        # Moneyness
                        if option_type == 'CALL':
                            if strike < current_price * 0.98:
                                moneyness = 'ITM'
                            elif strike > current_price * 1.02:
                                moneyness = 'OTM'
                            else:
                                moneyness = 'ATM'
                        else:
                            if strike > current_price * 1.02:
                                moneyness = 'ITM'
                            elif strike < current_price * 0.98:
                                moneyness = 'OTM'
                            else:
                                moneyness = 'ATM'
                        
                        signal = {
                            'ticker': ticker_symbol,
                            'type': option_type,
                            'strike': strike,
                            'expiry': exp,
                            'days_to_exp': days_to_exp,
                            'vol_oi_ratio': round(float(row['vol_oi_ratio']), 1),
                            'volume': int(row['volume']),
                            'open_interest': int(row['openInterest']),
                            'est_premium': round(float(row['est_premium'])),
                            'mid_price': round(float(row['mid_price']), 2),
                            'implied_volatility': round(float(row.get('impliedVolatility', 0)) * 100, 1),
                            'current_price': current_price,
                            'moneyness': moneyness,
                        }
                        signals.append(signal)
                        
                        print(f"\n  🚨 UNUSUAL FLOW: {option_type}")
                        print(f"     Strike: ${strike} | Exp: {exp} ({days_to_exp}d)")
                        print(f"     Vol/OI: {signal['vol_oi_ratio']}x | Volume: {signal['volume']}")
                        print(f"     Est. Premium: ${signal['est_premium']:,}")
                        print(f"     Mid Price: ${signal['mid_price']} | IV: {signal['implied_volatility']}%")
                        print(f"     Moneyness: {moneyness}")
                
            except Exception as e:
                print(f"  Error on expiry {exp}: {e}")
        
        if not signals:
            print(f"  No unusual flow found above thresholds")
        
        return signals
        
    except Exception as e:
        print(f"Error scanning {ticker_symbol}: {e}")
        return []

all_signals = []
for ticker in TICKERS:
    sigs = scan_ticker(ticker)
    all_signals.extend(sigs)

print(f"\n\n{'='*60}")
print(f"SCAN COMPLETE: {len(all_signals)} total signals found")
print('='*60)

# Also get SPY/QQQ for market context
print("\n--- MARKET CONTEXT ---")
for sym in ['SPY', 'QQQ']:
    try:
        t = yf.Ticker(sym)
        info = t.info
        price = info.get('regularMarketPrice', 'N/A')
        chg = info.get('regularMarketChangePercent', 'N/A')
        prev = info.get('regularMarketPreviousClose', 'N/A')
        print(f"{sym}: ${price} | Change: {chg:.2f}%" if isinstance(chg, float) else f"{sym}: ${price}")
    except Exception as e:
        print(f"{sym}: Error - {e}")
