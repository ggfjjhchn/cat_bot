import asyncio
import json
import os
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATA_FILE = "data.json"
user_state: dict[int, str] = {}


def load_data() -> dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return {"users": {}}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = {}
            return data
    except (json.JSONDecodeError, OSError):
        return {"users": {}}


def save_data(data: dict[str, Any]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user(data: dict[str, Any], user_id: int) -> dict[str, Any]:
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "cat_name": "",
            "trust": 5,
            "days": []
        }
    return data["users"][uid]


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🐱 Имя кота"), KeyboardButton(text="📅 Новый день")],
            [KeyboardButton(text="📝 Заметка"), KeyboardButton(text="✅ Статус")],
            [KeyboardButton(text="📖 История"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="❤️ Отношение"), KeyboardButton(text="🗑 Очистить день")],
        ],
        resize_keyboard=True
    )


def status_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="поел"), KeyboardButton(text="не убежал")],
            [KeyboardButton(text="убежал"), KeyboardButton(text="подошёл ближе")],
            [KeyboardButton(text="смотрел спокойно"), KeyboardButton(text="спрятался")],
        ],
        resize_keyboard=True
    )


def clamp_trust(value: int) -> int:
    return max(0, min(10, value))


def trust_bar(cat_name: str, trust: int) -> str:
    left = 10 - trust
    right = trust
    bar = "ты" + "—" * left + "❤️" + "—" * right + (cat_name if cat_name else "котик")
    return bar


def build_history_text(day: dict[str, Any]) -> str:
    lines = [f"📅 День {day['day_number']}"]

    if day["notes"]:
        for note in day["notes"]:
            lines.append(f"📝 {note}")
    else:
        lines.append("📝 нет заметок")

    if day["statuses"]:
        for status in day["statuses"]:
            lines.append(f"✅ {status}")
    else:
        lines.append("✅ нет статусов")

    return "\n".join(lines)


@dp.message(Command("start"))
async def start_cmd(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)
    save_data(data)

    if not user["cat_name"]:
        await message.answer(
            "Привет! 🐱\n"
            "Я дневник котиков.\n"
            "Сначала давай зададим имя котику.\n"
            "Напиши имя кота:",
            reply_markup=main_keyboard()
        )
        user_state[message.from_user.id] = "waiting_name"
    else:
        await message.answer(
            f"Привет! 🐱\n"
            f"Котик: {user['cat_name']}\n"
            "Бот готов.",
            reply_markup=main_keyboard()
        )


