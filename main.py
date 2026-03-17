import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- ТОКЕНЛАРНИ ОМБОРДАН ОЛИШ ---
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
        # Jadvalni o'qish
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        logging.info("Katalog muvaffaqiyatli yuklandi.")
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz A,B,C,D tartibida ishga tushdi! 🚀\nMahsulot kodi yoki nomini yozing.")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # СУПЕР-ҚИДИРУВ: Ҳамма устундан қидиради
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        # Маълумотларни устун тартиби бўйича оламиз (A=0, B=1, C=2, E=4)
        # Жадвалингизда: A-Kod, B-Nomi, C-Narxi, E-Ballari (одатда шундай бўлади)
        row = match.iloc[0]
        
        kod = row.iloc[0] # A устун
        nomi = row.iloc[1] # B устун
        narx_raw = str(row.iloc[2]) # C устун
        # Агар балл E устунда бўлса, индекс 4 бўлади. Агар D да бўлса 3 бўлади.
        # Келинг, баллни қидириб топадиган қиламиз:
        ball = row.iloc[4] if len(row) > 4 else row.iloc[-1]

        # Нархни чиройли қилиш
        clean_price = "".join(filter(str.isdigit, narx_raw))
        formatted_price = f"{int(clean_price):,}".replace(",", " ") if clean_price else narx_raw

        # Gemini 1.5 Flash Prompt
        instruction = f"""
        Siz Greenleaf mutaxassisiz. Quyidagi ma'lumotni o'zbekchada chiroyli reklama posti qiling:
        ✨ Greenleaf Sifati ✨
        🧼 Mahsulot: {nomi}
        🆔 Kod: {kod}
        💰 Narxi: {formatted_price} so'm
        💎 Ball: {ball} PV
        ✅ [Mahsulot haqida qisqa va foydali tavsiya yozing]
        🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
        📞 Tel: +998 33 993 4070
        """
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(instruction)
        await message.reply(response.text)

    except Exception as e:
        if "429" in str(e):
            await message.answer("⚠️ Лимит тўлди. 1 дақиқадан сўнг қайта уриниб кўринг.")
        else:
            logging.error(f"Xato: {e}")
            await message.answer("Маълумот топилди, лекин Гeмини жавоб беролмади. Қайта уриниб кўринг.")

# --- RENDER WEB SERVER ---
async def handle_ping(request):
    return web.Response(text="Live")

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
