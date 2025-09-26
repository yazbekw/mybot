import pandas as pd
import numpy as np
import ta

class IndicatorCalculator:
    def __init__(self, data):
        self.data = data
        self.high = data['high']
        self.low = data['low'] 
        self.close = data['close']
        self.volume = data['volume']
    
    def calculate_rsi(self):
        """حساب مؤشر RSI"""
        rsi = ta.momentum.RSIIndicator(self.close, window=14)
        rsi_value = rsi.rsi().iloc[-1]
        
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
    
    def calculate_macd(self):
        """حساب مؤشر MACD"""
        macd = ta.trend.MACD(self.close)
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]
        histogram = macd.macd_diff().iloc[-1]
        
        if macd_line > signal_line and histogram > 0:
            strength = (histogram / self.close.iloc[-1]) * 1000
            signal = 'BUY'
        elif macd_line < signal_line and histogram < 0:
            strength = abs(histogram / self.close.iloc[-1]) * 1000
            signal = 'SELL'
        else:
            strength = 0
            signal = 'NEUTRAL'
            
        return signal, min(strength, 100)
    
    def calculate_bollinger_bands(self):
        """حساب Bollinger Bands"""
        bb = ta.volatility.BollingerBands(self.close, window=20)
        upper_band = bb.bollinger_hband().iloc[-1]
        lower_band = bb.bollinger_lband().iloc[-1]
        current_price = self.close.iloc[-1]
        
        if current_price <= lower_band:
            strength = ((lower_band - current_price) / (upper_band - lower_band)) * 100
            signal = 'BUY'
        elif current_price >= upper_band:
            strength = ((current_price - upper_band) / (upper_band - lower_band)) * 100
            signal = 'SELL'
        else:
            strength = 0
            signal = 'NEUTRAL'
            
        return signal, min(strength, 100)
    
    def calculate_stochastic(self):
        """حساب Stochastic Oscillator"""
        stoch = ta.momentum.StochasticOscillator(self.high, self.low, self.close)
        k = stoch.stoch().iloc[-1]
        d = stoch.stoch_signal().iloc[-1]
        
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
    
    def calculate_ichimoku(self):
        """حساب Ichimoku Cloud"""
        ichimoku = ta.trend.IchimokuIndicator(self.high, self.low)
        tenkan = ichimoku.ichimoku_conversion_line().iloc[-1]
        kijun = ichimoku.ichimoku_base_line().iloc[-1]
        current_price = self.close.iloc[-1]
        
        if current_price > tenkan and current_price > kijun and tenkan > kijun:
            strength = 60  # قيمة متوسطة للإشارة القوية
            signal = 'BUY'
        elif current_price < tenkan and current_price < kijun and tenkan < kijun:
            strength = 60
            signal = 'SELL'
        else:
            strength = 0
            signal = 'NEUTRAL'
            
        return signal, strength
    
    def get_all_signals(self):
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
                    'strength': strength
                }
            except Exception as e:
                print(f"Error calculating {name}: {e}")
                signals[name] = {'signal': 'NEUTRAL', 'strength': 0}
        
        return signals
