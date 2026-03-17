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
        return "Katalog yuklanmadi."

# --- GEMINI ---
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz Render.com'da ishga tushdi! 😊")

@dp.message()
async def handle_text(message: types.Message):
    global cached_catalog
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    if not cached_catalog:
        cached_catalog = get_catalog_data()

    instruction = f"""
    Siz Greenleaf Rishton markazi mutaxassisiz. 
    Mahsulot nomini chiroyli o'zbekchaga tarjima qiling va shablon asosida javob bering.
  Faqat quyidagi shablonda javob bering:
    ✨ Greenleaf Сифати — Сизнинг саломатлигингиз учун! ✨
    🧼 Маҳсулот: [O'zbekcha nomi]
    🆔 Код: [Kodi]
    💰 Хамкор нархи: [Narxi] сўм
    💎 Балл: [PV] PV
    ✅ [Mahsulot haqida tavsiya]
    Katalog: {cached_catalog}
    """
    
try:
        # Модел номини барқарорроқ версияга алмаштирамиз
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=instruction)
        response = model.generate_content(message.text)
        await message.reply(response.text)
    except Exception as e:
        # Энг муҳими: хатони логларга чиқарамиз
        print(f"!!! ХАТОЛИК ЮЗ БЕРДИ: {e}") 
        logging.error(f"Xato tafsiloti: {e}")
        await message.answer("Маълумот олишда техник узилиш бўлди. Бироздан сўнг қайта уриниб кўринг.")

# --- RENDER UCHUN МАХСУС ВЕБ СЕРВЕР ---
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080)) # Render bergan portни олади
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    asyncio.create_task(start_web_server()) # Веб серверни бот билан бирга ёқади
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
