import gspread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ContentType, KeyboardButton, Message
from aiogram.filters import Command
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from datetime import datetime, timedelta, timezone
import os
import json
import pytz
from aiogram.client.bot import DefaultBotProperties
import logging

note_stat = {}
UA_TZ = pytz.timezone("Europe/Kyiv")  # Український час

# Налаштування логування для діагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Налаштування доступу до Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_path = "/etc/secrets/credentials.json"

users = {1: 1030040998, 2: 1995558338}

tabl = "——— ——— ———— ————————\n| день|     t    | Волога|              Дії            |\n ——— ——— ———— ———————— \n|     1   |  37.8 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     2   |  37.8 | 55-65%|  Вкл. переверт. |\n ——— ——— ———— ———————— \n|     3   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     4   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     5   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     6   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     7   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     8   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     9   |  37.7 | 55-65%|     1 Провітр.      |\n ——— ——— ———— ———————— \n|    10  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    11  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    12  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    13  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    14  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    15  |  37.4 | 75-80%|Вимк. переверт.|\n ——— ——— ———— ———————— \n|    16  |  37.4 | 75-80%|                               |\n ——— ——— ———— ———————— \n|    17  |  37.4 | 75-80%|                               |\n ——— ——— ———— ———————— \n|    18  |  37.4 | 75-80%|                               |\n ——— ——— ———— ————————"

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
KEY_1 = os.environ.get("KEY_1")
KEY_2 = os.environ.get("KEY_2")

sheet_1 = client.open_by_key(KEY_1)
worksheet_1 = sheet_1.get_worksheet(0)

sheet_2 = client.open_by_key(KEY_2)
worksheet_2 = sheet_2.get_worksheet(0)


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
    rows = worksheet_1.get_all_values()
    user_id = callback.from_user.id
    if rows and rows[-1][0] == '*':
        today_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")
        state_day_start["date"] = today_str
        today = datetime.strptime(today_str, "%d.%m.%Y")
        date_p_17 = (today + timedelta(days=17)).strftime("%d.%m.%Y")
        worksheet_1.append_row([None, None, today_str, None, date_p_17])
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
    logger.info(
        f"Новий користувач: ID {user_id} Username {username or 'не встановлено'}")
    await message.answer('Привіт, це бот мініферми "Степова перепілка"', reply_markup=keyboard)


async def send_note(user_id: int, message: types.Message, bot: Bot):
    rows = worksheet_1.get_all_values()
    czus = message.text
    last_row_index = len(rows)
    worksheet_1.update_cell(last_row_index, 6, czus)
    today_str = datetime.now(UA_TZ).strftime("%d.%m.%Y")
    state_day_start["date"] = today_str
    today = datetime.strptime(today_str, "%d.%m.%Y")
    date_p_17 = (today + timedelta(days=17)).strftime("%d.%m.%Y")
    for CHAT_ID in users.values():
        await bot.send_message(CHAT_ID, f"Відбувся запуск інкубатора\nК-ть закладених яєць:{czus}\nОрієнтовна дата вилупу: {date_p_17}")
    # await bot.send_message(user_id, f"Орієнтовна дата вилупу: {date_p_17}")


async def days_until_date(launch_date_str, target_date_str, date_format="%d.%m.%Y"):
    today = datetime.now(UA_TZ).date()
    start_date = datetime.strptime(launch_date_str, date_format).date()
    target_date = datetime.strptime(target_date_str, date_format).date()
    delta_1 = today - start_date
    delta_2 = target_date - today
    # Не враховуємо сьогодні
    days_1 = delta_1.days  # - (1 if delta_1.days >= 0 else 0)
    # Не враховуємо сьогодні
    days_2 = delta_2.days  # - (1 if delta_2.days >= 0 else 0)
    return days_1, days_2


@dp.callback_query(lambda c: c.data in ["add_date", "Arrngmnt", "check_date", "brk", "stop_brk", "tabl_incub"])
async def process_button(callback: types.CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if callback.data == "add_date":
        await add_date(callback)
    elif callback.data == "check_date":
        rows = worksheet_1.get_all_values()
        """if not rows or len(rows[-1]) < 5 or not all([rows[-1][1], rows[-1][3], rows[-1][4]]):
            await callback.message.answer("Помилка: Недостатньо даних у таблиці.")
            return"""
        last_row = rows[-1]
        logger.info("check_date")
        delta_day_1, delta_day_2 = await days_until_date(last_row[2], last_row[4])
        if isinstance(delta_day_2, str):
            await callback.message.answer(delta_day_2)
            return
        line_1 = "-" * delta_day_1 if delta_day_1 >= 0 else ""
        line_2 = "-" * delta_day_2 if delta_day_2 >= 0 else ""
        message = f"Вилуп впродож сьогоднішнього дня!" if delta_day_2 < 0 else f"📍{line_1}🥚{line_2}🐣\nДнів до вилупу: {delta_day_2}"
        brk = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Перервати інкубацію",
                                      callback_data="brk")]
            ]
        )
        await callback.message.answer(
            f"Дата закладання: {last_row[2]}\n"
            f"Дата вилупу: {last_row[4]}\n"
            f"Закладено, шт: {last_row[5] or 'не вказано'}\n\n"
            f"{message}", reply_markup=brk)
    elif callback.data == "brk":
        note_stat[user_id] = 2
        stop_brk = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Скасувати переривання",
                                      callback_data="stop_brk")]
            ]
        )
        await callback.message.answer("Ви впевнені, що хочете перевати інкубацію?\n(Для підтвердження напишіть 'так')", reply_markup=stop_brk)

    elif callback.data == "stop_brk":
        await callback.message.answer("Все окей, інкубація продовжується")
    elif callback.data == "tabl_incub":
        await callback.message.answer(tabl)
    """elif callback.data == "Arrngmnt":
        t = await Arrangement()
        await bot.send_message(user_id, f"Розміщення перепелів", reply_markup=t)"""

menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Запуск інкубатора",
                              callback_data="add_date")],
        [InlineKeyboardButton(text="Відстеження прогресу",
                              callback_data="check_date")],
        [InlineKeyboardButton(text="Інструкція інкубації",
                              callback_data="tabl_incub")]
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
    elif note_stat[user_id] == 2:
        note_stat[user_id] = 3
        await bot.send_message(user_id, "Додай коментар, аби інші також знали причину, або введи символ ' - '")
    elif note_stat[user_id] == 3:
        rows = worksheet_1.get_all_values()
        last_row_index = len(rows)
        worksheet_1.update_cell(last_row_index, 1, "*")
        worksheet_1.update_cell(last_row_index, 2, "Перервано")
        comment = "відсутній" if message.text == "-" else message.text
        for CHAT_ID in users.values():
            await bot.send_message(CHAT_ID, f"‼Інкубацію було перервано‼\n\nКоментар:{comment}\nХто перервав:{message.from_user.first_name or ''}{message.from_user.last_name or ''}")
        note_stat[user_id] = 0


async def on_startup():
    print("Програма запущена. Виконання ініціалізації...")
    rows = worksheet_1.get_all_values()
    # user_id = callback.from_user.id
    if rows:
        last_row = rows[-1]
        state_day_start["date"] = last_row[2]
        logger.info("Останній запис:", last_row[2])


async def check_periodically(bot: Bot):
    # users = os.environ.get("USERS_ID")
    while True:
        now = datetime.now(UA_TZ)
        logger.info("запуск перевірки")
        # відправка повідомлень за день до в обід

        if now.hour == 12 and now.minute == 00:
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

        # відправка повідомлення в той день зранку і ввечері

        elif (now.hour == 6 and now.minute == 00) or (now.hour == 20 and now.minute == 00):
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
        elif now.hour == 9 and now.minute == 00:
            logger.info("час співпадає")
            if "date" in state_day_start:
                logger.info("вибір дня")
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")

                date_plus_18 = (saved_date + timedelta(days=18)
                                ).strftime("%d.%m.%Y")

                if date_plus_18 == today_str:
                    logger.info("відправка")
                    print("✅ Дата збігається! Сьогодні 18-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 18-й день інкубації, день вилупу🥳")
                    rows = worksheet_1.get_all_values()
                    last_row_index = len(rows)
                    worksheet_1.update_cell(last_row_index, 1, "*")
                else:
                    print("❌ Дата не збігається.")
            else:
                print("Час перевірки! Але дати немає.")

        await asyncio.sleep(60)


async def monitor_sheet():
    prev_data = worksheet_1.get_all_values()

    while True:
        await asyncio.sleep(300)  # чекати 5 хвилин

        current_data = worksheet_1.get_all_values()
        if current_data != prev_data:
            logger.info("Таблиця змінилася!")

            header = current_data[0]  # перший рядок — заголовок
            row = current_data[-1]    # останній рядок
            filled_columns = {}
            profit_sum = 0
            expens_sum = 0
            result = 0

            # 🔧 вкажи індекси колонок, які потрібно перевіряти
            important_column_indexes = [0, 1, 2, 3, 4, 5]
            # result = None
            # 📈 Обчислення прибутку
            try:
                profit_index = header.index("прибуток")
                profit_value = row[profit_index].strip()

                expens_index = header.index("затрати/грн")
                expens_value = row[expens_index].strip()
                if profit_value:
                    profit_sum += float(profit_value)
                if expens_value:
                    expens_sum += float(expens_value)
                result = profit_sum - expens_sum

            except (ValueError, IndexError):
                pass  # якщо помилка — просто пропустити

            # ✅ Перевірка заповнених категорій
            for idx in important_column_indexes:
                if idx < len(row):
                    cell_value = str(row[idx]).strip().replace('\u200b', '')
                    if cell_value:
                        clean_name = header[idx].replace("за ", "").strip()
                        filled_columns[clean_name] = cell_value
            # 📨 Формування повідомлення
            if result >= 0:
                result_line = f"+{result}"
            else:
                result_line = f"{result}"

            message = result_line

            if profit_value:
                if filled_columns:
                    message += "\nПродано:\n"
                    for name, value in filled_columns.items():
                        message += f"{name} ({value}грн)\n"

            if expens_value:
                message += f"\nВитрачено на:\n{row[6]} ({expens_value}грн)"

            await bot.send_message(1030040998, message)

            prev_data = current_data


async def main():
    await on_startup()
    asyncio.create_task(check_periodically(bot))
    asyncio.create_task(monitor_sheet())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
