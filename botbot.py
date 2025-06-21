import io
from PIL import Image, ImageDraw, ImageFont
import gspread
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ContentType, KeyboardButton, Message, BufferedInputFile, InputMediaPhoto, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
from datetime import datetime, timedelta, timezone
import os
import json
import pytz
from aiogram.client.bot import DefaultBotProperties
import logging
import textwrap

note_stat = {}
chus_quail = {}
st = {}
UA_TZ = pytz.timezone("Europe/Kyiv")  # Український час

# Налаштування логування для діагностики
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Налаштування доступу до Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds_path = "/etc/secrets/credentials.json"

users = {1: 1030040998, 2: 1995558338}

tabl = "——— ——— ———— ————————\n| день|     t    | Волога|              Дії            |\n ——— ——— ———— ———————— \n|     1   |  37.8 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     2   |  37.8 | 55-65%|  Вкл. переверт. |\n ——— ——— ———— ———————— \n|     3   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     4   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     5   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     6   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     7   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     8   |  37.7 | 55-65%|                               |\n ——— ——— ———— ———————— \n|     9   |  37.7 | 55-65%|     1 Провітр.      |\n ——— ——— ———— ———————— \n|    10  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    11  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    12  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    13  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    14  |  37.7 |    40%   |     2 Провітр.      |\n ——— ——— ———— ———————— \n|    15  |  37.4 | 75-80%|Вимк. переверт.|\n ——— ——— ———— ———————— \n|    16  |  37.4 | 75-80%|                               |\n ——— ——— ———— ———————— \n|    17  |  37.4 | 75-80%|                               |\n ——— ——— ———— ————————"

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

sheet_2 = client.open_by_key(KEY_2)
worksheet_1 = sheet_2.get_worksheet(1)
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


class Menu_callback(CallbackData, prefix="menu"):
    level: int
    menu_name: str
    # description: str


class Pagination(CallbackData, prefix="pag"):
    page: int


main_description = {
    0: "Головне меню",
    1: "Категорії",
    2: "Товари",
    3: "Кошик"
}

tovar_description = {
    0: "мариновані Яйця\nОпис\nЦіна\n",
    1: "маринована перепілка\nОпис\nЦіна\n",
    2: "Столові Яйця\nОпис\nЦіна\n",
    3: "Свіже м'ясо\nОпис\nЦіна\n",
}
tovar_description11 = {
    0: "Є в наявності\n",
    1: "Є в наявності\n",
    2: "Є в наявності\n",
    3: "Є в наявності\n",
}
tovar_description12 = {
    0: "Немає в наявності\n",
    1: "Немає в наявності\n",
    2: "Немає в наявності\n",
    3: "Немає в наявності\n",
}
tovar_description13 = {
    0: "Обрано\n",
    1: "Обрано\n",
    2: "Обрано\n",
    3: "Обрано\n",
}
tovar_description2 = {
    0: "                              1 з 4",
    1: "                              2 з 4",
    2: "                              3 з 4",
    3: "                              4 з 4",
}


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

IMAGE_FOLDER = "images"
photo = {}
photo2 = {}


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
    # await bot.send_photo(user_id, photo=photo, caption='Привіт, це бот мініферми "Степова перепілка"', reply_markup=keyboard)


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


@dp.callback_query(lambda c: c.data in ["add_date", "Arrngmnt", "check_date", "brk", "stop_brk", "tabl_incub", "cans_qwiz"])
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
        # message = f"Вилуп впродож сьогоднішнього дня!" if delta_day_2 < 0 else f"📍{line_1}🥚{line_2}🐣\nДнів до вилупу: {delta_day_2}"
        brk = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Перервати інкубацію",
                                      callback_data="brk")]
            ]
        )
        zapusck = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Запуск інкубатора",
                                      callback_data="add_date")]
            ])
        if last_row[0] == "*":
            message = "Активної інкубації не вивлено"
            await callback.message.answer(message, reply_markup=zapusck)
        elif delta_day_2 == 0:
            message = "Вилуп впродож сьогоднішнього дня!"
            await callback.message.answer(
                f"Дата закладання: {last_row[2]}\n"
                f"Дата вилупу: {last_row[4]}\n"
                f"Закладено, шт: {last_row[5] or 'не вказано'}\n\n"
                f"{message}", reply_markup=brk)
        else:
            message = f"📍{line_1}🥚{line_2}🐣\nДнів до вилупу: {delta_day_2}"
            await callback.message.answer(
                f"Дата закладання: {last_row[2]}\n"
                f"Дата вилупу: {last_row[4]}\n"
                f"Закладено, шт: {last_row[5] or 'не вказано'}\n\n"
                f"{message}", reply_markup=brk)

    elif callback.data == "brk":
        rows = worksheet_1.get_all_values()
        last_row = rows[-1]
        if last_row[0] != "*":

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
        photo_inc = photo_incubation
        await callback.message.answer_photo(photo_inc)
    elif callback.data == "cans_qwiz":
        note_stat[user_id] = 4
        await callback.message.answer("Чи усіх циплаків було пораховано?\n(Для підтвердження/спростування напиши так/ні)")
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


