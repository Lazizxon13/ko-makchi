import asyncio
import logging
import pandas as pd
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = "8275086123:AAFM8iifVbe8cidhE07hoEbQ0svwqvRB8ac"
GOOGLE_API_KEY = "AIzaSyC5a0Rk9TuIpN0b4RIBYtx6RM0peLxSe1U"
# DIQQAT: Linkni Google Sheets-dan (.csv) formatida yangidan olib qo'ying
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQAYDb5of_bCQCIBVpDj6VL3JMterNGELwCQDkPxtdyjLw5X8ODIS5oegBYWv3wUUBp2knWYUHvQDW-/pub?gid=1939417886&single=true&output=csv" 

# --- JADVALNI TEKSHIRISH ---
def get_catalog_data():
    try:
        # Jadvalni o'qib ko'ramiz
        df = pd.read_csv(SHEET_CSV_URL)
        print(f"✅ MUVAFFAQIYAT: {len(df)} ta mahsulot yuklandi!")
        return df.to_string(index=False)
    except Exception as e:
        # Xatoni terminalda batafsil ko'rsatish
        print(f"❌ XATO: Jadvalni o'qib bo'lmadi! Sababi: {e}")
        return "XATO: Katalog yuklanmadi."

# --- GEMINI ---
genai.configure(api_key=GOOGLE_API_KEY)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Assalomu alaykum! Greenleaf Rishton botiga xush kelibsiz. 😊")

@dp.message()
async def handle_text(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    catalog = get_catalog_data()
    
    instruction = f"""
    Siz Greenleaf Rishton markazi mutaxassisiz. 
    Mijozlar bilan samimiy gaplashing. 
    Faqat quyidagi katalog bo'yicha javob bering:
    {catalog}
    """
    
    try:
        model = genai.GenerativeModel(
            model_name='models/gemini-2.5-flash',
            system_instruction=instruction
        )
        response = model.generate_content(message.text)
        await message.reply(response.text)
    except Exception as e:
        logging.error(f"Gemini xatosi: {e}")
        await message.answer("Texnik xatolik, biroz kuting...")

async def main():
    # BOT ISHGA TUSHIShIDAN OLDIN JADVALNI BIRINCHI TEKSHIRAMIZ
    print("Jadval tekshirilmoqda...")
    get_catalog_data() 
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("Bot polling boshladi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())