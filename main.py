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

# --- GLOBAL ---
df = None
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        df.columns = df.columns.str.strip()
        logging.info(f"Katalog yuklandi: {len(df)} ta mahsulot.")
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz Gemini 2.5 Flash'da tayyor! 😊")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        kod_col = 'Номер / Код'
        nomi_col = 'Наименование'
        
        match = df[
            df[kod_col].astype(str).str.lower().str.contains(query, na=False) | 
            df[nomi_col].str.lower().str.contains(query, na=False)
        ].head(1)

        if match.empty:
            await message.reply("Mahsulot topilmadi. Kodni tekshirib qayta yozing. 😊")
            return

        product = match.iloc[0].to_dict()
        
        # Narxni chiroyli formatlash (31 000 ko'rinishida)
        raw_price = product.get('Розничная цена', 0)
        try:
            formatted_price = f"{float(raw_price):,.0f}".replace(",", " ")
        except:
            formatted_price = str(raw_price)

        instruction = f"""
        Siz Greenleaf mutaxassisiz. Quyidagi ma'lumotni o'zbekchada chiroyli reklama posti qiling:
        ✨ Greenleaf Sifati ✨
        🧼 Mahsulot: {product.get(nomi_col)}
        🆔 Kod: {product.get(kod_col)}
        💰 Narxi: {formatted_price} so'm
        💎 Ball: {product.get('Баллы', 0)} PV
        ✅ [Mahsulot haqida qisqa va foydali tavsiya yozing]
        🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
        📞 Tel: +998 33 993 4070
        """
        
        # Gemini 2.5 Flash ishlatilmoqda
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(instruction)
        await message.reply(response.text)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Biroz kuting, tizim yangilanmoqda...")

# --- RENDER SERVER ---
async def handle_ping(request):
    return web.Response(text="Bot is Live!")

async def main():
    load_catalog()
    app = web.Application(); app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app); await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
