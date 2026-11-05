import asyncio
import logging
import requests
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
BOT_TOKEN = "9252766454:AAH4b534HujBB5WSmOgFFNSX53ES6CbuFK8"  # <--- ВСТАВЬ СЮДА ТОКЕН ОТ БОТА
CHAT_ID = "-1001234567890"             # <--- СЮДА ВСТАВИШЬ ID ГРУППЫ ПОЗЖЕ
GROUP_NAME = "2-ПТ"                    
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_schedule_from_api(group: str):
    url = f"https://omaviat.ru/api/schedule?group={group}" 
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"Ошибка: {e}")
    return None

def format_schedule(data, group: str):
    if not data or not data.get("lessons"):
        return f"👥 {group}\n\nПар нет или расписание не выложено. 😴"
    text = f"👥 {group}\n\n📅 РАСПИСАНИЕ\n"
    for lesson in data["lessons"]:
        text += f"\n{lesson.get('number', '')} пара ({lesson.get('time', '')})\n"
        text += f" Дисциплина: {lesson.get('subject', '')}\n"
        text += f" Кабинет: {lesson.get('room', '')}\n"
        text += f" Преподаватель: {lesson.get('teacher', '')}\n"
    return text

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("Привет! Команды:\n/today - на сегодня\n/id - узнать ID чата")

@dp.message(Command("id"))
async def id_cmd(message: Message):
    await message.answer(f"ID этого чата: `{message.chat.id}`", parse_mode="Markdown")

@dp.message(Command("today"))
async def today_cmd(message: Message):
    data = get_schedule_from_api(GROUP_NAME)
    await message.answer(format_schedule(data, GROUP_NAME))

async def monitor():
    last_data = ""
    while True:
        try:
            data = get_schedule_from_api(GROUP_NAME)
            if data:
                current = str(data)
                if last_data and current != last_data:
                    text = "⚠️ **ВНИМАНИЕ! РАСПИСАНИЕ ИЗМЕНИЛОСЬ!**\n\n" + format_schedule(data, GROUP_NAME)
                    try:
                        await bot.send_message(CHAT_ID, text, parse_mode="Markdown")
                    except: pass
                last_data = current
        except: pass
        await asyncio.sleep(900) # раз в 15 минут

async def main():
    asyncio.create_task(monitor())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
