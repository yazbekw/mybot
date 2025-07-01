from trading_monitor import TradingMonitor
import logging
import time
import sys

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # استدعاء المُنشئ الأب مع الوسيط الصحيح
        super().__init__(is_headless=True)
        
        # بدء المراقبة
        self.start_monitoring()
        
        # الحفاظ على البرنامج قيد التشغيل
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_monitoring()
            sys.exit(0)
        
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
