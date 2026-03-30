#!/usr/bin/env python3
"""
Backtester for Options Flow Analyzer
Tests if unusual options flow predicts price movements

Usage:
    python backtest.py --ticker NVDA --days 30
    python backtest.py --ticker AAPL --days 60 --threshold 5.0
"""
import argparse
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from dataclasses import dataclass, field

@dataclass
class BacktestSignal:
    date: str
    ticker: str
    option_type: str
    strike: float
    expiration: str
    volume_ratio: float
    premium_estimate: float
    stock_price_at_signal: float
    direction: str  # BULLISH or BEARISH

@dataclass 
class BacktestResult:
    signal: BacktestSignal
    price_1d: Optional[float] = None
    price_3d: Optional[float] = None
    price_5d: Optional[float] = None
    price_7d: Optional[float] = None
    return_1d: Optional[float] = None
    return_3d: Optional[float] = None
    return_5d: Optional[float] = None
    return_7d: Optional[float] = None
    correct_1d: Optional[bool] = None
    correct_5d: Optional[bool] = None

class OptionsBacktester:
    def __init__(self, volume_multiplier: float = 3.0, min_premium: float = 50000):
        self.volume_multiplier = volume_multiplier
        self.min_premium = min_premium
    
    def fetch_historical_options(self, ticker: str, lookback_days: int = 30) -> List[BacktestSignal]:
        """
        Simulate historical scanning using yfinance.
        
        Note: yfinance only provides current options data. For true historical
        options data you'd need a paid provider (CBOE, OptionsDX, etc.)
        We simulate by scanning current data across multiple expiration dates
        and using historical price data to assess what signals would have fired.
        """
        print(f"\nScanning current options chain for {ticker}...")
        print("(Note: yfinance doesn't provide historical options snapshots)")
        print("Running analysis on current chain as a live test...\n")
        
        stock = yf.Ticker(ticker)
        signals = []
        
        try:
            expirations = stock.options[:6]  # Next 6 expirations
            current_price = stock.info.get('regularMarketPrice', 0) or stock.info.get('currentPrice', 0)
            
            if not current_price:
                hist = stock.history(period="1d")
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            
            print(f"{ticker} current price: ${current_price:.2f}")
            print(f"Scanning {len(expirations)} expirations: {list(expirations)}\n")
            
            for exp in expirations:
                try:
                    chain = stock.option_chain(exp)
                    
                    for option_type, df in [("call", chain.calls), ("put", chain.puts)]:
                        for _, row in df.iterrows():
                            volume = row.get('volume', 0) or 0
                            if volume < 100:
                                continue
                            
                            # Use OI as a proxy for average (since we lack history)
                            # High vol/OI ratio suggests unusual activity
                            oi = row.get('openInterest', 1) or 1
                            vol_oi_ratio = volume / max(oi, 1)
                            
                            last_price = row.get('lastPrice', 0) or 0
                            premium = volume * last_price * 100
                            
                            # Flag as unusual if vol > OI (more traded today than total OI)
                            # AND premium meets threshold
                            if vol_oi_ratio >= self.volume_multiplier and premium >= self.min_premium:
                                signals.append(BacktestSignal(
                                    date=datetime.now().strftime('%Y-%m-%d'),
                                    ticker=ticker,
                                    option_type=option_type,
                                    strike=row.get('strike', 0),
                                    expiration=exp,
                                    volume_ratio=round(vol_oi_ratio, 2),
                                    premium_estimate=round(premium, 0),
                                    stock_price_at_signal=current_price,
                                    direction="BULLISH" if option_type == "call" else "BEARISH"
                                ))
                    time.sleep(0.2)
                except Exception as e:
                    print(f"  Error processing {exp}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error: {e}")
        
        signals.sort(key=lambda x: x.premium_estimate, reverse=True)
        return signals
    
    def fetch_price_history(self, ticker: str, days: int = 60) -> pd.DataFrame:
        """Get historical daily prices"""
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        return hist
    
    def get_forward_returns(self, prices: pd.DataFrame, signal_date: str, 
                            windows: List[int] = [1, 3, 5, 7]) -> Dict:
        """Get forward returns after a signal date"""
        returns = {}
        
        try:
            prices.index = prices.index.tz_localize(None) if prices.index.tz else prices.index
            signal_dt = pd.Timestamp(signal_date)
            
            # Find signal date or nearest trading day
            future_prices = prices[prices.index >= signal_dt]
            
            if future_prices.empty:
                return {}
            
            base_price = future_prices['Close'].iloc[0]
            
            for window in windows:
                if len(future_prices) > window:
                    fwd_price = future_prices['Close'].iloc[window]
                    returns[f"price_{window}d"] = round(fwd_price, 2)
                    returns[f"return_{window}d"] = round((fwd_price / base_price - 1) * 100, 2)
        except Exception as e:
            print(f"  Error calculating returns: {e}")
        
        return returns
    
    def run(self, ticker: str, lookback_days: int = 30) -> List[BacktestResult]:
        """Run backtest for a ticker"""
        print(f"{'='*60}")
        print(f"BACKTESTING: {ticker}")
        print(f"Volume threshold: {self.volume_multiplier}x OI")
        print(f"Min premium: ${self.min_premium:,.0f}")
        print(f"{'='*60}")
        
        # Get current signals
        signals = self.fetch_historical_options(ticker, lookback_days)
        
        if not signals:
            print("No unusual signals detected with current thresholds.")
            return []
        
        print(f"\nFound {len(signals)} unusual signals\n")
        
        # Get price history for forward returns
        prices = self.fetch_price_history(ticker, 30)
        
        results = []
        for signal in signals:
            result = BacktestResult(signal=signal)
            
            fwd_returns = self.get_forward_returns(prices, signal.date)
            
            result.price_1d = fwd_returns.get('price_1d')
            result.price_5d = fwd_returns.get('price_5d')
            result.return_1d = fwd_returns.get('return_1d')
            result.return_3d = fwd_returns.get('return_3d')
            result.return_5d = fwd_returns.get('return_5d')
            result.return_7d = fwd_returns.get('return_7d')
            
            # Check if signal direction was correct
            if result.return_1d is not None:
                bullish_correct = signal.direction == "BULLISH" and result.return_1d > 0
                bearish_correct = signal.direction == "BEARISH" and result.return_1d < 0
                result.correct_1d = bullish_correct or bearish_correct
            
            if result.return_5d is not None:
                bullish_correct = signal.direction == "BULLISH" and result.return_5d > 0
                bearish_correct = signal.direction == "BEARISH" and result.return_5d < 0
                result.correct_5d = bullish_correct or bearish_correct
            
            results.append(result)
        
        return results
    
    def print_report(self, results: List[BacktestResult], ticker: str):
        """Print formatted backtest report"""
        if not results:
            print("No results to report.")
            return
        
        print(f"\n{'='*60}")
        print(f"BACKTEST REPORT: {ticker}")
        print(f"{'='*60}")
        print(f"Total signals detected: {len(results)}")
        
        bullish = [r for r in results if r.signal.direction == "BULLISH"]
        bearish = [r for r in results if r.signal.direction == "BEARISH"]
        print(f"  Bullish signals: {len(bullish)}")
        print(f"  Bearish signals: {len(bearish)}")
        
        print(f"\n{'─'*60}")
        print("TOP SIGNALS DETECTED:")
        print(f"{'─'*60}")
        
        for i, r in enumerate(results[:10], 1):
            s = r.signal
            direction_emoji = "🟢" if s.direction == "BULLISH" else "🔴"
            
            print(f"\n{i}. {direction_emoji} {s.direction} {s.option_type.upper()}")
            print(f"   Strike: ${s.strike} | Expiry: {s.expiration}")
            print(f"   Volume/OI ratio: {s.volume_ratio}x")
            print(f"   Premium: ${s.premium_estimate:,.0f}")
            print(f"   Stock price at signal: ${s.stock_price_at_signal:.2f}")
            
            if r.return_1d is not None:
                correct_1d = "✅" if r.correct_1d else "❌"
                correct_5d = "✅" if r.correct_5d else "❌" if r.correct_5d is not None else "⏳"
                print(f"   1d return: {r.return_1d:+.2f}% {correct_1d} | 5d return: {r.return_5d:+.2f}% {correct_5d}" if r.return_5d else f"   1d return: {r.return_1d:+.2f}% {correct_1d}")
            else:
                print(f"   Returns: signal is from today (forward returns pending)")
        
        # Summary stats
        completed = [r for r in results if r.correct_1d is not None]
        if completed:
            accuracy_1d = sum(1 for r in completed if r.correct_1d) / len(completed)
            print(f"\n{'─'*60}")
            print(f"ACCURACY (signals with forward data):")
            print(f"  1-day accuracy: {accuracy_1d:.1%} ({sum(1 for r in completed if r.correct_1d)}/{len(completed)})")
            
            completed_5d = [r for r in results if r.correct_5d is not None]
            if completed_5d:
                accuracy_5d = sum(1 for r in completed_5d if r.correct_5d) / len(completed_5d)
                print(f"  5-day accuracy: {accuracy_5d:.1%} ({sum(1 for r in completed_5d if r.correct_5d)}/{len(completed_5d)})")
        
        print(f"\n{'─'*60}")
        print("NOTE: This uses vol/OI ratio as proxy for unusual activity.")
        print("True historical backtesting requires paid options history data")
        print("(CBOE DataShop, OptionsDX, or similar ~$50-100/mo)")
        print(f"{'='*60}\n")

def main():
    parser = argparse.ArgumentParser(description="Options Flow Backtester")
    parser.add_argument("--ticker", default="NVDA", help="Ticker to backtest (default: NVDA)")
    parser.add_argument("--days", type=int, default=30, help="Lookback days (default: 30)")
    parser.add_argument("--threshold", type=float, default=3.0, help="Volume/OI threshold (default: 3.0)")
    parser.add_argument("--min-premium", type=float, default=50000, help="Min premium in $ (default: 50000)")
    parser.add_argument("--tickers", nargs="+", help="Multiple tickers to test")
    args = parser.parse_args()
    
    tickers = args.tickers if args.tickers else [args.ticker]
    
    for ticker in tickers:
        backtester = OptionsBacktester(
            volume_multiplier=args.threshold,
            min_premium=args.min_premium
        )
        results = backtester.run(ticker, args.days)
        backtester.print_report(results, ticker)
        
        if len(tickers) > 1:
            time.sleep(2)

if __name__ == "__main__":
    main()
