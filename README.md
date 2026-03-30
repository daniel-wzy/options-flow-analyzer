# Options Flow Analyzer 📈

An AI-powered unusual options activity detector that scans for large, anomalous options trades and uses an LLM to explain what the flow likely means — then posts actionable paper trade signals to Discord.

> ⚠️ **This project is experimental and unvalidated. Accuracy data will be published after 30+ tracked trades. Do NOT use with real money until you have personally validated signal accuracy.**

---

## How It Works

1. **Fetch** options chains from Yahoo Finance (free, no API key needed for data)
2. **Detect** unusual activity: contracts where today's volume far exceeds open interest
3. **Analyze** each signal with Claude AI — explains the bet, break-even, and what it might signal
4. **Alert** via Discord bot with paper trade instructions

## Features

- 🔍 Scans 10+ tickers for unusual volume spikes
- 🧠 LLM analysis of each signal (Claude or OpenAI)
- 📊 Backtest CLI tool
- 💬 Discord bot posts signals automatically
- 📝 Signal accuracy tracker (`signals_log.json`)
- ⚡ Free data via yfinance — no paid data subscription needed

---

## Prerequisites

Before running, you'll need:

### 1. Claude API Key (or OpenAI)
- Go to [console.anthropic.com](https://console.anthropic.com) → create an account → API Keys → Create Key
- Or use [platform.openai.com](https://platform.openai.com) for OpenAI

### 2. Discord Bot (for alerts)
1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. New Application → Bot → Add Bot → copy the **Bot Token**
3. OAuth2 → URL Generator → scopes: `bot` → permissions: `Send Messages`, `View Channels`
4. Invite the bot to your server using the generated URL
5. Copy your target **Channel ID** (right-click channel → Copy Channel ID in Discord developer mode)

### 3. Python 3.9+

---

## Setup

```bash
git clone https://github.com/yourusername/options-flow-analyzer.git
cd options-flow-analyzer

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Open .env and fill in your keys
```

### `.env` configuration:
```env
# Choose one LLM provider:
ANTHROPIC_API_KEY=sk-ant-...
# or
OPENAI_API_KEY=sk-...

# Discord (for alerts):
DISCORD_BOT_TOKEN=your-bot-token
```

### `config.yaml` configuration:
```yaml
alerts:
  discord:
    enabled: true
    channel_id: "YOUR_CHANNEL_ID_HERE"   # paste your Discord channel ID
```

---

## Usage

```bash
# Scan full watchlist once
python main.py scan

# Analyze one ticker
python main.py analyze NVDA

# Continuous monitoring during market hours (every 60 min)
python main.py monitor

# Backtest / signal detection
python backtest.py --ticker NVDA --threshold 2.0
python backtest.py --tickers NVDA TSLA AAPL MSFT --threshold 3.0

# View accuracy report
python -m src.signal_tracker
```

---

## Signal Format

```
🟢 BUY CALL SIGNAL — NVDA
• Contract: CALL @ $177.5 strike, exp 2026-03-29
• Underlying: $175.64 | Moneyness: ATM
• Volume/OI: 7.1x normal | Est. Premium: $5,100,000
• IV: 68.3%

AI Analysis:
• Short-dated aggressive bullish bet — high conviction
• Break-even: ~$180.50 (+2.8% move needed in 6 days)
• Risk: Theta decay accelerates significantly this close to expiry
• Confidence: Medium

Paper trade: Moomoo Virtual → NVDA → Options → Mar 29 → $177.5 Call
Stop loss: -50% | Target: +100%
```

---

## Tracking Results

Signals are logged to `signals_log.json` (gitignored — stays local). After paper trading, run the accuracy reporter:

```bash
python -m src.signal_tracker
```

Contribute your results to help validate the algorithm before using real money.

---

## Project Structure

```
options-flow-analyzer/
├── main.py                 # Entry point
├── backtest.py             # Signal detection & backtest
├── discord_signal_bot.py   # Discord alert delivery
├── config.yaml             # Settings (watchlist, thresholds, channel)
├── requirements.txt
├── .env.example            # Template — copy to .env, add your keys
└── src/
    ├── data_fetcher.py     # yfinance + Moomoo data fetching
    ├── anomaly_detector.py # Volume spike detection logic
    ├── llm_analyzer.py     # Claude/GPT signal analysis
    ├── alerter.py          # Discord/Telegram delivery
    └── signal_tracker.py   # Paper trade result logging & stats
```

---

## Data Sources

| Source | Cost | Notes |
|--------|------|-------|
| yfinance | Free | Current options chain (default) |
| Moomoo OpenD | Free (with account) | Real-time, requires local OpenD daemon |
| Polygon.io | $29/mo | Historical snapshots for backtesting |
| CBOE DataShop | $100+/mo | Most complete historical data |

> For proper historical backtesting, a paid data source is needed. yfinance provides current chain only.

---

## ⚠️ Legal Disclaimer

**THIS SOFTWARE IS PROVIDED FOR EDUCATIONAL AND RESEARCH PURPOSES ONLY.**

- This tool does NOT constitute financial advice, investment advice, or trading recommendations.
- Past signal performance (if any) does not guarantee future results.
- Options trading involves substantial risk of loss and is not appropriate for all investors.
- You may lose the entire value of your investment.
- The authors and contributors of this project are NOT responsible for any financial losses incurred through use of this software.
- Always paper trade first. Never trade with money you cannot afford to lose.
- Consult a licensed financial advisor before making any investment decisions.

By using this software, you acknowledge and accept full responsibility for any trading decisions made.

---

## License

MIT — use freely, contribute back if you improve it.
