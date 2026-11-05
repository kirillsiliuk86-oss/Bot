import asyncio
import logging
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9252766454:AAH4b534HujBB5WSmOgFFNSX53ES6CbuFK8" # Твой токен
CHAT_ID = "7790715572"  
GROUP_NAME = "К215"         
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция запроса к сайту с маскировкой под браузер
def fetch_schedule(date_obj: datetime):
    date_str = date_obj.strftime("%d.%m.%Y")
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
    return None

# Функция парсинга (вытаскиваем красиво текст)
def parse_schedule(html, date_str):
    if not html:
        return "⚠️ Сайт недоступен или произошла ошибка."
    
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table')
    if not table:
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."
    
    rows = table.find_all('tr')
    result = [f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n📅 <b>РАСПИСАНИЕ</b>"]
    found = False
    
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 4 and GROUP_NAME in cols[1].text:
            found = True
            para = cols[2].text.strip()
            aud = cols[3].text.strip()
            subject = cols[4].text.strip()
            result.append(f"🔹 <b>{para} пара</b> | Каб. {aud}\n📖 {subject}")
    
    if not found:
        return f"👥 <b>{GROUP_NAME}</b> ({date_str})\n\n😴 На этот день пар нет."
    
    result.append("\n⭐ <i>Обязательно проверяйте изменения на сайте!</i>")
    return "\n\n".join(result)

# Клавиатура с кнопками
def get_keyboard(date_obj: datetime):
    prev_date = (date_obj - timedelta(days=1)).strftime("%d.%m.%Y")
    next_date = (date_obj + timedelta(days=1)).strftime("%d.%m.%Y")
    curr_date = date_obj.strftime("%d.%m.%Y")
    
    kb = [
        [
            InlineKeyboardButton(text="⬅️", callback_data=f"date_{prev_date}"),
            InlineKeyboardButton(text="📅 Сегодня", callback_data="today"),
            InlineKeyboardButton(text="➡️", callback_data=f"date_{next_date}")
        ],
        [
            InlineKeyboardButton(text="На неделю 🗓", callback_data="week")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# Обработчик команды /today
@dp.message(Command("today"))
async def today_cmd(message: Message):
    today = datetime.now()
    date_str = today.strftime("%d.%m.%Y")
    
    msg = await message.answer(f"⏳ Загружаю расписание на {date_str}...")
    html = fetch_schedule(today)
    text = parse_schedule(html, date_str)
    
    await msg.edit_text(text, reply_markup=get_keyboard(today), parse_mode="HTML")

# Обработчик нажатий на кнопки
@dp.callback_query(F.data.startswith("date_") | (F.data == "today"))
async def process_date_callback(callback: CallbackQuery):
    await callback.answer("Загружаю...")
    
    if callback.data == "today":
        date_obj = datetime.now()
    else:
        date_str = callback.data.split("_")[1]
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
    
    date_str_formatted = date_obj.strftime("%d.%m.%Y")
    html = fetch_schedule(date_obj)
    text = parse_schedule(html, date_str_formatted)
    
    await callback.message.edit_text(text, reply_markup=get_keyboard(date_obj), parse_mode="HTML")

# Обработчик кнопки "На неделю"
@dp.callback_query(F.data == "week")
async def process_week_callback(callback: CallbackQuery):
    await callback.answer("Собираю неделю...")
    
    today = datetime.now()
    # Ищем понедельник текущей недели
    monday = today - timedelta(days=today.weekday())
    
    text = f"🗓 <b>РАСПИСАНИЕ НА НЕДЕЛЮ ({GROUP_NAME})</b>\n\n"
    
    for i in range(6): # Пн - Сб
        current_day = monday + timedelta(days=i)
        date_str = current_day.strftime("%d.%m.%Y")
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб"][i]
        
        html = fetch_schedule(current_day)
        # Упрощенный парсинг для недели
        soup = BeautifulSoup(html, 'html.parser') if html else None
        table = soup.find('table') if soup else None
        
        text += f"<b>{day_name} ({date_str})</b>\n"
        if table and GROUP_NAME in html:
            rows = table.find_all('tr')
            day_lessons = []
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4 and GROUP_NAME in cols[1].text:
                    day_lessons.append(f"  {cols[2].text.strip()} пара - {cols[4].text.strip()} (каб. {cols[3].text.strip()})")
            if day_lessons:
                text += "\n".join(day_lessons) + "\n\n"
            else:
                text += "  Пар нет\n\n"
        else:
            text += "  Пар нет\n\n"
            
    # Кнопка "Назад"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к сегодня", callback_data="today")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# Обработчик команды /start
@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(f"Привет! Я бот расписания <b>{GROUP_NAME}</b>.\nНажми /today, чтобы начать.", parse_mode="HTML")

# Фоновая проверка изменений для группы
async def monitor():
    last_states = {}
    while True:
        try:
            today = datetime.now()
            date_str = today.strftime("%d.%m.%Y")
            html = fetch_schedule(today)
            if html:
                # Сравниваем текст таблицы
                soup = BeautifulSoup(html, 'html.parser')
                table_text = soup.find('table').text if soup.find('table') else "empty"
                
                if date_str in last_states and last_states[date_str] != table_text:
                    text = f"⚠️ <b>ВНИМАНИЕ! РАСПИСАНИЕ НА СЕГОДНЯ ИЗМЕНИЛОСЬ!</b>\n\n"
                    text += parse_schedule(html, date_str)
                    try:
                        await bot.send_message(CHAT_ID, text, parse_mode="HTML")
                    except Exception as e:
                        logging.error(f"Не могу отправить в чат: {e}")
                
                last_states[date_str] = table_text
        except Exception as e:
            logging.error(f"Ошибка монитора: {e}")
        await asyncio.sleep(900) # Проверка раз в 15 минут

async def main():
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
