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
        # 1. Жадвалдан қидириш
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        product = match.iloc[0].to_dict()
        
        # 2. Устунларни аниқлаш
        cols = list(product.keys())
        nomi = product.get(next((c for c in cols if 'наименование' in c.lower()), cols[1]), "Номсиз")
        kod = product.get(next((c for c in cols if 'код' in c.lower()), cols[0]), "Кодсиз")
        narx = product.get(next((c for c in cols if 'цена' in c.lower()), cols[2]), "0")

        # 3. Gemini 1.5 Flash га юбориш (Лимити каттароқ модел)
        instruction = f"Siz Greenleaf mutaxassisiz. Mahsulot: {nomi}, Kodi: {kod}, Narxi: {narx}. Buni o'zbekcha chiroyli reklama qiling."
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(instruction)
        await message.reply(response.text)

    except Exception as e:
        # Агар лимит тугаса, бот "Кутинг" демайди, аниқ айтади
        if "429" in str(e):
            await message.answer("⚠️ Кечирасиз, ҳозирча бепул сўровлар лимити тугади. 1 дақиқадан сўнг қайта уриниб кўринг.")
        else:
            logging.error(f"Xato: {e}")
            await message.answer("Маълумот қидиришда техник узилиш бўлди.")
        
        # Narxni tozalash
        raw_price = str(product.get(narx_col, '0'))
        clean_price = "".join(filter(str.isdigit, raw_price))
        try:
            formatted_price = f"{int(clean_price):,}".replace(",", " ")
        except:
            formatted_price = raw_price

        instruction = f"""
        Siz Greenleaf mutaxasisisiz. Quyidagi ma'lumotni o'zbekchada reklama posti qiling:
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
