import gspread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ContentType, KeyboardButton, Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from datetime import datetime, timedelta
import os
from aiogram.client.bot import DefaultBotProperties

from aiohttp import web, ClientSession
from configer import config


note_stat = {}
# Налаштування доступу до Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]
# Вкажіть шлях до вашого JSON файлу
SERVICE_ACCOUNT_FILE = 'perepilochka-737ab50d12b5.json'


print(os.path.abspath(SERVICE_ACCOUNT_FILE))
creds = ServiceAccountCredentials.from_json_keyfile_name(
    SERVICE_ACCOUNT_FILE, SCOPE)
client = gspread.authorize(creds)

# Відкриття Google таблиці за її назвою або URL
SHEET_NAME = 'Test-date'
sheet = client.open_by_key('1lCdMi8FrukmA5qNEgK7bpwEFQpgLcp-qTp5DNWUsEgs')
worksheet = sheet.get_worksheet(0)  # Відкриваємо перший аркуш

# Налаштування Telegram
# TOKEN = '7937477586:AAEzZowQ8jQpOHjebyG3wxipr83RsrhvuIw'
# CHAT_ID = '1030040998'
bot = Bot(config.bot_token.get_secret_value(),
          default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
# Шлях до файлу з надісланими повідомленнями
# SENT_NOTIFICATIONS_FILE = 'sent_notifications.json'


# https://docs.google.com/spreadsheets/d/1lCdMi8FrukmA5qNEgK7bpwEFQpgLcp-qTp5DNWUsEgs/edit?usp=sharing

state_day_start = {}

# URL KeepAliveBot (замініть на реальний URL після деплою)
KEEPALIVE_BOT_URL = "https://your-keepalive-bot.onrender.com/ping"

# Додаємо обробник для /ping


@dp.message(Command("ping"))
async def handle_ping(message: types.Message):
    pass  # Просто ігноруємо


async def add_date(callback: types.CallbackQuery):
    rows = worksheet.get_all_values()
    user_id = callback.from_user.id
    if rows and rows[-1][0] == '*':
        today = datetime.now().strftime("%d.%m.%Y")
        state_day_start["date"] = today
        today = datetime.strptime(today, "%d.%m.%Y")
        # Додаємо новий рядок, дата у 2-й стовпець
        print(f"Дата: {today}")
        date_p_17 = today + timedelta(days=17)
        date_p_17 = date_p_17.strftime("%d.%m.%Y")
        today = datetime.now().strftime("%d.%m.%Y")
        worksheet.append_row([None, today, None, date_p_17])
        await callback.answer("✅Дата записана✅")
        await callback.message.answer("✅ Дата успішно додана в таблицю!")
        note_stat[user_id] = 1
        await callback.message.answer("Яку кількість яєць було закладено?\n(Напишіть лише число)")
    else:
        await callback.answer("❌Помилка❌")
        await callback.message.answer("❌На жаль, немає вільних інкубаторів!")


@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Меню")]
    ],
        resize_keyboard=True)
    await message.answer('Привіт, це бот мініферми "Степова перепілка"', reply_markup=keyboard)


async def send_note(user_id: int, message: types.Message, bot: Bot):
    rows = worksheet.get_all_values()
    czus = message.text
    last_row_index = len(rows)
    worksheet.update_cell(last_row_index, 5, czus)
    today = datetime.now().strftime("%d.%m.%Y")
    state_day_start["date"] = today
    today = datetime.strptime(today, "%d.%m.%Y")
    date_p_17 = today + timedelta(days=17)
    date_p_17 = date_p_17.strftime("%d.%m.%Y")
    await bot.send_message(user_id, f"Орієнтовна дата вилупу: {date_p_17}")


# Обробник натискання кнопки


@dp.callback_query(lambda c: c.data in ["add_date", "Arrngmnt"])
async def process_button(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if callback.data == "add_date":
        await add_date(callback)
    """elif callback.data == "Arrngmnt":
        t = await Arrangement()
        await bot.send_message(user_id, f"Розміщення перепелів", reply_markup=t)"""


menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Запуск інкубатора",
                                 callback_data="add_date")

        ]
    ]

)
# кнопка розміщення перепілок у клітках
""",
        [
            InlineKeyboardButton(text="Розміщення",
                                 callback_data="Arrngmnt")

        ]"""


@dp.message(F.text.lower() == "меню")
async def reply_action(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    await bot.send_message(user_id, "Обери дію:", reply_markup=menu)

# Запуск бота


@dp.message(lambda message: message.content_type == ContentType.TEXT)
async def handle_text(message: Message, bot: Bot):
    user_id = message.from_user.id
    """if user_id not in note_stat:
        note_stat[user_id] = {}"""
    if note_stat[user_id] == 1:
        await send_note(user_id, message, bot)
        note_stat[user_id] = 0


async def on_startup():
    print("Програма запущена. Виконання ініціалізації...")
    rows = worksheet.get_all_values()

    # Перевіряємо, чи є записи в таблиці
    if rows:
        # Останній запис у таблиці
        last_row = rows[-1]
        state_day_start["date"] = last_row[1]
        # Друкуємо останній запис у консоль
        print("Останній запис:", last_row[1])


async def check_periodically(bot: Bot):
    users = {1: 1030040998}
    while True:
        now = datetime.now()
        if (now.hour == 9 and now.minute == 34):
            if "date" in state_day_start:
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                date_plus_9 = saved_date + timedelta(days=9)
                date_plus_15 = saved_date + timedelta(days=15)
                date_plus_18 = saved_date + timedelta(days=18)
                today = datetime.now().strftime("%d.%m.%Y")
                if date_plus_9.strftime("%d.%m.%Y") == today:
                    print("✅ Дата збігається! Сьогодні 9-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 9-й день інкубації, потрібно зменшити вологу до 40% та почати провітрювати інкубатор")
                elif date_plus_15.strftime("%d.%m.%Y") == today:
                    print("✅ Дата збігається! Сьогодні 15-й день.")
                    await bot.send_message(CHAT_ID, "Сьогодні 15-й день інкубації, потрібно зменшити температуру до 37.4, збільшити вологу до 75-80% та викласти яйця на дно інкубатора")
                elif date_plus_18.strftime("%d.%m.%Y") == today:
                    rows = worksheet.get_all_values()
                    last_row_index = len(rows)
                    worksheet.update_cell(last_row_index, 1, "*")

                else:
                    print("❌ Дата не збігається.")

            else:
                print("Час перевірки! Але дати немає.")

        await asyncio.sleep(60)


async def main():
    await on_startup()

    asyncio.create_task(check_periodically(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
