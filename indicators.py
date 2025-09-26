import pandas as pd
import numpy as np
import ta
from typing import Dict, Tuple, Any

class IndicatorCalculator:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.high = data['high'] if 'high' in data.columns else data['Close']
        self.low = data['low'] if 'low' in data.columns else data['Low']
        self.close = data['close'] if 'close' in data.columns else data['Close']
        self.volume = data['volume'] if 'volume' in data.columns else data['Volume']
    
    def calculate_rsi(self) -> Tuple[str, float]:
        """حساب مؤشر RSI"""
        try:
            rsi = ta.momentum.RSIIndicator(self.close, window=14)
            rsi_value = rsi.rsi().iloc[-1]
            
            if pd.isna(rsi_value):
                return 'NEUTRAL', 0
                
            if rsi_value < 30:
                strength = ((30 - rsi_value) / 30) * 100
                signal = 'BUY'
            elif rsi_value > 70:
                strength = ((rsi_value - 70) / 30) * 100
                signal = 'SELL'
            else:
                strength = 0
                signal = 'NEUTRAL'
                
            return signal, min(strength, 100)
        except Exception as e:
            print(f"Error in RSI calculation: {e}")
            return 'NEUTRAL', 0
    
    def calculate_macd(self) -> Tuple[str, float]:
        """حساب مؤشر MACD"""
        try:
            macd = ta.trend.MACD(self.close)
            macd_line = macd.macd().iloc[-1]
            signal_line = macd.macd_signal().iloc[-1]
            histogram = macd.macd_diff().iloc[-1]
            
            if pd.isna(macd_line) or pd.isna(signal_line):
                return 'NEUTRAL', 0
                
            if macd_line > signal_line and histogram > 0:
                strength = abs(histogram / self.close.iloc[-1]) * 1000
                signal = 'BUY'
            elif macd_line < signal_line and histogram < 0:
                strength = abs(histogram / self.close.iloc[-1]) * 1000
                signal = 'SELL'
            else:
                strength = 0
                signal = 'NEUTRAL'
                
            return signal, min(strength, 100)
        except Exception as e:
            print(f"Error in MACD calculation: {e}")
            return 'NEUTRAL', 0
    
    def calculate_bollinger_bands(self) -> Tuple[str, float]:
        """حساب Bollinger Bands"""
        try:
            bb = ta.volatility.BollingerBands(self.close, window=20)
            upper_band = bb.bollinger_hband().iloc[-1]
            lower_band = bb.bollinger_lband().iloc[-1]
            current_price = self.close.iloc[-1]
            
            if pd.isna(upper_band) or pd.isna(lower_band):
                return 'NEUTRAL', 0
                
            band_width = upper_band - lower_band
            if band_width == 0:
                return 'NEUTRAL', 0
                
            if current_price <= lower_band:
                strength = ((lower_band - current_price) / band_width) * 100
                signal = 'BUY'
            elif current_price >= upper_band:
                strength = ((current_price - upper_band) / band_width) * 100
                signal = 'SELL'
            else:
                strength = 0
                signal = 'NEUTRAL'
                
            return signal, min(strength, 100)
        except Exception as e:
            print(f"Error in Bollinger Bands calculation: {e}")
            return 'NEUTRAL', 0
    
    def calculate_stochastic(self) -> Tuple[str, float]:
        """حساب Stochastic Oscillator"""
        try:
            stoch = ta.momentum.StochasticOscillator(self.high, self.low, self.close)
            k = stoch.stoch().iloc[-1]
            d = stoch.stoch_signal().iloc[-1]
            
            if pd.isna(k) or pd.isna(d):
                return 'NEUTRAL', 0
                
            if k < 20 and d < 20:
                strength = ((20 - min(k, d)) / 20) * 100
                signal = 'BUY'
            elif k > 80 and d > 80:
                strength = ((max(k, d) - 80) / 20) * 100
                signal = 'SELL'
            else:
                strength = 0
                signal = 'NEUTRAL'
                
            return signal, min(strength, 100)
        except Exception as e:
            print(f"Error in Stochastic calculation: {e}")
            return 'NEUTRAL', 0
    
    def calculate_ichimoku(self) -> Tuple[str, float]:
        """حساب Ichimoku Cloud"""
        try:
            ichimoku = ta.trend.IchimokuIndicator(self.high, self.low)
            tenkan = ichimoku.ichimoku_conversion_line().iloc[-1]
            kijun = ichimoku.ichimoku_base_line().iloc[-1]
            current_price = self.close.iloc[-1]
            
            if pd.isna(tenkan) or pd.isna(kijun):
                return 'NEUTRAL', 0
                
            if current_price > tenkan and current_price > kijun and tenkan > kijun:
                strength = 60
                signal = 'BUY'
            elif current_price < tenkan and current_price < kijun and tenkan < kijun:
                strength = 60
                signal = 'SELL'
            else:
                strength = 0
                signal = 'NEUTRAL'
                
            return signal, strength
        except Exception as e:
            print(f"Error in Ichimoku calculation: {e}")
            return 'NEUTRAL', 0
    
    def get_all_signals(self) -> Dict[str, Dict[str, Any]]:
        """جمع جميع إشارات المؤشرات"""
        signals = {}
        
        indicators_methods = {
            'RSI': self.calculate_rsi,
            'MACD': self.calculate_macd,
            'Bollinger_Bands': self.calculate_bollinger_bands,
            'Stochastic': self.calculate_stochastic,
            'Ichimoku': self.calculate_ichimoku
        }
        
        for name, method in indicators_methods.items():
            try:
                signal, strength = method()
                signals[name] = {
                    'signal': signal,
                    'strength': round(strength, 2)
                }
            except Exception as e:
                print(f"Error calculating {name}: {e}")
                signals[name] = {'signal': 'NEUTRAL', 'strength': 0}
        
        return signals
