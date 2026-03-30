"""
Track paper trade signals and outcomes for accuracy analysis
Saves to signals_log.json (gitignored - your personal trading data)
"""
import json
import os
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, asdict

SIGNALS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "signals_log.json")

@dataclass
class SignalRecord:
    id: str
    date: str
    ticker: str
    direction: str        # BULLISH or BEARISH
    option_type: str      # call or put
    strike: float
    expiration: str
    stock_price_at_signal: float
    volume_ratio: float
    premium_estimate: float
    ai_analysis: str
    # Filled in when trade closes
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    exit_reason: Optional[str] = None  # target_hit, stop_loss, expired, manual
    pnl_pct: Optional[float] = None
    correct: Optional[bool] = None     # Did direction prediction match?

def load_signals() -> List[dict]:
    if not os.path.exists(SIGNALS_FILE):
        return []
    with open(SIGNALS_FILE) as f:
        return json.load(f)

def save_signals(signals: List[dict]):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals, f, indent=2, default=str)

def log_signal(activity, analysis: str) -> str:
    """Log a new signal, returns signal ID"""
    signals = load_signals()
    
    signal_id = f"{activity.ticker}_{activity.option_type}_{activity.strike}_{datetime.now().strftime('%Y%m%d%H%M')}"
    
    record = SignalRecord(
        id=signal_id,
        date=datetime.now().strftime('%Y-%m-%d %H:%M'),
        ticker=activity.ticker,
        direction=activity.direction,
        option_type=activity.option_type,
        strike=activity.strike,
        expiration=str(activity.expiration),
        stock_price_at_signal=activity.stock_price,
        volume_ratio=activity.volume_ratio,
        premium_estimate=activity.premium_estimate,
        ai_analysis=analysis
    )
    
    signals.append(asdict(record))
    save_signals(signals)
    
    return signal_id

def close_signal(signal_id: str, entry_price: float, exit_price: float, 
                 exit_reason: str, stock_direction_correct: bool):
    """Update a signal with trade outcome"""
    signals = load_signals()
    
    for s in signals:
        if s['id'] == signal_id:
            s['entry_price'] = entry_price
            s['exit_price'] = exit_price
            s['exit_date'] = datetime.now().strftime('%Y-%m-%d')
            s['exit_reason'] = exit_reason
            s['pnl_pct'] = round((exit_price / entry_price - 1) * 100, 1) if entry_price > 0 else None
            s['correct'] = stock_direction_correct
            break
    
    save_signals(signals)

def print_accuracy_report():
    """Print accuracy stats for all closed signals"""
    signals = load_signals()
    
    if not signals:
        print("No signals logged yet.")
        return
    
    closed = [s for s in signals if s.get('exit_price') is not None]
    open_signals = [s for s in signals if s.get('exit_price') is None]
    
    print(f"\n{'='*50}")
    print(f"SIGNAL ACCURACY REPORT")
    print(f"{'='*50}")
    print(f"Total signals: {len(signals)}")
    print(f"  Closed: {len(closed)}")
    print(f"  Open:   {len(open_signals)}")
    
    if not closed:
        print("\nNo closed trades yet.")
        return
    
    # Win rate
    winners = [s for s in closed if s.get('pnl_pct', 0) > 0]
    losers = [s for s in closed if s.get('pnl_pct', 0) <= 0]
    win_rate = len(winners) / len(closed) if closed else 0
    
    # Average P&L
    pnls = [s['pnl_pct'] for s in closed if s.get('pnl_pct') is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    
    # Direction accuracy
    direction_correct = [s for s in closed if s.get('correct') is True]
    direction_accuracy = len(direction_correct) / len(closed) if closed else 0
    
    print(f"\nPerformance:")
    print(f"  Win rate:          {win_rate:.1%} ({len(winners)}/{len(closed)})")
    print(f"  Avg P&L:           {avg_pnl:+.1f}%")
    print(f"  Direction accuracy: {direction_accuracy:.1%}")
    
    print(f"\nBy ticker:")
    tickers = set(s['ticker'] for s in closed)
    for ticker in sorted(tickers):
        t_signals = [s for s in closed if s['ticker'] == ticker]
        t_wins = [s for s in t_signals if s.get('pnl_pct', 0) > 0]
        t_avg = sum(s['pnl_pct'] for s in t_signals if s.get('pnl_pct')) / len(t_signals)
        print(f"  {ticker}: {len(t_wins)}/{len(t_signals)} wins, avg {t_avg:+.1f}%")
    
    print(f"\nExit reasons:")
    for reason in ['target_hit', 'stop_loss', 'expired', 'manual']:
        count = sum(1 for s in closed if s.get('exit_reason') == reason)
        if count:
            print(f"  {reason}: {count}")
    
    print(f"{'='*50}")

if __name__ == "__main__":
    print_accuracy_report()
