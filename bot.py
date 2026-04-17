import asyncio
import json
import os

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# 🔥 Токен берём из Railway
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"

# 👉 состояние пользователя (для имени и т.д.)
user_state = {}

# ---------- работа с данными ----------

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------- старт ----------

@dp.message(Command("start"))
async def start(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data:
        data[user_id] = {
            "name": None,
            "days": {}
        }
        save_data(data)

        await message.answer("Напиши имя котика 🐱:")
        user_state[message.from_user.id] = "waiting_name"
    else:
        await message.answer("С возвращением! 🐱")

# ---------- история ----------

@dp.message(Command("history"))
async def history(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data or not data[user_id]["days"]:
        await message.answer("История пустая 😿")
        return

    text = ""

    for day, info in data[user_id]["days"].items():
        text += f"📅 День {day}\n"
        text += f"📝 {info.get('note', '-')}\n"
        text += f"📊 {info.get('status', '-')}\n"
        text += "-----------------\n"

    await message.answer(text)

# ---------- добавление дня ----------

@dp.message(Command("day"))
async def add_day(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id not in data:
        return

    day_number = len(data[user_id]["days"]) + 1

    data[user_id]["days"][str(day_number)] = {
        "note": "нет заметки",
        "status": "обычный"
    }

    save_data(data)

    await message.answer(f"Добавлен день {day_number} 🐾")

# ---------- очистка ----------

@dp.message(Command("clear"))
async def clear(message: Message):
    user_id = str(message.from_user.id)
    data = load_data()

    if user_id in data:
        data[user_id]["days"] = {}
        save_data(data)

    await message.answer("Все дни очищены 🧹")

# ---------- ОБРАБОТКА ТЕКСТА (САМОЕ ВАЖНОЕ) ----------

@dp.message()
async def handle_text(message: Message):
    user_id = message.from_user.id
    data = load_data()

    # 👉 ввод имени БЕЗ команды
    if user_id in user_state:
        if user_state[user_id] == "waiting_name":
            name = message.text

            if str(user_id) not in data:
                data[str(user_id)] = {"name": None, "days": {}}

            data[str(user_id)]["name"] = name
            save_data(data)

            await message.answer(f"Имя сохранено: {name} 🐱")

            user_state.pop(user_id)
            return

# ---------- запуск ----------

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
