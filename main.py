import asyncio
import logging
import os
import pandas as pd
from openai import AsyncOpenAI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# --- ТОКЕНЛАРНИ ЯШИРИН ОМБОРДАН ОЛИШ ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv"

# --- GLOBAL СОЗЛАМАЛАР ---
df = None
# ChatGPT ga ulanish
client = AsyncOpenAI(api_key=OPENAI_API_KEY)
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
    await message.answer("Assalomu alaykum! Greenleaf Rishton botingiz ChatGPT (OpenAI) aqki bilan ishga tushdi! 🚀")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # 1. ЖАДВАЛДАН ҚИДИРИШ
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        row = match.iloc[0]
        
        # МАЪЛУМОТЛАРНИ ОЛИШ
        kod = str(row.iloc[0])
        nomi = str(row.iloc[1])
        narx_raw = str(row.iloc[2])
        ball = row.iloc[4] if len(row) > 4 else "0"

        clean_price = "".join(filter(str.isdigit, narx_raw))
        try:
            formatted_price = f"{int(clean_price):,}".replace(",", " ")
        except:
            formatted_price = narx_raw

        # 2. OPENAI (CHATGPT) ГА СЎРОВ ЮБОРИШ
        prompt_text = f"Siz Greenleaf mutaxassisiz. Mahsulot: {nomi}, Kodi: {kod}, Narxi: {formatted_price} so'm, Balli: {ball} PV. Buni o'zbekcha chiroyli reklama posti qiling."
        
        # gpt-4o-mini - энг тез ва ҳамёнбоп модел
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz mijozlarni jalb qiluvchi zo'r kopiraytersiz. Qisqa, tushunarli va chiroyli emojilar bilan yozasiz."},
                {"role": "user", "content": prompt_text}
            ]
        )
        
        # Жавобни телеграмга юбориш
        await message.reply(response.choices[0].message.content)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer(f"❌ Хатолик юз берди: {str(e)}")

@dp.message()
async def handle_text(message: types.Message):
    global df
    if df is None: load_catalog()
    
    query = message.text.strip().lower()
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # 1. Жадвалдан маҳсулотни қидириш
        mask = df.apply(lambda row: row.astype(str).str.lower().str.contains(query, na=False).any(), axis=1)
        match = df[mask].head(1)

        if match.empty:
            await message.reply(f"'{query}' бўйича маҳсулот топилмади. 😊")
            return

        row = match.iloc[0]
        
        # МАЪЛУМОТЛАРНИ ТАЙЁРЛАШ
        kod = str(row.iloc[0])
        nomi_ru = str(row.iloc[1]) # Жадвалдаги русча номи
        narx_raw = str(row.iloc[2])
        ball = str(row.iloc[4]) if len(row) > 4 else "0"

        # Нархни чиройли қилиш
        clean_price = "".join(filter(str.isdigit, narx_raw))
        formatted_price = f"{int(clean_price):,}".replace(",", " ") if clean_price else narx_raw

        # --- СИЗ КЎРСАТГАН ИНСТРУКЦИЯ (ПРОМПТ) ---
        instruction = f"""
        Siz Greenleaf Rishton markazi mutaxassisiz. 
        Mijozlar bilan samimiy gaplashing.
        
        Vazifangiz: Quyidagi "Наименование"ни чиройли ўзбек тилига таржима қилинг ва маҳсулот ҳақида қисқача фойдали тавсия ёзинг.
        
        Маҳсулот маълумотлари:
        - Код: {kod}    
        - Наименование: {nomi_ru}
        - Цена: {formatted_price}
        - Балл: {ball}
        
        Faqat quyidagi shablonda javob bering (ҳеч қандай ортиқча гап қўшманг):
        ✨ Greenleaf Сифати — Сизнинг саломатлигингиз учун! ✨
        🧼 Маҳсулот: [Бу ерга ўзбекча номини ёзинг]
        🆔 Код: {kod}
        💰 Хамкор нархи: {formatted_price} сўм
        💎 Балл: {ball} PV
        ✅ [Бу ерга маҳсулот ҳақида 1 та қисқа ва самимий тавсия ёзинг]
        🛒 Буюртма: https://t.me/ORIFFFFFFFFFF
        📞 Тел: +998 33 993 4070
        """

        # 2. CHATGPT (OpenAI) ГА ЮБОРИШ
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz Greenleaf Rishton markazi mutaxassisiz. Faqat berilgan shablonda javob berasiz."},
                {"role": "user", "content": instruction}
            ]
        )
        
        await message.reply(response.choices[0].message.content)

    except Exception as e:
        logging.error(f"Xato: {e}")
        await message.answer(f"❌ Техник узилиш бўлди.")