async def menu_setting(level: int):
    print(level)
    if level == 0:
        return await main_menu()
    elif level == 1:
        return await catalog_menu(level)
    # elif level == 2:
        # descr, rm = await product_menu(level)
        # return rm
    elif level == 3:
        return await cart_menu()
    elif level == 11:
        pass


async def main_menu():
    kb = InlineKeyboardBuilder()
    buttons = {
        "Товари": "catalog",
        "Кошик": "cart",
        "Про нас": "about",
        "Замовлення": "order"

    }

    for text, menu_name in buttons.items():
        if menu_name == 'catalog':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=1, menu_name=menu_name).pack()))
        elif menu_name == 'cart':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=3, menu_name=menu_name).pack()))
        elif menu_name == 'about':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=11, menu_name=menu_name).pack()))
        elif menu_name == 'order':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=11, menu_name=menu_name).pack()))
    return kb.adjust(2, 1, 1).as_markup()


async def catalog_menu(level: int):
    kb = InlineKeyboardBuilder()
    kb1 = {
        "Назад": "back",
        "Кошик": "cart",
        "Продукт": "product",
        "Товар": "tovar"}

    for text, menu_name in kb1.items():
        if menu_name == 'back':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=level-1, menu_name=menu_name).pack()))
        elif menu_name == 'cart':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=3, menu_name=menu_name).pack()))
        else:
            kb.add(InlineKeyboardButton(text=text, callback_data=Pagination(
                page=0).pack()))

    return kb.adjust(2, 2).as_markup()


async def product_menu(level: int, page=0, st=0):
    kb = InlineKeyboardBuilder()
    if st == 0:
        kb2 = {
            "назад": "back",
            "Кошик": "cart",
            "Обрати": "buy",
            "◀": "b",
            "▶": "n"}
    else:
        kb2 = {
            "назад": "back",
            "Кошик": "cart",
            "Обрано☑": "buyed",
            "◀": "b",
            "▶": "n"}

    print("page    ", page)
    t = len(tovar_description)-1
    if page > (len(tovar_description)-1):
        page = t
    print(page)

    if st == 0:
        tov_descr = tovar_description11[page]
    elif st == 1:
        tov_descr = tovar_description12[page]
    elif st == 2:
        tov_descr = tovar_description13[page]

    descr = tovar_description[page]+tov_descr+tovar_description2[page]
    print("descr    ", descr)
    for text, menu_name in kb2.items():
        if menu_name == 'back':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=level-1, menu_name=menu_name).pack()))
        elif menu_name == 'cart':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=3, menu_name=menu_name).pack()))
        elif menu_name == 'buy':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=11, menu_name=menu_name).pack()))
        elif menu_name == 'b':
            if page == 0:
                kb.add(InlineKeyboardButton(text=text, callback_data=Pagination(
                    page=page).pack()))
            else:
                kb.add(InlineKeyboardButton(text=text, callback_data=Pagination(
                    page=page-1).pack()))
        elif menu_name == 'n':

            if page <= t:
                kb.add(InlineKeyboardButton(text=text, callback_data=Pagination(
                    page=page+1).pack()))
            else:
                kb.add(InlineKeyboardButton(text=text, callback_data=Pagination(
                    page=page).pack()))

    return descr, kb.adjust(2, 1, 2).as_markup()


async def cart_menu():
    kb = InlineKeyboardBuilder()
    kb3 = {
        "Видалити": "delet",
        "-1": "min1",
        "+1": "plas1",
        "◀": "b",
        "▶": "n",
        "На головну": "main",
        "Замовити": "toOrder"}

    for text, menu_name in kb3.items():
        if menu_name == 'main':
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=0, menu_name=menu_name).pack()))
        else:
            kb.add(InlineKeyboardButton(text=text, callback_data=Menu_callback(
                level=11, menu_name=menu_name).pack()))

    return kb.adjust(3, 2, 2).as_markup()


