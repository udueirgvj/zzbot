import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import database

# معرف المالك (ضع معرفك هنا)
ADMIN_ID = 6001517585 # استبدل برقم معرفك
# يمكنك أيضاً استخدام كلمة مرور بدلاً من ذلك
# ADMIN_PASSWORD = "secret"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# حالات المحادثة الرئيسية
GOVERNORATE, NAME, SHOW_INFO = range(3)
# حالة لانتظار رفع الملف من المالك
WAITING_FOR_FILE = range(1)

GOVERNORATES = [
    'بغداد', 'البصرة', 'نينوى', 'أربيل', 'السليمانية', 'دهوك',
    'كركوك', 'صلاح الدين', 'ديالى', 'الأنبار', 'بابل', 'واسط',
    'القادسية', 'المثنى', 'ذي قار', 'ميسان', 'النجف', 'كربلاء'
]

# ========== دوال المستخدم العادي ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(gov, callback_data=gov)] for gov in GOVERNORATES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('مرحباً! اختر المحافظة:', reply_markup=reply_markup)
    return GOVERNORATE

async def governorate_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    governorate = query.data
    context.user_data['governorate'] = governorate
    await query.edit_message_text(f'تم اختيار محافظة {governorate}.\nالرجاء إرسال اسم الشخص:')
    return NAME

async def name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    governorate = context.user_data.get('governorate')
    info = database.get_person_info(governorate, name)
    if info:
        context.user_data['person_info'] = info
        context.user_data['person_name'] = name
        keyboard = [[InlineKeyboardButton("📋 عرض المعلومات", callback_data='show_info')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'✅ تم العثور على {name} في {governorate}. اضغط الزر أدناه لعرض جميع المعلومات:', reply_markup=reply_markup)
        return SHOW_INFO
    else:
        await update.message.reply_text('⚠️ لم يتم العثور على هذا الاسم في المحافظة المختارة. استخدم /start للبدء من جديد.')
        return ConversationHandler.END

async def show_info_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    info = context.user_data.get('person_info')
    if info:
        name, rate, age, job, emp_date, death_date, imprison_status = info
        response = (
            f"📌 **معلومات {name}**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 **الاسم:** {name}\n"
            f"🏙 **المحافظة:** {context.user_data.get('governorate')}\n"
            f"📊 **نسبة البطالة:** {rate}%\n"
            f"🎂 **العمر:** {age}\n"
            f"💼 **المهنة:** {job}\n"
            f"📅 **تاريخ التوظيف:** {emp_date}\n"
            f"⚰ **تاريخ الوفاة:** {death_date if death_date != 'لا يوجد' else 'لا يوجد'}\n"
            f"🔒 **حالة السجن:** {imprison_status}\n"
        )
        await query.edit_message_text(response, parse_mode='Markdown')
    else:
        await query.edit_message_text('⚠️ لم تعد المعلومات متاحة. استخدم /start من فضلك.')
    return ConversationHandler.END

# ========== دوال المالك ==========
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /admin للتحقق من هوية المالك"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية لاستخدام هذا الأمر.")
        return
    await update.message.reply_text(
        "🔐 مرحباً أيها المالك!\n"
        "يمكنك رفع ملف CSV جديد لتحديث قاعدة البيانات.\n"
        "أرسل الملف (يجب أن يكون بصيغة CSV ويحتوي على الأعمدة المطلوبة)."
    )
    return WAITING_FOR_FILE

async def handle_csv_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملف المرفوع (CSV)"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ ليس لديك صلاحية.")
        return ConversationHandler.END

    document = update.message.document
    if not document.file_name.endswith('.csv'):
        await update.message.reply_text("❌ يجب رفع ملف بصيغة CSV فقط.")
        return WAITING_FOR_FILE

    file = await document.get_file()
    file_content = await file.download_as_bytearray()
    try:
        columns = database.update_from_csv(file_content)
        await update.message.reply_text(
            f"✅ تم تحديث قاعدة البيانات بنجاح!\n"
            f"الأعمدة المستوردة: {', '.join(columns)}"
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ حدث خطأ أثناء تحديث قاعدة البيانات:\n{str(e)}")
    return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# ========== تشغيل البوت ==========
def main():
    TOKEN = 'YOUR_BOT_TOKEN'
    database.init_db()  # تهيئة الجدول (بدون بيانات)

    application = Application.builder().token(TOKEN).build()

    # محادثة المستخدم العادي
    user_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            GOVERNORATE: [CallbackQueryHandler(governorate_selected)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_received)],
            SHOW_INFO: [CallbackQueryHandler(show_info_button, pattern='show_info')],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
    )

    # محادثة المالك لرفع الملف
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_command)],
        states={
            WAITING_FOR_FILE: [MessageHandler(filters.Document.ALL, handle_csv_file)],
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
    )

    application.add_handler(user_conv)
    application.add_handler(admin_conv)

    application.run_polling()

if __name__ == '__main__':
    main()
