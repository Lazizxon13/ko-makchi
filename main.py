import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- СОЗЛАМАЛАРНИ ХАВФСИЗ ОЛИШ ---
# Render Environment Variables бўлимидан олинади
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- GLOBAL МАЪЛУМОТЛАР ---
catalog_text = "Каталог юкланмади."
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog_to_memory():
    """Жадвални бир марта хотирага юклаб оламиз (Тез ишлаши учун)"""
    global catalog_text
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        catalog_text = df.to_string(index=False)
        logging.info("✅ Каталог хотирага муваффақиятли юкланди!")
    except Exception as e:
        logging.error(f"❌ Жадвал юклашда хато: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton боти тайёр. Маҳсулот ҳақида сўранг. 😊")

@dp.message()
async def handle_text(message: types.Message):
    global catalog_text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    instruction = f"""
    Siz Greenleaf Rishton markazi mutaxassisiz.
    Mijozlar bilan samimiy gaplashing.
    Faqat quyidagi katalog bo'yicha javob bering:
    {catalog_text}
    """

    try:
        # Модел номини 'gemini-1.5-flash' қилиш хавфсизроқ (404 бермайди)
        model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            system_instruction=instruction
        )
        response = model.generate_content(message.text)
        await message.reply(response.text)
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        await message.answer("Ҳозирча лимит тўлди ёки техник узилиш. Бироздан сўнг уриниб кўринг.")

# --- RENDER УЧУН ВЕБ-СЕРВЕР ---
async def handle_ping(request):
    return web.Response(text="Live")

async def main():
    # 1. Жадвални юклаш
    load_catalog_to_memory()
    
    # 2. Веб-сервер (Render портни кўриши учун)
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()

    # 3. Ботни бошлаш
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