@dp.callback_query(Menu_callback.filter())
async def handle_menu_callback(callback: CallbackQuery, callback_data: Menu_callback):

    await callback.answer()
    rm = await menu_setting(callback_data.level)

    await callback.message.edit_media(media=InputMediaPhoto(media=photo[callback_data.level], caption=main_description[callback_data.level]), reply_markup=rm)


@dp.callback_query(Pagination.filter())
async def handle_menu_callback(callback: CallbackQuery, callback_data: Pagination):

    await callback.answer()
    descr, rm = await product_menu(2, callback_data.page)
    if callback_data.page > (len(tovar_description)-1):
        await callback.message.edit_media(media=InputMediaPhoto(media=photo2[len(tovar_description)-1], caption=descr), reply_markup=rm)
    else:
        await callback.message.edit_media(media=InputMediaPhoto(media=photo2[callback_data.page], caption=descr), reply_markup=rm)


@dp.message(F.text.lower() == "меню")
async def reply_action(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    if user_id == 1030040998 or user_id == 1995558338:
        await bot.send_message(user_id, "Обери дію:", reply_markup=menu)
    else:
        rm = await main_menu()
        await bot.send_photo(user_id, photo=photo[0], caption=main_description[0], reply_markup=rm)

cans = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Вимкнути оновлення",
                              callback_data="cans_qwiz")]
    ])


@dp.message(lambda message: message.content_type == ContentType.TEXT)
async def handle_text(message: Message, bot: Bot):
    user_id = message.from_user.id
    if 1111 not in note_stat:
        note_stat[1111] = 0
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
    elif note_stat[user_id] == 4:
        if message.text.lower() == "так":
            st[1] = 1
            note_stat[1111] = 1
            await cycl()
        elif message.text.lower() == "ні":
            await bot.send_message(user_id, "Наступне оновлення через 2 години")
        note_stat[user_id] = 0

    if note_stat[1111] == 1:

        last_row_index = chus_quail[1]
        worksheet_1.update_cell(last_row_index, 7, message.text)
        for CHAT_ID in users.values():
            await bot.send_message(CHAT_ID, f"Оновлення кількості вилуплених циплаків: {message.text}")
            await bot.send_message(CHAT_ID, "Наступне оновлення через 2 години", reply_markup=cans)

        note_stat[1111] = 0

photo_incubation = None


async def on_startup():
    global photo_incubation
    print("Програма запущена. Виконання ініціалізації...")
    rows = worksheet_1.get_all_values()
    # user_id = callback.from_user.id
    if rows:
        last_row = rows[-1]
        state_day_start["date"] = last_row[2]
        logger.info("Останній запис:", last_row[2])

    t = len(main_description)
    t2 = len(tovar_description)

    # image_path = os.path.join(IMAGE_FOLDER, f"{1}.jpg")

    for i in range(t):
        # image_path = os.path.join(IMAGE_FOLDER, f"{i}.jpg")
        with open(f"images/{i}.jpg", 'rb') as image_file:
            image_data = image_file.read()
        # butt=await paginator(page=0)
        # Використовуємо BufferedInputFile для байтових даних
        photo[i] = BufferedInputFile(
            file=image_data, filename=f"{i}.jpg")

    for i in range(t2):
        # image_path = os.path.join(IMAGE_FOLDER, f"{i}11.jpg")
        with open(f"images/{i}11.jpg", 'rb') as image_file:
            image_data = image_file.read()
        # butt=await paginator(page=0)
        # Використовуємо BufferedInputFile для байтових даних
        photo2[i] = BufferedInputFile(
            file=image_data, filename=f"{i}11.jpg")

    with open(f"images/incubation.jpg", 'rb') as image_file:
        image_data = image_file.read()
    photo_incubation = BufferedInputFile(
        file=image_data, filename=f"incubation.jpg")


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
                date_plus_16 = (saved_date + timedelta(days=16)
                                ).strftime("%d.%m.%Y")

                if date_plus_8 == today_str:
                    print("✅ Дата збігається! Сьогодні 8-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 8-й день інкубації, завтра потрібно зменшити вологу до 40% та почати провітрювати інкубатор")
                elif date_plus_14 == today_str:
                    print("✅ Дата збігається! Сьогодні 14-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 14-й день інкубації, завтра потрібно зменшити температуру до 37.4, збільшити вологу до 75-80% та викласти яйця на дно інкубатора")
                elif date_plus_16 == today_str:
                    print("✅ Дата збігається! Сьогодні 16-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 16-й день інкубації, скоро почнеться вилуп🥳")
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
                date_plus_2 = (saved_date + timedelta(days=2)
                               ).strftime("%d.%m.%Y")
                date_plus_9 = (saved_date + timedelta(days=9)
                               ).strftime("%d.%m.%Y")
                date_plus_15 = (saved_date + timedelta(days=15)
                                ).strftime("%d.%m.%Y")
                if date_plus_2 == today_str and (now.hour == 6 and now.minute == 00):
                    print("✅ Дата збігається! Сьогодні 2-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 2-й день інкубації, потрібно увімкнути перевертання")
                elif date_plus_9 == today_str:
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
        elif now.hour == 10 and now.minute == 00:
            logger.info("час співпадає")
            if "date" in state_day_start:
                logger.info("вибір дня")
                print(f"Час перевірки! Дата старту: {state_day_start['date']}")
                saved_date = datetime.strptime(
                    state_day_start["date"], "%d.%m.%Y")
                today_str = now.strftime("%d.%m.%Y")

                date_plus_17 = (saved_date + timedelta(days=17)
                                ).strftime("%d.%m.%Y")

                if date_plus_17 == today_str:
                    logger.info("відправка")
                    print("✅ Дата збігається! Сьогодні 17-й день.")
                    for CHAT_ID in users.values():
                        await bot.send_message(CHAT_ID, "Сьогодні 17-й день інкубації, день вилупу🥳")
                    rows = worksheet_1.get_all_values()
                    last_row_index = len(rows)

                    chus_quail[1] = last_row_index
                    worksheet_1.update_cell(last_row_index, 1, "*")
                    st[1] = 0
                    await cycl()

                else:
                    print("❌ Дата не збігається.")
            else:
                print("Час перевірки! Але дати немає.")

        await asyncio.sleep(60)


