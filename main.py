import asyncio
import logging
import os
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN o'rnatilmagan!")
if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY o'rnatilmagan!")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- GLOBAL ---
df = None
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        logging.info(f"Katalog yuklandi: {len(df)} ta mahsulot.")
        return True
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Greenleaf Rishton botiga xush kelibsiz! 🌿\n\n"
        "Mahsulot nomi yoki kodi yozing — men topib beraman! 🔍"
    )

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None:
        load_catalog()

    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        mask = df.apply(
            lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(),
            axis=1
        )
        match = df[mask].head(1)

        if match.empty:
            await message.reply(
                f"🔍 '{message.text}' bo'yicha mahsulot topilmadi.\n"
                "Boshqa nom yoki kod bilan urinib ko'ring! 😊"
            )
            return

        row = match.iloc[0]

        def clean_val(val, default=""):
            return str(val).strip() if str(val).lower() != 'nan' else default

        kod      = clean_val(row.iloc[0], "Kod yo'q")
        nomi_ru  = clean_val(row.iloc[1], "Nomsiz")
        nomi_uz  = clean_val(row.iloc[2], nomi_ru)   # O'zbekcha nom, yo'q bo'lsa ruscha
        narx_raw = clean_val(row.iloc[3], "Ko'rsatilmagan")
        ball     = clean_val(row.iloc[4], "0")

        # Narxni formatlash
        clean_price = "".join(filter(str.isdigit, narx_raw))
        formatted_price = f"{int(clean_price):,}".replace(",", " ") if clean_price else narx_raw

        prompt = f"""
Siz Greenleaf Rishton sog'liqni saqlash markazi mutaxassisisiz.
Quyidagi mahsulot haqida 1-2 jumlali samimiy va foydali tavsiya yozing.
Faqat tavsiya qismini yozing, boshqa hech narsa qo'shmang.

Mahsulot: {nomi_uz}
"""

        response = model.generate_content(prompt)
        tavsiya = response.text.strip()

        javob = (
            f"✨ Greenleaf Sifati — Sizning salomatligigiz uchun! ✨\n\n"
            f"🧼 Mahsulot: {nomi_uz}\n"
            f"🆔 Kod: {kod}\n"
            f"💰 Hamkor narxi: {formatted_price} so'm\n"
            f"💎 Ball: {ball} PV\n\n"
            f"✅ {tavsiya}\n\n"
            f"🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF\n"
            f"📞 Tel: +998 33 993 4070"
        )

        await message.reply(javob)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("⚠️ Qidiruvda texnik xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")

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
    logging.info(f"Web server {port}-portda ishga tushdi.")

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

---

### 📦 `requirements.txt`:
```
aiogram
aiohttp
pandas
google-generativeai
