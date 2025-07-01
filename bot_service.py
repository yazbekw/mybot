import pandas as pd
from trading_monitor import TradingMonitor
import logging
import time

class HeadlessMonitor(TradingMonitor):
    def __init__(self):
        # Initialize without GUI components
        self.performance_log = pd.DataFrame(columns=['symbol', 'signal', 'price', 'time'])
        self.orders_log = pd.DataFrame(columns=['symbol', 'side', 'price', 'amount', 'timestamp'])
        self.indicators_data = {}
        self.is_running = True
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        self.load_api_keys()
        self.setup_daily_report()
        self.connect_coinex()
        
        # Start monitoring immediately
        self.monitoring_loop()

if __name__ == "__main__":
    bot = HeadlessMonitor()
