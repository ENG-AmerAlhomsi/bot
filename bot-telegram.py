import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import sqlite3

# تحميل المتغيرات من .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

MARKETERS = {
    "2425": "أحمد",
    "3691": "خالد",
    "1234": "حمزة",
    # ... يمكنك إضافة المزيد حسب الحاجة
}

# خطوات المحادثة
NAME, PHONE, PRODUCT, STORE, PAYMENT, REFERRAL, REVIEW, CORRECTION_FIELD, CORRECTION_VALUE = range(9)

# إعداد قاعدة البيانات
def setup_database():
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        phone TEXT,
                        product TEXT,
                        store TEXT,
                        payment TEXT,
                        referral TEXT,
                        marketer_name TEXT 
                    )''')
    conn.commit()
    conn.close()

def save_order(name, phone, product, store, payment, referral, marketer_name):
    conn = sqlite3.connect("orders.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (name, phone, product, store, payment, referral, marketer_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, product, store, payment, referral, marketer_name))
    conn.commit()
    conn.close()

# دالة timeout 
async def timeout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "انتهت مهلة الجلسة لعدم التفاعل.\nإذا أردت البدء مجددًا، اكتب /start"
        )
    else:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="انتهت مهلة الجلسة لعدم التفاعل.\nاكتب /start لبدء محادثة جديدة."
            )
    return ConversationHandler.END

# بدء المحادثة
async def start(update: Update, context):
    args = context.args
    if args:
        marketer_code = args[0]
        marketer_name = MARKETERS.get(marketer_code, "unknown")
        context.user_data['marketer_name'] = marketer_name
    else:
        context.user_data['marketer_name'] = "unknown"
    message = (
        "مرحبا بك في شركة EasyPay SY\n"
        "(لبيع وتقسيط المنتجات).\n"
        "أمامك 6 خطوات لإتمام الطلب...\n\n"
        "لنبدأ!\n"
        "1-يرجى إدخال الاسم الثلاثي:\n"
        "/cancel"
    )
    await update.message.reply_text(message)
    return NAME

async def get_name(update: Update, context):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("2-يرجى إدخال رقم هاتفك:\n/cancel")
    return PHONE

async def get_phone(update: Update, context):
    phone = update.message.text
    if not phone.isdigit() or len(phone) < 10 or len(phone) > 10:
        await update.message.reply_text("يرجى إدخال رقم هاتف صحيح يحتوي على أرقام فقط (10 أرقام فقط).")
        return PHONE
    context.user_data['phone'] = phone
    await update.message.reply_text("3-يرجى إدخال اسم المنتج الذي ترغب بشرائه مع كامل التفاصيل مثلاً (اللون أو الحجم أو الماركة):\n/cancel")
    return PRODUCT

async def get_product(update: Update, context):
    context.user_data['product'] = update.message.text
    await update.message.reply_text("4-يرجى إدخال اسم المتجر الذي ترغب بالشراء منه. في حال لا يوجد متجر معين، يرجى كتابة ((غير محدد)):\n/cancel")
    return STORE

async def get_store(update: Update, context):
    context.user_data['store'] = update.message.text
    reply_keyboard = [["كاش", "تقسيط 3 أشهر", "تقسيط 6 أشهر"]]
    await update.message.reply_text(
        "5-يرجى اختيار نوع الدفع:\n/cancel",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return PAYMENT

async def get_payment(update: Update, context):
    context.user_data['payment'] = update.message.text
    await update.message.reply_text(
        "6-هل من الممكن اخبارنا بطريقة معرفتك بخدمتنا؟ في حال لا يوجد شخص معين يرجى كتابة ((غير محدد)):\n/cancel"
    )
    return REFERRAL

async def get_referral(update: Update, context):
    context.user_data['referral'] = update.message.text
    await update.message.reply_text("شكرًا لك. الآن سيتم عرض البيانات للتأكد من صحتها.")
    return await review_data(update, context)

async def review_data(update: Update, context):
    user_data = context.user_data
    summary = (
        f"هذه هي بياناتك:\n"
        f"الاسم الثلاثي: {user_data['name']}\n"
        f"رقم الهاتف: {user_data['phone']}\n"
        f"اسم المنتج: {user_data['product']}\n"
        f"اسم المتجر: {user_data['store']}\n"
        f"نوع الدفع: {user_data['payment']}\n"
        f"الشخص الذي عرفك بالشركة: {user_data['referral']}\n\n"
        "هل البيانات صحيحة؟"
    )
    reply_keyboard = [["نعم", "لا"]]
    await update.message.reply_text(summary, reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    return REVIEW

async def handle_review(update: Update, context):
    if update.message.text == "نعم":
        user_data = context.user_data
        save_order(
            user_data['name'],
            user_data['phone'],
            user_data['product'],
            user_data['store'],
            user_data['payment'],
            user_data['referral'],
            user_data.get('marketer_name', 'unknown')
        )

        # أرسل معلومات الطلب للإدمن كنص
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                "طلب جديد وصل!\n\n"
                f"الاسم: {user_data['name']}\n"
                f"رقم الهاتف: {user_data['phone']}\n"
                f"اسم المنتج: {user_data['product']}\n"
                f"اسم المتجر: {user_data['store']}\n"
                f"نوع الدفع: {user_data['payment']}\n"
                f"الشخص الذي عرفك بالشركة: {user_data['referral']}\n"
                f"المسوِّق الذي جلب الزبون: {user_data.get('marketer_name', 'غير معروف')}"
            )
        )

        await update.message.reply_text("شكرًا لك! تم إرسال طلبك.", reply_markup=ReplyKeyboardRemove())
        # الرسالة الثانية: كيفية بدء طلب جديد
        await update.message.reply_text(
            "إذا أردت إرسال طلب آخر، اكتب الأمر /start من جديد.\n"
            "شكرًا لاستخدامك EasyPay SY!"
        )
        return ConversationHandler.END

    elif update.message.text == "لا":
        reply_keyboard = [
            ["الاسم", "رقم الهاتف"],
            ["اسم المنتج", "اسم المتجر"],
            ["نوع الدفع", "الشخص الذي عرفك بالشركة"]
        ]
        await update.message.reply_text(
            "يرجى اختيار البيانات التي تريد تعديلها:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CORRECTION_FIELD

async def handle_correction_field(update: Update, context):
    field_to_edit = update.message.text
    context.user_data['field_to_edit'] = field_to_edit

    if field_to_edit == "نوع الدفع":
        reply_keyboard = [["كاش", "تقسيط 3 أشهر", "تقسيط 6 أشهر"]]
        await update.message.reply_text(
            "يرجى اختيار نوع الدفع الجديد:",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return CORRECTION_VALUE
    else:
        # بقية الحقول:
        await update.message.reply_text(
            f"يرجى إدخال القيمة الجديدة لـ {field_to_edit}:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CORRECTION_VALUE

async def handle_correction_value(update: Update, context):
    field = context.user_data.get('field_to_edit')
    new_value = update.message.text

    if field == "الاسم":
        context.user_data['name'] = new_value
    elif field == "رقم الهاتف":
        if not new_value.isdigit() or len(new_value) < 10 or len(new_value) > 10:
            await update.message.reply_text(
                "الرقم المدخل غير صالح! يرجى إدخال رقم يحتوي على أرقام فقط (10 أرقام فقط)."
            )
            return CORRECTION_VALUE
        context.user_data['phone'] = new_value
    elif field == "اسم المنتج":
        context.user_data['product'] = new_value
    elif field == "اسم المتجر":
        context.user_data['store'] = new_value
    elif field == "نوع الدفع":
        context.user_data['payment'] = new_value
    elif field == "الشخص الذي عرفك بالشركة":
        context.user_data['referral'] = new_value
    else:
        await update.message.reply_text("خطأ: لم يتم التعرف على الحقل.")
        return CORRECTION_FIELD

    await update.message.reply_text(
        f"تم تحديث {field} بنجاح.",
        reply_markup=ReplyKeyboardRemove()
    )
    return await review_data(update, context)

async def cancel_conversation(update: Update, context):
    await update.message.reply_text("تم إلغاء العملية. يمكنك إعادة البدء بكتابة /start في أي وقت.")
    return ConversationHandler.END

def main():
    setup_database()
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product)],
            STORE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_store)],
            PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_payment)],
            REFERRAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_referral)],

            REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review)],

            CORRECTION_FIELD: [
                MessageHandler(filters.Regex('^(الاسم|رقم الهاتف|اسم المنتج|اسم المتجر|نوع الدفع|الشخص الذي عرفك بالشركة)$'),
                            handle_correction_field)
            ],
            CORRECTION_VALUE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction_value)
            ],

            # حالة انقضاء المهلة (اختيارية)
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, timeout_callback)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            MessageHandler(filters.Regex("^خروج$"), cancel_conversation)
        ],
        conversation_timeout=30  # 900 ثانية (15 دقيقة)
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
