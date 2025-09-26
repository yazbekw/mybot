import pandas as pd
import requests
import numpy as np
from typing import List, Optional
from config import Config

class MarketAnalyzer:
    def __init__(self):
        self.top_coins = []
        self.volatility_threshold = Config.MIN_DAILY_VOLATILITY
    
    def get_top_coins(self, limit: int = 10) -> List[str]:
        """جلب أهم العملات من Binance API"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # تصفية العملات ذات الحجم الكافي
            filtered_coins = [
                coin for coin in data 
                if (float(coin.get('quoteVolume', 0)) > 1000000 and 
                    coin.get('symbol', '').endswith('USDT'))
            ]
            
            # ترتيب حسب حجم التداول
            sorted_coins = sorted(filtered_coins, 
                                key=lambda x: float(x.get('quoteVolume', 0)), 
                                reverse=True)[:limit]
            
            self.top_coins = [coin['symbol'] for coin in sorted_coins]
            return self.top_coins
            
        except Exception as e:
            print(f"Error fetching top coins: {e}")
            return ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 
                   'BNBUSDT', 'XRPUSDT', 'DOGEUSDT', 'SOLUSDT', 'MATICUSDT']
    
    def get_historical_data(self, symbol: str, interval: str = '15m', limit: int = 100) -> Optional[pd.DataFrame]:
        """جلب البيانات التاريخية من Binance"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                return None
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy', 'ignored'
            ])
            
            # تحويل الأنواع
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.dropna()
            
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
