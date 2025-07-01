import pandas as pd
from trading_monitor import TradingMonitor
import logging
import time
import tkinter as tk  # أضف هذا الاستيراد

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # إنشاء نافذة Tkinter خفية
        root = tk.Tk()
        root.withdraw()  # إخفاء النافذة الرئيسية
        
        # استدعاء المُنشئ الأب
        super().__init__(root)
        
        # إعدادات خاصة بالوضع الخفي
        self.performance_log = pd.DataFrame(columns=['symbol', 'signal', 'price', 'time'])
        self.orders_log = pd.DataFrame(columns=['symbol', 'side', 'price', 'amount', 'timestamp'])
        self.indicators_data = {}
        self.is_running = True
        
        # بدء المراقبة
        self.monitoring_loop()

if __name__ == "__main__":
    bot = HeadlessMonitor()
