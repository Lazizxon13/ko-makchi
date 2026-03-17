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

# --- JADVALNI YUKLASH ---
df = None

def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        # Ustun nomlaridagi bo'shliqlarni olib tashlaymiz
        df.columns = df.columns.str.strip()
        print(f"Muvaffaqiyat: {len(df)} ta mahsulot yuklandi!")
    except Exception as e:
        print(f"Jadval yuklashda xato: {e}")

# --- AI ---
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz tayyor. Mahsulot kodi yoki nomini yozing. 😊")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None:
        load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 1. JADVALDAN QIDIRISH (AQLI QIDIRUV)
    try:
        # Kod bo'yicha yoki Nomi bo'yicha qidiramiz
        result = df[
            df['Номер / Код'].astype(str).str.lower().contains(query) | 
            df['Наименование'].str.lower().str.contains(query)
        ].head(3) # Faqat birinchi 3 ta mos kelganini olamiz

        if result.empty:
            await message.reply("Kechirasiz, bunday mahsulot topilmadi. Kodni to'g'ri yozganingizni tekshiring.")
            return

        # 2. TOPILGAN MA'LUMOTNI GEMINI'GA YUBORISH (FAQAT BITTA MAHSULOTNI)
        product_info = result.to_string(index=False)
        
        instruction = f"""
        Siz Greenleaf mutaxassisiz. Quyidagi mahsulot ma'lumotini chiroyli o'zbekchaga o'girib, 
        avvalgi shablonimizda (✨ Greenleaf Sifati ✨) javob bering.
        🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
        📞 Tel: +998 33 993 4070
        
        Mahsulot ma'lumoti: {product_info}
        """
        
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=instruction)
        response = model.generate_content(f"Mana bu mahsulotni chiroyli ko'rinishga keltir: {query}")
        await message.reply(response.text)

    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")
        await message.answer("Biroz kuting, tizim qayta yuklanmoqda...")

# --- RENDER PORT VA SERVER ---
async def handle_ping(request):
    return web.Response(text="Bot is live!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    load_catalog()
    asyncio.create_task(start_web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
