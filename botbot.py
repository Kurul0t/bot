import gspread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ContentType, KeyboardButton, Message
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from datetime import datetime, timedelta
import os
import json
import pytz
from aiogram.client.bot import DefaultBotProperties

note_stat = {}
UA_TZ = pytz.timezone("Europe/Kyiv")  # Український час

# Налаштування доступу до Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_json = os.getenv("GOOGLE_CREDS_JSON")
if not creds_json:
    raise ValueError("GOOGLE_CREDS_JSON не знайдено")

try:
    creds_dict = json.loads(creds_json)
    if isinstance(creds_dict, str):
        creds_dict = json.loads(creds_dict)
except Exception as e:
    raise ValueError(f"Помилка при розпарсуванні JSON: {e}")

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
client = gspread.authorize(creds)

# Відкриття Google таблиці
sheet = client.open_by_key('1lCdMi8FrukmA5qNEgK7bpwEFQpgLcp-qTp5DNWUsEgs')
worksheet = sheet.get_worksheet(0)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
state_day_start = {}

KEEPALIVE_BOT_URL = "https://your-keepalive-bot.onrender.com/ping"


@dp.message(Command("ping"))
async def handle_ping(message: types.Message):
    pass


async def add_date(callback: types.CallbackQuery):
    rows = worksheet.get_all_values()
    user_id = callback.from_user.id
    if rows and rows[-1][0] == '*':
        today_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")
        state_day_start["date"] = today_str
        today = datetime.strptime(today_str, "%d.%m.%Y")
        date_p_17 = (today + timedelta(days=17)).strftime("%d.%m.%Y")
        worksheet.append_row([None, today_str, None, date_p_17])
        await callback.answer("✅Дата записана✅")
        await callback.message.answer("✅ Дата успішно додана в таблицю!")
        note_stat[user_id] = 1
        await callback.message.answer("Яку кількість яєць було закладено?\n(Напишіть лише число)")
    else:
        await callback.answer("❌Помилка❌")
        await callback.message.answer("❌На жаль, немає вільних інкубаторів!")


@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Меню")]],
        resize_keyboard=True
    )
    await message.answer('Привіт, це бот мініферми "Степова перепілка"', reply_markup=keyboard)


async def send_note(user_id: int, message: types.Message, bot: Bot):
    rows = worksheet.get_all_values()
    czus = message.text
    last_row_index = len(rows)
    worksheet.update_cell(last_row_index, 5, czus)
    today_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")
    state_day_start["date"] = today_str
    today = datetime.strptime(today_str, "%d.%m.%Y")
    date_p_17 = (today + timedelta(days=17)).strftime("%d.%m.%Y")
    await bot.send_message(user_id, f"Орієнтовна дата вилупу: {date_p_17}")


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
        [InlineKeyboardButton(text="Запуск інкубатора",
                              callback_data="add_date")]
    ]
)


@dp.message(F.text.lower() == "меню")
async def reply_action(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    await bot.send_message(user_id, "Обери дію:", reply_markup=menu)


@dp.message(lambda message: message.content_type == ContentType.TEXT)
async def handle_text(message: Message, bot: Bot):
    user_id = message.from_user.id
    if user_id not in note_stat:
        note_stat[user_id] = 0
    if note_stat[user_id] == 1:
        await send_note(user_id, message, bot)
        note_stat[user_id] = 0


async def on_startup():
    print("Програма запущена. Виконання ініціалізації...")
    rows = worksheet.get_all_values()
    if rows:
        last_row = rows[-1]
        state_day_start["date"] = last_row[1]
        print("Останній запис:", last_row[1])


async def check_periodically(bot: Bot):
    users = {1: 1030040998}
    while True:
        now = datetime.now(UA_TZ)

        # відправка повідомлень за день до в обід

        if now.hour == 12 and now.minute == 00:
            if "date" in state_day_start:
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")
                date_plus_8 = (saved_date + timedelta(days=9)
                               ).strftime("%d.%m.%Y")
                date_plus_14 = (saved_date + timedelta(days=15)
                                ).strftime("%d.%m.%Y")
                date_plus_17 = (saved_date + timedelta(days=18)
                                ).strftime("%d.%m.%Y")

                if date_plus_8 == today_str:
                    print("✅ Дата збігається! Сьогодні 8-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 8-й день інкубації, завтра потрібно зменшити вологу до 40% та почати провітрювати інкубатор")
                elif date_plus_14 == today_str:
                    print("✅ Дата збігається! Сьогодні 14-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 14-й день інкубації, завтра потрібно зменшити температуру до 37.4, збільшити вологу до 75-80% та викласти яйця на дно інкубатора")
                elif date_plus_17 == today_str:
                    print("✅ Дата збігається! Сьогодні 17-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 17-й день інкубації, скоро почнеться вилуп🥳")
                else:
                    print("❌ Дата не збігається.")
            else:
                print("Час перевірки! Але дати немає.")

        # відправка повідомлення в той день зранку

        elif now.hour == 8 and now.minute == 00:
            if "date" in state_day_start:
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")
                date_plus_9 = (saved_date + timedelta(days=9)
                               ).strftime("%d.%m.%Y")
                date_plus_15 = (saved_date + timedelta(days=15)
                                ).strftime("%d.%m.%Y")
                date_plus_18 = (saved_date + timedelta(days=18)
                                ).strftime("%d.%m.%Y")

                if date_plus_9 == today_str:
                    print("✅ Дата збігається! Сьогодні 9-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 9-й день інкубації, потрібно зменшити вологу до 40% та почати провітрювати інкубатор")
                elif date_plus_15 == today_str:
                    print("✅ Дата збігається! Сьогодні 15-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 15-й день інкубації, потрібно зменшити температуру до 37.4, збільшити вологу до 75-80% та викласти яйця на дно інкубатора")
                elif date_plus_18 == today_str:
                    print("✅ Дата збігається! Сьогодні 18-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 18-й день інкубації, день вилупу🥳")
                    rows = worksheet.get_all_values()
                    last_row_index = len(rows)
                    worksheet.update_cell(last_row_index, 1, "*")
                else:
                    print("❌ Дата не збігається.")
            else:
                print("Час перевірки! Але дати немає.")

        # відправка повідомлення в той день ввечері

        elif now.hour == 21 and now.minute == 00:
            if "date" in state_day_start:
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")
                date_plus_9 = (saved_date + timedelta(days=9)
                               ).strftime("%d.%m.%Y")
                date_plus_15 = (saved_date + timedelta(days=15)
                                ).strftime("%d.%m.%Y")

                if date_plus_9 == today_str:
                    print("✅ Дата збігається! Сьогодні 9-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 9-й день інкубації, потрібно зменшити вологу до 40% та почати провітрювати інкубатор")
                elif date_plus_15 == today_str:
                    print("✅ Дата збігається! Сьогодні 15-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 15-й день інкубації, потрібно зменшити температуру до 37.4, збільшити вологу до 75-80% та викласти яйця на дно інкубатора")
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
