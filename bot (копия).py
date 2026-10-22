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

QUIZZES = {
    "math_easy": {
        "title": "Математика — легко",
        "questions": [
            ("Сколько будет 2 + 2?", ["4", "5", "22"], 0),
            ("Сколько будет 10 − 3?", ["6", "7", "8"], 1),
            ("Сколько будет 3 × 3?", ["6", "9", "12"], 1),
            ("Чему равна половина от 20?", ["5", "10", "15"], 1),
            ("Сколько будет 15 + 6?", ["20", "21", "22"], 1),
        ],
    },
    "math_hard": {
        "title": "Математика — сложно",
        "questions": [
            ("Сколько будет 5 × 2?", ["10", "5", "25"], 0),
            ("Чему равно 12²?", ["124", "144", "122"], 1),
            ("Сколько будет 81 ÷ 9?", ["8", "9", "10"], 1),
            ("Реши уравнение: 3x = 27", ["7", "8", "9"], 2),
            ("Сколько будет 7 × 8 − 6?", ["50", "56", "62"], 0),
        ],
    },
    "capitals_easy": {
        "title": "Столицы стран — легко",
        "questions": [
            ("Какая столица Франции?", ["Париж", "Рим", "Берлин"], 0),
            ("Какая столица Италии?", ["Мадрид", "Рим", "Лиссабон"], 1),
            ("Какая столица Германии?", ["Вена", "Прага", "Берлин"], 2),
            ("Какая столица Японии?", ["Токио", "Пекин", "Сеул"], 0),
            ("Какая столица Канады?", ["Торонто", "Оттава", "Ванкувер"], 1),
        ],
    },
    "capitals_hard": {
        "title": "Столицы стран — сложно",
        "questions": [
            ("Какая столица Андорры?", ["Андорра-ла-Велья", "Монако", "Барселона"], 0),
            ("Какая столица Бутана?", ["Катманду", "Тхимпху", "Дакка"], 1),
            ("Какая столица Молдовы?", ["Кишинёв", "Бухарест", "София"], 0),
            ("Какая столица Мадагаскара?", ["Антананариву", "Мапуту", "Лусака"], 0),
            ("Какая столица Словении?", ["Загреб", "Любляна", "Братислава"], 1),
        ],
    },
    "flags": {
        "title": "Флаги стран",
        "questions": [
            ("Какой флаг у Андорры?", ["🇦🇩", "🇲🇨", "🇪🇸"], 0),
            ("Какой флаг у Японии?", ["🇨🇳", "🇯🇵", "🇰🇷"], 1),
            ("Какой флаг у Бразилии?", ["🇦🇷", "🇵🇹", "🇧🇷"], 2),
            ("Какой флаг у Канады?", ["🇨🇦", "🇺🇸", "🇬🇧"], 0),
            ("Какой флаг у Греции?", ["🇮🇹", "🇬🇷", "🇫🇮"], 1),
        ],
    },
    "history": {
        "title": "История",
        "questions": [
            ("В каком году началась Вторая мировая война?", ["1939", "1941", "1945"], 0),
            ("Кто был первым президентом США?", ["Джордж Вашингтон", "Томас Джефферсон", "Джон Адамс"], 0),
            ("В каком году была подписана Махачкальская конвенция?", ["1920", "1922", "1924"], 1),
            ("В каком году началась Отечественная война?", ["1939", "1941", "1945"], 1),
            ("Кто был лидером Советского Союза во время Второй мировой войны?", ["Иосиф Сталин", "Владимир Ленин", "Никита Хрущёв"], 0)
        ],
    },
}

active_quizzes = {}

def finish_quiz(chat_id, user_id, quiz_state):
    active_quizzes.pop((chat_id, user_id), None)
    quiz_key = quiz_state["quiz_key"]
    question_count = len(QUIZZES[quiz_key]["questions"])
    bot.send_message(
        chat_id,
        f"Викторина «{QUIZZES[quiz_key]['title']}» завершена! "
        f"Правильных ответов: {quiz_state['score']} из {question_count}.",
    )

