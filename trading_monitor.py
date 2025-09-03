import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')
import pickle
import json
from tqdm import tqdm
import telegram
from telegram import Update, InputFile
from telegram.ext import Application, ContextTypes
import asyncio
import io

# إعداد التنسيقات
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['axes.unicode_minus'] = False
sns.set_palette("viridis")

class BNBTimeWeightIndicator:
    def __init__(self, telegram_token=None, chat_id=None):
        self.df = None
        self.time_weights_matrix = None
        self.performance_report = {}
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.bot = None
        
        if telegram_token and chat_id:
            self.setup_telegram_bot(telegram_token)
    
    def setup_telegram_bot(self, token):
        """إعداد بوت التلغرام"""
        try:
            self.bot = telegram.Bot(token=token)
            print("✅ تم إعداد بوت التلغرام بنجاح")
        except Exception as e:
            print(f"❌ خطأ في إعداد بوت التلغرام: {e}")
    
    async def send_telegram_message(self, message):
        """إرسال رسالة إلى التلغرام"""
        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(chat_id=self.chat_id, text=message)
            except Exception as e:
                print(f"❌ خطأ في إرسال الرسالة: {e}")
    
    async def send_telegram_image(self, image_path, caption=""):
        """إرسال صورة إلى التلغرام"""
        if self.bot and self.chat_id:
            try:
                with open(image_path, 'rb') as photo:
                    await self.bot.send_photo(chat_id=self.chat_id, photo=photo, caption=caption)
            except Exception as e:
                print(f"❌ خطأ في إرسال الصورة: {e}")
    
    async def send_telegram_document(self, file_path, caption=""):
        """إرسال ملف إلى التلغرام"""
        if self.bot and self.chat_id:
            try:
                with open(file_path, 'rb') as document:
                    await self.bot.send_document(chat_id=self.chat_id, document=document, caption=caption)
            except Exception as e:
                print(f"❌ خطأ في إرسال الملف: {e}")

    def fetch_historical_data(self, days=180):
        """جلب البيانات التاريخية من Binance API"""
        print("📊 جلب البيانات التاريخية لـ BNB...")
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        current_time = start_time
        total_days = (end_time - start_time) / (1000 * 60 * 60 * 24)
        
        with tqdm(total=total_days, desc="جلب البيانات") as pbar:
            while current_time < end_time:
                url = "https://api.binance.com/api/v3/klines"
                params = {
                    'symbol': 'BNBUSDT',
                    'interval': '5m',
                    'limit': 1000,
                    'startTime': current_time
                }
                
                try:
                    response = requests.get(url, params=params, timeout=15)
                    data = response.json()
                    
                    if not data:
                        break
                        
                    all_data.extend(data)
                    current_time = data[-1][0] + 300000  # 5 دقائق
                    pbar.update(1)
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"⚠️ خطأ في جلب البيانات: {e}")
                    break
        
        if not all_data:
            raise Exception("❌ لم يتم جلب أي بيانات")
        
        # معالجة البيانات
        columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                  'close_time', 'quote_asset_volume', 'number_of_trades',
                  'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
        
        self.df = pd.DataFrame(all_data, columns=columns)
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'], unit='ms')
        self.df.set_index('timestamp', inplace=True)
        
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col])
        
        # حساب العوائد
        self.df['returns'] = self.df['close'].pct_change()
        
        print(f"✅ تم جلب {len(self.df)} سجل للبيانات")
        return self.df
    
    def remove_outliers(self, data, threshold=3):
        """إزالة القيم المتطرفة باستخدام Z-Score"""
        if len(data) < 2:
            return data
        z_scores = np.abs(stats.zscore(data.dropna()))
        return data[(z_scores < threshold)]
    
    def calculate_time_weights(self):
        """حساب الأوزان الزمنية لكل فترة 5 دقائق"""
        if self.df is None:
            raise Exception("❌ يجب جلب البيانات أولاً")
        
        print("⚖️ حساب الأوزان الزمنية...")
        
        # إعداد مصفوفة الأوزان (7 أيام × 288 فترة)
        self.time_weights_matrix = np.zeros((7, 288))
        performance_stats = np.zeros((7, 288))
        
        # استخراج معلومات الوقت
        self.df['weekday'] = self.df.index.weekday
        self.df['time_slot'] = (self.df.index.hour * 12 + 
                               self.df.index.minute // 5)
        
        # حساب الأوزان لكل فترة
        for weekday in range(7):
            for time_slot in tqdm(range(288), desc=f"يوم {weekday}"):
                mask = (self.df['weekday'] == weekday) & (self.df['time_slot'] == time_slot)
                returns_data = self.df.loc[mask, 'returns']
                
                if len(returns_data) > 10:  # تحتاج إلى بيانات كافية
                    # إزالة القيم المتطرفة
                    clean_returns = self.remove_outliers(returns_data)
                    
                    if len(clean_returns) > 5:
                        # حساب الأداء والمؤشر
                        mean_return = clean_returns.mean()
                        success_rate = (clean_returns > 0).mean()
                        confidence = min(len(clean_returns) / 100, 1.0)  # ثقة إحصائية
                        
                        # حساب الوزن (-10 إلى +10)
                        weight = mean_return * 1000  # تضخيم للتأثير
                        weight *= confidence  # مرجحة بالثقة
                        
                        # تطبيق معدل النجاح
                        if success_rate > 0.6:
                            weight *= 1.5
                        elif success_rate < 0.4:
                            weight *= 0.5
                        
                        # تقييد بين -10 و +10
                        weight = max(min(weight, 10), -10)
                        
                        self.time_weights_matrix[weekday, time_slot] = weight
                        performance_stats[weekday, time_slot] = len(clean_returns)
        
        return self.time_weights_matrix
    
    def generate_performance_report(self):
        """توليد تقرير أداء مفصل"""
        if self.time_weights_matrix is None:
            raise Exception("❌ يجب حساب الأوزان أولاً")
        
        print("📈 توليد تقرير الأداء...")
        
        weekdays = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
        
        # أفضل أوقات الشراء والبيع
        best_buy_times = []
        best_sell_times = []
        
        for weekday in range(7):
            for time_slot in range(288):
                weight = self.time_weights_matrix[weekday, time_slot]
                if weight > 5:  # إشارة شراء قوية
                    hour = time_slot // 12
                    minute = (time_slot % 12) * 5
                    best_buy_times.append({
                        'time': f"{weekdays[weekday]} {hour:02d}:{minute:02d}",
                        'weight': float(weight),
                        'hour': hour,
                        'minute': minute,
                        'weekday': weekday
                    })
                elif weight < -5:  # إشارة بيع قوية
                    hour = time_slot // 12
                    minute = (time_slot % 12) * 5
                    best_sell_times.append({
                        'time': f"{weekdays[weekday]} {hour:02d}:{minute:02d}",
                        'weight': float(weight),
                        'hour': hour,
                        'minute': minute,
                        'weekday': weekday
                    })
        
        # ترتيب النتائج
        best_buy_times.sort(key=lambda x: x['weight'], reverse=True)
        best_sell_times.sort(key=lambda x: x['weight'])
        
        self.performance_report = {
            'best_buy_times': best_buy_times[:15],
            'best_sell_times': best_sell_times[:15],
            'overall_stats': {
                'positive_signals': int(np.sum(self.time_weights_matrix > 0)),
                'negative_signals': int(np.sum(self.time_weights_matrix < 0)),
                'neutral_signals': int(np.sum(self.time_weights_matrix == 0)),
                'avg_positive_weight': float(np.mean(self.time_weights_matrix[self.time_weights_matrix > 0])),
                'avg_negative_weight': float(np.mean(self.time_weights_matrix[self.time_weights_matrix < 0])),
                'total_signals': int(np.prod(self.time_weights_matrix.shape)),
                'analysis_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'data_points': len(self.df)
            }
        }
        
        return self.performance_report
    
    def create_detailed_report_text(self):
        """إنشاء نص التقرير المفصل للتلغرام"""
        report = self.performance_report
        stats = report['overall_stats']
        
        text = "📊 *تقرير أداء المؤشر الزمني لـ BNB*\n\n"
        text += f"📅 تاريخ التحليل: {stats['analysis_date']}\n"
        text += f"📈 عدد نقاط البيانات: {stats['data_points']:,}\n\n"
        
        text += "📊 *الإحصائيات العامة:*\n"
        text += f"• إشارات الشراء: {stats['positive_signals']} \n"
        text += f"• إشارات البيع: {stats['negative_signals']} \n"
        text += f"• إشارات محايدة: {stats['neutral_signals']} \n"
        text += f"• متوسط وزن الشراء: {stats['avg_positive_weight']:.2f} \n"
        text += f"• متوسط وزن البيع: {stats['avg_negative_weight']:.2f} \n\n"
        
        text += "🟢 *أقوى 5 إشارات شراء:*\n"
        for i, signal in enumerate(report['best_buy_times'][:5]):
            text += f"{i+1}. {signal['time']} - الوزن: {signal['weight']:.2f}\n"
        
        text += "\n🔴 *أقوى 5 إشارات بيع:*\n"
        for i, signal in enumerate(report['best_sell_times'][:5]):
            text += f"{i+1}. {signal['time']} - الوزن: {signal['weight']:.2f}\n"
        
        text += "\n💡 *التوصية:*\n"
        if stats['avg_positive_weight'] > abs(stats['avg_negative_weight']):
            text += "السوق يميل للشراء بشكل عام"
        else:
            text += "السوق يميل للبيع بشكل عام"
        
        return text
    
    def save_results(self):
        """حفظ النتائج إلى ملفات"""
        if self.time_weights_matrix is None:
            raise Exception("❌ يجب حساب الأوزان أولاً")
        
        # حفظ مصفوفة الأوزان
        weights_df = pd.DataFrame(self.time_weights_matrix)
        weights_df.index = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
        weights_df.columns = [f"{h//12:02d}:{(h%12)*5:02d}" for h in range(288)]
        weights_df.to_csv('bnb_time_weights.csv', encoding='utf-8-sig')
        
        # حفظ إشارات التداول
        signals = []
        for weekday in range(7):
            for time_slot in range(288):
                weight = self.time_weights_matrix[weekday, time_slot]
                if abs(weight) > 1:  # إشارات ذات معنى
                    hour = time_slot // 12
                    minute = (time_slot % 12) * 5
                    signals.append({
                        'weekday': ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'][weekday],
                        'time': f"{hour:02d}:{minute:02d}",
                        'weight': float(weight),
                        'signal': 'BUY' if weight > 0 else 'SELL',
                        'strength': abs(weight)
                    })
        
        signals_df = pd.DataFrame(signals)
        signals_df.to_csv('bnb_trading_signals.csv', encoding='utf-8-sig', index=False)
        
        # حفظ التقرير
        with open('bnb_performance_report.json', 'w', encoding='utf-8') as f:
            json.dump(self.performance_report, f, ensure_ascii=False, indent=2)
        
        # حفظ المصفوفة للاستخدام المباشر
        np.save('bnb_time_weights_matrix.npy', self.time_weights_matrix)
        
        print("💾 تم حفظ النتائج في الملفات")
    
    def visualize_results(self):
        """تصور النتائج برسوم بيانية"""
        if self.time_weights_matrix is None:
            raise Exception("❌ يجب حساب الأوزان أولاً")
        
        print("🎨 إنشاء الرسوم البيانية...")
        
        # خريطة حرارية
        plt.figure(figsize=(20, 10))
        sns.heatmap(self.time_weights_matrix, 
                   cmap='RdYlGn',
                   center=0,
                   cbar_kws={'label': 'وزن الإشارة (-10 إلى +10)'})
        plt.title('خريطة أوزان التداول الزمنية لـ BNB')
        plt.ylabel('يوم الأسبوع')
        plt.xlabel('وقت اليوم (كل 5 دقائق)')
        plt.savefig('bnb_trading_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # توزيع الأوزان
        plt.figure(figsize=(12, 6))
        plt.hist(self.time_weights_matrix.flatten(), bins=50, alpha=0.7, color='skyblue')
        plt.title('توزيع أوزان الإشارات الزمنية')
        plt.xlabel('الوزن')
        plt.ylabel('التكرار')
        plt.grid(True, alpha=0.3)
        plt.savefig('bnb_weights_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # أفضل أوقات التداول
        buy_times = [signal['weight'] for signal in self.performance_report['best_buy_times'][:10]]
        sell_times = [signal['weight'] for signal in self.performance_report['best_sell_times'][:10]]
        
        plt.figure(figsize=(12, 6))
        plt.bar(range(len(buy_times)), buy_times, alpha=0.7, label='شراء', color='green')
        plt.bar(range(len(sell_times)), sell_times, alpha=0.7, label='بيع', color='red')
        plt.title('أقوى إشارات التداول')
        plt.xlabel('الإشارة')
        plt.ylabel('الوزن')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.savefig('bnb_top_signals.png', dpi=300, bbox_inches='tight')
        plt.close()

    async def send_complete_report(self):
        """إرسال التقرير الكامل إلى التلغرام"""
        if not self.bot or not self.chat_id:
            print("⚠️ إعدادات التلغرام غير مكتملة")
            return
        
        try:
            # إرسال النص الرئيسي
            report_text = self.create_detailed_report_text()
            await self.send_telegram_message(report_text)
            
            # إرسال الصور
            await asyncio.sleep(1)
            await self.send_telegram_image('bnb_trading_heatmap.png', 'خريطة حرارية لأوزان التداول')
            
            await asyncio.sleep(1)
            await self.send_telegram_image('bnb_weights_distribution.png', 'توزيع الأوزان')
            
            await asyncio.sleep(1)
            await self.send_telegram_image('bnb_top_signals.png', 'أقوى إشارات التداول')
            
            # إرسال الملفات
            await asyncio.sleep(1)
            await self.send_telegram_document('bnb_time_weights.csv', 'مصفوفة الأوزان الكاملة')
            
            await asyncio.sleep(1)
            await self.send_telegram_document('bnb_trading_signals.csv', 'إشارات التداول')
            
            await asyncio.sleep(1)
            await self.send_telegram_document('bnb_performance_report.json', 'التقرير المفصل')
            
            print("✅ تم إرسال التقرير الكامل إلى التلغرام")
            
        except Exception as e:
            print(f"❌ خطأ في إرسال التقرير: {e}")

# الدالة الرئيسية غير المتزامنة
async def main():
    # إعدادات التلغرام - ضع التوكن والآيدي الخاصين بك
    TELEGRAM_TOKEN = "7925838105:AAF5HwcXewyhrtyEi3_EF4r2p_R4Q5iMBfg"
    CHAT_ID = "1467259305"
    
    try:
        analyzer = BNBTimeWeightIndicator(telegram_token=TELEGRAM_TOKEN, chat_id=CHAT_ID)
        
        # إرسال رسالة بدء التحليل
        await analyzer.send_telegram_message("🔍 بدء تحليل المؤشر الزمني لـ BNB...")
        
        # جلب البيانات
        analyzer.fetch_historical_data(days=180)
        
        # حساب الأوزان
        analyzer.calculate_time_weights()
        
        # توليد التقرير
        analyzer.generate_performance_report()
        
        # حفظ النتائج
        analyzer.save_results()
        
        # تصور النتائج
        analyzer.visualize_results()
        
        # إرسال التقرير الكامل إلى التلغرام
        await analyzer.send_complete_report()
        
        print("🎉 تم الانتهاء بنجاح وإرسال النتائج إلى التلغرام!")
        
    except Exception as e:
        error_msg = f"❌ خطأ في التحليل: {str(e)}"
        print(error_msg)
        if analyzer.bot:
            await analyzer.send_telegram_message(error_msg)

# للتشغيل على Render
if __name__ == "__main__":
    # التشغيل على Render (بدون توكن التلغرام)
    analyzer = BNBTimeWeightIndicator()
    
    try:
        # جلب البيانات
        analyzer.fetch_historical_data(days=180)
        
        # حساب الأوزان
        analyzer.calculate_time_weights()
        
        # توليد التقرير
        report = analyzer.generate_performance_report()
        
        # حفظ النتائج
        analyzer.save_results()
        
        # تصور النتائج
        analyzer.visualize_results()
        
        print("🎉 تم الانتهاء بنجاح!")
        print("\n📋 ملخص النتائج:")
        print(f"   - إشارات شراء قوية: {len(report['best_buy_times'])}")
        print(f"   - إشارات بيع قوية: {len(report['best_sell_times'])}")
        print(f"   - متوسط وزن الشراء: {report['overall_stats']['avg_positive_weight']:.2f}")
        print(f"   - متوسط وزن البيع: {report['overall_stats']['avg_negative_weight']:.2f}")
        
    except Exception as e:
        print(f"❌ خطأ: {e}")

