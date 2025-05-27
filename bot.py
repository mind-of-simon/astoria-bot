import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# Шаги диалога
ASK_NAME, ASK_DATETIME, ASK_PHONE = range(3)

# Доступ к Google Sheets
SERVICE_ACCOUNT_FILE = 'sonic-stratum-457808-m2-85af1af437f9.json'  # <-- поменяй на имя твоего JSON-файла
SPREADSHEET_NAME = 'Astoria_Bot_Заявки'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Посмотреть меню ресторана", url="https://your-site.com/menu")],
        [InlineKeyboardButton("Посмотреть СПА услуги", url="https://your-site.com/spa")],
        [InlineKeyboardButton("Забронировать столик", callback_data="book_table")],
        [InlineKeyboardButton("Записаться на СПА процедуру", callback_data="book_spa")],
    ]
    await update.message.reply_text(
        "Астория Гранде приветствует вас 🛳️\n"
        "Через этот бот вы можете получить *скидку 20%* при бронировании столика в ресторане *Selection*,\n"
        "а также при записи на *СПА услуги* до дня начала вашего круиза",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "book_table":
        context.user_data['service'] = "Ресторан"
    elif query.data == "book_spa":
        context.user_data['service'] = "СПА"

    await query.message.reply_text("Введите вашу Фамилию и Имя:")
    return ASK_NAME

# Запрос даты
async def ask_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите дату и время посещения:")
    return ASK_DATETIME

# Запрос телефона
async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['datetime'] = update.message.text
    await update.message.reply_text("Введите ваш номер телефона:")
    return ASK_PHONE

# Финал — запись в таблицу
async def final_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text

    row = [
        context.user_data['service'],
        context.user_data['name'],
        context.user_data['datetime'],
        context.user_data['phone'],
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ]
    sheet.append_row(row)

    await update.message.reply_text(
        f"✅ Спасибо! Вы записались на {context.user_data['service']}.\n"
        f"Мы вас ждём!"
    )
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Запуск бота
def main():
    app = ApplicationBuilder().token("7621300616:AAHNW0uEBMdkKZImBbA53Z8ws-ZvrAqyMC0").build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_datetime)],
            ASK_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
