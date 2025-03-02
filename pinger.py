
import asyncio
import os
from aiogram import Bot
from aiogram.client.bot import DefaultBotProperties

# Токен другого бота від @BotFather
PING_BOT_TOKEN = os.environ.get("PING_BOT_TOKEN")  # Заміни на реальний токен
CHAT_ID = 1030040998  # Твій Telegram ID або ID чату, де працює основний бот

# Ініціалізація пінг-бота
ping_bot = Bot(PING_BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))

# Функція для надсилання пінгу


async def keep_alive():
    while True:
        await ping_bot.send_message(CHAT_ID, "Пінг! Я тримаю основного бота активним.")
        print("Пінг надіслано!")
        await asyncio.sleep(300)  # 5 хвилин (300 секунд)

# Основна функція


async def main():
    # Видаляємо Webhook, якщо був
    await ping_bot.delete_webhook(drop_pending_updates=True)
    await keep_alive()

if __name__ == "__main__":
    asyncio.run(main())
