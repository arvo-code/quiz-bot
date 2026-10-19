import telebot
from telebot import types
import sqlite3

TOKEN=""

bot = telebot.TeleBot(TOKEN, parse_mode=None)

DB = "quiz.db"


# ==================== БАЗА ДАННЫХ ====================
# Правило: открыл (db()) -> запрос -> commit() -> close()

def db():
    return sqlite3.connect(DB)

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            tg_id INTEGER PRIMARY KEY,
            name TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            answer_id INTEGER,
            is_correct BOOLEAN
        )
    """)
    conn.commit()
    conn.close()

def save_answer(call, answer_id, is_correct):
    user = call.from_user
    name = f"@{user.username}" if user.username else user.first_name
    conn = db()
    conn.execute(
        "INSERT INTO users (tg_id, name) VALUES (?, ?) "
        "ON CONFLICT(tg_id) DO UPDATE SET name = excluded.name",
        (user.id, name),
    )
    conn.execute(
        "INSERT INTO user_answers (user_id, answer_id, is_correct) VALUES (?, ?, ?)",
        (user.id, answer_id, is_correct),
    )
    conn.commit()
    conn.close()

def send_leaderboard(chat_id):
    conn = db()
    leaderboard = conn.execute("""
        SELECT COALESCE(users.name, 'Игрок ' || scores.user_id), scores.score
        FROM (
            SELECT user_id, COUNT(*) AS score
            FROM user_answers
            WHERE is_correct = 1
            GROUP BY user_id
        ) AS scores
        LEFT JOIN users ON users.tg_id = scores.user_id
        ORDER BY scores.score DESC, users.name COLLATE NOCASE ASC
        LIMIT 10
    """).fetchall()
    conn.close()

    if not leaderboard:
        bot.send_message(chat_id, "Таблица лидеров пока пуста. Ответь правильно на вопрос, чтобы попасть в рейтинг!")
        return

    leaderboard_text = "\n".join(
        f"{place}. {name} — {score} балл(ов)"
        for place, (name, score) in enumerate(leaderboard, start=1)
    )
    bot.send_message(chat_id, f"🏆 Таблица лидеров:\n{leaderboard_text}")

# /start
@bot.message_handler(commands=["start"])
def welcome(message):
    name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Математика", callback_data="math"),
        types.InlineKeyboardButton("Столицы стран", callback_data="capitals"),
        types.InlineKeyboardButton("Флаги стран", callback_data="flags"),
        types.InlineKeyboardButton("Таблица лидеров", callback_data="leaderboard"),
    )
    bot.send_message(
        message.chat.id,
        f"Привет, {name}! Добро пожаловать в бота с викторинами. "
        "Если хочешь, чтобы здесь появилась новая викторина — пиши мне в ЛС: @arvodev\n", reply_markup=markup
    )

# Все нажатия кнопок
@bot.callback_query_handler(func=lambda call: True)
def on_click(call):
    if call.data == "math":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Легко", callback_data="math_easy"),
            types.InlineKeyboardButton("Сложно", callback_data="math_hard"),
        )
        bot.send_message(call.message.chat.id, "Выбери уровень сложности", reply_markup=markup)
    elif call.data == "math_easy":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("4", callback_data="math_easy_1_4"),
            types.InlineKeyboardButton("5", callback_data="math_easy_1_5"),
            types.InlineKeyboardButton("22", callback_data="math_easy_1_22"),
        )
        bot.send_message(call.message.chat.id, "1. Сколько будет 2 + 2?", reply_markup=markup)
    elif call.data == "math_hard":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("10", callback_data="math_hard_2_10"),
            types.InlineKeyboardButton("5", callback_data="math_hard_2_5"),
        )
        bot.send_message(call.message.chat.id, "2. Сколько будет 5 × 2?", reply_markup=markup)
    elif call.data == "math_easy_1_4":
        save_answer(call, 4, True)
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по математике.")
    elif call.data == "math_easy_1_5":
        save_answer(call, 5, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "math_easy_1_22":
        save_answer(call, 22, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "math_hard_2_10":
        save_answer(call, 10, True)
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по математике.")
    elif call.data == "math_hard_2_5":
        save_answer(call, 5, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    if call.data == "capitals":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Легко", callback_data="capitals_easy"),
            types.InlineKeyboardButton("Сложно", callback_data="capitals_hard"),
        )
        bot.send_message(call.message.chat.id, "Выбери уровень сложности", reply_markup=markup)
    elif call.data == "capitals_easy":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Париж", callback_data="paris"),
            types.InlineKeyboardButton("Рим", callback_data="rome"),
            types.InlineKeyboardButton("Берлин", callback_data="berlin"),
        )
        bot.send_message(call.message.chat.id, "1. Какая столица Франции?", reply_markup=markup)
    elif call.data == "capitals_hard":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Андорра-ла-Велья", callback_data="andorra"),
            types.InlineKeyboardButton("Монако", callback_data="monako"),
            types.InlineKeyboardButton("Барселона", callback_data="barcelona"),
        )
        bot.send_message(call.message.chat.id, "2. Какая столица Андорры?", reply_markup=markup)
    elif call.data == "paris":
        save_answer(call, 4, True)
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "rome":
        save_answer(call, 5, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "berlin":
        save_answer(call, 6, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "andorra":
        save_answer(call, 7, True)
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "monako":
        save_answer(call, 8, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "barcelona":
        save_answer(call, 9, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "flags":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🇦🇩", callback_data="andorra_flag"),
            types.InlineKeyboardButton("🇲🇨", callback_data="monako_flag"),
            types.InlineKeyboardButton("🇪🇸", callback_data="spain_flag"),
        )
        bot.send_message(call.message.chat.id, "1. Какой флаг у Андорры?", reply_markup=markup)
    elif call.data == "andorra_flag":
        save_answer(call, 11, True)
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "monako_flag":
        save_answer(call, 12, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "spain_flag":
        save_answer(call, 13, False)
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "leaderboard":
        send_leaderboard(call.message.chat.id)
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=["leaderboard"])
def leaderboard_command(message):
    send_leaderboard(message.chat.id)


# Любое текстовое сообщение
@bot.message_handler(content_types="text")
def echo(message):
    bot.send_message(
        message.chat.id,
        "Ты либо опечатался, либо такой викторины ещё нету в боте. "
        "Если хочешь предложить викторину, пиши мне в ЛС: @arvodev"
    )


if __name__ == "__main__":
    init_db()
    print("Бот запущен. Ctrl+C чтобы остановить.")
    bot.infinity_polling()

