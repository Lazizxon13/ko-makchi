import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- ТОКЕНЛАРНИ ЯШИРИН ОМБОРДАН ОЛИШ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- GLOBAL СОЗЛАМАЛАР ---
df = None
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        logging.info("Katalog muvaffaqiyatli yuklandi.")
        return True
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz ТОЗАЛАНДИ ва ишга тушди! 🚀")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Ҳамма устундан қидириш
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        row = match.iloc[0]
        
        # МАЪЛУМОТЛАРНИ УСТУН ТАРТИБИ (A, B, C, D) БЎЙИЧА ОЛИШ
        kod = str(row.iloc[0])   # A устун
        nomi = str(row.iloc[1])  # B устун
        narx_raw = str(row.iloc[2]) # C устун
        ball = row.iloc[4] if len(row) > 4 else "0" # E устун ёки охиргиси

        # Нархни тозалаш ва чиройли қилиш
        clean_price = "".join(filter(str.isdigit, narx_raw))
        try:
            formatted_price = f"{int(clean_price):,}".replace(",", " ")
        except:
            formatted_price = narx_raw

        # Gemini 1.5 Flash (Лимити катта модел)
        prompt = f"Siz Greenleaf mutaxassisiz. Mahsulot: {nomi}, Kodi: {kod}, Narxi: {formatted_price} so'm, Balli: {ball} PV. Buni o'zbekcha chiroyli reklama posti qiling."
        
       # Янги ва энг барқарор қатор:
model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        await message.reply(response.text)

    except Exception as e:
        # Хато бўлса, уни аниқ кўрамиз
        logging.error(f"Xato: {e}")
        await message.answer(f"❌ Хатолик: {str(e)}")

# --- RENDER WEB SERVER ---
async def handle_ping(request):
    return web.Response(text="Bot is Live")

async def main():
    load_catalog()
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    # ЭНГ МУҲИМИ: Conflict хатосини йўқотиш учун эски алоқаларни узамиз
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
