import os
from dotenv import load_dotenv

# تحميل المتغيرات من .env
load_dotenv()

class Config:
    # مفاتيح التلغرام - مطلوبة
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # إعدادات السوق - مع قيم افتراضية
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '15'))
    TOP_COINS_COUNT = int(os.getenv('TOP_COINS_COUNT', '10'))
    MIN_DAILY_VOLATILITY = float(os.getenv('MIN_DAILY_VOLATILITY', '2.0'))
    
    # المؤشرات المختارة
    INDICATORS = ['RSI', 'MACD', 'Bollinger_Bands', 'Stochastic', 'Ichimoku']
    
    # أوزان المؤشرات
    INDICATOR_WEIGHTS = {
        'RSI': 20,
        'MACD': 25, 
        'Bollinger_Bands': 20,
        'Stochastic': 15,
        'Ichimoku': 20
    }

def validate_config():
    """التحقق من صحة الإعدادات"""
    if not Config.TELEGRAM_BOT_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN is required')
    if not Config.TELEGRAM_CHAT_ID:
        raise ValueError('TELEGRAM_CHAT_ID is required')
    print("✅ Configuration validated successfully")
