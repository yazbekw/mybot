import pandas as pd
from trading_monitor import TradingMonitor  # تأكد من أن الملف باسم trading_monitor.py
import logging
import time

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # تجاوز تهيئة الواجهة الرسومية
        self.performance_log = pd.DataFrame(columns=['symbol', 'signal', 'price', 'time'])
        self.orders_log = pd.DataFrame(columns=['symbol', 'side', 'price', 'amount', 'timestamp'])
        self.indicators_data = {}
        self.is_running = True
        
        # إعداد التسجيل
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        self.load_api_keys()
        self.setup_daily_report()
        self.connect_coinex()

if __name__ == "__main__":
    bot = HeadlessMonitor()
    bot.monitoring_loop()  # سيتم تشغيل الحلقة إلى الأبد
