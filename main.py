import asyncio
import logging
import os
import pandas as pd
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- СОЗЛАМАЛАРНИ ОЛИШ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- ЛОГИКА ВА ОБЪЕКТЛАР ---
df = None
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def load_catalog():
    global df
    try:
        # Жадвални А, B, C, D устунлари билан ўқиш
        df = pd.read_csv(SHEET_CSV_URL, on_bad_lines='skip', sep=',')
        logging.info(f"Каталог юкланди: {len(df)} та маҳсулот.")
        return True
    except Exception as e:
        logging.error(f"Жадвал юклашда хато: {e}")
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "✨ **Greenleaf Rishton марказига хуш келибсиз!**\n\n"
        "Мен сизга маҳсулотларни топишда ва улар ҳақида маълумот беришда ёрдам бераман.\n"
        "Қидираётган маҳсулот кодини (масалан: `KAC951`) ёки номини ёзинг. 😊"
    )

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # 1. ЖАДВАЛДАН ҚИДИРИШ (Ҳамма устун бўйлаб)
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        row = match.iloc[0]
        
        # МАЪЛУМОТЛАРНИ ТАЙЁРЛАШ ВА "Nan"ДАН ТОЗАЛАШ
        def clean_val(val, default=""):
            return str(val) if str(val).lower() != 'nan' else default

        kod = clean_val(row.iloc[0], "Кодсиз")
        nomi_ru = clean_val(row.iloc[1], "Номсиз маҳсулот")
        narx_raw = clean_val(row.iloc[2], "Кўрсатилмаган")
        ball = clean_val(row.iloc[4] if len(row) > 4 else "0", "0")

        # Нархни форматлаш
        clean_price = "".join(filter(str.isdigit, narx_raw))
        formatted_price = f"{int(clean_price):,}".replace(",", " ") if clean_price else narx_raw

        # 2. CHATGPT УЧУН МАХСУС ИНСТРУКЦИЯ (Сиз айтган шаблон асосида)
        instruction = f"""
        Siz Greenleaf Rishton markazi mutaxassisiz. 
        Mijozlar bilan samimiy gaplashing.
        
        Vazifangiz: Quyidagi ruscha "Наименование"ni chiroyli o'zbek tiliga tarjima qiling va mahsulot haqida 1 ta qisqa foydali tavsiya yozing.
        
        Ma'lumotlar:
        - Nomi (RU): {nomi_ru}
        - Kodi: {kod}
        - Narxi: {formatted_price}
        - Ball: {ball}
        
        Faqat quyidagi shablonda javob bering:
        ✨ Greenleaf Сифати — Сизнинг саломатлигингиз учун! ✨
        🧼 Маҳсулот: [O'zbekcha nomi]
        🆔 Код: {kod}
        💰 Хамкор нархи: {formatted_price} сўм
        💎 Балл: {ball} PV
        ✅ [Mahsulot haqida qisqa va samimiy tavsiya]
        🛒 Буюртма: https://t.me/ORIFFFFFFFFFF
        📞 Тел: +998 33 993 4070
        """

        # 3. CHATGPT ГА СЎРОВ
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz Greenleaf mutaxassisiz. Faqat berilgan shablonda javob berasiz."},
                {"role": "user", "content": instruction}
            ]
        )
        
        await message.reply(response.choices[0].message.content)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer("⚠️ Қидирувда техник хатолик бўлди. Бироздан сўнг қайта уриниб кўринг.")

# --- RENDER WEB SERVER (ПОРТ МУАММОСИНИ ҲАЛ ҚИЛИШ) ---
async def handle_ping(request):
    return web.Response(text="Bot is running with ChatGPT!")

async def main():
    load_catalog()
    
    # Render учун портни созлаш
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Поллингни бошлаш
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
