import asyncio
import logging
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
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

# --- Расписания звонков ---
# Обычные дни (Пн, Вт, Ср, Пт, Сб)
REGULAR_CALLS = {
    "1": "08:00 - 09:30",
    "2": "09:40 - 11:10",
    "3": "11:40 - 13:10",
    "4": "13:40 - 15:10",
    "5": "15:30 - 17:00",
    "6": "17:10 - 18:40"
}

# 1-й и 3-й четверг (Классные часы)
THURSDAY_1_3_CALLS = {
    "1": "08:00 - 09:20",
    "2": "09:30 - 10:50",
    "3": "11:20 - 12:40",
    "4": "14:20 - 15:40",
    "5": "15:50 - 17:10",
    "6": "17:20 - 18:40"
}

# 2-й и 4-й четверг (Единые методические часы)
THURSDAY_2_4_CALLS = {
    "1": "08:00 - 09:20",
    "2": "09:30 - 10:50",
    "3": "11:20 - 12:40",
    "4": "14:20 - 15:40",
    "5": "15:50 - 17:10",
    "6": "17:20 - 18:40"
}

def get_calls_for_date(date_obj: datetime):
    # Если это не четверг (weekday 3 = четверг), возвращаем обычное расписание
    if date_obj.weekday() != 3:
        return REGULAR_CALLS
    
    # Вычисляем, какой это четверг месяца (1-й, 2-й, 3-й или 4-й)
    # (день_месяца - 1) // 7 + 1 дает номер недели
    week_of_month = (date_obj.day - 1) // 7 + 1
    
    # 1-й и 3-й четверг
    if week_of_month % 2 != 0:
        return THURSDAY_1_3_CALLS
    # 2-й и 4-й четверг
    else:
        return THURSDAY_2_4_CALLS

def fetch_schedule(date_obj: datetime):
    date_str = date_obj.strftime("%d.%m") 
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
        return f"ERROR_{response.status_code}"
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return None

def parse_schedule(html, date_obj):
    date_str = date_obj.strftime("%d.%m.%Y")
    if not html:
        return "⚠️ Сайт не отвечает."
    if html.startswith("ERROR_"):
        return f"⚠️ Ошибка сайта (Код: {html.split('_')[1]})."
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    
    # Получаем нужное расписание звонков для этого дня
    calls = get_calls_for_date(date_obj)
    
    if not table:
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."
    
    rows = table.find_all('tr')
    result = [f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n📅 <b>РАСПИСАНИЕ</b>"]
    found = False
    
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 5 and GROUP_NAME in cols[1].text:
            found = True
            para_num = cols[2].text.strip()
            aud = cols[3].text.strip() if cols[3].text.strip() else "---"
            subject = cols[4].text.strip() if len(cols) > 4 else ""
            teacher = cols[5].text.strip() if len(cols) > 5 else ""
            
            if "Отмена" in subject or "Отмена" in teacher:
                result.append(f"🔹 <b>{para_num} пара:</b> ❌ ОТМЕНА")
                continue
                
            # Берем время из нужного расписания звонков
            time_str = calls.get(para_num, "")
            time_text = f" ({time_str})" if time_str else ""
            
            text = f"🔹 <b>{para_num} пара</b>{time_text}\n"
            text += f"📖 {subject}\n"
            if aud and aud != "---":
                text += f"🚪 Каб: {aud}\n"
            if teacher:
                text += f"👨‍🏫 {teacher}"
            
            result.append(text.strip())
    
    if not found:
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."
    
    result.append("\n⭐ <i>Обязательно проверяйте изменения на сайте!</i>")
    return "\n\n".join(result)

def get_keyboard(date_obj: datetime):
    prev_date = (date_obj - timedelta(days=1)).strftime("%d.%m.%Y")
    next_date = (date_obj + timedelta(days=1)).strftime("%d.%m.%Y")
    
    kb = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"date_{prev_date}"),
            InlineKeyboardButton(text="📅 Сегодня", callback_data="today"),
            InlineKeyboardButton(text="➡️", callback_data=f"date_{next_date}")
        ]
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
    html = fetch_schedule(today)
    text = parse_schedule(html, today)
    await msg.edit_text(text, reply_markup=get_keyboard(today), parse_mode="HTML")

@dp.callback_query(F.data.startswith("date_") | (F.data == "today"))
async def process_date_callback(callback: CallbackQuery):
    await callback.answer("Загружаю...")
    if callback.data == "today":
        date_obj = datetime.now()
    else:
        date_str = callback.data.split("_")[1]
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    
    html = fetch_schedule(date_obj)
    text = parse_schedule(html, date_obj)
    await safe_edit(callback.message, text, get_keyboard(date_obj))

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(f"Привет! Я бот расписания <b>{GROUP_NAME}</b>.\nНажми /today, чтобы начать.", parse_mode="HTML")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
