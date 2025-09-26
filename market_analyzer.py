import pandas as pd
import requests
import numpy as np
from config import Config

class MarketAnalyzer:
    def __init__(self):
        self.top_coins = []
        self.volatility_threshold = Config.MIN_DAILY_VOLATILITY
    
    def get_top_coins(self, limit=10):
        """جلب أهم العملات من Binance API"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            response = requests.get(url)
            data = response.json()
            
            # تصفية العملات ذات الحجم الكافي
            filtered_coins = [
                coin for coin in data 
                if float(coin['quoteVolume']) > 1000000 and coin['symbol'].endswith('USDT')
            ]
            
            # ترتيب حسب حجم التداول
            sorted_coins = sorted(filtered_coins, 
                                key=lambda x: float(x['quoteVolume']), 
                                reverse=True)[:limit]
            
            self.top_coins = [coin['symbol'] for coin in sorted_coins]
            return self.top_coins
            
        except Exception as e:
            print(f"Error fetching top coins: {e}")
            return []
    
    def get_historical_data(self, symbol, interval='15m', limit=100):
        """جلب البيانات التاريخية من Binance"""
        try:
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy', 'ignored'
            ])
            
            # تحويل الأنواع
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_volatility(self, df):
        """حساب التقلب اليومي"""
        if df is None or len(df) < 2:
            return 0
        
        daily_returns = df['close'].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(365) * 100  # التقلب السنوي %
        return volatility
