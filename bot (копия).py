import telebot
from telebot import types
import sqlite3
import threading

TOKEN=""

bot = telebot.TeleBot(TOKEN, parse_mode=None)

DB = "quiz.db"
DEFAULT_QUESTION_TIME = 30
QUESTION_TIME_OPTIONS = (10, 20, 30, 60)
active_questions = {}
active_questions_lock = threading.Lock()


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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            tg_id INTEGER PRIMARY KEY,
            timer_seconds INTEGER NOT NULL DEFAULT 30
        )
    """)
    conn.commit()
    conn.close()

def get_question_time(user_id):
    conn = db()
    row = conn.execute(
        "SELECT timer_seconds FROM user_settings WHERE tg_id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return row[0] if row else DEFAULT_QUESTION_TIME

def set_question_time(user_id, seconds):
    conn = db()
    conn.execute(
        "INSERT INTO user_settings (tg_id, timer_seconds) VALUES (?, ?) "
        "ON CONFLICT(tg_id) DO UPDATE SET timer_seconds = excluded.timer_seconds",
        (user_id, seconds),
    )
    conn.commit()
    conn.close()

def expire_question(chat_id, message_id, user_id):
    key = (chat_id, message_id)
    with active_questions_lock:
        state = active_questions.get(key)
        if not state or state["user_id"] != user_id:
            return
        active_questions.pop(key)

    try:
        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
    except Exception:
        pass
    bot.send_message(chat_id, "⏰ Время вышло! Ответить на этот вопрос уже нельзя.")

def send_question(call, text, markup):
    seconds = get_question_time(call.from_user.id)
    message = bot.send_message(
        call.message.chat.id,
        f"{text}\n\n⏱ На ответ: {seconds} сек.",
        reply_markup=markup,
    )
    key = (message.chat.id, message.message_id)
    timer = threading.Timer(
        seconds, expire_question, args=(message.chat.id, message.message_id, call.from_user.id)
    )
    timer.daemon = True
    with active_questions_lock:
        active_questions[key] = {"user_id": call.from_user.id, "timer": timer}
    timer.start()

def check_question_answer(call):
    key = (call.message.chat.id, call.message.message_id)
    with active_questions_lock:
        state = active_questions.get(key)
        if not state:
            return False
        if state["user_id"] != call.from_user.id:
            return False
        if call.data in CORRECT_ANSWERS:
            active_questions.pop(key)
            state["timer"].cancel()
    return True

CORRECT_ANSWERS = {
    "math_easy_1_4", "math_hard_2_10", "paris", "andorra", "andorra_flag"
}
QUESTION_ANSWERS = CORRECT_ANSWERS | {
    "math_easy_1_5", "math_easy_1_22", "math_hard_2_5", "rome", "berlin",
    "monako", "barcelona", "monako_flag", "spain_flag"
}

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
        types.InlineKeyboardButton("Настройки", callback_data="settings"),
    )
    bot.send_message(
        message.chat.id,
        f"Привет, {name}! Добро пожаловать в бота с викторинами. "
        "Если хочешь, чтобы здесь появилась новая викторина — пиши мне в ЛС: @arvodev\n", reply_markup=markup
    )

# Все нажатия кнопок
@bot.callback_query_handler(func=lambda call: True)
def on_click(call):
    if call.data in QUESTION_ANSWERS and not check_question_answer(call):
        bot.answer_callback_query(
            call.id,
            "Время вышло, вопрос закрыт или отвечать может только начавший викторину.",
            show_alert=True,
        )
        return

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
        send_question(call, "1. Сколько будет 2 + 2?", markup)
    elif call.data == "math_hard":
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("10", callback_data="math_hard_2_10"),
            types.InlineKeyboardButton("5", callback_data="math_hard_2_5"),
        )
        send_question(call, "2. Сколько будет 5 × 2?", markup)
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
        send_question(call, "1. Какая столица Франции?", markup)
    elif call.data == "capitals_hard":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Андорра-ла-Велья", callback_data="andorra"),
            types.InlineKeyboardButton("Монако", callback_data="monako"),
            types.InlineKeyboardButton("Барселона", callback_data="barcelona"),
        )
        send_question(call, "2. Какая столица Андорры?", markup)
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
        send_question(call, "1. Какой флаг у Андорры?", markup)
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
    elif call.data == "settings":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Изменить время на вопрос", callback_data="timer"),
            types.InlineKeyboardButton("Назад", callback_data="start"),
        )
        seconds = get_question_time(call.from_user.id)
        bot.send_message(
            call.message.chat.id,
            f"Настройки:\nВремя на вопрос: {seconds} сек.",
            reply_markup=markup,
        )
    elif call.data == "timer":
        markup = types.InlineKeyboardMarkup(row_width=2)
        for seconds in QUESTION_TIME_OPTIONS:
            markup.add(types.InlineKeyboardButton(
                f"{seconds} сек.", callback_data=f"timer_set_{seconds}"
            ))
        markup.add(types.InlineKeyboardButton("Назад к настройкам", callback_data="settings"))
        bot.send_message(call.message.chat.id, "Выбери время на каждый вопрос:", reply_markup=markup)
    elif call.data.startswith("timer_set_"):
        try:
            seconds = int(call.data[len("timer_set_"):])
        except ValueError:
            seconds = None
        if seconds in QUESTION_TIME_OPTIONS:
            set_question_time(call.from_user.id, seconds)
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("Изменить время на вопрос", callback_data="timer"),
                types.InlineKeyboardButton("Назад", callback_data="start"),
            )
            bot.send_message(
                call.message.chat.id,
                f"Настройки сохранены. Время на вопрос: {seconds} сек.",
                reply_markup=markup,
            )
    elif call.data == "start":
        welcome(call.message)
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

