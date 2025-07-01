import os
import pandas as pd
import ccxt
import time
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import telegram
from telegram import ParseMode
import threading
from ta.trend import EMAIndicator  # استيراد EMA من ta
from ta.momentum import RSIIndicator  # استيراد RSI من ta

# إعدادات الاستراتيجية
SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT', 'ADA/USDT', 'DOGE/USDT']
INTERVAL = '1h'
FAST_EMA = 12
SLOW_EMA = 26
RSI_PERIOD = 10
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35
TRADE_SIZE = 9  # دولار لكل صفقة
MAX_OPEN_TRADES = 1  # صفقة واحدة مفتوحة لكل زوج

class TradingMonitor:
    def __init__(self, is_headless=False):
        self.performance_log = pd.DataFrame(columns=['symbol', 'signal', 'price', 'time'])
        self.orders_log = pd.DataFrame(columns=['symbol', 'side', 'price', 'amount', 'timestamp'])
        self.indicators_data = {}
        self.is_running = False
        self.coinex_connected = False
        self.client = None
        self.is_headless = is_headless
        
        # إعداد التسجيل
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
        
        self.load_api_keys()
        self.setup_daily_report()
        
        # إعداد بوت التليجرام إذا كانت المفاتيح متوفرة
        if hasattr(self, 'telegram_token') and hasattr(self, 'telegram_chat_id'):
            try:
                self.tg_bot = telegram.Bot(token=self.telegram_token)
                self.log_message("Telegram bot initialized successfully")
            except Exception as e:
                self.log_message(f"Failed to initialize Telegram bot: {str(e)}", "error")
    
    def load_api_keys(self):
        try:
            # تحميل المفاتيح من متغيرات البيئة
            self.access_id = os.getenv('COINEX_ACCESS_ID')
            self.secret_key = os.getenv('COINEX_SECRET_KEY')
            self.telegram_token = os.getenv('TELEGRAM_TOKEN')
            self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
        except Exception as e:
            self.log_message(f"Error loading environment variables: {str(e)}", "error")
    
    def connect_coinex(self):
        if not self.access_id or not self.secret_key:
            self.log_message("CoinEx API keys not found", "error")
            return
    
        try:
            self.client = ccxt.coinex({
                'apiKey': self.access_id,
                'secret': self.secret_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
        
            # اختبار الاتصال
            self.client.fetch_balance()
            self.coinex_connected = True
            self.log_message("Successfully connected to CoinEx")
        
        except Exception as e:
            self.coinex_connected = False
            self.log_message(f"Failed to connect to CoinEx: {str(e)}", "error")
    
    def log_message(self, message, level="info"):
        """إضافة رسالة إلى السجل"""
        if level.lower() == "error":
            logging.error(message)
        elif level.lower() == "warning":
            logging.warning(message)
        else:
            logging.info(message)
    
    def setup_daily_report(self):
        """جدولة التقرير اليومي"""
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.send_daily_report,
            'cron',
            hour=23,  # الساعة 11 مساءً
            minute=0
        )
        self.scheduler.start()
        self.log_message("Daily report scheduler started")

    def send_daily_report(self):
        """إرسال التقرير اليومي على Telegram"""
        if not hasattr(self, 'tg_bot'):
            return
            
        try:
            today = datetime.now().date()
            today_signals = self.performance_log[
                pd.to_datetime(self.performance_log['time']).dt.date == today
            ]
            
            completed_orders = self.get_today_completed_orders()
            profit_loss = self.calculate_daily_profit(completed_orders)
            
            report = self.generate_report_text(today_signals, completed_orders, profit_loss)
            
            self.tg_bot.send_message(
                chat_id=self.telegram_chat_id,
                text=report,
                parse_mode=ParseMode.MARKDOWN
            )
            self.log_message("Daily report sent to Telegram")
        except Exception as e:
            self.log_message(f"Error sending daily report: {str(e)}", "error")

    def get_today_completed_orders(self):
        if not self.coinex_connected:
            return []
            
        today = datetime.now().date()
        orders = []
        
        for symbol in SYMBOLS:
            try:
                completed = self.client.fetch_closed_orders(symbol, since=int(time.mktime(today.timetuple())*1000))
                orders.extend(completed)
            except Exception as e:
                self.log_message(f"Error fetching completed orders for {symbol}: {str(e)}", "error")
        
        return orders

    def calculate_daily_profit(self, orders):
        profit = 0.0
        
        for order in orders:
            if order['status'] == 'closed' and order['filled'] > 0:
                if order['side'] == 'sell':
                    profit += float(order['cost']) - float(order['filled']) * float(order['price'])
                elif order['side'] == 'buy':
                    profit -= float(order['cost'])
        
        return profit

    def generate_report_text(self, signals, orders, profit_loss):
        today = datetime.now().strftime('%Y-%m-%d')
        
        buy_signals = len(signals[signals['signal'] == 'BUY'])
        sell_signals = len(signals[signals['signal'] == 'SELL'])
        
        buy_orders = len([o for o in orders if o['side'] == 'buy'])
        sell_orders = len([o for o in orders if o['side'] == 'sell'])
        
        report = f"""
📊 *Daily Trading Report - {today}*

📈 *Signals Today:*
- BUY Signals: {buy_signals}
- SELL Signals: {sell_signals}

💼 *Executed Orders:*
- BUY Orders: {buy_orders}
- SELL Orders: {sell_orders}

💰 *Profit/Loss:*
${profit_loss:.2f} {'✅' if profit_loss >= 0 else '❌'}

🔍 *Last 5 Signals:*
"""
        
        last_signals = signals.tail(5).to_dict('records')
        for sig in last_signals:
            report += f"- {sig['signal']} {sig['symbol']} at {sig['price']:.4f}\n"
        
        return report
        
    def analyze_symbol(self, symbol):
        if not self.coinex_connected:
            self.log_message("Cannot analyze symbol - not connected to CoinEx", "warning")
            return
        
        try:
            ohlcv = self.client.fetch_ohlcv(symbol, INTERVAL, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
            # حساب المؤشرات باستخدام ta بدلاً من talib
            ema_fast = EMAIndicator(close=df['close'], window=FAST_EMA)
            df['fast_ema'] = ema_fast.ema_indicator()
            
            ema_slow = EMAIndicator(close=df['close'], window=SLOW_EMA)
            df['slow_ema'] = ema_slow.ema_indicator()
            
            rsi_indicator = RSIIndicator(close=df['close'], window=RSI_PERIOD)
            df['rsi'] = rsi_indicator.rsi()
            
            df = df.dropna()
        
            last_row = df.iloc[-1]
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
            buy_condition = (last_row['fast_ema'] > last_row['slow_ema']) and (last_row['rsi'] < RSI_OVERSOLD)
            sell_condition = (last_row['fast_ema'] < last_row['slow_ema']) and (last_row['rsi'] > RSI_OVERBOUGHT)
            
            signal = 'NEUTRAL'
            if buy_condition:
                signal = 'BUY'
            elif sell_condition:
                signal = 'SELL'
                
            self.indicators_data[symbol] = {
                'price': last_row['close'],
                'fast_ema': last_row['fast_ema'],
                'slow_ema': last_row['slow_ema'],
                'rsi': last_row['rsi'],
                'signal': signal
            }
        
            if buy_condition:
                signal_data = {
                    'symbol': symbol,
                    'signal': 'BUY',
                    'price': last_row['close'],
                    'time': current_time
                }
                self.performance_log = pd.concat([self.performance_log, pd.DataFrame([signal_data])], ignore_index=True)
                message = f"🚀 BUY Signal: {symbol} Price: {last_row['close']:.4f}"
                self.log_message(message)
            
                if self.coinex_connected:
                    self.place_order(symbol, 'buy', last_row['close'])
            
            elif sell_condition:
                signal_data = {
                    'symbol': symbol,
                    'signal': 'SELL',
                    'price': last_row['close'],
                    'time': current_time
                }
                self.performance_log = pd.concat([self.performance_log, pd.DataFrame([signal_data])], ignore_index=True)
                message = f"🔴 SELL Signal: {symbol} Price: {last_row['close']:.4f}"
                self.log_message(message)
            
                if self.coinex_connected:
                    self.place_order(symbol, 'sell', last_row['close'])
        
        except Exception as e:
            self.log_message(f"Analysis error for {symbol}: {str(e)}", "error")
        
    def place_order(self, symbol, side, price):
        try:
            open_orders = self.client.fetch_open_orders(symbol)
            if len(open_orders) >= MAX_OPEN_TRADES:
                self.log_message(f"Max open trades ({MAX_OPEN_TRADES}) reached for {symbol}", "warning")
                return False

            amount = TRADE_SIZE / float(price)
            amount = float(self.client.amount_to_precision(symbol, amount))

            if side == 'buy':
                balance = self.client.fetch_balance()
                usdt_balance = balance['free'].get('USDT', 0)
            
                if usdt_balance < TRADE_SIZE:
                    self.log_message(f"Insufficient USDT balance for {symbol}. Needed: {TRADE_SIZE}, Available: {usdt_balance:.2f}", "warning")
                    return False

            elif side == 'sell':
                base_currency = symbol.split('/')[0]
                balance = self.client.fetch_balance()
                coin_balance = balance['free'].get(base_currency, 0)
            
                if coin_balance < amount:
                    self.log_message(f"Insufficient {base_currency} balance for {symbol}. Needed: {amount:.6f}, Available: {coin_balance:.6f}", "warning")
                    return False

            order = self.client.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=self.client.price_to_precision(symbol, price),
                params={
                    'stop_loss': str(float(price) * 0.95),
                    'take_profit': str(float(price) * 1.10)
                }
            )
        
            self.log_message(f"Placed {side} order for {symbol} | Amount: {amount:.6f} | Price: {price:.4f}")
            return True
        
        except Exception as e:
            self.log_message(f"Failed to place {side} order for {symbol}: {str(e)}", "error")
            return False
    
    def monitoring_loop(self):
        # تأخير البدء لمدة 30 ثانية للسماح بتهيئة النظام
        time.sleep(30)
        
        while self.is_running:
            self.log_message("\n" + "="*40)
            self.log_message("Starting new market scan")
            
            for symbol in SYMBOLS:
                if not self.is_running:
                    break
                
                self.analyze_symbol(symbol)
                time.sleep(1)
            
            if self.is_running:
                time.sleep(300)
                
    def start_monitoring(self):
        if not self.is_running:
            self.is_running = True
            self.log_message("Monitoring started...")
            
            # استخدام threading فقط في الوضع العادي
            if not self.is_headless:
                monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
                monitor_thread.start()
            else:
                self.monitoring_loop()
        
    def stop_monitoring(self):
        self.is_running = False
        self.log_message("Monitoring stopped")
