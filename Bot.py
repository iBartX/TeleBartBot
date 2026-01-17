import os
import asyncio
import logging
import pandas_ta as ta
import pandas as pd
from datetime import datetime
from expertoptionapi.stable_api import ExpertOptionAPI
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# إعدادات البيئة
load_dotenv()
SSID = os.getenv('EXPERT_OPTION_SSID')
TG_TOKEN = os.getenv('TG_TOKEN')
ADMIN_ID = int(os.getenv('MY_CHAT_ID'))

# متغيرات الحالة
AUTO_TRADE = False # وضع التداول الآلي (مغلق افتراضياً)
RISK_PERCENT = 0.02 # المخاطرة بـ 2% من الرصيد لكل صفقة
TAKE_PROFIT_GOAL = 100 # التوقف إذا ربح البوت 100 دولار مثلاً
STOP_LOSS_LIMIT = 50   # التوقف إذا خسر البوت 50 دولار كإجمالي

# تهيئة المنصة
api = ExpertOptionAPI(SSID)
logging.basicConfig(level=logging.INFO)

# --- وظائف التداول والاستراتيجية ---

def get_signal():
    """ استراتيجية بسيطة تعتمد على مؤشر RSI """
    # هنا يتم جلب الشموع وتحليلها (مثال توضيحي)
    # في ExpertOption نحتاج لجلب البيانات عبر السوكت
    candles = api.get_candles("EURUSD", 60) # جلب آخر شموع
    df = pd.DataFrame(candles)
    rsi = ta.rsi(df['close'], length=14)
    last_rsi = rsi.iloc[-1]
    
    if last_rsi < 30: return "buy"  # تشبع بيعي
    elif last_rsi > 70: return "sell" # تشبع شرائي
    return None

async def execute_trade(direction, amount, update=None):
    """ تنفيذ الصفقة مع التحقق من الرصيد """
    status, info = api.buy(amount, "EURUSD", direction, 60)
    msg = f"🚀 تم تنفيذ صفقة {direction} بمبلغ {amount}$" if status else f"❌ فشل: {info}"
    print(msg)
    if update:
        await update.message.reply_text(msg)

# --- أوامر تليجرام ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_text(
        "🛠️ بوت ExpertOption الاحترافي جاهز\n\n"
        "🎮 **التحكم اليدوي:**\n"
        "/buy - شراء | /sell - بيع\n\n"
        "🤖 **التداول الآلي:**\n"
        "/auto_on - تشغيل الآلي | /auto_off - إيقاف\n\n"
        "📊 **الحساب:**\n"
        "/status - حالة الرصيد والأرباح"
    )

async def toggle_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global AUTO_TRADE
    if update.effective_user.id != ADMIN_ID: return
    AUTO_TRADE = not AUTO_TRADE
    status = "شغال ✅" if AUTO_TRADE else "متوقف 🛑"
    await update.message.reply_text(f"وضع التداول الآلي الآن: {status}")

async def manual_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    success, balance = api.get_balance()
    amount = int(balance * RISK_PERCENT) # حساب حجم الصفقة آلياً (2%)
    await execute_trade("buy", amount, update)

async def manual_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    success, balance = api.get_balance()
    amount = int(balance * RISK_PERCENT)
    await execute_trade("sell", amount, update)

# --- المحرك الرئيسي (Background Task) ---

async def trading_engine(app):
    """ المحرك الذي يعمل في الخلفية للتحليل الآلي """
    global AUTO_TRADE
    print("المحرك يعمل في الخلفية...")
    while True:
        if AUTO_TRADE:
            # 1. فحص الرصيد لإدارة المخاطر
            success, balance = api.get_balance()
            if success:
                amount = int(balance * RISK_PERCENT)
                
                # 2. الحصول على إشارة التداول
                signal = get_signal() 
                if signal:
                    await execute_trade(signal, amount)
                    await app.bot.send_message(chat_id=ADMIN_ID, text=f"🤖 آلي: فتح صفقة {signal}")
        
        await asyncio.sleep(10) # فحص كل 10 ثواني

if __name__ == '__main__':
    application = ApplicationBuilder().token(TG_TOKEN).build()
    
    # تعريف الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auto_on", toggle_auto))
    application.add_handler(CommandHandler("auto_off", toggle_auto))
    application.add_handler(CommandHandler("buy", manual_buy))
    application.add_handler(CommandHandler("sell", manual_sell))

    # تشغيل المحرك الآلي مع البوت
    loop = asyncio.get_event_loop()
    loop.create_task(trading_engine(application))
    
    application.run_polling()