def send_quiz_question(chat_id, user_id, quiz_state):
    quiz_key = quiz_state["quiz_key"]
    questions = QUIZZES[quiz_key]["questions"]
    question_index = quiz_state["index"]
    if question_index >= len(questions):
        finish_quiz(chat_id, user_id, quiz_state)
        return

    text, options, _ = questions[question_index]
    markup = types.InlineKeyboardMarkup(row_width=1)
    for option_index, option in enumerate(options):
        markup.add(types.InlineKeyboardButton(
            option, callback_data=f"a|{quiz_key}|{question_index}|{option_index}"
        ))
    seconds = get_question_time(user_id)
    message = bot.send_message(
        chat_id,
        f"{question_index + 1}/{len(questions)}. {text}\n\n⏱ На ответ: {seconds} сек.",
        reply_markup=markup,
    )
    quiz_state["message_id"] = message.message_id
    key = (message.chat.id, message.message_id)
    timer = threading.Timer(
        seconds, expire_question, args=(message.chat.id, message.message_id, user_id)
    )
    timer.daemon = True
    with active_questions_lock:
        active_questions[key] = {
            "user_id": user_id,
            "timer": timer,
            "quiz_key": quiz_key,
            "question_index": question_index,
        }
    timer.start()

def advance_quiz(chat_id, user_id, message_id, timed_out=False, is_correct=False):
    quiz_state = active_quizzes.get((chat_id, user_id))
    if not quiz_state or quiz_state.get("message_id") != message_id:
        return
    if timed_out:
        bot.send_message(chat_id, "⏰ Время вышло! Переходим к следующему вопросу.")
    elif is_correct:
        quiz_state["score"] += 1
    quiz_state["index"] += 1
    send_quiz_question(chat_id, user_id, quiz_state)

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
    advance_quiz(chat_id, user_id, message_id, timed_out=True)

def start_quiz(call, quiz_key):
    quiz_state = {"quiz_key": quiz_key, "index": 0, "score": 0}
    active_quizzes[(call.message.chat.id, call.from_user.id)] = quiz_state
    send_quiz_question(call.message.chat.id, call.from_user.id, quiz_state)

def handle_quiz_answer(call):
    try:
        _, quiz_key, question_index, option_index = call.data.split("|")
        question_index = int(question_index)
        option_index = int(option_index)
    except (ValueError, TypeError):
        return False

    key = (call.message.chat.id, call.message.message_id)
    with active_questions_lock:
        question_state = active_questions.get(key)
        if (not question_state or question_state["user_id"] != call.from_user.id
                or question_state["quiz_key"] != quiz_key
                or question_state["question_index"] != question_index):
            return False
        quiz_state = active_quizzes.get((call.message.chat.id, call.from_user.id))
        if not quiz_state or quiz_state.get("message_id") != call.message.message_id:
            return False
        active_questions.pop(key)
        question_state["timer"].cancel()

    question = QUIZZES[quiz_key]["questions"][question_index]
    if option_index < 0 or option_index >= len(question[1]):
        return False
    is_correct = option_index == question[2]
    category_id = list(QUIZZES).index(quiz_key) + 1
    save_answer(call, category_id * 1000 + question_index * 10 + option_index, is_correct)
    bot.answer_callback_query(call.id, "Верно!" if is_correct else "Неверно")
    advance_quiz(call.message.chat.id, call.from_user.id, call.message.message_id,
                 is_correct=is_correct)
    return True

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
        types.InlineKeyboardButton("История", callback_data="history"),
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
    if call.data.startswith("a|"):
        if not handle_quiz_answer(call):
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
    elif call.data in ("math_easy", "math_hard"):
        start_quiz(call, call.data)
    elif call.data == "capitals":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("Легко", callback_data="capitals_easy"),
            types.InlineKeyboardButton("Сложно", callback_data="capitals_hard"),
        )
        bot.send_message(call.message.chat.id, "Выбери уровень сложности", reply_markup=markup)
    elif call.data in ("capitals_easy", "capitals_hard"):
        start_quiz(call, call.data)
    elif call.data == "flags":
        start_quiz(call, "flags")
    elif call.data == "history":
        start_quiz(call, "history")
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

