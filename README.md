# Options Flow Analyzer 📈

An AI-powered unusual options activity detector that scans for large, anomalous options trades and uses an LLM to explain what the flow likely means.

Built for paper trading validation — scan signals, track results, decide if it's worth automating with real money.

## How It Works

1. **Fetch** options chains from Yahoo Finance (free, no API key needed)
2. **Detect** unusual activity: contracts where today's volume far exceeds normal (vol/OI ratio)
3. **Analyze** each signal with Claude/GPT — explains the bet, break-even, and what it might signal
4. **Alert** via Discord or terminal

## Features

- 🔍 Scans 10+ tickers for unusual volume spikes
- 🧠 LLM analysis of each unusual contract
- 📊 Backtesting tool (vol/OI ratio as proxy)
- 💬 Discord alerts with paper trade instructions
- 📝 Signal logging for accuracy tracking
- ⚡ Zero cost for data (yfinance)

## Quick Start

```bash
git clone https://github.com/yourusername/options-flow-analyzer.git
cd options-flow-analyzer

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your API keys
```

## Configuration

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...   # or use OPENAI_API_KEY
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...  # optional
```

Edit `config.yaml` to set your watchlist, thresholds, and alert preferences.

## Usage

```bash
# Scan full watchlist
python main.py scan

# Analyze one ticker
python main.py analyze NVDA

# Continuous monitoring (market hours)
python main.py monitor

# Backtest / signal detection
python backtest.py --ticker NVDA --threshold 2.0 --min-premium 50000
python backtest.py --tickers NVDA TSLA AAPL MSFT --threshold 3.0
```

## Signal Format

```
🟢 BULLISH CALL — NVDA
• Strike: $177.5 | Expiry: 2026-03-29 | ATM
• Volume: 51,717 (7.1x OI)
• Est. Premium: $5,100,000
• IV: 68.3%
• Underlying: $175.64

AI Analysis:
• Aggressive bullish bet expiring in 6 days — short-dated = high conviction
• Break-even: ~$180.50 (+2.8% move needed)
• Similar ATM call sweeps on NVDA have preceded 3-5% moves within 3 days
• Confidence: Medium-High
```

## Paper Trading Workflow

1. Run `python main.py monitor` or use the hourly cron
2. Signal appears → open your broker's paper/virtual trading
3. Execute the suggested contract (1-2 contracts)
4. Track in `signals_log.json`
5. After 30+ signals, run accuracy analysis

## Project Structure

```
options-flow-analyzer/
├── main.py                 # Entry point (scan/monitor/analyze)
├── backtest.py             # Backtesting & signal detection
├── discord_signal_bot.py   # Discord alert bot
├── config.yaml             # Watchlist, thresholds, settings
├── requirements.txt
├── .env.example            # Template (copy to .env)
└── src/
    ├── data_fetcher.py     # yfinance + Moomoo data
    ├── anomaly_detector.py # Volume spike detection
    ├── llm_analyzer.py     # Claude/GPT analysis
    └── alerter.py          # Discord/Telegram alerts
```

## Data Sources

| Source | Cost | Notes |
|--------|------|-------|
| yfinance | Free | Current options chain only |
| Moomoo OpenD | Free (with account) | Real-time, requires local OpenD |
| Polygon.io | $29/mo | Historical options snapshots |
| CBOE DataShop | $100+/mo | Most complete historical data |

> **Note:** For true historical backtesting, you need a paid options data provider. yfinance only provides the current chain, so "backtesting" here uses vol/OI ratio as a real-time proxy.

## Disclaimer

This is an experimental tool for educational and paper trading purposes only. Not financial advice. Always validate signals before trading real money.

## License

MIT
