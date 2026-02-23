import asyncio
import json
import os
from datetime import datetime, date, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== НАСТРОЙКИ ==========
TOKEN = "8712543109:AAFFOmfO2BrtkjTqyJ3TrTYz4bzwY_oCrFk"  # замени на свой
TARGET = 100000
START_DATE = date(2026, 2, 1)
END_DATE = date(2026, 12, 31)

# План по месяцам: (месяц, дней, сумма_в_день)
MONTHLY_PLAN = [
    (2, 28, 150), (3, 31, 150), (4, 30, 150),
    (5, 31, 300), (6, 30, 300), (7, 31, 300),
    (8, 31, 400), (9, 30, 400), (10, 31, 400),
    (11, 30, 430), (12, 31, 430)
]
# ================================

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Файл для хранения данных
DATA_FILE = "savings_data.json"

# ---------- Машина состояний ----------
class AddMoney(StatesGroup):
    waiting_for_amount = State()

# ---------- Работа с данными ----------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}}  # {user_id: {"records": [{"date": "2026-02-23", "amount": 150}]}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    user_id_str = str(user_id)
    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {"records": []}
        save_data(data)
    return data["users"][user_id_str], data

def save_user_data(user_id, user_data):
    data = load_data()
    data["users"][str(user_id)] = user_data
    save_data(data)

# ---------- Вспомогательные функции ----------
def get_daily_plan_for_date(d: date) -> int:
    for month, _, amount in MONTHLY_PLAN:
        if d.month == month and d.year == 2026:
            return amount
    return 0

def get_plan_total_to_date(d: date) -> int:
    if d < START_DATE:
        return 0
    total = 0
    current = START_DATE
    while current <= d and current <= END_DATE:
        total += get_daily_plan_for_date(current)
        current += timedelta(days=1)
    return total

def format_amount(amount: int) -> str:
    return f"{amount:,} ₽".replace(",", " ")

def get_month_name(month_num: int) -> str:
    months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
    return months[month_num - 1]

# ---------- Клавиатуры ----------
def main_keyboard():
    kb = [
        [InlineKeyboardButton(text="💰 Добавить взнос", callback_data="add")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
         InlineKeyboardButton(text="📜 История", callback_data="history")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def cancel_keyboard():
    kb = [[InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ---------- Обработчики команд и кнопок ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Привет! Это бот для накопления 100 000 ₽ к концу 2026 года.\n"
        "Я помогу тебе отслеживать ежедневные взносы.\n\n"
        "Выбери действие:",
        reply_markup=main_keyboard()
    )

@dp.callback_query(F.data == "menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "cancel")
async def cancel_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Действие отменено. Главное меню:",
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = (
        "❓ **Как пользоваться ботом**\n\n"
        "1. Каждый день нажимай «💰 Добавить взнос» и вводи сумму, которую отложил.\n"
        "2. Смотри статистику — там видно, успеваешь или нет.\n"
        "3. История показывает последние операции.\n\n"
        "📅 **План по месяцам:**\n"
    )
    for month, days, daily in MONTHLY_PLAN:
        text += f"   {get_month_name(month)}: {daily} ₽/день (всего {daily*days} ₽)\n"
    text += f"\n🎯 Цель: {format_amount(TARGET)}"
    await callback.message.edit_text(text, reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "add")
async def add_money(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AddMoney.waiting_for_amount)
    await callback.message.edit_text(
        "💰 Введи сумму взноса (только число, например 150):",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user_data, _ = get_user_data(user_id)
    
    today = date.today()
    total_saved = sum(r["amount"] for r in user_data["records"])
    remaining = TARGET - total_saved
    percent = (total_saved / TARGET) * 100
    
    plan_today = get_daily_plan_for_date(today)
    plan_cumulative = get_plan_total_to_date(today)
    diff = total_saved - plan_cumulative
    
    # Прогресс-бар (10 символов)
    bar_len = 10
    filled = int(bar_len * total_saved / TARGET)
    bar = "█" * filled + "░" * (bar_len - filled)
    
    text = (
        f"📊 **Статистика**\n\n"
        f"Накоплено: {format_amount(total_saved)} / {format_amount(TARGET)}\n"
        f"Прогресс: {bar} {percent:.1f}%\n"
        f"Осталось: {format_amount(remaining)}\n\n"
        f"📅 **План на сегодня:** {format_amount(plan_today)}\n"
        f"🎯 Должно быть по плану: {format_amount(plan_cumulative)}\n"
    )
    
    if diff >= 0:
        text += f"✅ Опережение: {format_amount(diff)}"
    else:
        text += f"⚠️ Отставание: {format_amount(abs(diff))}"
    
    # Добавим план по текущему месяцу
    current_month_plan = next((p for p in MONTHLY_PLAN if p[0] == today.month), None)
    if current_month_plan and today.year == 2026:
        _, days, daily = current_month_plan
        text += f"\n\n📆 В этом месяце: {daily} ₽/день (нужно {daily*days} ₽)"
    
    await callback.message.edit_text(text, reply_markup=main_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "history")
async def show_history(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = callback.from_user.id
    user_data, _ = get_user_data(user_id)
    
    records = user_data["records"]
    if not records:
        await callback.message.edit_text("📭 История пуста", reply_markup=main_keyboard())
        await callback.answer()
        return
    
    # Сортируем по дате (новые сверху)
    records_sorted = sorted(records, key=lambda x: x["date"], reverse=True)
    last_10 = records_sorted[:10]
    
    text = "📜 **Последние 10 взносов:**\n\n"
    for r in last_10:
        d = datetime.fromisoformat(r["date"]).strftime("%d.%m")
        text += f"  {d}: {format_amount(r['amount'])}\n"
    
    total = sum(r["amount"] for r in records)
    text += f"\nВсего записей: {len(records)}, всего {format_amount(total)}"
    
    await callback.message.edit_text(text, reply_markup=main_keyboard())
    await callback.answer()

# ---------- Обработчик ввода суммы (только в состоянии waiting_for_amount) ----------
@dp.message(AddMoney.waiting_for_amount, F.text)
async def process_amount(message: types.Message, state: FSMContext):
    # Проверяем, что введено число
    try:
        amount = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Это не число. Введи сумму цифрами (например, 150):")
        return
    
    if amount <= 0:
        await message.answer("❌ Сумма должна быть положительной. Попробуй ещё раз:")
        return
    
    user_id = message.from_user.id
    user_data, _ = get_user_data(user_id)
    
    today_str = date.today().isoformat()
    user_data["records"].append({"date": today_str, "amount": amount})
    save_user_data(user_id, user_data)
    
    total = sum(r["amount"] for r in user_data["records"])
    
    await state.clear()
    await message.answer(
        f"✅ Записано: {format_amount(amount)}\n"
        f"Всего накоплено: {format_amount(total)}",
        reply_markup=main_keyboard()
    )

# ---------- Обработчик всех остальных сообщений ----------
@dp.message()
async def handle_unknown(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Используй кнопки меню.",
            reply_markup=main_keyboard()
        )
    # Если мы в состоянии, но сообщение не подошло под условия (например, пустое), ничего не делаем,
    # потому что process_amount уже показал ошибку.

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())