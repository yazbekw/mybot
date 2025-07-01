import pandas as pd
from trading_monitor import TradingMonitor
import logging
import time

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # إزالة أي مرجع لـ tkinter
        super().__init__(is_headless=True)
        self.is_running = True
        self.monitoring_loop()
        
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
