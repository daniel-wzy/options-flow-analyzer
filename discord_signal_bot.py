#!/usr/bin/env python3
"""
Posts options flow signals to Discord #options channel
Runs during market hours, scans watchlist, posts actionable signals
"""
import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_fetcher import OptionsFetcher
from src.anomaly_detector import AnomalyDetector, UnusualActivity
from src.llm_analyzer import LLMAnalyzer

# Discord channel ID for #options
OPTIONS_CHANNEL_ID = "1485827753407287408"
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "META", "AMZN", "SPY", "QQQ", "GOOGL"]

def send_discord_message(channel_id: str, message: str):
    """Send message to Discord channel via bot token"""
    if not DISCORD_TOKEN:
        print(f"[DISCORD] No bot token. Message:\n{message}")
        return False
    
    # Truncate if needed
    if len(message) > 1900:
        message = message[:1900] + "..."
    
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {DISCORD_TOKEN}",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json={"content": message}, timeout=10)
    return resp.status_code == 200

def format_signal(activity: UnusualActivity, analysis: str) -> str:
    """Format a signal for Discord"""
    emoji = "🟢" if activity.direction == "BULLISH" else "🔴"
    action = "BUY CALL" if activity.direction == "BULLISH" else "BUY PUT"
    
    # Build approximate contract symbol
    exp_clean = activity.expiration.replace("-", "")[-6:]
    type_char = "C" if activity.option_type == "call" else "P"
    strike_str = f"{int(activity.strike * 1000):08d}"
    contract = f"{activity.ticker}{exp_clean}{type_char}{strike_str}"
    
    # Entry: use mid-price estimate (rough)
    entry_note = f"Check bid/ask on Moomoo — look for contracts near ${activity.stock_price:.0f} underlying"
    
    msg = f"""{emoji} **{action} SIGNAL — {activity.ticker}**

📋 **Contract Details:**
• Ticker: `{activity.ticker}`
• Type: **{activity.option_type.upper()}** @ **${activity.strike}** strike
• Expiry: **{activity.expiration}**
• Moneyness: {activity.moneyness}
• Underlying price: **${activity.stock_price:.2f}**

📊 **Flow Data:**
• Volume: **{activity.current_volume:,}** contracts ({activity.volume_ratio}x normal)
• Est. premium: **${activity.premium_estimate:,.0f}**
• IV: {activity.implied_volatility:.1%}

🧠 **AI Analysis:**
{analysis}

⚠️ **Paper Trade Instructions:**
• Open Moomoo → Virtual Trading
• Search: `{activity.ticker}` → Options → {activity.expiration}
• Buy 1-2 contracts of ${activity.strike} {activity.option_type}
• Stop loss: -50% | Target: +100%

⏰ Signal time: {activity.detected_at.strftime('%Y-%m-%d %H:%M EST')}"""
    
    return msg

def run_scan():
    """Run one scan and post signals"""
    print(f"\n[{datetime.now().strftime('%H:%M')}] Running options scan...")
    
    fetcher = OptionsFetcher()
    detector = AnomalyDetector(volume_multiplier=3.0, min_premium=500000)
    analyzer = LLMAnalyzer(provider="anthropic", model="claude-haiku-4-20250514")
    
    signals_posted = 0
    
    for ticker in WATCHLIST:
        try:
            chain = fetcher.get_options_chain(ticker)
            if chain is None:
                continue
            
            price = fetcher.get_stock_price(ticker)
            if not price:
                continue
            
            detector.add_historical_snapshot(ticker, chain)
            unusual = detector.detect_unusual(chain, price)
            
            for activity in unusual[:2]:  # Max 2 per ticker per scan
                analysis = analyzer.analyze(activity)
                message = format_signal(activity, analysis)
                
                if send_discord_message(OPTIONS_CHANNEL_ID, message):
                    print(f"  ✅ Posted signal: {activity.ticker} {activity.direction} ${activity.strike}")
                    signals_posted += 1
                else:
                    print(f"  ⚠️ Failed to post: {activity.ticker}")
                
                time.sleep(2)  # Rate limit
            
            time.sleep(1)
        except Exception as e:
            print(f"  Error scanning {ticker}: {e}")
    
    fetcher.close()
    
    if signals_posted == 0:
        print("  No signals above thresholds this scan")
    else:
        print(f"  Posted {signals_posted} signals total")
    
    return signals_posted

if __name__ == "__main__":
    run_scan()
