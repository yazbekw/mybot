import requests
from config import Config

class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_signal(self, coin, overall_strength, signals, total_signal):
        """إرسال إشارة التداول"""
        if overall_strength < 60:
            return False
        
        # بناء الرسالة
        message = f"🚨 **إشارة {total_signal}** 🚨\n"
        message += f"**العملة:** {coin}\n"
        message += f"**القوة الإجمالية:** {overall_strength:.1f}%\n\n"
        message += "**تفاصيل المؤشرات:**\n"
        
        for indicator, data in signals.items():
            if data['strength'] > 50:
                message += f"• {indicator}: {data['signal']} ({data['strength']:.1f}%)\n"
        
        message += f"\n⏰ الوقت: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}"
        
        # إرسال الرسالة
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False
