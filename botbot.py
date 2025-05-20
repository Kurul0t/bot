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
import logging

note_stat = {}
# UA_TZ = pytz.timezone("Europe/Kyiv")  # Український час

# Налаштування логування для діагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Налаштування доступу до Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_path = "/etc/secrets/credentials.json"

# Перевірка наявності файлу
if not os.path.exists(creds_path):
    logger.error("Файл облікових даних не знайдено: %s", creds_path)
    raise ValueError(f"Файл облікових даних не знайдено: {creds_path}")

# Зчитування JSON-файлу
try:
    with open(creds_path, "r") as f:
        creds_dict = json.load(f)
    logger.info("Файл credentials.json успішно зчитано")
    if not isinstance(creds_dict, dict):
        logger.error("credentials.json не є коректним словником")
        raise ValueError("credentials.json не є коректним словником")
    if "private_key" not in creds_dict:
        logger.error("Поле 'private_key' відсутнє в credentials.json")
        raise ValueError("Поле 'private_key' відсутнє в credentials.json")
    if not creds_dict["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
        logger.error("Поле 'private_key' не є коректним PEM-ключем")
        raise ValueError("Поле 'private_key' не є коректним PEM-ключем")
    logger.info("Поле private_key присутнє, перші 20 символів: %s",
                creds_dict["private_key"][:20])
except json.JSONDecodeError as e:
    logger.error("Помилка при розпарсуванні credentials.json: %s", e)
    raise ValueError(f"Помилка при розпарсуванні credentials.json: {e}")
except Exception as e:
    logger.error("Невідома помилка при обробці credentials.json: %s", e)
    raise ValueError(f"Невідома помилка при обробці credentials.json: {e}")

# Створення облікових даних
try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
    logger.info("Облікові дані успішно створено")
except Exception as e:
    logger.error("Помилка при створенні облікових даних: %s", e)
    raise ValueError(f"Помилка при створенні облікових даних: {e}")

client = gspread.authorize(creds)

# Відкриття Google таблиціDA
KEY = os.environ.get("KEY")

sheet = client.open_by_key(KEY)
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
        today_str = datetime.now().strftime("%d.%m.%Y")
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
    user_id = message.from_user.id
    username = message.from_user.username
    logger.info(f"Новий користувач: ID {user_id} Username {username or 'не встановлено'}")
    await message.answer('Привіт, це бот мініферми "Степова перепілка"', reply_markup=keyboard)


async def send_note(user_id: int, message: types.Message, bot: Bot):
    rows = worksheet.get_all_values()
    czus = message.text
    last_row_index = len(rows)
    worksheet.update_cell(last_row_index, 5, czus)
    today_str = datetime.now().strftime("%d.%m.%Y")
    state_day_start["date"] = today_str
    today = datetime.strptime(today_str, "%d.%m.%Y")
    date_p_17 = (today + timedelta(days=17)).strftime("%d.%m.%Y")
    await bot.send_message(user_id, f"Орієнтовна дата вилупу: {date_p_17}")


async def days_until_date(launch_date_str, target_date_str, date_format="%d.%m.%Y"):
    today = datetime.now().date()
    start_date = datetime.strptime(launch_date_str, date_format).date()
    target_date = datetime.strptime(target_date_str, date_format).date()
    delta_1 = today - start_date
    delta_2 = target_date - today
    # Не враховуємо сьогодні
    days_1 = delta_1.days - (1 if delta_1.days >= 0 else 0)
    # Не враховуємо сьогодні
    days_2 = delta_2.days - (1 if delta_2.days >= 0 else 0)
    return days_1, days_2


@dp.callback_query(lambda c: c.data in ["add_date", "Arrngmnt", "check_date"])
async def process_button(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if callback.data == "add_date":
        await add_date(callback)
    elif callback.data == "check_date":
        rows = worksheet.get_all_values()
        if not rows or len(rows[-1]) < 5 or not all([rows[-1][1], rows[-1][3], rows[-1][4]]):
            await callback.message.answer("Помилка: Недостатньо даних у таблиці.")
            return
        last_row = rows[-1]
        logger.info("check_date")
        delta_day_1, delta_day_2 = await days_until_date(last_row[1], last_row[3])
        if isinstance(delta_day_2, str):
            await callback.message.answer(delta_day_2)
            return
        line_1 = "-" * delta_day_1 if delta_day_1 >= 0 else ""
        line_2 = "-" * delta_day_2 if delta_day_2 >= 0 else ""
        message = f"Вилуп впродож сьогоднішнього дня!" if delta_day_2 < 0 else f"📍{line_1}🥚{line_2}🐣\nДнів до вилупу: {delta_day_2}"
        await callback.message.answer(
            f"Дата закладання: {last_row[1]}\n"
            f"Дата вилупу: {last_row[3]}\n"
            f"Закладено, шт: {last_row[4]}\n\n"
            f"{message}"
        )
    """elif callback.data == "Arrngmnt":
        t = await Arrangement()
        await bot.send_message(user_id, f"Розміщення перепелів", reply_markup=t)"""

menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Запуск інкубатора",
                              callback_data="add_date")],
        [InlineKeyboardButton(text="Відстеження прогресу",
                              callback_data="check_date")]
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
    # user_id = callback.from_user.id
    if rows:
        last_row = rows[-1]
        state_day_start["date"] = last_row[1]
        logger.info("Останній запис:", last_row[1])


async def check_periodically(bot: Bot):
    users = {1: 1030040998, 2: 1995558338}
    #users = os.environ.get("USERS_ID")
    while True:
        now = datetime.now()

        # відправка повідомлень за день до в обід
        if now.hour == 19 and now.minute == 5:
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
                    worksheet.update_cell(last_row_index, 0, "*")
                else:
                    print("❌ Дата не збігається.")
            else:
                print("Час перевірки! Але дати немає.")

        elif now.hour == 9 and now.minute == 00:
            if "date" in state_day_start:
                logger.info(
                    f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")
                date_plus_8 = (saved_date + timedelta(days=8)
                               ).strftime("%d.%m.%Y")
                date_plus_14 = (saved_date + timedelta(days=14)
                                ).strftime("%d.%m.%Y")
                date_plus_17 = (saved_date + timedelta(days=17)
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

        # відправка повідомлення в той день ввечері

        elif now.hour == 18 and now.minute == 00:
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

        await asyncio.sleep(40)


async def main():
    await on_startup()
    asyncio.create_task(check_periodically(bot))
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
