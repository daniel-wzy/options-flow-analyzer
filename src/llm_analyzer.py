"""
LLM-powered analysis of unusual options activity
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class LLMAnalyzer:
    def __init__(self, provider: str = "anthropic", model: str = "claude-sonnet-4-20250514"):
        self.provider = provider
        self.model = model
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            if self.provider == "anthropic":
                from anthropic import Anthropic
                self._client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            else:
                from openai import OpenAI
                self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        return self._client
    
    def analyze(self, activity) -> str:
        """Generate analysis for unusual options activity"""
        
        prompt = f"""Analyze this unusual options activity and explain what it might signal. Be concise but insightful.

**Unusual Options Activity Detected:**
- Ticker: {activity.ticker}
- Type: {activity.option_type.upper()} (Direction: {activity.direction})
- Strike: ${activity.strike}
- Expiration: {activity.expiration}
- Current Stock Price: ${activity.stock_price:.2f}
- Moneyness: {activity.moneyness}
- Volume: {activity.current_volume:,} contracts (normally ~{activity.avg_volume:.0f})
- Volume Ratio: {activity.volume_ratio}x average
- Estimated Premium: ${activity.premium_estimate:,.0f}
- Open Interest: {activity.open_interest:,}
- Implied Volatility: {activity.implied_volatility:.1%}

Analyze:
1. What's the bet? (direction, size, conviction level)
2. Break-even price and % move required from current
3. What could this signal? (earnings play, news catalyst, hedging, etc.)
4. Risk/reward assessment
5. Confidence level (Low/Medium/High) with brief reasoning

Keep response under 200 words. Use bullet points."""

        try:
            client = self._get_client()
            
            if self.provider == "anthropic":
                response = client.messages.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
            else:
                response = client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
                
        except Exception as e:
            return f"Analysis failed: {e}"
    
    def analyze_batch(self, activities: List) -> List[dict]:
        """Analyze multiple activities"""
        results = []
        for activity in activities:
            analysis = self.analyze(activity)
            results.append({
                "activity": activity,
                "analysis": analysis
            })
        return results
