# -*- coding: utf-8 -*-
import json
import os
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATA_FILE = "cats_data.json"


# ================= ДАННЫЕ =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "days": [],
            "stats": {"notes": 0, "statuses": 0, "photos": 0},
            "cats": {},
            "trust": {}
        }

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ================= КНОПКИ =================

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Новый день")],
        [KeyboardButton(text="📝 Заметка"), KeyboardButton(text="✅ Статус")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📖 История")],
        [KeyboardButton(text="🐱 Имя кота"), KeyboardButton(text="❤️ Отношение")],
        [KeyboardButton(text="🗑 Очистить день")]
    ],
    resize_keyboard=True
)

status_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="поел"), KeyboardButton(text="не убежал")],
        [KeyboardButton(text="убежал"), KeyboardButton(text="подошёл ближе")]
    ],
    resize_keyboard=True
)


# ================= СТАРТ =================

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer("🐱 Бот готов!", reply_markup=main_kb)


# ================= НОВЫЙ ДЕНЬ =================

@dp.message(F.text == "📅 Новый день")
async def new_day_btn(message: Message):
    data = load_data()
    day_number = len(data["days"]) + 1

    data["days"].append({
        "day": day_number,
        "notes": [],
        "statuses": [],
        "photos": []
    })

    save_data(data)
    await message.answer(f"📅 День {day_number} начат")


# ================= ЗАМЕТКИ =================

@dp.message(F.text == "📝 Заметка")
async def ask_note(message: Message):
    await message.answer("Напиши заметку:")


@dp.message(Command("note"))
async def add_note(message: Message):
    text = message.text.replace("/note", "", 1).strip()
    data = load_data()

    if not data["days"]:
        await message.answer("Сначала новый день")
        return

    data["days"][-1]["notes"].append(text)
    data["stats"]["notes"] += 1
    save_data(data)

    await message.answer("📝 Сохранено")


# ================= СТАТУСЫ =================

@dp.message(F.text == "✅ Статус")
async def choose_status(message: Message):
    await message.answer("Выбери статус:", reply_markup=status_kb)


@dp.message(Command("status"))
@dp.message(F.text.in_(["поел", "не убежал", "убежал", "подошёл ближе"]))
async def add_status(message: Message):
    text = message.text.replace("/status", "", 1).strip()
    data = load_data()

    if not data["days"]:
        await message.answer("Сначала новый день")
        return

    data["days"][-1]["statuses"].append(text)
    data["stats"]["statuses"] += 1

    # влияние на доверие
    trust = data["trust"].get("cat", 5)

    if "поел" in text:
        trust += 1
    if "подошёл" in text:
        trust += 2
    if "убежал" in text:
        trust -= 2

    trust = max(0, min(10, trust))
    data["trust"]["cat"] = trust

    save_data(data)

    await message.answer("✅ Записано", reply_markup=main_kb)


# ================= ФОТО =================

@dp.message(F.photo)
async def save_photo(message: Message):
    data = load_data()

    if not data["days"]:
        await message.answer("Сначала новый день")
        return

    photo = message.photo[-1]
    data["days"][-1]["photos"].append(photo.file_id)
    data["stats"]["photos"] += 1

    save_data(data)
    await message.answer("📷 Фото сохранено")


# ================= СТАТИСТИКА =================

@dp.message(F.text == "📊 Статистика")
@dp.message(Command("stats"))
async def stats_cmd(message: Message):
    data = load_data()

    await message.answer(
        f"📊 Дней: {len(data['days'])}\n"
        f"📝 Заметок: {data['stats']['notes']}\n"
        f"✅ Статусов: {data['stats']['statuses']}\n"
        f"📷 Фото: {data['stats']['photos']}"
    )


# ================= ИСТОРИЯ =================

@dp.message(F.text == "📖 История")
@dp.message(Command("history"))
async def history_cmd(message: Message):
    data = load_data()

    for day in data["days"]:
        text = f"📅 День {day['day']}\n"

        for note in day["notes"]:
            text += f"📝 {note}\n"

        for status in day["statuses"]:
            text += f"✅ {status}\n"

        await message.answer(text)

        for photo in day["photos"]:
            await message.answer_photo(photo)

        await message.answer("----------")


# ================= ИМЯ КОТА =================

@dp.message(F.text == "🐱 Имя кота")
async def set_name(message: Message):
    await message.answer("Напиши имя кота:")


@dp.message()
async def save_name(message: Message):
    data = load_data()

    if len(message.text) < 20:
        data["cats"]["name"] = message.text
        save_data(data)
        await message.answer(f"🐱 Имя сохранено: {message.text}", reply_markup=main_kb)


# ================= ОТНОШЕНИЕ =================

@dp.message(F.text == "❤️ Отношение")
async def trust_view(message: Message):
    data = load_data()

    trust = data["trust"].get("cat", 5)

    bar = "ты" + "—" * trust + "❤️" + "—" * (10 - trust) + "котик"

    await message.answer(f"{bar}")


# ================= ОЧИСТКА =================

@dp.message(F.text == "🗑 Очистить день")
async def clear_day(message: Message):
    await message.answer("Напиши номер дня (например: 1)")


@dp.message()
async def delete_day(message: Message):
    data = load_data()

    if message.text.isdigit():
        num = int(message.text)

        for day in data["days"]:
            if day["day"] == num:
                day["notes"] = []
                day["statuses"] = []
                day["photos"] = []

        save_data(data)
        await message.answer(f"🗑 День {num} очищен", reply_markup=main_kb)


# ================= ЗАПУСК =================

async def main():
    me = await bot.get_me()
    print(f"Бот запущен: @{me.username}")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
