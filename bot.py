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
SERVICE_ACCOUNT_FILE = 'sonic-stratum-457808-m2-85af1af437f9.json'
SPREADSHEET_NAME = 'Astoria_Bot_Заявки'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
gc = gspread.authorize(credentials)
sheet = gc.open(SPREADSHEET_NAME).sheet1

from telegram import InputFile

async def send_restaurant_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("menurest.pdf", "rb") as file:
        await update.callback_query.message.reply_document(InputFile(file), filename="Меню ресторана.pdf")

async def send_spa_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open("SPAMENU.pdf", "rb") as file:
        await update.callback_query.message.reply_document(InputFile(file), filename="Меню СПА услуг.pdf")

# Старт
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Посмотреть меню ресторана", callback_data="menu_rest")],
        [InlineKeyboardButton("Посмотреть СПА услуги", callback_data="menu_spa")],
        [InlineKeyboardButton("Забронировать столик", callback_data="book_table")],
        [InlineKeyboardButton("Записаться на СПА процедуру", callback_data="book_spa")],
    ]
    await update.message.reply_text(
        "Астория Гранде приветствует вас 🛳️\n"
        "Через этот бот вы можете получить *скидку 20%* в ресторане *Selection* и на *СПА процедуры*, при бронировании до дня начала Вашего круиза",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Сброс всех данных пользователя
    context.user_data.clear()
    context.application.chat_data[update.effective_chat.id].clear()

    if query.data == "menu_rest":
        await send_restaurant_menu(update, context)
        return ConversationHandler.END
    elif query.data == "menu_spa":
        await send_spa_menu(update, context)
        return ConversationHandler.END
    elif query.data == "book_table":
        context.user_data['service'] = "Ресторан"
    elif query.data == "book_spa":
        context.user_data['service'] = "СПА"

    await query.message.reply_text("Введите фамилию и имя гостя:")
    return ASK_NAME

# Запрос даты
async def ask_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Введите желаемую дату и время посещения:")
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
        f"✅ Спасибо! Вы записались в {context.user_data['service']}.\n"
        f"Пожалуйста, для подтверждения брони обратитесь на ресепшен в день посадки"
    )
    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Запуск бота
def main():
    app = ApplicationBuilder().token("7621300616:AAEMK_LyhhNk7ZTI0D3IPPB_hEGrsAHqzsY").build()

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
