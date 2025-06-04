import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, ContextTypes, filters
)

# Шаги диалога
ASK_DEPARTURE_DATE, ASK_NAME, ASK_CABIN, ASK_DATETIME, ASK_GUESTS, ASK_PHONE = range(6)

# Доступ к Google Sheets
SERVICE_ACCOUNT_FILE = 'sonic-stratum-457808-m2-85af1af437f9.json'
SPREADSHEET_NAME = 'Astoria_Bot_Заявки'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1

# Приветствие
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Посмотреть меню ресторана", callback_data="menu_rest")],
        [InlineKeyboardButton("Посмотреть СПА услуги", callback_data="menu_spa")],
        [InlineKeyboardButton("Забронировать столик", callback_data="book_table")],
        [InlineKeyboardButton("Забронировать торжество", callback_data="book_event")],
        [InlineKeyboardButton("Записаться на СПА процедуру", callback_data="book_spa")],
    ]
    await update.message.reply_text(
        "Астория Гранде приветствует вас!\n\n"
        "Через этот бот вы можете заранее забронировать столик в ресторане Selection или услуги в СПА-комплексе и получить специальную скидку:\n\n"
        "- 10% на все меню в ресторане Selection при бронировании семейного или романтического ужина\n"
        "- 20% на все меню в ресторане Selection, если вы хотите отметить торжество (от 6 человек)\n"
        "- 10% на первую и 15% на вторую процедуру в СПА-комплексе",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Меню
async def send_restaurant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("menurest.pdf", "rb") as file:
        await update.callback_query.message.reply_document(InputFile(file), filename="Меню ресторана.pdf")

async def send_spa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("SPAMENU.pdf", "rb") as file:
        await update.callback_query.message.reply_document(InputFile(file), filename="Меню СПА услуг.pdf")

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    if query.data == "menu_rest":
        await send_restaurant_menu(update, context)
        return ConversationHandler.END
    elif query.data == "menu_spa":
        await send_spa_menu(update, context)
        return ConversationHandler.END
    elif query.data in ["book_table", "book_event", "book_spa"]:
        service = {
            "book_table": "Ресторан (ужин)",
            "book_event": "Ресторан (торжество)",
            "book_spa": "СПА"
        }[query.data]
        context.user_data['service'] = service
        await query.message.reply_text("1. Введите дату отправления вашего круиза:")
        return ASK_DEPARTURE_DATE

# Последовательные шаги запроса данных
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['departure_date'] = update.message.text
    await update.message.reply_text("2. Введите фамилию и имя гостя:")
    return ASK_NAME

async def ask_cabin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("3. Введите номер каюты:")
    return ASK_CABIN

async def ask_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['cabin'] = update.message.text
    await update.message.reply_text("4. Введите желаемую дату и время посещения:")
    return ASK_DATETIME

async def ask_guests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['datetime'] = update.message.text
    await update.message.reply_text("5. Введите количество гостей:")
    return ASK_GUESTS

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['guests'] = update.message.text
    await update.message.reply_text("6. Введите ваш номер телефона:")
    return ASK_PHONE

# Финальный шаг
async def final_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.text
    moscow_time = datetime.datetime.now(pytz.timezone('Europe/Moscow')).strftime("%Y-%m-%d %H:%M:%S")

    row = [
        context.user_data['departure_date'],
        context.user_data['cabin'],
        context.user_data['service'],
        context.user_data['name'],
        context.user_data['datetime'],
        context.user_data['guests'],
        context.user_data['phone'],
        moscow_time
    ]
    sheet.append_row(row)

    await update.message.reply_text(
        "✅ Спасибо! Вы записались\n"
        "Для подтверждения записи, пожалуйста, обратитесь на ресепшн в день посадки.\n"
        "Важно! Скидка действительна при подтверждении записи до 23:59 в день посадки.\n"
        "Приятного путешествия с Astoria Grande!"
    )
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Запуск
def main():
    app = ApplicationBuilder().token("7621300616:AAGUQmS-rY7o_UE1TzWh-M5KO5doEijzpAw").build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            ASK_DEPARTURE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cabin)],
            ASK_CABIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_datetime)],
            ASK_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_guests)],
            ASK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
