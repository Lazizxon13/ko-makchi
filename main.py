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
        # Jadvalni o'qiymiz va ustun nomlarini tozalaymiz
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        df.columns = [str(c).strip() for c in df.columns]
        logging.info(f"Katalog yuklandi: {len(df)} ta mahsulot.")
        logging.info(f"Mavjud ustunlar: {list(df.columns)}")
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz tayyor. Mahsulot kodi yoki nomini yozing. 😊")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # AQLI QIDIRUV: Ustun nomiga qarab emas, tartibiga qarab (0-kod, 1-nomi)
        # Jadvilingizda B ustuni (Kod) - 1-index, C ustuni (Nomi) - 2-index
        
        # Har ehtimolga qarshi kod va nom ustunlarini aniqlab olamiz
        kod_col = df.columns[1] # 2-ustun
        nomi_col = df.columns[2] # 3-ustun
        narx_col = df.columns[3] # 4-ustun
        ball_col = df.columns[5] # 6-ustun

        match = df[
            df[kod_col].astype(str).str.lower().str.contains(query, na=False) | 
            df[nomi_col].str.lower().str.contains(query, na=False)
        ].head(1)

        if match.empty:
            await message.reply(f"'{query}' bo'yicha mahsulot topilmadi. 😊")
            return

        product = match.iloc[0].to_dict()
        
        # Narxni chiroyli ko'rinishga keltirish
        raw_price = product.get(narx_col, 0)
        try:
            formatted_price = f"{float(str(raw_price).replace('uzs','').strip()):,.0f}".replace(",", " ")
        except:
            formatted_price = str(raw_price)

        prompt = f"""
        Siz Greenleaf mutaxassisiz. Quyidagi ma'lumotni o'zbekchada chiroyli reklama posti qiling:
        ✨ Greenleaf Sifati ✨
        🧼 Mahsulot: {product.get(nomi_col)}
        🆔 Kod: {product.get(kod_col)}
        💰 Narxi: {formatted_price} so'm
        💎 Ball: {product.get(ball_col, 0)} PV
        ✅ [Foydali tavsiya yozing]
        🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
        📞 Tel: +998 33 993 4070
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        await message.reply(response.text)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Biroz kuting, ma'lumot qidirilmoqda...")

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
