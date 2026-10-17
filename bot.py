# Это твой первый Telegram-бот на pyTelegramBotAPI (telebot).
# Как запустить:
#   quizbot
# или:
#   run ~/Документы/Программирование/"Тестовые скрипты"/Python/telebot/Викторины

import telebot
from telebot import types

TOKEN="8676195348:AAGg8Crv6uWu6-wPse3efyV5zFrO6RKYkK8"

bot = telebot.TeleBot(TOKEN, parse_mode=None)


# /start
@bot.message_handler(commands=["start"])
def welcome(message):
    name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("Математика", callback_data="math"),
        types.InlineKeyboardButton("Столицы стран", callback_data="capitals"),
        types.InlineKeyboardButton("Флаги стран", callback_data="flags"),
    )
    bot.send_message(
        message.chat.id,
        f"Привет, {name}! Добро пожаловать в бота с викторинами. "
        "Если хочешь, чтобы здесь появилась новая викторина — пиши мне в ЛС: @artyom20081\n", reply_markup=markup
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
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по математике.")
    elif call.data == "math_easy_1_5":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "math_easy_1_22":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "math_hard_2_10":
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по математике.")
    elif call.data == "math_hard_2_5":
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
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "rome":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "berlin":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "andorra":
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "monako":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "barcelona":
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
        bot.send_message(call.message.chat.id, "Верно! Ты прошёл викторину по столицам стран.")
    elif call.data == "monako_flag":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    elif call.data == "spain_flag":
        bot.send_message(call.message.chat.id, "Неверно. Попробуй ещё раз")
    bot.answer_callback_query(call.id)


# Любое текстовое сообщение
@bot.message_handler(content_types="text")
def echo(message):
    bot.send_message(
        message.chat.id,
        "Ты либо опечатался, либо такой викторины ещё нету в боте. "
        "Если хочешь предложить викторину, пиши мне в ЛС: @artyom20081"
    )


if __name__ == "__main__":
    print("Бот запущен. Ctrl+C чтобы остановить.")
    bot.infinity_polling()

