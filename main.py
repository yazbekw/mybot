import time
import schedule
from datetime import datetime
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config import Config, validate_config
from market_analyzer import MarketAnalyzer
from indicators import IndicatorCalculator
from telegram_bot import TelegramBot

class TradingBot:
    def __init__(self):
        logger.info("Initializing Trading Bot...")
        validate_config()
        self.market_analyzer = MarketAnalyzer()
        self.telegram_bot = TelegramBot()
        self.processed_signals = set()
        logger.info("Trading Bot initialized successfully")
    
    def calculate_overall_signal(self, signals):
        """حساب الإشارة الإجمالية بناءً على المؤشرات المؤهلة"""
        try:
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
            
        except Exception as e:
            logger.error(f"Error calculating overall signal: {e}")
            return 0, 'NEUTRAL', {}
    
    def analyze_coin(self, symbol):
        """تحليل عملة معينة"""
        try:
            logger.info(f"Analyzing {symbol}...")
            
            # جلب البيانات
            data = self.market_analyzer.get_historical_data(symbol)
            if data is None or len(data) < 20:
                logger.warning(f"Insufficient data for {symbol}")
                return None
            
            # حساب المؤشرات
            calculator = IndicatorCalculator(data)
            signals = calculator.get_all_signals()
            
            # حساب الإشارة الإجمالية
            overall_strength, total_signal, contributing_indicators = self.calculate_overall_signal(signals)
            
            result = {
                'symbol': symbol,
                'overall_strength': overall_strength,
                'signal': total_signal,
                'contributing_indicators': contributing_indicators,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Analysis complete for {symbol}: {total_signal} ({overall_strength:.1f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def run_analysis(self):
        """تشغيل التحليل لجميع العملات"""
        logger.info("Starting market analysis...")
        
        try:
            # جلب أهم العملات
            top_coins = self.market_analyzer.get_top_coins(Config.TOP_COINS_COUNT)
            logger.info(f"Analyzing {len(top_coins)} coins: {top_coins}")
            
            signals_sent = 0
            
            for coin in top_coins:
                try:
                    result = self.analyze_coin(coin)
                    if result and result['overall_strength'] >= 60:
                        # منع الإشارات المكررة
                        signal_key = f"{coin}_{result['signal']}"
                        if signal_key not in self.processed_signals:
                            success = self.telegram_bot.send_signal(
                                coin=coin,
                                overall_strength=result['overall_strength'],
                                signals=result['contributing_indicators'],
                                total_signal=result['signal']
                            )
                            if success:
                                self.processed_signals.add(signal_key)
                                signals_sent += 1
                                logger.info(f"Signal sent for {coin}")
                    
                    time.sleep(2)  # تجنب rate limits
                    
                except Exception as e:
                    logger.error(f"Error processing {coin}: {e}")
                    continue
            
            logger.info(f"Analysis complete. Signals sent: {signals_sent}")
            
        except Exception as e:
            logger.error(f"Error in run_analysis: {e}")
    
    def start(self):
        """بدء تشغيل البوت"""
        logger.info("Starting Trading Bot...")
        
        # التشغيل الفوري أول مرة
        self.run_analysis()
        
        # جدولة التشغيل كل 15 دقيقة
        schedule.every(Config.CHECK_INTERVAL).minutes.do(self.run_analysis)
        
        logger.info(f"Bot scheduled to run every {Config.CHECK_INTERVAL} minutes")
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # فحص الجدولة كل دقيقة
            except KeyboardInterrupt:
                logger.info("Bot stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)

if __name__ == "__main__":
    try:
        bot = TradingBot()
        bot.start()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
