import asyncio
import logging
import requests
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
# Твой токен (он уже вставлен)
BOT_TOKEN = "9252766454:AAH4b534HujBB5WSmOgFFNSX53ES6CbuFK8" 
# ID чата из твоего скриншота
CHAT_ID = "7790715572"  
# Название группы
GROUP_NAME = "К215"         
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_schedule_for_day(date_str: str):
    # Ссылка на сайт колледжа
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
    return None

def parse_schedule(html):
    if not html:
        return "Сайт недоступен или произошла ошибка."
    
    # Ищем упоминание группы на странице
    if GROUP_NAME in html:
        return "На этот день есть изменения или пары. Проверьте сайт."
    return "На этот день пар нет (или их не нашли)."

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(f"Привет! Я слежу за расписанием группы {GROUP_NAME}.\nКоманды:\n/today - на сегодня\n/week - на неделю\n/id - ID чата")

@dp.message(Command("id"))
async def id_cmd(message: Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

@dp.message(Command("today"))
async def today_cmd(message: Message):
    today = datetime.now().strftime("%d.%m.%Y")
    await message.answer(f"Смотрю расписание на {today}...")
    html = get_schedule_for_day(today)
    result = parse_schedule(html)
    await message.answer(f"👥 {GROUP_NAME} ({today})\n\n{result}")

@dp.message(Command("week"))
async def week_cmd(message: Message):
    await message.answer("Проверяю расписание на неделю...")
    # Берем даты из твоего примера (пока для теста)
    dates = ["05.11.2026", "06.11.2026"]
    result_text = f"📅 **РАСПИСАНИЕ {GROUP_NAME}**\n\n"
    
    for d in dates:
        html = get_schedule_for_day(d)
        result_text += f"**{d}**:\n"
        result_text += parse_schedule(html) + "\n\n"
        
    await message.answer(result_text, parse_mode="Markdown")

# Фоновая проверка изменений
async def monitor():
    last_states = {}
    while True:
        try:
            today = datetime.now().strftime("%d.%m.%Y")
            html = get_schedule_for_day(today)
            if html:
                if today in last_states and last_states[today] != html:
                    text = f"⚠️ **ВНИМАНИЕ! РАСПИСАНИЕ НА {today} ИЗМЕНИЛОСЬ!**\n\n"
                    text += parse_schedule(html)
                    try:
                        await bot.send_message(CHAT_ID, text, parse_mode="Markdown")
                    except Exception as e:
                        logging.error(f"Не могу отправить в чат: {e}")
                
                last_states[today] = html
        except Exception as e:
            logging.error(f"Ошибка монитора: {e}")
        await asyncio.sleep(900) # Проверка раз в 15 минут

async def main():
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
