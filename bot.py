import asyncio
import logging
import requests
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9252766454:AAHvS_i2srqb26RYC9C6VVOvbw7CbBJO6A8" 
CHAT_ID = "7790715572"  
GROUP_NAME = "К215"         
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def fetch_schedule(date_obj: datetime):
    # Берем формат без года, как ты нашел: 06.11
    date_str = date_obj.strftime("%d.%m") 
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    
    # Идеальная маскировка под Safari на iPhone
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Connection": "keep-alive"
    }
    
    try:
        # Делаем обычный запрос (без прокси)
        response = requests.get(url, headers=headers, timeout=15)
        logging.info(f"Статус ответа: {response.status_code}")
        
        if response.status_code == 200:
            return response.text
        return f"ERROR_{response.status_code}"
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None

def parse_schedule(html, date_str):
    if not html:
        return "⚠️ Сайт не отвечает (сервер заблокирован)."
    if html.startswith("ERROR_"):
        return f"⚠️ Ошибка сайта (Код: {html.split('_')[1]})."
    
    # Ищем текст страницы
    if GROUP_NAME in html:
        # Если группа есть на странице, выводим сообщение, что изменения есть
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n✅ <b>На этот день есть расписание!</b>\nПроверьте сайт, чтобы увидеть детали."
    
    return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."

def get_keyboard(date_obj: datetime):
    prev_date = (date_obj - timedelta(days=1)).strftime("%d.%m.%Y")
    next_date = (date_obj + timedelta(days=1)).strftime("%d.%m.%Y")
    kb = [
        [InlineKeyboardButton(text="⬅️", callback_data=f"date_{prev_date}"),
         InlineKeyboardButton(text="📅 Сегодня", callback_data="today"),
         InlineKeyboardButton(text="➡️", callback_data=f"date_{next_date}")],
        [InlineKeyboardButton(text="На неделю 🗓", callback_data="week")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

async def safe_edit(message: Message, text: str, markup: InlineKeyboardMarkup):
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest:
        pass

@dp.message(Command("today"))
async def today_cmd(message: Message):
    today = datetime.now()
    msg = await message.answer("⏳ Загружаю...")
    html = fetch_schedule(today)
    text = parse_schedule(html, today.strftime("%d.%m.%Y"))
    await msg.edit_text(text, reply_markup=get_keyboard(today), parse_mode="HTML")

@dp.callback_query(F.data.startswith("date_") | (F.data == "today"))
async def process_date_callback(callback: CallbackQuery):
    await callback.answer()
    if callback.data == "today":
        date_obj = datetime.now()
    else:
        date_str = callback.data.split("_")[1]
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    
    html = fetch_schedule(date_obj)
    text = parse_schedule(html, date_obj.strftime("%d.%m.%Y"))
    await safe_edit(callback.message, text, get_keyboard(date_obj))

@dp.callback_query(F.data == "week")
async def process_week_callback(callback: CallbackQuery):
    await callback.answer()
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    text = f"🗓 <b>НЕДЕЛЯ ({GROUP_NAME})</b>\n\n"
    for i in range(6):
        current_day = monday + timedelta(days=i)
        html = fetch_schedule(current_day)
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][i]
        text += f"<b>{day_name}</b>: "
        if html and GROUP_NAME in html:
            text += "Есть пары ✅\n"
        else:
            text += "Пар нет ❌\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="today")]])
    await safe_edit(callback.message, text, kb)

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(f"Привет! Я бот расписания <b>{GROUP_NAME}</b>.\nНажми /today.", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
