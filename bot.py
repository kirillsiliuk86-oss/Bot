import asyncio
import logging
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= НАСТРОЙКИ =================
# ВСТАВЬ СЮДА НОВЫЙ ТОКЕН ОТ BOTFATHER (после /revoke)
BOT_TOKEN = "9252766454:AAHvS_i2srqb26RYC9C6VVOvbw7CbBJO6A8"
CHAT_ID = "7790715572"  
GROUP_NAME = "К215"         
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def fetch_schedule(date_obj: datetime):
    # Формат даты без года: 06.11
    date_str = date_obj.strftime("%d.%m") 
    
    # Твоя правильная ссылка
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*"
    }
    
    try:
        logging.info(f"Запрос к API: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Ответ API: {response.status_code}")
        
        if response.status_code == 200:
            return response.json() 
        else:
            return f"ERROR_CODE_{response.status_code}"
    except Exception as e:
        logging.error(f"Ошибка API: {e}")
        return None

def parse_schedule(data, date_str):
    if not data:
        return "⚠️ Сайт не отвечает."
    if isinstance(data, str) and data.startswith("ERROR_CODE_"):
        return f"⚠️ Ошибка загрузки (Код: {data.split('_')[2]})."
    
    # Пытаемся достать данные из ответа
    lessons = data.get("lessons", data.get("data", data)) if isinstance(data, dict) else data
    
    if not lessons or not isinstance(lessons, list):
         # Если данных нет, выводим то, что пришло (для отладки)
         return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет.\n\n<i>Ответ сайта:</i>\n<code>{str(data)[:500]}</code>"
         
    result = [f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n📅 <b>РАСПИСАНИЕ</b>"]
    found = False
    
    for item in lessons:
        if GROUP_NAME in str(item):
            found = True
            result.append(f"🔹 {item}")
    
    if not found:
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."
    
    return "\n\n".join(result)

def get_keyboard(date_obj: datetime):
    prev_date = (date_obj - timedelta(days=1)).strftime("%d.%m.%Y")
    next_date = (date_obj + timedelta(days=1)).strftime("%d.%m.%Y")
    
    kb = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"date_{prev_date}"),
            InlineKeyboardButton(text="📅 Сегодня", callback_data="today"),
            InlineKeyboardButton(text="➡️", callback_data=f"date_{next_date}")
        ],
        [InlineKeyboardButton(text="На неделю 🗓", callback_data="week")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def safe_edit(message: Message, text: str, markup: InlineKeyboardMarkup):
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logging.error(f"Ошибка: {e}")

@dp.message(Command("today"))
async def today_cmd(message: Message):
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    msg = await message.answer(f"⏳ Загружаю расписание на {date_str}...")
    data = fetch_schedule(today)
    text = parse_schedule(data, date_str)
    await msg.edit_text(text, reply_markup=get_keyboard(today), parse_mode="HTML")

@dp.callback_query(F.data.startswith("date_") | (F.data == "today"))
async def process_date_callback(callback: CallbackQuery):
    await callback.answer("Загружаю...")
    if callback.data == "today":
        date_obj = datetime.now()
    else:
        date_str = callback.data.split("_")[1]
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    
    date_str_formatted = date_obj.strftime("%d.%m.%Y")
    data = fetch_schedule(date_obj)
    text = parse_schedule(data, date_str_formatted)
    await safe_edit(callback.message, text, get_keyboard(date_obj))

@dp.callback_query(F.data == "week")
async def process_week_callback(callback: CallbackQuery):
    await callback.answer("Собираю неделю...")
    await callback.message.edit_text("⏳ Собираю расписание на неделю, подождите...")
    
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    text = f"🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ ({GROUP_NAME})</b>\n\n"
    
    for i in range(6):
        current_day = monday + timedelta(days=i)
        date_str = current_day.strftime("%d.%m.%Y")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][i]
        
        data = fetch_schedule(current_day)
        text += f"<b>{day_name} ({date_str})</b>\n"
        
        if isinstance(data, dict) or isinstance(data, list):
             text += "  Данные получены (требуется настройка вывода)\n\n"
        else:
             text += "  Пар нет / Ошибка\n\n"
            
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к сегодня", callback_data="today")]])
    await safe_edit(callback.message, text, kb)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(f"Привет! Я бот расписания <b>{GROUP_NAME}</b>.\nНажми /today, чтобы начать.", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
