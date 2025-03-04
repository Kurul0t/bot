import asyncio
import aiohttp
from aiohttp import web, ClientSession

# URL основного бота (замініть на реальний URL після деплою)
MAIN_BOT_URL = "https://your-main-bot.onrender.com/ping"

# Веб-сервер для отримання пінгів


async def handle_ping_request(request):
    return web.Response(text="Pong")


async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/ping', handle_ping_request)])  # Ендпоінт /ping
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)  # Порт 8080 для Render
    await site.start()
    print("Веб-сервер KeepAliveBot запущено на порту 8080")

# Функція для надсилання пінгів до основного бота


async def send_keepalive_request():
    async with ClientSession() as session:
        while True:
            try:
                async with session.get(MAIN_BOT_URL) as response:
                    if response.status == 200:
                        print(f"KeepAliveBot надіслав пінг до основного бота: {await response.text()}")
                    else:
                        print(
                            f"Помилка пінгу до основного бота: статус {response.status}")
            except Exception as e:
                print(f"Помилка при надсиланні запиту до основного бота: {e}")

            await asyncio.sleep(600)  # Надсилаємо кожні 10 хвилин


async def main():
    print("KeepAliveBot запущено!")
    # Запускаємо веб-сервер і пінгування паралельно
    asyncio.create_task(start_web_server())
    await send_keepalive_request()

if __name__ == "__main__":
    asyncio.run(main())
