import pandas as pd
from trading_monitor import TradingMonitor
import logging
import time
import tkinter as tk

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # إنشاء نافذة خفية
        root = tk.Tk()
        root.withdraw()  # إخفاء النافذة
        
        # استدعاء المُنشئ الأب مع النافذة الخفية
        super().__init__(root)
        
        # إعدادات خاصة بالوضع الخفي
        self.is_running = True
        
        # بدء المراقبة
        self.monitoring_loop()
        
    def setup_ui(self):
        """تجاوز تهيئة الواجهة في الوضع الخفي"""
        # لا نقوم بإنشاء أي عناصر واجهة
        pass
        
    def log_message(self, message, level="info"):
        """تسجيل الرسائل فقط في ملف السجل"""
        if level.lower() == "error":
            logging.error(message)
        elif level.lower() == "warning":
            logging.warning(message)
        else:
            logging.info(message)

if __name__ == "__main__":
    bot = HeadlessMonitor()
