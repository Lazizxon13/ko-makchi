import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = "8275086123:AAFM8iifVbe8cidhE07hoEbQ0svwqvRB8ac"
GOOGLE_API_KEY = "AIzaSyC5a0Rk9TuIpN0b4RIBYtx6RM0peLxSe1U"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- JADVAL ---
cached_catalog = ""

def get_catalog_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df.to_string(index=False)
    except Exception as e:
        print(f"Jadval oqishda xato: {e}")
        return "Katalog yuklanmadi."

# --- AI VA BOT ---
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz Render'da tayyor! 😊")

@dp.message()
async def handle_text(message: types.Message):
    global cached_catalog
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    if not cached_catalog:
        cached_catalog = get_catalog_data()

    instruction = f"""
    Siz Greenleaf Rishton markazi mutaxassisiz. Samimiy javob bering.
    Mahsulot nomini o'zbekchaga tarjima qiling.
    Shablon asosida javob bering:
    ✨ Greenleaf Sifati ✨
    🧼 Mahsulot: [O'zbekcha nomi]
    🆔 Kod: [Kodi]
    💰 Narxi: [Narxi] so'm
    💎 Ball: [PV] PV
    ✅ [Mahsulot haqida foydali tavsiya]
    🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
    📞 Tel: +998 33 993 4070
    
    Katalog: {cached_catalog}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)
        response = model.generate_content(message.text)
        await message.reply(response.text)
    except Exception as e:
        print(f"Xatolik: {e}")
        await message.answer("Biroz kuting, qayta urinib ko'ring...")

# --- RENDER PORT SOZLAMASI (ENG MUHIMI) ---
async def handle_ping(request):
    return web.Response(text="Bot is live!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render PORTni environment variable orqali beradi (default: 10000)
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Veb-server port {port} da ishga tushdi")

async def main():
    # Veb serverni orqa fonda ishga tushiramiz
    asyncio.create_task(start_web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
