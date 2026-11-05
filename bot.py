import asyncio
import logging
import requests
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9252766454:AAH4b534HujBB5WSmOgFFNSX53ES6CbuFK8" # Твой токен (он уже вставлен)
CHAT_ID = "-1001234567890"  # <--- СЮДА ВСТАВЬ ID ГРУППЫ ИЗ КОМАНДЫ /id
GROUP_NAME = "К215"         # Твоя группа
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_schedule_for_day(date_str: str):
    # Правильный адрес сайта колледжа
    url = f"https://www.oat.ru/timetable/Changes/b3/{date_str}?search={GROUP_NAME}"
    try:
        # Сайт может медленно отвечать, ставим таймаут побольше
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            # Отдаем HTML страницу для дальнейшего разбора
            return response.text
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
    return None

def parse_schedule(html):
    # Заглушка парсера. Если на сайте таблица, мы её тут найдем и распарсим.
    if not html:
        return "Нет данных или сайт недоступен."
    
    # Простейший поиск упоминаний группы и пар в HTML
    if GROUP_NAME in html:
        return "На этот день есть пары. Проверьте расписание на сайте."
    return "На этот день пар нет."

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("Привет! Я слежу за расписанием группы К215.\nКоманды:\n/week - расписание на неделю\n/id - узнать ID чата")

@dp.message(Command("id"))
async def id_cmd(message: Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

@dp.message(Command("week"))
async def week_cmd(message: Message):
    await message.answer("Проверяю расписание на неделю...")
    # Демонстрационный формат (даты берем из твоего примера)
    dates = ["02.11.2026", "03.11.2026", "05.11.2026", "06.11.2026"]
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
                # Если расписание изменилось (сравниваем хэш страницы или текст)
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
