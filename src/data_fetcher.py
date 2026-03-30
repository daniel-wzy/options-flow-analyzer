"""
Fetch options data from Moomoo OpenD and yfinance
"""
import os
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

class OptionsFetcher:
    def __init__(self):
        self.moomoo_host = os.getenv("MOOMOO_HOST", "127.0.0.1")
        self.moomoo_port = int(os.getenv("MOOMOO_PORT", "11111"))
        self._moomoo_ctx = None
    
    def _get_moomoo_ctx(self):
        """Lazy load Moomoo context"""
        if self._moomoo_ctx is None:
            try:
                from moomoo import OpenQuoteContext
                self._moomoo_ctx = OpenQuoteContext(
                    host=self.moomoo_host, 
                    port=self.moomoo_port
                )
            except Exception as e:
                print(f"Moomoo connection failed: {e}")
                return None
        return self._moomoo_ctx
    
    def get_options_chain_yfinance(self, ticker: str) -> Optional[pd.DataFrame]:
        """Get options chain from yfinance (free, reliable)"""
        try:
            stock = yf.Ticker(ticker)
            expirations = stock.options
            
            if not expirations:
                return None
            
            all_options = []
            for exp in expirations[:4]:  # Next 4 expirations
                try:
                    chain = stock.option_chain(exp)
                    calls = chain.calls.copy()
                    calls['type'] = 'call'
                    calls['expiration'] = exp
                    puts = chain.puts.copy()
                    puts['type'] = 'put'
                    puts['expiration'] = exp
                    all_options.extend([calls, puts])
                except Exception:
                    continue
            
            if not all_options:
                return None
                
            df = pd.concat(all_options, ignore_index=True)
            df['ticker'] = ticker
            df['fetched_at'] = datetime.now()
            return df
            
        except Exception as e:
            print(f"yfinance error for {ticker}: {e}")
            return None
    
    def get_options_chain_moomoo(self, ticker: str) -> Optional[pd.DataFrame]:
        """Get options chain from Moomoo OpenD"""
        ctx = self._get_moomoo_ctx()
        if ctx is None:
            return None
        
        try:
            code = f"US.{ticker}"
            
            # Get expiration dates
            ret, dates = ctx.get_option_expiration_date(code)
            if ret != 0 or dates is None or dates.empty:
                return None
            
            all_options = []
            for _, row in dates.head(4).iterrows():
                exp_date = row['strike_time']
                ret, chain = ctx.get_option_chain(code, exp_date)
                if ret == 0 and chain is not None:
                    chain['ticker'] = ticker
                    chain['fetched_at'] = datetime.now()
                    all_options.append(chain)
            
            if not all_options:
                return None
                
            return pd.concat(all_options, ignore_index=True)
            
        except Exception as e:
            print(f"Moomoo error for {ticker}: {e}")
            return None
    
    def get_options_chain(self, ticker: str, source: str = "yfinance") -> Optional[pd.DataFrame]:
        """Get options chain from specified source"""
        if source == "moomoo":
            return self.get_options_chain_moomoo(ticker)
        return self.get_options_chain_yfinance(ticker)
    
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Get current stock price"""
        try:
            stock = yf.Ticker(ticker)
            return stock.info.get('regularMarketPrice') or stock.info.get('currentPrice')
        except Exception:
            return None
    
    def close(self):
        if self._moomoo_ctx:
            self._moomoo_ctx.close()
            self._moomoo_ctx = None
