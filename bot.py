import random
import time
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- НАСТРОЙКИ ---
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN") 
FILE_NAME = "user.json"
CASE_PRICE = 100
DAILY_BONUS = 5000000

ITEMS_DATA = {
    "⚪ Обычный": {"chance": 60, "price": 15, "items": ["Glock-18 | Candy", "P250 | Sand Dune", "MP9 | Sand Scale", "Nova | Clear Polymer", "MAC-10 | Palm"]},
    "🟢 Редкий": {"chance": 25, "price": 50, "items": ["AK-47 | Elite Build", "M4A4 | Magnesium", "USP-S | Ticket to Hell", "FAMAS | Mecha Industries", "Desert Eagle | Light Rail"]},
    "🔵 Эпический": {"chance": 10, "price": 200, "items": ["AK-47 | Redline", "M4A1-S | Decimator", "AWP | Atheris", "USP-S | Neo-Noir", "Glock-18 | Vogue"]},
    "🟣 Легендарный": {"chance": 4, "price": 800, "items": ["AWP | Hyper Beast", "AK-47 | Neon Rider", "M4A4 | The Emperor", "Desert Eagle | Printstream", "USP-S | Kill Confirmed"]},
    "🟡 Мифический": {"chance": 1, "price": 3000, "items": ["AWP | Dragon Lore", "AK-47 | Fire Serpent", "M4A4 | Howl", "Karambit | Fade", "Butterfly Knife | Doppler"]}
}


# --- РАБОТА С JSON И ПРОФИЛЕМ ---

def load_users():
    if os.path.exists(FILE_NAME) and os.path.getsize(FILE_NAME) > 0:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_users():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(users_db, f, ensure_ascii=False, indent=4)

users_db = load_users()

def get_user_data(user_id: str, nickname: str = "Игрок"):
    """Создает или загружает профиль, сохраняя никнейм и прогресс"""
    if user_id not in users_db:
        users_db[user_id] = {
            "nickname": nickname,      # Запоминаем имя
            "balance": 1000,           # Стартовый баланс
            "inventory": [],           # Инвентарь
            "last_bonus": 0,           # Время бонуса
            "cases_opened": 0          # Прогресс: счетчик открытых кейсов
        }
        save_users()
    return users_db[user_id]

def drop_random_item():
    rarities = list(ITEMS_DATA.keys())
    chances = [ITEMS_DATA[r]["chance"] for r in rarities]
    chosen_rarity = random.choices(rarities, weights=chances, k=1)[0]
    item_name = random.choice(ITEMS_DATA[chosen_rarity]["items"])
    return {"name": item_name, "rarity": chosen_rarity, "price": ITEMS_DATA[chosen_rarity]["price"]}


# --- ИНТЕРФЕЙС ИНВЕНТАРЯ ---

async def show_inventory(update_or_query, user_data) -> None:
    items = user_data["inventory"]
    message = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
    
    if not items:
        await message.reply_text("🎒 Твой инвентарь пуст. Открой пару кейсов!")
        return

    total_sum = sum(item['price'] for item in items)
    items_text = []
    keyboard = []

    for idx, item in enumerate(items):
        item_number = idx + 1
        items_text.append(f"{item_number}. {item['rarity']} <b>{item['name']}</b> — {item['price']} монет")
        keyboard.append([InlineKeyboardButton(f"❌ Продать №{item_number} ({item['price']}💰)", callback_data=f"sell_item_{idx}")])

    keyboard.append([InlineKeyboardButton(f"💸 Продать ВСЁ ({total_sum}💰)", callback_data="sell_all")])
    markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🎒 <b>Твой инвентарь:</b>\n\n" + "\n".join(items_text) + f"\n\n💰 Общая стоимость: <b>{total_sum}</b> монет"
    await message.reply_text(text, parse_mode="HTML", reply_markup=markup)


# --- КОМАНДЫ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    # Берем имя пользователя из Телеграма (first_name)
    user_name = update.message.from_user.first_name 
    get_user_data(user_id, nickname=user_name)
    
    reply_keyboard = [[KeyboardButton("🎮 Играть"), KeyboardButton("👤 Профиль")], [KeyboardButton("🎁 Бонус"), KeyboardButton("ℹ️ Помощь")]]
    reply_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Привет, {user_name}! 🖐 Я бот для открытия кейсов.\nВыбери действие в меню ниже:", reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📜 <b>Команды:</b>\n/start — Главное меню\n/play — Открыть кейсы\n/profile — Мой профиль\n/daily — Бонус", parse_mode="HTML")

