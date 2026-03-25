import asyncio
import logging
import os
import pandas as pd
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("GOOGLE_API_KEY")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ5Y5lhFw0cKz8UuVb_fjbv1JKT0ncQYPxihlAycO9cGyZa2E92TKZB3fNx8er9N5EclXKNyzB63Fe7/pub?output=csv"

# --- GLOBAL MA'LUMOTLAR ---
df = None
client = AsyncOpenAI(api_key=GOOGLE_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)


def load_catalog():
    global df
    try:
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip')
        df.columns = df.columns.str.strip()  # Ustun nomlaridan bo'sh joylarni olib tashlash
        logging.info(f"Katalog yuklandi: {len(df)} ta mahsulot. Ustunlar: {list(df.columns)}")
        return True
    except Exception as e:
        logging.error(f"Jadval yuklashda xato: {e}")
        return False


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! Greenleaf Rishton botingiz ChatGPT bilan ishga tushdi! 🚀\n"
        "Mahsulot nomini yoki kodini yuboring."
    )


@dp.message(Command("reload"))
async def cmd_reload(message: types.Message):
    success = load_catalog()
    if success:
        await message.answer(f"✅ Katalog qayta yuklandi: {len(df)} ta mahsulot.")
    else:
        await message.answer("❌ Katalogni yuklashda xatolik yuz berdi.")


@dp.message()
async def handle_text(message: types.Message):
    global df

    # Katalog yuklanmagan bo'lsa, qayta yuklash
    if df is None:
        load_catalog()

    if df is None:
        await message.answer("⚠️ Katalog yuklanmadi. Iltimos, biroz kutib qayta urinib ko'ring.")
        return

    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Jadvaldan qidirish
        mask = df.apply(
            lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(),
            axis=1
        )
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{message.text}' bo'yicha mahsulot topilmadi. 😊\nBoshqa nom yoki kod kiriting.")
            return

        row = match.iloc[0]

        # Ma'lumotlarni tозалаш
        def clean_val(val, default=""):
            s = str(val).strip()
            return s if s.lower() != 'nan' else default

        # Ustun nomlarini log qilish (debug uchun)
        logging.info(f"Topilgan qator: {row.to_dict()}")

        # Ustunlarni nomidan olish (mavjud bo'lsa), aks holda indeksdan
        cols = list(df.columns)

        def get_col(index, default=""):
            if index < len(row):
                return clean_val(row.iloc[index], default)
            return default

        kod       = get_col(0, "Kod yo'q")
        nomi_ru   = get_col(1, "Nomsiz")
        narx_raw  = get_col(2, "Ko'rsatilmagan")
        ball      = get_col(4, "0")

        # Narxni formatlash
        clean_price = "".join(filter(str.isdigit, narx_raw))
        formatted_price = f"{int(clean_price):,}".replace(",", " ") if clean_price else narx_raw

        # ChatGPT Prompt
        instruction = f"""
Siz Greenleaf Rishton markazi mutaxassisiz.
Mijozlar bilan samimiy gaplashing.

Vazifangiz: Quyidagi ruscha "Наименование"ni chiroyli o'zbek tiliga tarjima qiling va mahsulot haqida qisqa foydali tavsiya yozing.

Ma'lumotlar:
- Наименование: {nomi_ru}
- Kodi: {kod}
- Narxi: {formatted_price}
- Ball: {ball}

Faqat quyidagi shablonda javob bering (boshqa gap qo'shmang):
✨ Greenleaf Sifati — Sizning sog'ligingiz uchun! ✨
🧼 Mahsulot: [O'zbekcha nomi]
🆔 Kod: {kod}
💰 Hamkor narxi: {formatted_price} so'm
💎 Ball: {ball} PV
✅ [Mahsulot haqida qisqa va samimiy tavsiya]
🛒 Buyurtma: https://t.me/ORIFFFFFFFFFF
📞 Tel: +998 33 993 4070
"""

        # ChatGPT so'rov
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Siz Greenleaf Rishton markazi mutaxassisiz. Faqat berilgan shablonda javob berasiz."
                },
                {"role": "user", "content": instruction}
            ]
        )

        await message.reply(response.choices[0].message.content)

    except Exception as e:
        logging.error(f"Xato: {e}", exc_info=True)
        await message.answer("⚠️ Qidiruvda texnik xatolik yuz berdi. Iltimos qayta urinib ko'ring.")


# --- RENDER WEB SERVER (bot uyg'oq turishi uchun) ---
async def handle_ping(request):
    return web.Response(text="Live")


async def main():
    # Katalogni yuklash
    if not load_catalog():
        logging.warning("Katalog yuklanmadi! Bot ishga tushadi, lekin mahsulotlar topilmasligi mumkin.")

    # Aiohttp web server (Render uchun)
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    logging.info(f"Web server port {port} da ishga tushdi.")

    # Telegram bot polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
