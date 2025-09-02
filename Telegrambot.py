import sqlite3
import telebot
from telebot import types
import re

TOKEN = '7970205116:AAEQCTUQaTJb-YxXSyW_gd3-uSi_Iz_AQd0'
CHANNEL = '@organizerandphotokids'
GROUP_CHAT_ID = -1002735056666

bot = telebot.TeleBot(TOKEN, parse_mode='Markdown')

conn = sqlite3.connect('botdata.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS castings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
''')
conn.commit()

cursor.execute('SELECT COUNT(*) FROM castings')
if cursor.fetchone()[0] == 0:
    initial_castings = ["Кастинг Весна 2026", "Кастинг Осень 2025", "Новогодний Кастинг 2026"]
    cursor.executemany('INSERT INTO castings (name) VALUES (?)', [(c,) for c in initial_castings])
    conn.commit()

def get_castings():
    cursor.execute('SELECT name FROM castings ORDER BY id')
    return [row[0] for row in cursor.fetchall()]

STATE_WAITING_CASTING = 'waiting_casting'
STATE_WAITING_NAME = 'waiting_name'
STATE_WAITING_LASTNAME = 'waiting_lastname'
STATE_WAITING_AGE = 'waiting_age'
STATE_WAITING_HEIGHT = 'waiting_height'
STATE_WAITING_SHOESIZE = 'waiting_shoesize'
STATE_WAITING_CITY = 'waiting_city'
STATE_WAITING_PORTFOLIO = 'waiting_portfolio'
STATE_WAITING_PHOTOS = 'waiting_photos'
STATE_SUPPORT_MODE = 'support_mode'

user_data = {}
user_state = {}
user_message_ids = {}

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def send_subscription_request(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_sub = types.InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL.strip('@')}")
    btn_check = types.InlineKeyboardButton("Проверить подписку", callback_data="check_subscription")
    markup.add(btn_sub, btn_check)
    bot.send_message(chat_id, "Для использования бота подпишитесь на канал и нажмите Проверить подписку.", reply_markup=markup)

def format_application(data, username=None, user_id=None):
    def italic(text):
        return f"_{text}_"
    if username:
        user_link = f"[@{username}](https://t.me/{username})"
    elif user_id:
        user_link = f"[Пользователь](tg://user?id={user_id})"
    else:
        user_link = "_Неизвестный_"
    return (
        f"Заявка от {user_link}:\n"
        f"Имя: {italic(data.get('name', ''))}\n"
        f"Фамилия: {italic(data.get('lastname', ''))}\n"
        f"Возраст: {italic(data.get('age', ''))}\n"
        f"Рост: {italic(data.get('height', ''))}\n"
        f"Размер обуви: {italic(data.get('shoesize', ''))}\n"
        f"Город: {italic(data.get('city', ''))}\n"
        f"Портфолио: {italic(data.get('portfolio', ''))}\n"
        f"Кастинг: {italic(data.get('casting', ''))}\n"
    )

def valid_name(t): return bool(re.fullmatch(r'[A-Za-zА-Яа-яЁё\-]+', t.strip()))
def valid_age(t): return bool(re.fullmatch(r'\d{1,2}', t.strip()))
def valid_height(t): return bool(re.fullmatch(r'\d{1,3}', t.strip()))
def valid_shoesize(t): return bool(re.fullmatch(r'\d{2}', t.strip()))
def valid_city(t): return bool(re.fullmatch(r'([A-Za-zА-Яа-яЁё\-]+\s?){1,3}', t.strip()))
def valid_portfolio(t): return bool(re.fullmatch(r'https?://\S+', t.strip()))

def get_quick_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🏁 Начать", "🔄 Обновить", "❓ Проблема")
    return kb

def build_casting_buttons():
    kb = types.InlineKeyboardMarkup(row_width=1)
    for c in get_castings():
        kb.add(types.InlineKeyboardButton(c, callback_data=f"cast_{c}"))
    return kb

def save_msg(chat_id, msg_id):
    if chat_id not in user_message_ids:
        user_message_ids[chat_id] = []
    user_message_ids[chat_id].append(msg_id)

def clear_msgs(chat_id):
    for msg_id in user_message_ids.get(chat_id, []):
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    user_message_ids[chat_id] = []

@bot.message_handler(commands=['start'])
def start_handler(m):
    chat_id = m.chat.id
    user_state[chat_id] = None
    user_data[chat_id] = {}
    user_message_ids[chat_id] = []
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    sent = bot.send_message(chat_id, "Добро пожаловать! Нажмите 'Начать' для подачи заявки.", reply_markup=get_quick_keyboard())
    save_msg(chat_id, sent.message_id)

@bot.message_handler(func=lambda m: m.text == "🏁 Начать")
def start_fill(m):
    chat_id = m.chat.id
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    user_state[chat_id] = STATE_WAITING_CASTING
    clear_msgs(chat_id)
    sent = bot.send_message(chat_id, "Выберите кастинг:", reply_markup=build_casting_buttons())
    save_msg(chat_id, sent.message_id)

@bot.message_handler(func=lambda m: m.text == "🔄 Обновить")
def refresh_menu(m):
    chat_id = m.chat.id
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    sent = bot.send_message(chat_id, "Обновлено! Выберите кастинг:", reply_markup=build_casting_buttons())
    save_msg(chat_id, sent.message_id)

@bot.message_handler(func=lambda m: m.text == "❓ Проблема")
def problem_start(m):
    chat_id = m.chat.id
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    user_state[chat_id] = STATE_SUPPORT_MODE
    bot.send_message(chat_id, "Опишите вашу проблему или вопрос. Ваше сообщение будет отправлено в поддержку.")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_SUPPORT_MODE)
def handle_support_message(m):
    chat_id = m.chat.id
    username = m.from_user.username or f"user_{chat_id}"
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    try:
        bot.send_message(GROUP_CHAT_ID, f"📩 Сообщение поддержки от [{username}](tg://user?id={chat_id}):\n{m.text}", parse_mode="Markdown")
        bot.send_message(chat_id, "Сообщение отправлено в поддержку. Спасибо!")
    except Exception:
        bot.send_message(chat_id, "Ошибка отправки. Пожалуйста, попробуйте позже.")
    user_state[chat_id] = None
    clear_msgs(chat_id)
    sent = bot.send_message(chat_id, "Выберите кастинг:", reply_markup=build_casting_buttons())
    save_msg(chat_id, sent.message_id)
    user_state[chat_id] = STATE_WAITING_CASTING

@bot.callback_query_handler(func=lambda c: True)
def callback_handler(c):
    chat_id = c.message.chat.id
    data = c.data

    if data == "check_subscription":
        if check_subscription(c.from_user.id):
            bot.answer_callback_query(c.id, "Подписка подтверждена!")
            sent = bot.send_message(chat_id, "Теперь можете заполнить заявку.", reply_markup=get_quick_keyboard())
            save_msg(chat_id, sent.message_id)
        else:
            bot.answer_callback_query(c.id, "Вы не подписаны на канал.", show_alert=True)
        return

    if data.startswith("cast_"):
        if not check_subscription(c.from_user.id):
            send_subscription_request(chat_id)
            bot.answer_callback_query(c.id)
            return
        cast_name = data[5:]
        user_data[chat_id]['casting'] = cast_name
        user_state[chat_id] = STATE_WAITING_NAME
        clear_msgs(chat_id)
        msg1 = bot.send_message(chat_id, "Вот ваша заявка (будет формироваться здесь):")
        msg2 = bot.send_message(chat_id, "*Введите имя:*")
        user_data[chat_id]['application_message_id'] = msg1.message_id
        save_msg(chat_id, msg1.message_id)
        save_msg(chat_id, msg2.message_id)
        user_data[chat_id]['last_prompt_id'] = msg2.message_id
        bot.answer_callback_query(c.id)

def try_process_input(message, field, validate_func):
    chat_id = message.chat.id
    if not check_subscription(message.from_user.id):
        send_subscription_request(chat_id)
        return False
    bot.delete_message(chat_id, message.message_id)
    if validate_func and not validate_func(message.text):
        return False
    user_data.setdefault(chat_id, {})
    user_data[chat_id][field] = message.text.strip()
    update_application(chat_id)
    return True

def update_application(chat_id):
    data = user_data.get(chat_id, {})
    user = bot.get_chat(chat_id)
    username = user.username if user.username else None
    text = format_application(data, username=username, user_id=chat_id)
    app_msg_id = user_data.get(chat_id, {}).get('application_message_id')
    if app_msg_id:
        bot.edit_message_text(chat_id=chat_id, message_id=app_msg_id, text=text, parse_mode='Markdown')

def send_next_prompt(chat_id, prompt):
    msg = bot.send_message(chat_id, f"*{prompt}*")
    user_data[chat_id]['last_prompt_id'] = msg.message_id
    save_msg(chat_id, msg.message_id)

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_NAME)
def process_name(m):
    if try_process_input(m, 'name', valid_name):
        user_state[m.chat.id] = STATE_WAITING_LASTNAME
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите фамилию:")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_LASTNAME)
def process_lastname(m):
    if try_process_input(m, 'lastname', valid_name):
        user_state[m.chat.id] = STATE_WAITING_AGE
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите возраст:")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_AGE)
def process_age(m):
    if try_process_input(m, 'age', valid_age):
        user_state[m.chat.id] = STATE_WAITING_HEIGHT
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите рост:")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_HEIGHT)
def process_height(m):
    if try_process_input(m, 'height', valid_height):
        user_state[m.chat.id] = STATE_WAITING_SHOESIZE
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите размер обуви:")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_SHOESIZE)
def process_shoesize(m):
    if try_process_input(m, 'shoesize', valid_shoesize):
        user_state[m.chat.id] = STATE_WAITING_CITY
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите город (до 3 слов):")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_CITY)
def process_city(m):
    if try_process_input(m, 'city', valid_city):
        user_state[m.chat.id] = STATE_WAITING_PORTFOLIO
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        send_next_prompt(m.chat.id, "Введите ссылку на портфолио:")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == STATE_WAITING_PORTFOLIO)
def process_portfolio(m):
    if try_process_input(m, 'portfolio', valid_portfolio):
        bot.delete_message(m.chat.id, user_data[m.chat.id]['last_prompt_id'])
        user_state[m.chat.id] = STATE_WAITING_PHOTOS
        send_next_prompt(m.chat.id, "Прикрепите коллаж из 6 фото (фото или документ):")

@bot.message_handler(content_types=['photo', 'document'])
def process_photos(m):
    chat_id = m.chat.id
    if user_state.get(chat_id) != STATE_WAITING_PHOTOS:
        return
    if not check_subscription(m.from_user.id):
        send_subscription_request(chat_id)
        return
    if m.content_type == 'photo':
        file_id = m.photo[-1].file_id
    elif m.content_type == 'document' and m.document.mime_type.startswith('image/'):
        file_id = m.document.file_id
    else:
        bot.send_message(chat_id, "Пожалуйста, пришлите изображение или документ с коллажем.")
        return
    user_data[chat_id]['file_id'] = file_id
    bot.delete_message(chat_id, m.message_id)
    bot.delete_message(chat_id, user_data[chat_id]['last_prompt_id'])

    clear_msgs(chat_id)

    data = user_data[chat_id]
    user = bot.get_chat(chat_id)
    username = user.username if user.username else None
    app_text = format_application(data, username=username, user_id=chat_id)

    bot.send_photo(chat_id, file_id, caption=app_text, parse_mode='Markdown')

    try:
        bot.send_photo(GROUP_CHAT_ID, file_id, caption=app_text, parse_mode='Markdown')
    except Exception as e:
        print(f"Ошибка отправки в группу: {e}")

    bot.send_message(chat_id, "✅ Ваша заявка принята! Спасибо!")

    user_data.pop(chat_id, None)
    user_state.pop(chat_id, None)
    user_message_ids.pop(chat_id, None)

@bot.message_handler(commands=['admin'])
def admin_handler(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Админский режим временно отключён. Изменение кастингов пока недоступно.")

bot.infinity_polling()