async def play_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    inline_markup = InlineKeyboardMarkup([[InlineKeyboardButton(f"📦 Открыть кейс ({CASE_PRICE} монет)", callback_data="open_case")]])
    await update.message.reply_text("Испытай удачу и открой кейс:", reply_markup=inline_markup)

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    # Загружаем данные. Если бота только запустили, берем имя из тг
    user_data = get_user_data(user_id, nickname=update.message.from_user.first_name) 
    
    inline_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🎒 Инвентарь", callback_data="inventory"), InlineKeyboardButton("💰 Баланс", callback_data="balance")]])
    
    await update.message.reply_text(
        f"👤 <b>Профиль игрока: {user_data['nickname']}</b>\n\n"
        f"📈 Прогресс:\n"
        f" └ Открыто кейсов: <b>{user_data.get('cases_opened', 0)}</b>\n"
        f" └ Вещей в инвентаре: <b>{len(user_data['inventory'])}</b>\n\n"
        f"💰 Баланс: <b>{user_data['balance']}</b> монет",
        parse_mode="HTML",
        reply_markup=inline_markup
    )

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    user_data = get_user_data(user_id, nickname=update.message.from_user.first_name)
    current_time = time.time()

    if current_time - user_data["last_bonus"] > 86400:
        user_data["balance"] += DAILY_BONUS
        user_data["last_bonus"] = current_time
        save_users()
        await update.message.reply_text(f"🎁 Ты получил бонус: <b>{DAILY_BONUS}</b> монет!", parse_mode="HTML")
    else:
        await update.message.reply_text("⏳ Ты уже получал бонус. Приходи завтра!")

my_name = "жабо"
my_age = 15
my_hobby = "бэкенд-разработка"

async def about(update, context):
    text = (
        f"Привет! Меня зовут {my_name}.\n"
        f"Мне {my_age} лет.\n"
        f"Моё хобби: {my_hobby}.\n"
        "Меня создал ученик CAP Education"
    )
    await update.message.reply_text(text)


# --- ОБРАБОТЧИКИ ---

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    if text == "🎮 Играть": await play_command(update, context)
    elif text == "👤 Профиль": await profile_command(update, context)
    elif text == "🎁 Бонус": await daily_command(update, context)
    elif text == "ℹ️ Помощь": await help_command(update, context)
    else: await update.message.reply_text("🤔 Я тебя не понял. Воспользуйся меню.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    user_data = get_user_data(user_id, nickname=query.from_user.first_name)

    if query.data == "open_case":
        if user_data["balance"] >= CASE_PRICE:
            user_data["balance"] -= CASE_PRICE
            user_data["cases_opened"] = user_data.get("cases_opened", 0) + 1 # Плюсуем прогресс!
            
            item = drop_random_item()
            user_data["inventory"].append(item)
            save_users()
            
            await query.message.reply_text(
                f"📦 <b>{user_data['nickname']}</b> открыл кейс!\n\n"
                f"Редкость: {item['rarity']}\n🎉 Выпало: <b>{item['name']}</b>\n"
                f"💵 Цена: <code>{item['price']}</code> монет",
                parse_mode="HTML"
            )
        else:
            await query.message.reply_text("❌ Недостаточно монет!")

    elif query.data == "inventory": await show_inventory(query, user_data)
    elif query.data.startswith("sell_item_"):
        idx = int(query.data.split("_")[-1])
        if 0 <= idx < len(user_data["inventory"]):
            sold_item = user_data["inventory"].pop(idx)
            user_data["balance"] += sold_item["price"]
            save_users()
            await query.message.reply_text(f"✅ Продано: <b>{sold_item['name']}</b> за {sold_item['price']}💰", parse_mode="HTML")
            await show_inventory(query, user_data)
        else:
            await query.message.reply_text("❌ Предмет уже продан!")
            
    elif query.data == "sell_all":
        if not user_data["inventory"]:
            await query.message.reply_text("🎒 Пусто!")
        else:
            total_sum = sum(item['price'] for item in user_data["inventory"])
            user_data["balance"] += total_sum
            user_data["inventory"] = []
            save_users()
            await query.message.reply_text(f"✅ Всё продано! Получено: <b>+{total_sum}</b>💰", parse_mode="HTML")
            
    elif query.data == "balance":
        await query.message.reply_text(f"💰 Баланс: {user_data['balance']} монет.")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("❌ Неизвестная команда.")

def main() -> None:
    application = Application.builder().token(TOKEN).connect_timeout(30).read_timeout(30).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("play", play_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("daily", daily_command))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(CommandHandler("about", about)) 

    print("Бот с сохранением профиля и прогресса запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()