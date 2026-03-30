#!/usr/bin/env python3
"""
Options Flow Analyzer - Main entry point
"""
import argparse
import time
from datetime import datetime
import yaml
import schedule
from src.data_fetcher import OptionsFetcher
from src.anomaly_detector import AnomalyDetector
from src.llm_analyzer import LLMAnalyzer
from src.alerter import Alerter

def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)

def is_market_hours(config) -> bool:
    """Check if within market hours"""
    if not config['monitor']['market_hours_only']:
        return True
    
    now = datetime.now()
    if now.weekday() >= 5:  # Weekend
        return False
    
    market_open = datetime.strptime(config['monitor']['market_open'], "%H:%M").time()
    market_close = datetime.strptime(config['monitor']['market_close'], "%H:%M").time()
    
    return market_open <= now.time() <= market_close

def scan_ticker(ticker: str, fetcher: OptionsFetcher, detector: AnomalyDetector,
                analyzer: LLMAnalyzer, alerter: Alerter, config: dict):
    """Scan a single ticker for unusual activity"""
    print(f"Scanning {ticker}...")
    
    # Get current price
    stock_price = fetcher.get_stock_price(ticker)
    if not stock_price:
        print(f"  Could not get price for {ticker}")
        return []
    
    # Get options chain
    chain = fetcher.get_options_chain(ticker)
    if chain is None:
        print(f"  No options data for {ticker}")
        return []
    
    # Store for historical comparison
    detector.add_historical_snapshot(ticker, chain)
    
    # Detect unusual activity
    unusual = detector.detect_unusual(chain, stock_price)
    
    if unusual:
        print(f"  Found {len(unusual)} unusual activities!")
        for activity in unusual:
            # Get AI analysis
            analysis = analyzer.analyze(activity)
            print(f"\n  {activity.ticker} {activity.option_type.upper()} ${activity.strike}")
            print(f"  Volume: {activity.current_volume:,} ({activity.volume_ratio}x avg)")
            print(f"  Premium: ${activity.premium_estimate:,.0f}")
            
            # Send alert
            alerter.send(
                activity, 
                analysis,
                discord=config['alerts']['discord']['enabled'],
                telegram=config['alerts']['telegram']['enabled']
            )
    else:
        print(f"  No unusual activity")
    
    return unusual

def scan_watchlist(config: dict):
    """Scan entire watchlist"""
    fetcher = OptionsFetcher()
    detector = AnomalyDetector(
        volume_multiplier=config['thresholds']['volume_multiplier'],
        min_premium=config['thresholds']['min_premium']
    )
    analyzer = LLMAnalyzer(
        provider=config['llm']['provider'],
        model=config['llm']['model']
    )
    alerter = Alerter()
    
    all_unusual = []
    for ticker in config['watchlist']:
        unusual = scan_ticker(ticker, fetcher, detector, analyzer, alerter, config)
        all_unusual.extend(unusual)
        time.sleep(1)  # Rate limiting
    
    fetcher.close()
    return all_unusual

def monitor(config: dict):
    """Run continuous monitoring"""
    print(f"Starting options flow monitor...")
    print(f"Watchlist: {config['watchlist']}")
    print(f"Checking every {config['monitor']['interval_minutes']} minutes")
    
    def job():
        if is_market_hours(config):
            print(f"\n{'='*50}")
            print(f"Scan at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print(f"{'='*50}")
            scan_watchlist(config)
        else:
            print("Outside market hours, skipping...")
    
    # Run immediately
    job()
    
    # Schedule periodic runs
    schedule.every(config['monitor']['interval_minutes']).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def analyze_single(ticker: str, config: dict):
    """Analyze a single ticker"""
    print(f"Analyzing {ticker}...")
    
    fetcher = OptionsFetcher()
    detector = AnomalyDetector(
        volume_multiplier=config['thresholds']['volume_multiplier'],
        min_premium=config['thresholds']['min_premium']
    )
    analyzer = LLMAnalyzer(
        provider=config['llm']['provider'],
        model=config['llm']['model']
    )
    alerter = Alerter()
    
    unusual = scan_ticker(ticker, fetcher, detector, analyzer, alerter, config)
    
    if not unusual:
        print(f"\nNo unusual activity detected for {ticker}")
        print("This could mean:")
        print("  - Volume is within normal range")
        print("  - Premium size below threshold")
        print("  - Normal trading day for this ticker")
    
    fetcher.close()

def main():
    parser = argparse.ArgumentParser(description="Options Flow Analyzer")
    parser.add_argument("command", choices=["scan", "monitor", "analyze"],
                       help="Command to run")
    parser.add_argument("ticker", nargs="?", help="Ticker for analyze command")
    args = parser.parse_args()
    
    config = load_config()
    
    if args.command == "scan":
        scan_watchlist(config)
    elif args.command == "monitor":
        monitor(config)
    elif args.command == "analyze":
        if not args.ticker:
            print("Error: ticker required for analyze command")
            return
        analyze_single(args.ticker.upper(), config)

if __name__ == "__main__":
    main()
