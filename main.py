import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

import os # Тизим билан ишлаш учун керак

# --- ТОКЕНЛАРНИ ЯШИРИН ОМБОРДАН ОЛИШ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Энди Гитҳубда ҳеч ким сизнинг калитларингизни кўра олмайди!
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- GLOBAL O'ZGARUVCHILAR ---
df = None
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        df.columns = [str(c).strip() for c in df.columns]
        logging.info("Katalog muvaffaqiyatli yuklandi.")
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz Gemini 2.5 Flash'da ishga tushdi! 🚀")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        cols = list(df.columns)
        kod_col = next((c for c in cols if 'код' in c.lower() or 'номер' in c.lower()), cols[1])
        nomi_col = next((c for c in cols if 'наименование' in c.lower() or 'номи' in c.lower()), cols[2])
        narx_col = next((c for c in cols if 'цена' in c.lower() or 'нарх' in c.lower()), cols[3])
        ball_col = next((c for c in cols if 'балл' in c.lower() or 'pv' in c.lower()), cols[-1])

        match = df[
            df[kod_col].astype(str).str.lower().str.contains(query, na=False, regex=False) | 
            df[nomi_col].str.lower().str.contains(query, na=False, regex=False)
        ].head(1)

        if match.empty:
            await message.reply(f"'{query}' bo'yicha mahsulot topilmadi. 😊")
            return

        product = match.iloc[0].to_dict()
        
        # Narxni tozalash
        raw_price = str(product.get(narx_col, '0'))
        clean_price = "".join(filter(str.isdigit, raw_price))
        try:
            formatted_price = f"{int(clean_price):,}".replace(",", " ")
        except:
            formatted_price = raw_price

        instruction = f"""
        Siz Greenleaf mutaxassisiz. Quyidagi ma'lumotni o'zbekchada reklama posti qiling:
        ✨ Greenleaf Sifati ✨
        🧼 Mahsulot: {product.get(nomi_col)}
        🆔 Kod: {product.get(kod_col)}
        💰 Narxi: {formatted_price} so'm
        💎 Ball: {product.get(ball_col, 0)} PV
        ✅ [Mahsulot haqida juda qisqa va qiziqarli tavsiya yozing]
        🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
        📞 Tel: +998 33 993 4070
        """
        
       # main.py ичидаги мана шу қаторни топинг ва ўзгартиринг:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(instruction)
        await message.reply(response.text)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("Biroz kuting, ma'lumot qidirilmoqda...")

# --- RENDER WEB SERVER ---
async def handle_ping(request):
    return web.Response(text="Live")

async def main():
    load_catalog()
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    
    # Conflict xatosini yo'qotish uchun webhookni tozalash
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
