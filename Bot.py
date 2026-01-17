import os
import logging
import ccxt.async_support as ccxt
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# تحميل المتغيرات من البيئة(Render Environment Variables)
load_dotenv()

# إعداد السجلات(Logs) لمراقبة البوت من Render
logging.basicConfig(
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level = logging.INFO
)

# الإعدادات الأساسية
API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
TG_TOKEN = os.getenv('TG_TOKEN')
ADMIN_ID = int(os.getenv('MY_CHAT_ID')) # حماية: البوت لا يرد إلا عليك

# تهيئة المنصة(بينانس كمثال)
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret' : SECRET_KEY,
    'enableRateLimit' : True,
    'options' : {'defaultType': 'spot'}
    })

    # دالة التأكد من هوية المستخدم
    def is_admin(update: Update) :
    return update.effective_user.id == ADMIN_ID

    # امر البدء / start
    async def start(update: Update, context : ContextTypes.DEFAULT_TYPE) :
    if not is_admin(update) : return
        await update.message.reply_text(
            "🤖 بوت التداول يعمل بنجاح!\n"
            "الأوامر المتاحة:\n"
            "/balance - عرض رصيد المحفظة\n"
            "/buy BTC/USDT 50 - شراء بـ 50 دولار\n"
            "/sell BTC/USDT 0.001 - بيع كمية محددة"
        )

        # امر جلب الرصيد
        async def get_balance(update: Update, context : ContextTypes.DEFAULT_TYPE) :
        if not is_admin(update) : return
            try :
            balance = await exchange.fetch_balance()
            usdt_balance = balance['total'].get('USDT', 0)
            await update.message.reply_text(f"💰 رصيدك المتاح: {usdt_balance} USDT")
            except Exception as e :
await update.message.reply_text(f"❌ خطأ في جلب الرصيد: {str(e)}")

# امر الشراء المباشر
async def buy(update: Update, context : ContextTypes.DEFAULT_TYPE) :
    if not is_admin(update) : return
        try :
        symbol = context.args[0].upper() # مثال : BTC / USDT
        amount_usdt = float(context.args[1])

        # تنفيذ أمر شراء بسعر السوق
        order = await exchange.create_market_buy_order(symbol, amount_usdt)
        await update.message.reply_text(f"✅ تم الشراء بنجاح!\nالرقم المرجعي: {order['id']}")
        except Exception as e :
await update.message.reply_text(f"❌ فشل الشراء: {str(e)}")

# إغلاق الاتصال عند توقف البوت
async def shutdown(app) :
    await exchange.close()

    if __name__ == '__main__' :
        application = ApplicationBuilder().token(TG_TOKEN).build()

        # إضافة الأوامر
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("balance", get_balance))
        application.add_handler(CommandHandler("buy", buy))

        print("🚀 Bot is starting on Render...")
        application.run_polling(close_loop = False)