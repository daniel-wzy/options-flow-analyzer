"""
apex_confirmation.py
--------------------
APEX signal confirmation module for the options flow scanner.
Reads signals from ~/clawd/moomoo-alerts/alert_log.jsonl and provides
directional stance + options alignment recommendations.

Usage:
    from apex_confirmation import get_apex_stance, check_options_alignment, format_apex_summary
"""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Path to the APEX alert log
ALERT_LOG_PATH = Path.home() / "clawd" / "moomoo-alerts" / "alert_log.jsonl"


def _load_signals(ticker: str, lookback_hours: int) -> list[dict]:
    """
    Load signals for a given ticker from the alert log.
    ticker: bare symbol like "NVDA" → matches "US.NVDA" in the log.
    """
    code = f"US.{ticker.upper()}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    signals = []

    if not ALERT_LOG_PATH.exists():
        return signals

    with open(ALERT_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if entry.get("ticker", "").upper() != code.upper():
                continue

            # Parse timestamp — handle both naive and aware datetimes
            ts_raw = entry.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_raw)
                # Make timezone-aware if naive (assume UTC)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            if ts >= cutoff:
                signals.append(entry)

    return signals


def get_apex_stance(ticker: str, lookback_hours: int = 24) -> dict:
    """
    Analyze recent APEX signals for a ticker and return directional stance.

    Args:
        ticker: Stock symbol, e.g. "NVDA"
        lookback_hours: How far back to look (default 24h)

    Returns:
        dict with direction, confidence, signal counts, indicators, etc.
    """
    signals = _load_signals(ticker, lookback_hours)

    # Defaults for empty result
    base = {
        "ticker": ticker.upper(),
        "direction": "NEUTRAL",
        "confidence": "LOW",
        "buy_signals": 0,
        "sell_signals": 0,
        "net_score": 0,
        "indicators": [],
        "timeframes": [],
        "latest_signal": None,
        "latest_price": None,
        "latest_timestamp": None,
    }

    if not signals:
        return base

    buy_signals = [s for s in signals if s.get("direction", "").upper() == "BUY"]
    sell_signals = [s for s in signals if s.get("direction", "").upper() == "SELL"]

    buy_count = len(buy_signals)
    sell_count = len(sell_signals)
    net_score = buy_count - sell_count

    # Direction
    if net_score > 2:
        direction = "BULLISH"
        dominant_signals = buy_signals
    elif net_score < -2:
        direction = "BEARISH"
        dominant_signals = sell_signals
    else:
        direction = "NEUTRAL"
        dominant_signals = signals  # use all for indicator counting

    # Unique indicators and timeframes from dominant signals
    indicators = list(dict.fromkeys(
        s.get("indicator", "").upper()
        for s in dominant_signals
        if s.get("indicator")
    ))
    timeframes = list(dict.fromkeys(
        s.get("timeframe", "")
        for s in dominant_signals
        if s.get("timeframe")
    ))

    # Confidence based on unique indicators agreeing with direction
    unique_indicator_count = len(indicators)
    if unique_indicator_count >= 3:
        confidence = "HIGH"
    elif unique_indicator_count == 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # If direction is NEUTRAL, confidence reflects overall signal agreement
    if direction == "NEUTRAL":
        all_indicators = list(dict.fromkeys(
            s.get("indicator", "").upper()
            for s in signals
            if s.get("indicator")
        ))
        # Conflicting or insufficient signals = LOW confidence when neutral
        confidence = "LOW"
        indicators = all_indicators
        timeframes = list(dict.fromkeys(
            s.get("timeframe", "")
            for s in signals
            if s.get("timeframe")
        ))

    # Latest signal (most recent timestamp)
    latest = max(signals, key=lambda s: s.get("timestamp", ""))
    latest_signal = latest.get("direction", "").upper() or None
    latest_price = latest.get("close")
    latest_timestamp = latest.get("timestamp")
    # Normalize timestamp to clean ISO format (strip microseconds if present)
    if latest_timestamp:
        try:
            ts = datetime.fromisoformat(latest_timestamp)
            latest_timestamp = ts.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            pass

    return {
        "ticker": ticker.upper(),
        "direction": direction,
        "confidence": confidence,
        "buy_signals": buy_count,
        "sell_signals": sell_count,
        "net_score": net_score,
        "indicators": indicators,
        "timeframes": timeframes,
        "latest_signal": latest_signal,
        "latest_price": latest_price,
        "latest_timestamp": latest_timestamp,
    }


