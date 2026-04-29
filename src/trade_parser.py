#!/usr/bin/env python3
"""
Parses trade messages from Discord #options channel
Looks for patterns like:
  "entered NVDA $177.5 call @ $2.50"
  "exited NVDA $177.5 call @ $4.80"
  "entered TSLA $250 put @ 3.20"
  "sold AAPL $175 call @ 1.50"
"""
import re
import json
import os
from datetime import datetime
from src.signal_tracker import load_signals, save_signals, log_signal

SIGNALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signals_log.json")
TRADE_STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "trade_state.json")

def load_trade_state():
    if not os.path.exists(TRADE_STATE_FILE):
        return {"last_processed_message_id": None, "open_trades": {}}
    with open(TRADE_STATE_FILE) as f:
        return json.load(f)

def save_trade_state(state):
    with open(TRADE_STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def parse_trade_message(content: str) -> dict | None:
    """Parse a trade message. Returns dict or None if not a trade message."""
    content = content.lower().strip()
    
    # Entry patterns: "entered NVDA $177.5 call @ $2.50" or "bought NVDA 177.5 call at 2.50"
    entry_pattern = re.compile(
        r'(?:entered|bought|buy|filled)\s+'
        r'([A-Za-z]+)\s+'
        r'\$?([\d.]+)\s+'
        r'(call|put|c|p)\s+'
        r'(?:@|at)\s+\$?([\d.]+)',
        re.IGNORECASE
    )
    
    # Exit patterns: "exited NVDA $177.5 call @ $4.80" or "sold TSLA 250 put at 1.20"
    exit_pattern = re.compile(
        r'(?:exited|sold|sell|closed)\s+'
        r'([A-Za-z]+)\s+'
        r'\$?([\d.]+)\s+'
        r'(call|put|c|p)\s+'
        r'(?:@|at)\s+\$?([\d.]+)',
        re.IGNORECASE
    )
    
    entry_match = entry_pattern.search(content)
    if entry_match:
        ticker, strike, option_type, price = entry_match.groups()
        option_type = "call" if option_type.lower() in ["call", "c"] else "put"
        return {
            "action": "entry",
            "ticker": ticker.upper(),
            "strike": float(strike),
            "option_type": option_type,
            "price": float(price)
        }
    
    exit_match = exit_pattern.search(content)
    if exit_match:
        ticker, strike, option_type, price = exit_match.groups()
        option_type = "call" if option_type.lower() in ["call", "c"] else "put"
        return {
            "action": "exit",
            "ticker": ticker.upper(),
            "strike": float(strike),
            "option_type": option_type,
            "price": float(price)
        }
    
    return None

def find_matching_signal(ticker: str, strike: float, option_type: str) -> str | None:
    """Find a signal ID that matches the trade"""
    signals = load_signals()
    
    # Look for open signals matching ticker + approximate strike + type
    for s in signals:
        if (s.get('ticker') == ticker and 
            s.get('option_type') == option_type and
            abs(s.get('strike', 0) - strike) < 1.0 and
            s.get('exit_price') is None):
            return s['id']
    
    return None

def log_manual_entry(ticker: str, option_type: str, strike: float, 
                      expiration: str, entry_price: float, direction: str):
    """Manually log a new trade entry (when no prior signal exists)"""
    signals = load_signals()
    
    signal_id = f"MANUAL_{ticker}_{option_type}_{strike}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    record = {
        "id": signal_id,
        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "ticker": ticker,
        "direction": direction,
        "option_type": option_type,
        "strike": strike,
        "expiration": expiration,
        "stock_price_at_signal": 0,
        "volume_ratio": 0,
        "premium_estimate": 0,
        "ai_analysis": "Manually logged trade",
        "entry_price": entry_price,
        "exit_price": None,
        "exit_date": None,
        "exit_reason": None,
        "pnl_pct": None,
        "correct": None
    }
    
    signals.append(record)
    save_signals(signals)
    return signal_id

def close_trade(signal_id: str, exit_price: float, entry_price: float = None):
    """Close a trade and calculate P&L"""
    signals = load_signals()
    
    for s in signals:
        if s['id'] == signal_id:
            if entry_price:
                s['entry_price'] = entry_price
            
            actual_entry = s.get('entry_price', 0)
            s['exit_price'] = exit_price
            s['exit_date'] = datetime.now().strftime('%Y-%m-%d')
            
            if actual_entry and actual_entry > 0:
                pnl = (exit_price / actual_entry - 1) * 100
                s['pnl_pct'] = round(pnl, 1)
                
                # Direction correct if: bullish+profit or bearish+profit (both mean option gained)
                s['correct'] = pnl > 0
                
                if pnl >= 100:
                    s['exit_reason'] = 'target_hit'
                elif pnl <= -50:
                    s['exit_reason'] = 'stop_loss'
                else:
                    s['exit_reason'] = 'manual'
    
    save_signals(signals)

if __name__ == "__main__":
    # Test parser
    test_msgs = [
        "entered NVDA $177.5 call @ $2.50",
        "exited NVDA $177.5 call @ $4.80",
        "bought TSLA 250 put at 3.20",
        "sold AAPL $175 call @ 1.50",
        "hey what's up", # should return None
    ]
    for msg in test_msgs:
        result = parse_trade_message(msg)
        print(f"'{msg}' -> {result}")
