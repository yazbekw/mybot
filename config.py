import os
from dotenv import load_dotenv

# تحميل المتغيرات من .env
load_dotenv()

class Config:
    # مفاتيح التلغرام
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # إعدادات السوق
    CHECK_INTERVAL = 15  # دقائق
    TOP_COINS_COUNT = 10
    MIN_DAILY_VOLATILITY = 2.0  # % تقلب يومي أدنى
    
    # المؤشرات المختارة
    INDICATORS = [
        'RSI',
        'MACD', 
        'Bollinger_Bands',
        'Stochastic',
        'Ichimoku'
    ]
    
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
    required_vars = ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    for var in required_vars:
        if not getattr(Config, var):
            raise ValueError(f'Missing required environment variable: {var}')