def check_options_alignment(ticker: str, option_type: str) -> dict:
    """
    Check whether APEX stance aligns with an options trade direction.

    Args:
        ticker: Stock symbol, e.g. "NVDA"
        option_type: "CALL" or "PUT"

    Returns:
        dict with aligned, stance, confidence, recommendation, reason
    """
    stance_data = get_apex_stance(ticker)
    direction = stance_data["direction"]
    confidence = stance_data["confidence"]
    opt = option_type.upper()
    buy_count = stance_data["buy_signals"]
    sell_count = stance_data["sell_signals"]

    # Build recommendation
    if opt == "CALL":
        if direction == "BULLISH":
            aligned = True
            if confidence == "HIGH":
                recommendation = "STRONG_BUY"
            elif confidence == "MEDIUM":
                recommendation = "BUY"
            else:
                recommendation = "CAUTION"
        elif direction == "NEUTRAL":
            aligned = False
            recommendation = "CAUTION"
        else:  # BEARISH
            aligned = False
            recommendation = "SKIP"

    elif opt == "PUT":
        if direction == "BEARISH":
            aligned = True
            if confidence == "HIGH":
                recommendation = "STRONG_BUY"
            elif confidence == "MEDIUM":
                recommendation = "BUY"
            else:
                recommendation = "CAUTION"
        elif direction == "NEUTRAL":
            aligned = False
            recommendation = "CAUTION"
        else:  # BULLISH
            aligned = False
            recommendation = "SKIP"

    else:
        return {
            "aligned": False,
            "stance": direction,
            "confidence": confidence,
            "recommendation": "SKIP",
            "reason": f"Unknown option_type '{option_type}'. Use 'CALL' or 'PUT'.",
        }

    # Human-readable reason
    if buy_count == 0 and sell_count == 0:
        reason = f"No recent APEX signals found for {ticker.upper()} in the last 24h"
    else:
        reason = (
            f"APEX shows {direction} on {ticker.upper()} "
            f"({buy_count} BUY signal{'s' if buy_count != 1 else ''} vs "
            f"{sell_count} SELL signal{'s' if sell_count != 1 else ''}, "
            f"{confidence} confidence)"
        )

    return {
        "aligned": aligned,
        "stance": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "reason": reason,
    }


def format_apex_summary(ticker: str) -> str:
    """
    Returns a short Discord-ready string summarizing the APEX stance.

    Examples:
        "⚡ APEX: BULLISH (4↑ 1↓ | MMTS+LDZN | HIGH)"
        "➡️ APEX: NEUTRAL (2↑ 2↓ | LOW)"
        "🔻 APEX: BEARISH (1↑ 5↓ | MMTS+KDZS | HIGH)"
    """
    s = get_apex_stance(ticker)
    direction = s["direction"]
    confidence = s["confidence"]
    buy_count = s["buy_signals"]
    sell_count = s["sell_signals"]
    indicators = s["indicators"]

    emoji_map = {
        "BULLISH": "⚡",
        "NEUTRAL": "➡️",
        "BEARISH": "🔻",
    }
    emoji = emoji_map.get(direction, "➡️")

    counts = f"{buy_count}↑ {sell_count}↓"

    if indicators and direction != "NEUTRAL":
        ind_str = "+".join(indicators[:3])  # cap at 3 for brevity
        body = f"{counts} | {ind_str} | {confidence}"
    else:
        body = f"{counts} | {confidence}"

    return f"{emoji} APEX: {direction} ({body})"


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    test_tickers = ["NVDA", "TSLA", "AMD", "AAPL", "MSFT"]

    print("=" * 60)
    print("APEX Signal Confirmation — Quick Test")
    print(f"Log: {ALERT_LOG_PATH}")
    print("=" * 60)

    for ticker in test_tickers:
        stance = get_apex_stance(ticker)
        call_check = check_options_alignment(ticker, "CALL")
        summary = format_apex_summary(ticker)

        print(f"\n{'─' * 50}")
        print(f"  {ticker}")
        print(f"{'─' * 50}")
        print(f"  Stance   : {stance['direction']} ({stance['confidence']})")
        print(f"  Signals  : {stance['buy_signals']}↑ {stance['sell_signals']}↓  net={stance['net_score']}")
        print(f"  Indicators: {', '.join(stance['indicators']) or 'none'}")
        print(f"  Timeframes: {', '.join(stance['timeframes']) or 'none'}")
        if stance["latest_timestamp"]:
            print(f"  Latest   : {stance['latest_signal']} @ ${stance['latest_price']:.2f} ({stance['latest_timestamp']})")
        else:
            print(f"  Latest   : no signals found")
        print(f"  CALL rec : {call_check['recommendation']} — {call_check['reason']}")
        print(f"  Summary  : {summary}")

    print(f"\n{'=' * 60}")
    print("Done.")
