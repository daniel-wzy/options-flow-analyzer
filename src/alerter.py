"""
Send alerts to Discord and Telegram
"""
import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Alerter:
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    def format_alert(self, activity, analysis: str) -> str:
        """Format activity + analysis for alerting"""
        emoji = "🟢" if activity.direction == "BULLISH" else "🔴"
        
        return f"""{emoji} **UNUSUAL OPTIONS FLOW: {activity.ticker}**

📊 **Activity:**
• Type: {activity.option_type.upper()} @ ${activity.strike} ({activity.moneyness})
• Expiry: {activity.expiration}
• Volume: {activity.current_volume:,} ({activity.volume_ratio}x avg)
• Premium: ${activity.premium_estimate:,.0f}
• Stock Price: ${activity.stock_price:.2f}

🧠 **AI Analysis:**
{analysis}

⏰ Detected: {activity.detected_at.strftime('%Y-%m-%d %H:%M')}
"""

    def send_discord(self, message: str) -> bool:
        """Send alert to Discord webhook"""
        if not self.discord_webhook:
            print("Discord webhook not configured")
            return False
        
        try:
            # Discord has 2000 char limit
            if len(message) > 1900:
                message = message[:1900] + "..."
            
            response = requests.post(
                self.discord_webhook,
                json={"content": message},
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"Discord alert failed: {e}")
            return False
    
    def send_telegram(self, message: str) -> bool:
        """Send alert to Telegram"""
        if not self.telegram_token or not self.telegram_chat_id:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            response = requests.post(
                url,
                json={
                    "chat_id": self.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram alert failed: {e}")
            return False
    
    def send(self, activity, analysis: str, discord: bool = True, telegram: bool = False) -> bool:
        """Send alert to configured channels"""
        message = self.format_alert(activity, analysis)
        success = False
        
        if discord:
            success = self.send_discord(message) or success
        if telegram:
            success = self.send_telegram(message) or success
        
        return success