async def cycl():
    # st=st
    while True:
        if st[1] == 1:
            rows = worksheet_1.get_all_values()
            row = rows[-1]
            # ch = row[6]*100/row[5]
            if note_stat[1111] == 1:
                for CHAT_ID in users.values():
                    await bot.send_message(CHAT_ID, f"Загалом вилупилося циплаків: {row[6]}\n Відсоток вилупу: {row[7]}%")
                logger.info(f"перед {st[1]}")
            note_stat[1111] = 0
            break
        else:
            logger.info(st[1])
            note_stat[1111] = 1
            for CHAT_ID in users.values():
                await bot.send_message(CHAT_ID, "Скільки циплаків вилупилося на даний момент?")
            await asyncio.sleep(2*3600)


async def monitor_sheet():
    prev_data = worksheet_2.get_all_values()

    while True:
        await asyncio.sleep(300)  # чекати 5 хвилин

        current_data = worksheet_2.get_all_values()
        """row1 = current_data[1]
        logger.info(f"1_12{row1[12]}")
        row2 = current_data[2]
        logger.info(f"2_13{row2[13]}")
        row3 = current_data[3]
        logger.info(f"3_14{row3[14]}")"""

        if current_data != prev_data:
            logger.info("Таблиця змінилася!")

            header = current_data[0]
            row = current_data[-1]
            filled_columns = {}

            # Ініціалізація значень за замовчуванням
            profit_sum = 0
            expens_sum = 0
            result = 0
            profit_value = "0"
            expens_value = "0"

            # important_column_indexes = [12, 13, 14, 15, 16]

            try:
                profit_index = header.index("прибуток")
                profit_value = row[profit_index].strip() or "0"

                expens_index = header.index("затрати/грн")
                expens_value = row[expens_index].strip() or "0"

                profit_sum = int(profit_value)
                expens_sum = int(expens_value)
                result = profit_sum - expens_sum

            except (ValueError, IndexError):
                # Обробка, якщо якісь колонки відсутні або нечислові
                try:
                    profit_sum = int(profit_value)
                except ValueError:
                    profit_sum = 0

                try:
                    expens_sum = int(expens_value)
                except ValueError:
                    expens_sum = 0

                result = profit_sum - expens_sum


            income = f"+{result}" if result >= 0 else f"{result}"
            sales = [
                ("інкубаційні яйця", row[12] if row[12] else 0),
                ("столові яйця", row[13] if row[13] else 0),
                ("тушки", row[14] if row[14] else 0),
                ("жива птиця", row[15] if row[15] else 0),
                ("марин. тушки", row[16] if row[16] else 0),
            ]

            
            """if row[17] is not None:
                text = f"{row[17]}"
                wrapped = textwrap.wrap(text, width=17, break_long_words=False)
            else:
                wrapped = ""

            expenses = [(wrapped if row[17] else "Витрати", expens_value)]"""

            text = row[17] if row[17] else ""
            text = " ".join(text.strip().split())
            if text:
                wrapped_lines = textwrap.wrap(
                    text,
                    width=17,# ширина рядка в символах
                    break_long_words=False
                )
            else:
                wrapped_lines = ["Витрати"]

            expenses = "\n".join(wrapped_lines)
            header2 = current_data[2]
            balance = header2[20]

            # Генеруємо звіт

            def generate_farm_report(income, sales_list, expenses_list, balance):
                width, height = 330, 447
                img = Image.new('RGB', (width, height), color='#000000')
                draw = ImageDraw.Draw(img)

                # Шрифт
                font_path = "courier-prime.ttf"
                font_large = ImageFont.truetype(font_path, 20)
                font_small = ImageFont.truetype(font_path, 16)



                draw.rounded_rectangle(
                    [5, 5, 325, 55], radius=8, fill='#edf0f2', outline='black')

                # Функція малювання блоків
                def draw_box(x, y, w, h, text, bg='#c6c5c3', text_color='black', font=None, align='center'):
                    draw.rounded_rectangle(
                        [x, y, x + w, y + h], radius=8, fill=bg,outline='black')
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    if align == 'center':
                        text_x = x + (w - text_w) / 2
                    elif align == 'left':
                        text_x = x + 10
                    else:
                        text_x = x
                    text_y = y + (h - text_h) / 2
                    draw.text((text_x, text_y), text,
                              fill=text_color, font=font)

                # Верхній прибуток
                if result <0:
                    draw_box(15, 10, 300, 40, f"{income}грн",
                         bg="#929292", text_color="red", font=font_large)
                else:
                    draw_box(15, 10, 300, 40, f"{income}грн",
                         bg="#929292", text_color="green", font=font_large)

                # Продажі
                y = 60
                draw.rounded_rectangle(
                    [5, 60, 325, 275], radius=8, fill='#d1ffc7', outline='black')
                row_h = 40
                for i, (label, price) in enumerate(sales_list):
                    draw_box(15, 70 + i * row_h, 180, row_h - 5,
                             label, bg="#c6c5c3", font=font_small)
                    draw_box(200, 70 + i * row_h, 115, row_h - 5,
                             f"{price}грн", bg="#c6c5c3", font=font_small)

                # Витрати
                y2 = y + 220
                draw.rounded_rectangle(
                    [5, 280, 325, 380], radius=8, fill='#ff9292', outline='black')
                
                draw_box(15, 290, 180, 80, expenses_list,
                             bg="#c6c5c3", font=font_small)
                draw_box(200, 290, 115, 80,
                             f"{row[18]}грн", bg="#c6c5c3", font=font_small)

                # Баланс
                def draw_box1(x, y, w, h, text, bg='#929292', text_color='black', font=None, align='center'):
                    draw.rectangle([x, y, x + w, y + h],
                                   fill=bg, outline='black')
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    if align == 'center':
                        text_x = x + (w - text_w) / 2
                    elif align == 'left':
                        text_x = x + 10
                    else:
                        text_x = x
                    text_y = y + (h - text_h) / 2
                    draw.text((text_x, text_y), text,
                              fill=text_color, font=font)
                y3 = y2 + 110
                y_y = 150
                draw.rounded_rectangle(
                    [5, 385, 325, y3 + 50], radius=8, fill='#dddddd', outline='black')
                draw_box1(15, y3+2, y_y, 40, "баланс ферми",
                          bg="#c6c5c3", text_color="black", font=font_small)
                draw_box1(y_y+15, y3 + 2, y_y, 40, f"{balance}грн",
                          bg="#929292", text_color="green", font=font_small)

                # Зберігаємо зображення в пам’яті як байти
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)

                # Повертаємо BufferedInputFile для надсилання в Telegram
                photo_incubation = BufferedInputFile(
                    file=img_byte_arr.getvalue(), filename="incubation.jpg")

                return photo_incubation

            pht = generate_farm_report(income, sales, expenses, balance)

            #await bot.send_message(1030040998, message)
            #for CHAT_ID in users.values():
            await bot.send_photo(chat_id=1030040998, photo=pht)


            """if float(profit_value):
                bot.send_message(1030040998,"Надішли номер телефону замовника та його Ім'я")"""

            prev_data = current_data


async def main():
    await on_startup()
    asyncio.create_task(check_periodically(bot))
    asyncio.create_task(monitor_sheet())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
