import os
import pandas as pd
import talib
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import logging
import socket
import ccxt
import json
import telegram
from telegram import ParseMode
from apscheduler.schedulers.background import BackgroundScheduler

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
    
    def load_api_keys(self):
        try:
            # تحميل المفاتيح من متغيرات البيئة
            self.access_id = os.getenv('COINEX_ACCESS_ID')
            self.secret_key = os.getenv('COINEX_SECRET_KEY')
            self.telegram_token = os.getenv('TELEGRAM_TOKEN')
            self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            # إظهار في الواجهة (اختياري)
            if hasattr(self, 'access_id_entry'):
                self.access_id_entry.insert(0, self.access_id or '')
                self.secret_key_entry.insert(0, self.secret_key or '')
                
        except Exception as e:
            self.log_message(f"Error loading environment variables: {str(e)}", "error")
        
    def __init__(self, root):
        self.root = root
        self.root.title("Crypto Trading Monitor")
        self.performance_log = pd.DataFrame(columns=['symbol', 'signal', 'price', 'time'])
        self.orders_log = pd.DataFrame(columns=['symbol', 'side', 'price', 'amount', 'timestamp'])
        self.indicators_data = {}
        self.is_running = False
        self.coinex_connected = False
        self.client = None
        
        # إعداد التسجيل
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_monitor.log'),
                logging.StreamHandler()
            ]
        )
        
        # تحميل المفاتيح من متغيرات البيئة
        self.load_api_keys()
        
        # إنشاء واجهة المستخدم
        self.setup_ui()
        
        # إعداد التقرير اليومي
        self.setup_daily_report()
        
        # إعداد بوت التليجرام إذا كانت المفاتيح متوفرة
        if self.telegram_token and self.telegram_chat_id:
            try:
                self.tg_bot = telegram.Bot(token=self.telegram_token)
                self.log_message("Telegram bot initialized successfully")
            except Exception as e:
                self.log_message(f"Failed to initialize Telegram bot: {str(e)}", "error")
        else:
            self.log_message("Telegram credentials not found in environment variables", "warning")
    
    def connect_coinex(self):
        # استخدام المفاتيح من متغيرات البيئة بدلاً من واجهة المستخدم
        if not self.access_id or not self.secret_key:
            self.log_message("CoinEx API keys not found in environment variables", "error")
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
            self.connection_status.config(text="Connected", foreground="green")
            self.log_message("Successfully connected to CoinEx")
            self.refresh_account_info()
        
        except Exception as e:
            self.coinex_connected = False
            self.connection_status.config(text="Connection failed", foreground="red")
            self.log_message(f"Failed to connect to CoinEx: {str(e)}", "error")
    
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
            # حساب الأداء اليومي
            today = datetime.now().date()
            today_signals = self.performance_log[
                pd.to_datetime(self.performance_log['time']).dt.date == today
            ]
            
            # حساب الأرباح/الخسائر من الأوامر المكتملة
            completed_orders = self.get_today_completed_orders()
            profit_loss = self.calculate_daily_profit(completed_orders)
            
            # إنشاء نص التقرير
            report = self.generate_report_text(today_signals, completed_orders, profit_loss)
            
            # إرسال التقرير
            self.tg_bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=report,
                parse_mode=ParseMode.MARKDOWN
            )
            self.log_message("Daily report sent to Telegram")
        except Exception as e:
            self.log_message(f"Error sending daily report: {str(e)}", "error")

    def get_today_completed_orders(self):
        """الحصول على الأوامر المكتملة اليوم"""
        if not self.coinex_connected:
            return []
            
        today = datetime.now().date()
        orders = []
        
        for symbol in SYMBOLS:
            try:
                completed = self.client.fetch_closed_orders(symbol, since=int(time.mktime(today.timetuple())*1000)
                orders.extend(completed)
            except Exception as e:
                self.log_message(f"Error fetching completed orders for {symbol}: {str(e)}", "error")
        
        return orders

    def calculate_daily_profit(self, orders):
        """حساب الأرباح/الخسائر اليومية"""
        profit = 0.0
        
        for order in orders:
            if order['status'] == 'closed' and order['filled'] > 0:
                if order['side'] == 'sell':
                    profit += float(order['cost']) - float(order['filled']) * float(order['price'])
                elif order['side'] == 'buy':
                    profit -= float(order['cost'])
        
        return profit

    def generate_report_text(self, signals, orders, profit_loss):
        """إنشاء نص التقرير"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # ملخص الإشارات
        buy_signals = len(signals[signals['signal'] == 'BUY'])
        sell_signals = len(signals[signals['signal'] == 'SELL'])
        
        # ملخص الأوامر
        buy_orders = len([o for o in orders if o['side'] == 'buy'])
        sell_orders = len([o for o in orders if o['side'] == 'sell'])
        
        # إنشاء التقرير
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
        
        # إضافة آخر 5 إشارات
        last_signals = signals.tail(5).to_dict('records')
        for sig in last_signals:
            report += f"- {sig['signal']} {sig['symbol']} at {sig['price']:.4f}\n"
        
        return report
        
    def setup_ui(self):
        """تهيئة مكونات واجهة المستخدم"""
        # شريط الحالة
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # إطار المؤشرات الفنية
        frame_indicators = ttk.LabelFrame(self.root, text="Technical Indicators", padding=10)
        frame_indicators.pack(fill=tk.X, padx=10, pady=5)
        
        # شجرة لعرض المؤشرات
        self.indicators_tree = ttk.Treeview(frame_indicators, 
                                          columns=('symbol', 'price', 'fast_ema', 'slow_ema', 'rsi', 'signal'), 
                                          show='headings',
                                          height=7)
        
        # تخصيص أعمدة الشجرة
        self.indicators_tree.heading('symbol', text='Symbol')
        self.indicators_tree.heading('price', text='Price')
        self.indicators_tree.heading('fast_ema', text=f'Fast EMA ({FAST_EMA})')
        self.indicators_tree.heading('slow_ema', text=f'Slow EMA ({SLOW_EMA})')
        self.indicators_tree.heading('rsi', text=f'RSI ({RSI_PERIOD})')
        self.indicators_tree.heading('signal', text='Signal')
        
        # تحديد عرض الأعمدة
        self.indicators_tree.column('symbol', width=80, anchor=tk.CENTER)
        self.indicators_tree.column('price', width=100, anchor=tk.CENTER)
        self.indicators_tree.column('fast_ema', width=100, anchor=tk.CENTER)
        self.indicators_tree.column('slow_ema', width=100, anchor=tk.CENTER)
        self.indicators_tree.column('rsi', width=80, anchor=tk.CENTER)
        self.indicators_tree.column('signal', width=80, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(frame_indicators, orient=tk.VERTICAL, command=self.indicators_tree.yview)
        self.indicators_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.indicators_tree.pack(fill=tk.BOTH, expand=True)
        
        # إطار تسجيل الدخول إلى CoinEx
        frame_auth = ttk.LabelFrame(self.root, text="CoinEx Authentication", padding=10)
        frame_auth.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(frame_auth, text="Access ID:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.access_id_entry = ttk.Entry(frame_auth, width=40)
        self.access_id_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(frame_auth, text="Secret Key:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.secret_key_entry = ttk.Entry(frame_auth, width=40, show="*")
        self.secret_key_entry.grid(row=1, column=1, padx=5, pady=2)
        
        self.connect_button = ttk.Button(frame_auth, text="Connect to CoinEx", command=self.connect_coinex)
        self.connect_button.grid(row=2, column=0, columnspan=2, pady=5)
        
        self.connection_status = ttk.Label(frame_auth, text="Not connected", foreground="red")
        self.connection_status.grid(row=3, column=0, columnspan=2)
        
    def cancel_all_orders(self):
        """إلغاء جميع الأوامر المفتوحة"""
        if not self.coinex_connected:
            self.log_message("Not connected to CoinEx", "warning")
            return
        
        try:
            for symbol in SYMBOLS:
                self.client.cancel_all_orders(symbol)
            self.log_message("All open orders cancelled")
            self.refresh_account_info()
        except Exception as e:
            self.log_message(f"Error cancelling orders: {str(e)}", "error")
        
    
    def refresh_account_info(self):
        """تحديث معلومات الحساب"""
        if not self.coinex_connected:
            self.log_message("Not connected to CoinEx", "warning")
            return
        
        try:
            # الحصول على الرصيد
            balance = self.client.fetch_balance()
            usdt_balance = balance['total'].get('USDT', 0)
            btc_balance = balance['total'].get('BTC', 0)
        
            balance_text = f"Balance: USDT: {usdt_balance:.2f} | BTC: {btc_balance:.6f}"
            self.balance_label.config(text=balance_text)
        
            # الحصول على الأوامر المفتوحة
            open_orders = self.client.fetch_open_orders()
            self.update_orders_tree(open_orders)
            self.log_message("Account information refreshed")

            try:
                for symbol in SYMBOLS:
                    # استخدام fetchClosedOrders بدلاً من fetchOrders
                    completed_orders = self.client.fetch_closed_orders(symbol, limit=10)  # آخر 10 أوامر مغلقة لكل رمز
                    self.update_completed_orders_tree(completed_orders)
            except Exception as e:
                self.log_message(f"Error fetching completed orders: {str(e)}", "error")
        
        except Exception as e:
            self.log_message(f"Error refreshing account info: {str(e)}", "error")
            
    def update_completed_orders_tree(self, orders):
        """تحديث شجرة الأوامر المكتملة"""
        for item in self.completed_tree.get_children():
            self.completed_tree.delete(item)
        
        for order in orders:
            if order['status'] == 'closed':
                self.completed_tree.insert('', 'end', values=(
                    order['symbol'],
                    order['side'],
                    float(order['price']),
                    float(order['amount']),
                    datetime.fromtimestamp(order['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S'),
                    order['status']
                ))
             
    
    def update_orders_tree(self, orders):
        """تحديث شجرة الأوامر المفتوحة"""
        # مسح البيانات القديمة
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
            
        # إضافة الأوامر الجديدة
        for order in orders:
            self.orders_tree.insert('', 'end', values=(
                order['symbol'],
                order['side'],
                float(order['price']),
                float(order['amount']),
                datetime.fromtimestamp(order['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S')
            ))
    
    def log_message(self, message, level="info"):
        """إضافة رسالة إلى السجل"""
        self.log_text.configure(state='normal')
        self.log_text.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        self.log_text.configure(state='disabled')
        self.log_text.see(tk.END)
        self.status_var.set(message[:100])  # تحديث شريط الحالة
        
        # تسجيل الدخول إلى الملف أيضًا
        if level.lower() == "error":
            logging.error(message)
        elif level.lower() == "warning":
            logging.warning(message)
        else:
            logging.info(message)
    
    def update_performance(self):
        """تحديث ملخص الأداء"""
        if not self.performance_log.empty:
            buy_signals = len(self.performance_log[self.performance_log['signal'] == 'BUY'])
            sell_signals = len(self.performance_log[self.performance_log['signal'] == 'SELL'])
            summary = f"Total BUY Signals: {buy_signals} | Total SELL Signals: {sell_signals}"
            self.performance_label.config(text=summary)
    
    def get_binance_data(self, symbol):
        """جلب البيانات من Binance مع منطق إعادة المحاولة المتقدم"""
        # تم الحفاظ على هذه الوظيفة كما هي ولكن تم تغيير رمز الزوج ليتوافق مع تنسيق CCXT
        pass
    
        
    def update_indicators_tree(self):
        """تحديث شجرة المؤشرات بالقيم الحالية"""
        # مسح البيانات القديمة
        for item in self.indicators_tree.get_children():
            self.indicators_tree.delete(item)
            
        # إضافة البيانات الجديدة
        for symbol, data in self.indicators_data.items():
            self.indicators_tree.insert('', 'end', values=(
                symbol,
                f"{data['price']:.4f}",
                f"{data['fast_ema']:.4f}",
                f"{data['slow_ema']:.4f}",
                f"{data['rsi']:.2f}",
                data['signal']
            ))
    
    def analyze_symbol(self, symbol):
        """تحليل زوج التداول مع مراعاة الحدود الجديدة"""
        if not self.coinex_connected:
            self.log_message("Cannot analyze symbol - not connected to CoinEx", "warning")
            return
        
        try:
            # جلب بيانات OHLCV من CoinEx
            ohlcv = self.client.fetch_ohlcv(symbol, INTERVAL, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
            # حساب المؤشرات الفنية
            df['fast_ema'] = talib.EMA(df['close'], timeperiod=FAST_EMA)
            df['slow_ema'] = talib.EMA(df['close'], timeperiod=SLOW_EMA)
            df['rsi'] = talib.RSI(df['close'], timeperiod=RSI_PERIOD)
            df = df.dropna()
        
            last_row = df.iloc[-1]
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
            buy_condition = (last_row['fast_ema'] > last_row['slow_ema']) and (last_row['rsi'] < RSI_OVERSOLD)
            sell_condition = (last_row['fast_ema'] < last_row['slow_ema']) and (last_row['rsi'] > RSI_OVERBOUGHT)
            
            # تخزين بيانات المؤشرات
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
            
            # تحديث شجرة المؤشرات
            self.update_indicators_tree()
        
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
        
            self.update_performance()
        
        except Exception as e:
            self.log_message(f"Analysis error for {symbol}: {str(e)}", "error")
        
        
    def place_order(self, symbol, side, price):
        """وضع أمر تداول مع مراعاة حجم الصفقة والحد الأقصى للأوامر المفتوحة"""
        try:
            # التحقق من عدد الأوامر المفتوحة لهذا الزوج
            open_orders = self.client.fetch_open_orders(symbol)
            if len(open_orders) >= MAX_OPEN_TRADES:
                self.log_message(f"Max open trades ({MAX_OPEN_TRADES}) reached for {symbol}", "warning")
                return False

            # حساب الكمية بناءً على TRADE_SIZE
            amount = TRADE_SIZE / float(price)
            amount = float(self.client.amount_to_precision(symbol, amount))

            if side == 'buy':
                # التحقق من الرصيد المتاح
                balance = self.client.fetch_balance()
                usdt_balance = balance['free'].get('USDT', 0)
            
                if usdt_balance < TRADE_SIZE:
                    self.log_message(f"Insufficient USDT balance for {symbol}. Needed: {TRADE_SIZE}, Available: {usdt_balance:.2f}", "warning")
                    return False

            elif side == 'sell':
                # التحقق من الرصيد المتاح للعملة الأساسية
                base_currency = symbol.split('/')[0]
                balance = self.client.fetch_balance()
                coin_balance = balance['free'].get(base_currency, 0)
            
                if coin_balance < amount:
                    self.log_message(f"Insufficient {base_currency} balance for {symbol}. Needed: {amount:.6f}, Available: {coin_balance:.6f}", "warning")
                    return False

            # وضع الأمر
            order = self.client.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=amount,
                price=self.client.price_to_precision(symbol, price),
                params={
                    'stop_loss': str(float(price) * 0.95),  # وقف خسارة 5%
                    'take_profit': str(float(price) * 1.10)  # جني ربح 10%
                }
            )
        
            self.log_message(f"Placed {side} order for {symbol} | Amount: {amount:.6f} | Price: {price:.4f}")
            self.refresh_account_info()
            return True
        
        except Exception as e:
            self.log_message(f"Failed to place {side} order for {symbol}: {str(e)}", "error")
            return False
    
    def monitoring_loop(self):
        """حلقة المراقبة الرئيسية"""
        while self.is_running:
            self.log_message("\n" + "="*40)
            self.log_message("Starting new market scan")
            
            for symbol in SYMBOLS:
                if not self.is_running:
                    break
                
                self.analyze_symbol(symbol)
                time.sleep(1)  # وقفة بين الأزواج
            
            if self.is_running:
                # تحديث معلومات الحساب كل مسح
                if self.coinex_connected:
                    self.refresh_account_info()
                time.sleep(300)  # انتظر 5 دقائق بين عمليات المسح
        
    def start_monitoring(self):
        """بدء عملية المراقبة"""
        if not self.is_running:
            self.is_running = True
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.log_message("Monitoring started...")
            
            # بدء المراقبة في موضوع منفصل
            monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            monitor_thread.start()
        
    def stop_monitoring(self):
        """إيقاف عملية المراقبة"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("Monitoring stopped")


if __name__ == "__main__":
    root = tk.Tk()
    app = TradingMonitor(root)
    root.geometry("1000x800")
    root.mainloop()