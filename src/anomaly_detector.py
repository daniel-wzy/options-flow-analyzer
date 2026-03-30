"""
Detect unusual options activity
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import pandas as pd
import numpy as np

@dataclass
class UnusualActivity:
    ticker: str
    option_type: str  # call or put
    strike: float
    expiration: str
    current_volume: int
    avg_volume: float
    volume_ratio: float
    open_interest: int
    premium_estimate: float
    implied_volatility: float
    stock_price: float
    detected_at: datetime
    
    @property
    def direction(self) -> str:
        return "BULLISH" if self.option_type == "call" else "BEARISH"
    
    @property
    def moneyness(self) -> str:
        if self.option_type == "call":
            if self.strike < self.stock_price * 0.97:
                return "ITM"
            elif self.strike > self.stock_price * 1.03:
                return "OTM"
        else:
            if self.strike > self.stock_price * 1.03:
                return "ITM"
            elif self.strike < self.stock_price * 0.97:
                return "OTM"
        return "ATM"

class AnomalyDetector:
    def __init__(self, volume_multiplier: float = 3.0, min_premium: float = 100000):
        self.volume_multiplier = volume_multiplier
        self.min_premium = min_premium
        self.historical_data = {}  # ticker -> list of daily snapshots
    
    def add_historical_snapshot(self, ticker: str, df: pd.DataFrame):
        """Store a snapshot for calculating averages"""
        if ticker not in self.historical_data:
            self.historical_data[ticker] = []
        
        # Keep last 20 snapshots
        self.historical_data[ticker].append(df)
        self.historical_data[ticker] = self.historical_data[ticker][-20:]
    
    def _calculate_avg_volume(self, ticker: str, strike: float, 
                               option_type: str, expiration: str) -> float:
        """Calculate average volume for a specific contract"""
        if ticker not in self.historical_data:
            return 0
        
        volumes = []
        for snapshot in self.historical_data[ticker]:
            matching = snapshot[
                (snapshot['strike'] == strike) & 
                (snapshot['type'] == option_type) &
                (snapshot['expiration'] == expiration)
            ]
            if not matching.empty:
                volumes.append(matching['volume'].iloc[0])
        
        return np.mean(volumes) if volumes else 0
    
    def detect_unusual(self, df: pd.DataFrame, stock_price: float) -> List[UnusualActivity]:
        """Detect unusual activity in options chain"""
        if df is None or df.empty:
            return []
        
        unusual = []
        ticker = df['ticker'].iloc[0]
        
        for _, row in df.iterrows():
            volume = row.get('volume', 0) or 0
            if volume < 100:  # Skip low volume
                continue
            
            strike = row.get('strike', 0)
            option_type = row.get('type', 'call')
            expiration = row.get('expiration', '')
            
            # Get average volume
            avg_vol = self._calculate_avg_volume(ticker, strike, option_type, expiration)
            if avg_vol < 10:
                avg_vol = 100  # Default baseline
            
            volume_ratio = volume / avg_vol
            
            # Estimate premium
            last_price = row.get('lastPrice', 0) or row.get('last_price', 0) or 0
            premium = volume * last_price * 100  # Each contract = 100 shares
            
            # Check thresholds
            if volume_ratio >= self.volume_multiplier and premium >= self.min_premium:
                unusual.append(UnusualActivity(
                    ticker=ticker,
                    option_type=option_type,
                    strike=strike,
                    expiration=str(expiration),
                    current_volume=int(volume),
                    avg_volume=avg_vol,
                    volume_ratio=round(volume_ratio, 1),
                    open_interest=int(row.get('openInterest', 0) or 0),
                    premium_estimate=round(premium, 2),
                    implied_volatility=round(row.get('impliedVolatility', 0) or 0, 3),
                    stock_price=stock_price,
                    detected_at=datetime.now()
                ))
        
        # Sort by premium (biggest bets first)
        unusual.sort(key=lambda x: x.premium_estimate, reverse=True)
        return unusual[:5]  # Top 5 most unusual
