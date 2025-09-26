import time
import schedule
from datetime import datetime
from config import Config, validate_config
from market_analyzer import MarketAnalyzer
from indicators import IndicatorCalculator
from telegram_bot import TelegramBot

class TradingBot:
    def __init__(self):
        validate_config()
        self.market_analyzer = MarketAnalyzer()
        self.telegram_bot = TelegramBot()
        self.processed_signals = set()
    
    def calculate_overall_signal(self, signals):
        """حساب الإشارة الإجمالية بناءً على المؤشرات المؤهلة"""
        total_weight = 0
        weighted_strength = 0
        contributing_indicators = {}
        
        for indicator, data in signals.items():
            if data['strength'] > 50:  # تجاهل المؤشرات الضعيفة
                weight = Config.INDICATOR_WEIGHTS.get(indicator, 0)
                total_weight += weight
                
                # تحديد اتجاه الإشارة (شراء/بيع)
                signal_multiplier = 1 if data['signal'] == 'BUY' else -1
                weighted_strength += data['strength'] * weight * signal_multiplier
                
                contributing_indicators[indicator] = data
        
        if total_weight == 0:
            return 0, 'NEUTRAL', {}
        
        overall_strength = abs(weighted_strength) / total_weight
        total_signal = 'BUY' if weighted_strength > 0 else 'SELL'
        
        return overall_strength, total_signal, contributing_indicators
    
    def analyze_coin(self, symbol):
        """تحليل عملة معينة"""
        try:
            # جلب البيانات
            data = self.market_analyzer.get_historical_data(symbol)
            if data is None or len(data) < 20:
                return None
            
            # حساب المؤشرات
            calculator = IndicatorCalculator(data)
            signals = calculator.get_all_signals()
            
            # حساب الإشارة الإجمالية
            overall_strength, total_signal, contributing_indicators = self.calculate_overall_signal(signals)
            
            return {
                'symbol': symbol,
                'overall_strength': overall_strength,
                'signal': total_signal,
                'contributing_indicators': contributing_indicators,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None
    
    def run_analysis(self):
        """تشغيل التحليل لجميع العملات"""
        print(f"{datetime.now()} - بدء التحليل...")
        
        # جلب أهم العملات
        top_coins = self.market_analyzer.get_top_coins(Config.TOP_COINS_COUNT)
        
        if not top_coins:
            print("فشل في جلب قائمة العملات")
            return
        
        print(f"تحليل {len(top_coins)} عملة...")
        
        for coin in top_coins:
            try:
                result = self.analyze_coin(coin)
                if result and result['overall_strength'] >= 60:
                    # منع الإشارات المكررة
                    signal_key = f"{coin}_{result['signal']}_{int(result['overall_strength'])}"
                    if signal_key not in self.processed_signals:
                        self.telegram_bot.send_signal(
                            coin=coin,
                            overall_strength=result['overall_strength'],
                            signals=result['contributing_indicators'],
                            total_signal=result['signal']
                        )
                        self.processed_signals.add(signal_key)
                        print(f"إشارة مرسلة لـ {coin}")
                
                time.sleep(1)  # تجنب rate limits
                
            except Exception as e:
                print(f"Error processing {coin}: {e}")
                continue
    
    def start(self):
        """بدء تشغيل البوت"""
        print("بدء تشغيل بوت التداول...")
        
        # التشغيل الفوري أول مرة
        self.run_analysis()
        
        # جدولة التشغيل كل 15 دقيقة
        schedule.every(Config.CHECK_INTERVAL).minutes.do(self.run_analysis)
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # فحص الجدولة كل دقيقة
            except KeyboardInterrupt:
                print("إيقاف البوت...")
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.start()