@dp.message(Command("day"))
@dp.message(F.text == "📅 Новый день")
async def new_day(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    day_number = len(user["days"]) + 1
    user["days"].append({
        "day_number": day_number,
        "notes": [],
        "statuses": [],
        "photos": []
    })

    save_data(data)
    await message.answer(f"📅 День {day_number} начат", reply_markup=main_keyboard())


@dp.message(Command("history"))
@dp.message(F.text == "📖 История")
async def history_cmd(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("История пустая 😿", reply_markup=main_keyboard())
        return

    for day in user["days"]:
        await message.answer(build_history_text(day), reply_markup=main_keyboard())

        for photo_id in day["photos"]:
            await message.answer_photo(photo_id)

        await message.answer("----------", reply_markup=main_keyboard())


@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def stats_cmd(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    notes_count = sum(len(day["notes"]) for day in user["days"])
    statuses_count = sum(len(day["statuses"]) for day in user["days"])
    photos_count = sum(len(day["photos"]) for day in user["days"])

    await message.answer(
        f"📊 Статистика\n"
        f"🐱 Имя: {user['cat_name'] if user['cat_name'] else 'не задано'}\n"
        f"📅 Дней: {len(user['days'])}\n"
        f"📝 Заметок: {notes_count}\n"
        f"✅ Статусов: {statuses_count}\n"
        f"📷 Фото: {photos_count}",
        reply_markup=main_keyboard()
    )


@dp.message(Command("clear"))
@dp.message(F.text == "🗑 Очистить день")
async def ask_clear_day(message: Message) -> None:
    await message.answer(
        "Напиши номер дня, который нужно очистить.\nНапример: 1",
        reply_markup=main_keyboard()
    )
    user_state[message.from_user.id] = "waiting_clear_day"


@dp.message(F.text == "🐱 Имя кота")
async def ask_cat_name(message: Message) -> None:
    await message.answer("Напиши имя кота 🐱", reply_markup=main_keyboard())
    user_state[message.from_user.id] = "waiting_name"


@dp.message(F.text == "📝 Заметка")
async def ask_note(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
        return

    await message.answer("Напиши заметку 📝", reply_markup=main_keyboard())
    user_state[message.from_user.id] = "waiting_note"


@dp.message(Command("note"))
async def note_cmd(message: Message) -> None:
    text = message.text.replace("/note", "", 1).strip()
    if not text:
        await message.answer("После /note нужно написать текст заметки")
        return

    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
        return

    user["days"][-1]["notes"].append(text)
    save_data(data)
    await message.answer("📝 Заметка сохранена", reply_markup=main_keyboard())


@dp.message(F.text == "✅ Статус")
async def ask_status(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
        return

    await message.answer("Выбери статус:", reply_markup=status_keyboard())
    user_state[message.from_user.id] = "waiting_status"


@dp.message(Command("status"))
async def status_cmd(message: Message) -> None:
    text = message.text.replace("/status", "", 1).strip()
    if not text:
        await message.answer("После /status нужно написать статус")
        return
    await save_status(message, text)


async def save_status(message: Message, status_text: str) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
        return

    user["days"][-1]["statuses"].append(status_text)

    trust = user.get("trust", 5)

    if status_text == "поел":
        trust += 1
    elif status_text == "подошёл ближе":
        trust += 2
    elif status_text == "смотрел спокойно":
        trust += 1
    elif status_text == "не убежал":
        trust += 1
    elif status_text == "убежал":
        trust -= 2
    elif status_text == "спрятался":
        trust -= 1

    user["trust"] = clamp_trust(trust)
    save_data(data)

    await message.answer("✅ Статус сохранён", reply_markup=main_keyboard())


@dp.message(F.text == "❤️ Отношение")
async def relation_cmd(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    await message.answer(
        trust_bar(user["cat_name"], user.get("trust", 5)),
        reply_markup=main_keyboard()
    )


@dp.message(F.photo)
async def save_photo(message: Message) -> None:
    data = load_data()
    user = get_user(data, message.from_user.id)

    if not user["days"]:
        await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
        return

    photo = message.photo[-1]
    user["days"][-1]["photos"].append(photo.file_id)
    save_data(data)

    await message.answer("📷 Фото сохранено", reply_markup=main_keyboard())


@dp.message()
async def handle_text(message: Message) -> None:
    user_id = message.from_user.id
    text = (message.text or "").strip()

    if not text:
        return

    state = user_state.get(user_id)

    if state == "waiting_name":
        data = load_data()
        user = get_user(data, user_id)
        user["cat_name"] = text
        save_data(data)

        user_state.pop(user_id, None)
        await message.answer(f"Имя сохранено: {text} 🐱", reply_markup=main_keyboard())
        return

    if state == "waiting_note":
        data = load_data()
        user = get_user(data, user_id)

        if not user["days"]:
            user_state.pop(user_id, None)
            await message.answer("Сначала начни новый день 📅", reply_markup=main_keyboard())
            return

        user["days"][-1]["notes"].append(text)
        save_data(data)

        user_state.pop(user_id, None)
        await message.answer("📝 Заметка сохранена", reply_markup=main_keyboard())
        return

    if state == "waiting_status":
        allowed_statuses = {
            "поел",
            "не убежал",
            "убежал",
            "подошёл ближе",
            "смотрел спокойно",
            "спрятался",
        }

        if text in allowed_statuses:
            user_state.pop(user_id, None)
            await save_status(message, text)
            return

        await message.answer("Выбери статус кнопкой или напиши такой же текст", reply_markup=status_keyboard())
        return

    if state == "waiting_clear_day":
        if not text.isdigit():
            await message.answer("Напиши номер дня цифрой", reply_markup=main_keyboard())
            return

        day_number = int(text)
        data = load_data()
        user = get_user(data, user_id)

        found = False
        for day in user["days"]:
            if day["day_number"] == day_number:
                day["notes"] = []
                day["statuses"] = []
                day["photos"] = []
                found = True
                break

        save_data(data)
        user_state.pop(user_id, None)

        if found:
            await message.answer(f"🗑 День {day_number} очищен", reply_markup=main_keyboard())
        else:
            await message.answer("Такого дня нет", reply_markup=main_keyboard())
        return

    await message.answer(
        "Я не понял сообщение.\n"
        "Используй кнопки или команды: /start, /day, /history, /stats, /clear",
        reply_markup=main_keyboard()
    )


async def main() -> None:
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
