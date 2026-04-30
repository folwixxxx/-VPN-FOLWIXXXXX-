import os
import requests
import time
import base64
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from threading import Thread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, BotCommand, BotCommandScopeDefault, WebAppInfo
from flask import Flask, request, Response

# ==================== ТОКЕНЫ ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"
TON_WALLET = os.environ.get("TON_WALLET")
TON_API_KEY = os.environ.get("TON_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_change_me_12345")

# ==================== ЦЕНЫ ====================
PRICES = {
    30: {"ton": 2.0, "stars": 200, "balance": 200},
    60: {"ton": 3.5, "stars": 350, "balance": 350},
    90: {"ton": 5.0, "stars": 500, "balance": 500}
}

# ==================== КАНАЛ ====================
REQUIRED_CHANNEL = "folwixxxvpn"
CHANNEL_URL = f"https://t.me/{REQUIRED_CHANNEL}"

# ==================== ПРОВЕРКА ====================
if not all([TELEGRAM_TOKEN, GITHUB_TOKEN, GITHUB_REPO, TON_WALLET, TON_API_KEY]):
    raise Exception("❌ Ошибка: не все переменные окружения заданы!")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = telebot.TeleBot(TELEGRAM_TOKEN)
pending_payments = {}

YOUR_ADMIN_ID = 8684879669
YOUR_USERNAME = "ylvvvl"

BANNER_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/banner.jpg"
LOCATIONS_IMAGE_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/locations.jpg"

# ==================== ФУНКЦИИ ====================
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(f"@{REQUIRED_CHANNEL}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def require_subscription(func):
    def wrapper(message):
        if not is_subscribed(message.from_user.id):
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📢 Подписаться", url=CHANNEL_URL))
            keyboard.add(InlineKeyboardButton("✅ Подписался", callback_data="check_subscription"))
            bot.send_message(message.chat.id, "❌ **Доступ ограничен!**\n\nПодпишитесь на канал.", reply_markup=keyboard, parse_mode='Markdown')
            return
        return func(message)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    if is_subscribed(call.from_user.id):
        bot.edit_message_text("✅ Спасибо! Введите /start", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Подписка подтверждена!")
    else:
        bot.answer_callback_query(call.id, "Вы не подписаны!", show_alert=True)

def generate_user_token(user_id, expiry_timestamp):
    return hashlib.md5(f"{user_id}_{expiry_timestamp}_{SECRET_KEY}".encode()).hexdigest()[:32]

def verify_user_token(user_id, token, expiry_timestamp):
    return hmac.compare_digest(generate_user_token(user_id, expiry_timestamp), token)

def ensure_folder(folder_path):
    url = f"{API_BASE}/contents/{folder_path}/.gitkeep"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    data = {"message": f"Create folder {folder_path}", "content": base64.b64encode(b"").decode('utf-8')}
    resp = requests.put(url, headers=headers, json=data)
    return resp.status_code in [200, 201, 409]

def github_upload_file(filename, content, folder=""):
    full_path = f"{folder}/{filename}" if folder else filename
    url = f"{API_BASE}/contents/{full_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    data = {"message": f"Create/Update {full_path}", "content": content_b64}
    result = requests.put(url, headers=headers, json=data)
    
    if result.status_code == 409:
        get_resp = requests.get(url, headers=headers)
        if get_resp.status_code == 200:
            data["sha"] = get_resp.json()["sha"]
            result = requests.put(url, headers=headers, json=data)
    
    return result.status_code in [200, 201]

def github_get_file_content(filepath):
    url = f"{API_BASE}/contents/{filepath}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        return base64.b64decode(resp.json()["content"]).decode('utf-8')
    except:
        return None

def get_all_users():
    content = github_get_file_content("users.json")
    if not content:
        return []
    try:
        return json.loads(content)
    except:
        return []

def save_user(user_id):
    users = get_all_users()
    if user_id not in users:
        users.append(user_id)
        github_upload_file("users.json", json.dumps(users, indent=2), "")
        return True
    return False

def get_template_content():
    content = github_get_file_content("all-sub.txt")
    if not content:
        try:
            resp = requests.get(f"{RAW_BASE}/all-sub.txt", timeout=10)
            if resp.status_code == 200:
                return resp.text
        except:
            pass
        return None
    return content

def create_subscription(user_id, days):
    ensure_folder("subscriptions/all-sub")
    
    filename = f"user_{user_id}"
    folder = "all-sub"
    
    template = get_template_content()
    if not template:
        print(f"❌ Не удалось получить шаблон all-sub.txt")
        return None
    
    expiry_timestamp = int((datetime.now() + timedelta(days=days)).timestamp())
    expiry_date_str = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    
    config_content = template.replace("❀VPN USER❀", f"ALL-SUB {user_id}")
    config_content += f"\n# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    config_content += f"# Expires: {expiry_date_str}\n"
    config_content += f"# Days: {days}\n"
    
    header = f"""#subscription-userinfo: upload=0; download=0; total=0; expire={expiry_timestamp}
# profile-title: ALL-SUB {user_id}
# profile-update-interval: 1440
# expire: {expiry_date_str}
# days: {days}
# created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    full_content = header + config_content
    
    success1 = github_upload_file(f"{filename}.txt", full_content, f"subscriptions/{folder}")
    success2 = github_upload_file(f"{filename}.expiry", str(expiry_timestamp), f"subscriptions/{folder}")
    github_upload_file(f"{filename}.type", "all", f"subscriptions/{folder}")
    
    if not (success1 and success2):
        return None
    
    token = generate_user_token(user_id, expiry_timestamp)
    return f"{RAW_BASE}/subscriptions/{folder}/{filename}.txt?token={token}&t={int(time.time())}"

def get_user_subscription_info(user_id):
    content = github_get_file_content(f"subscriptions/all-sub/user_{user_id}.expiry")
    if content:
        try:
            ts = int(content.strip())
            now = int(time.time())
            if now > ts:
                return None, None, None
            days = (ts - now) // 86400
            date = datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M:%S")
            token = generate_user_token(user_id, ts)
            link = f"{RAW_BASE}/subscriptions/all-sub/user_{user_id}.txt?token={token}&t={int(time.time())}"
            return days, date, link
        except:
            return None, None, None
    return None, None, None

# ==================== БАЛАНС ====================
def get_balance(user_id):
    ensure_folder("balances")
    content = github_get_file_content(f"balances/balance_{user_id}.json")
    if not content:
        return 0
    try:
        return json.loads(content).get("balance", 0)
    except:
        return 0

def update_balance(user_id, amount):
    current = get_balance(user_id)
    new_balance = current + amount
    data = {"user_id": user_id, "balance": new_balance, "updated": datetime.now().isoformat()}
    ok = github_upload_file(f"balance_{user_id}.json", json.dumps(data, indent=2), "balances")
    return ok, new_balance

def deduct_balance(user_id, amount):
    current = get_balance(user_id)
    if current < amount:
        return False, current
    new_balance = current - amount
    data = {"user_id": user_id, "balance": new_balance, "updated": datetime.now().isoformat()}
    ok = github_upload_file(f"balance_{user_id}.json", json.dumps(data, indent=2), "balances")
    if ok:
        return True, new_balance
    return False, current

# ==================== TON & STARS ====================
def check_ton_transaction(amount_ton, user_id):
    try:
        resp = requests.get("https://toncenter.com/api/v2/getTransactions", params={"address": TON_WALLET, "limit": 20, "api_key": TON_API_KEY}, timeout=30)
        data = resp.json()
        if not data.get("ok"):
            return False
        for tx in data.get("result", []):
            in_msg = tx.get("in_msg", {})
            if in_msg.get("destination") != TON_WALLET:
                continue
            if int(in_msg.get("value", 0)) / 1e9 >= amount_ton - 0.05:
                return True
    except:
        pass
    return False

def monitor_payment(user_id, amount_ton, days):
    start = time.time()
    while time.time() - start < 600:
        if check_ton_transaction(amount_ton, user_id):
            bot.send_message(user_id, f"✅ Оплата {amount_ton} TON получена!")
            link = create_subscription(user_id, days)
            if link:
                bot.send_message(user_id, f"✅ **Подписка ALL-SUB создана!**\n\n🔗 {link}\n\n📅 {days} дней")
                bot.send_message(YOUR_ADMIN_ID, f"✅ ОПЛАТА TON\n👤 {user_id}\n💰 {amount_ton} TON\n📅 {days}д")
            else:
                bot.send_message(user_id, "❌ Ошибка при создании")
            return True
        time.sleep(15)
    bot.send_message(user_id, "⏰ Время оплаты истекло")
    return False

def send_stars_invoice(user_id, days, stars_amount):
    try:
        bot.send_invoice(user_id, f"⭐ ALL-SUB {days}д", f"Подписка на {days} дней", f"stars_{days}_{stars_amount}", "", "XTR", [LabeledPrice("ALL-SUB", stars_amount)], start_parameter="vpn_sub", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton(f"⭐ Оплатить {stars_amount} Stars", pay=True)))
        return True
    except:
        return False

@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    parts = message.successful_payment.invoice_payload.split('_')
    if len(parts) >= 3 and parts[0] == "stars":
        days = int(parts[1])
        link = create_subscription(message.from_user.id, days)
        if link:
            bot.send_message(message.from_user.id, f"✅ **Подписка ALL-SUB создана!**\n\n🔗 {link}\n\n📅 {days} дней")
            bot.send_message(YOUR_ADMIN_ID, f"⭐ ОПЛАТА STARS\n👤 {message.from_user.id}\n⭐ {parts[2]}\n📅 {days}д")

# ==================== КНОПКИ И КОМАНДЫ ====================
def setup_main_menu_button():
    try:
        bot.set_my_commands([
            BotCommand("start", "🏠 Главное меню"),
            BotCommand("profile", "👤 Профиль"),
            BotCommand("buy", "💰 Купить"),
            BotCommand("trial", "🎁 Пробный"),
            BotCommand("support", "🛠️ Поддержка"),
        ])
    except:
        pass

@bot.callback_query_handler(func=lambda call: call.data == 'locations')
def locations_info(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📖 Читать", url="https://teletype.in/@ylvv/location"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    bot.send_photo(call.message.chat.id, LOCATIONS_IMAGE_URL, caption="📍 **ЛОКАЦИИ**\n\nВыбирайте сервер под задачу!", reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'privacy_policy')
def privacy_policy(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📄 Читать", url="https://teletype.in/@ylvv/politica"))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    bot.send_message(call.message.chat.id, "📚 **ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ**\n\nМы серьезно относимся к защите ваших данных.", reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['start'])
@require_subscription
def start_command(message):
    save_user(message.from_user.id)
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.row(InlineKeyboardButton("👤 Профиль", callback_data="profile"), InlineKeyboardButton("💰 Купить VPN", callback_data="buy_menu"))
    keyboard.row(InlineKeyboardButton("🎁 Пробный период", callback_data="trial"), InlineKeyboardButton("🛠️ Поддержка", callback_data="support"))
    keyboard.row(InlineKeyboardButton("⚠️ Канал с новостями", url=CHANNEL_URL), InlineKeyboardButton("📱 Инструкция", web_app=WebAppInfo(url=f"https://folwixxxx.github.io/-VPN-FOLWIXXXXX-/instructions.html?user_id={message.from_user.id}")))
    keyboard.row(InlineKeyboardButton("📍 Локации", callback_data="locations"), InlineKeyboardButton("📚 Политика", callback_data="privacy_policy"))
    
    caption = (
        "💻 **Добро пожаловать в FOLWIXXX VPN сервис!**\n\n"
        "✅ Быстрые серверы\n"
        "✅ Обход ограничений\n"
        "✅ Безлимитный трафик\n\n"
        "**📦 ALL-SUB — ЕДИНЫЙ ТАРИФ**\n"
        "🌍 **16 серверов** (Нидерланды, Германия, Финляндия, Польша, Латвия, Чехия, США)\n"
        "⚡ **Выбирайте сервер в самом приложении v2rayNG**\n"
        "🔒 **Блокировка рекламы и трекеров**\n\n"
        "💰 **Цены:**\n"
        "• 30 дней — 2 TON / 200⭐ / 200💵\n"
        "• 60 дней — 3.5 TON / 350⭐ / 350💵\n"
        "• 90 дней — 5 TON / 500⭐ / 500💵\n\n"
        "🎁 **Пробный период 1 день — бесплатно!**\n\n"
        "👇 Выберите действие"
    )
    try:
        bot.send_photo(message.chat.id, BANNER_URL, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, caption, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['profile'])
@require_subscription
def profile_command(message):
    user_id = message.from_user.id
    balance = get_balance(user_id)
    days_left, expiry_date, link = get_user_subscription_info(user_id)
    keyboard = InlineKeyboardMarkup()
    if days_left:
        keyboard.add(InlineKeyboardButton("🔄 Обновить конфиг", callback_data="refresh_config_profile"))
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    
    text = f"👤 **ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ**\n\n"
    text += f"🆔 ID: `{user_id}`\n"
    text += f"💰 Баланс: {balance} 💵\n"
    if days_left is None:
        text += "📅 Статус: ❌ **Нет активной подписки**\n\n💡 Используйте /buy для покупки ALL-SUB"
    else:
        text += f"📦 **ТАРИФ: ALL-SUB**\n"
        text += f"🌍 16 серверов (выбор в приложении)\n"
        text += f"📅 Статус: ✅ **Активна**\n"
        text += f"📅 Осталось дней: {days_left}\n"
        text += f"📅 Действует до: `{expiry_date}`\n"
        text += f"🔗 Ссылка для v2rayNG:\n`{link}`\n\n"
        text += f"📱 **Как выбрать сервер:**\n"
        text += f"• Добавьте ссылку в v2rayNG\n"
        text += f"• Нажмите на иконку профиля вверху\n"
        text += f"• Выберите нужный сервер\n"
        text += f"• Нажмите ▶️ для подключения\n\n"
        text += f"🔄 Конфиг обновляется автоматически"
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['buy'])
@require_subscription
def buy_command(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📆 30 дней", callback_data="buy_30"),
        InlineKeyboardButton("📆 60 дней", callback_data="buy_60"),
        InlineKeyboardButton("📆 90 дней", callback_data="buy_90")
    )
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="back_to_main"))
    
    bot.send_message(
        message.chat.id,
        "💎 **ALL-SUB — ЕДИНЫЙ ТАРИФ**\n\n"
        "🌍 **16 серверов в одном конфиге:**\n"
        "🇳🇱 Нидерланды (3 сервера) • 🇩🇪 Германия (3 сервера)\n"
        "🇫🇮 Финляндия (2 сервера) • 🇵🇱 Польша (3 сервера)\n"
        "🇱🇻 Латвия (2 сервера) • 🇨🇿 Чехия (1 сервер) • 🇺🇸 США (1 сервер)\n\n"
        "⚡ **Вы выбираете сервер в самом приложении v2rayNG!**\n"
        "🔒 **Встроенная блокировка рекламы и трекеров**\n\n"
        "💰 **Цены:**\n"
        "• 30 дней — 2 TON / 200⭐ / 200💵\n"
        "• 60 дней — 3.5 TON / 350⭐ / 350💵\n"
        "• 90 дней — 5 TON / 500⭐ / 500💵\n\n"
        "📅 **Выберите период:**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'buy_30')
def buy_30(call):
    process_payment(call, 30, 2.0, 200, 200)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_60')
def buy_60(call):
    process_payment(call, 60, 3.5, 350, 350)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_90')
def buy_90(call):
    process_payment(call, 90, 5.0, 500, 500)

def process_payment(call, days, ton, stars, bal):
    pending_payments[call.from_user.id] = {"days": days}
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("💎 TON", callback_data=f"ton_{days}_{ton}"),
        InlineKeyboardButton("⭐ Stars", callback_data=f"stars_{days}_{stars}")
    )
    keyboard.row(
        InlineKeyboardButton("💰 Баланс", callback_data=f"balance_{days}_{bal}"),
        InlineKeyboardButton("◀️ Назад", callback_data="buy_menu")
    )
    bot.edit_message_text(
        f"💳 **Способ оплаты ALL-SUB**\n\n"
        f"📅 {days} дней\n"
        f"🌍 16 серверов (выбор в приложении)\n\n"
        f"💎 TON: {ton}\n"
        f"⭐ Stars: {stars}\n"
        f"💰 Баланс: {bal} 💵",
        call.message.chat.id, call.message.message_id,
        reply_markup=keyboard, parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['trial'])
@require_subscription
def trial_command(message):
    user_id = message.from_user.id
    if github_get_file_content(f"trials/trial_{user_id}"):
        bot.reply_to(message, "❌ Вы уже использовали пробный период!")
        return
    days_left, _, _ = get_user_subscription_info(user_id)
    if days_left:
        bot.reply_to(message, "❌ У вас уже есть активная подписка!")
        return
    
    link = create_subscription(user_id, 1)
    if link:
        github_upload_file(f"trial_{user_id}", "used", "trials")
        bot.send_message(
            user_id,
            f"🎁 **Пробный период ALL-SUB активирован!**\n\n"
            f"🌍 16 серверов\n"
            f"📅 Действует: 1 день\n\n"
            f"🔗 **Ваша ссылка:**\n{link}\n\n"
            f"📱 **Как выбрать сервер в v2rayNG:**\n"
            f"1. Добавьте ссылку в приложение\n"
            f"2. Нажмите на иконку профиля вверху\n"
            f"3. Выберите нужный сервер из списка\n"
            f"4. Нажмите ▶️ для подключения"
        )
        bot.send_message(YOUR_ADMIN_ID, f"🎁 **ПРОБНЫЙ ПЕРИОД ALL-SUB**\n👤 {user_id}\n📅 1 день")
    else:
        bot.reply_to(message, "❌ Ошибка при активации пробного периода")

@bot.message_handler(commands=['support'])
@require_subscription
def support_command(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📩 Написать в поддержку", url=f"https://t.me/{YOUR_USERNAME}"))
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    bot.send_message(
        message.chat.id,
        "🛠️ **ПОДДЕРЖКА**\n\n"
        "Если у вас возникли проблемы с подключением,\n"
        "вопросы по оплате или другие сложности —\n\n"
        "Нажмите на кнопку ниже, чтобы написать в поддержку.\n\n"
        "Мы постараемся ответить как можно быстрее!",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['refresh_config'])
@require_subscription
def refresh_config_command(message):
    user_id = message.from_user.id
    days_left, exp_date, _ = get_user_subscription_info(user_id)
    if days_left is None:
        bot.reply_to(message, "❌ У вас нет активной подписки!")
        return
    
    link = create_subscription(user_id, days_left)
    if link:
        _, _, new_link = get_user_subscription_info(user_id)
        bot.reply_to(
            message,
            f"✅ **Ваш конфиг ALL-SUB обновлен!**\n\n"
            f"📱 Обновите ссылку в приложении:\n{new_link}\n\n"
            f"🌍 Все 16 серверов обновлены!",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "❌ Ошибка при обновлении")

# ==================== АДМИН КОМАНДЫ ====================
@bot.message_handler(commands=['pay'])
def admin_add_balance(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ Использование: /pay `user_id` `сумма`\n\nПример: /pay 123456789 100", parse_mode='Markdown')
        return
    try:
        user_id = int(parts[1])
        amount = float(parts[2])
        if amount <= 0:
            bot.reply_to(message, "❌ Сумма должна быть положительной")
            return
        success, new_balance = update_balance(user_id, amount)
        if success:
            bot.reply_to(message, f"✅ Баланс пользователя `{user_id}` пополнен на {amount} 💵\n💰 Текущий баланс: {new_balance} 💵", parse_mode='Markdown')
            try:
                bot.send_message(user_id, f"🎉 **Баланс пополнен!**\n\n💰 Сумма: {amount} 💵\n💰 Баланс: {new_balance} 💵\n\n💡 Используйте /buy для покупки ALL-SUB", parse_mode='Markdown')
            except:
                pass
        else:
            bot.reply_to(message, "❌ Ошибка при пополнении баланса")
    except ValueError:
        bot.reply_to(message, "❌ Неверный формат. Использование: /pay `user_id` `сумма`", parse_mode='Markdown')

@bot.message_handler(commands=['users_count'])
def users_count(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа")
        return
    users = get_all_users()
    bot.reply_to(message, f"👥 Всего пользователей: {len(users)}")

# ==================== ОПЛАТА БАЛАНСОМ ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('balance_'))
def handle_balance_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount = int(parts[2])
    user_id = call.from_user.id
    balance = get_balance(user_id)
    
    if balance < amount:
        bot.answer_callback_query(call.id, f"❌ Недостаточно средств! Баланс: {balance} 💵", show_alert=True)
        return
    
    success, new_balance = deduct_balance(user_id, amount)
    if not success:
        bot.answer_callback_query(call.id, "❌ Ошибка при списании средств", show_alert=True)
        return
    
    bot.edit_message_text("⏳ **Создаю подписку...**\n\nПожалуйста, подождите несколько секунд.", call.message.chat.id, call.message.message_id, parse_mode='Markdown')
    
    link = create_subscription(user_id, days)
    if link:
        bot.edit_message_text(
            f"✅ **Подписка ALL-SUB создана!**\n\n"
            f"💰 {amount} 💵\n"
            f"💰 Остаток: {new_balance} 💵\n"
            f"📅 {days} дней\n"
            f"🌍 16 серверов\n\n"
            f"🔗 {link}\n\n"
            f"📱 **Как добавить подписку в v2rayNG:**\n"
            f"• Скопируйте ссылку выше\n"
            f"• Откройте v2rayNG\n"
            f"• Нажмите ➕ → «Добавить подписку»\n"
            f"• Вставьте ссылку → «ОК»\n"
            f"• Нажмите ▶️ для подключения",
            call.message.chat.id, call.message.message_id,
            parse_mode='Markdown'
        )
        bot.send_message(YOUR_ADMIN_ID, f"💰 ОПЛАТА БАЛАНСОМ!\n👤 {user_id}\n💰 {amount} 💵\n📅 {days}д")
        bot.answer_callback_query(call.id, "✅ Подписка создана!")
        pending_payments.pop(user_id, None)
    else:
        update_balance(user_id, amount)
        bot.edit_message_text(
            "❌ **Ошибка при создании подписки!**\n\n"
            "Средства возвращены на ваш баланс.\n"
            "Попробуйте позже или обратитесь в поддержку @ylvvvl.",
            call.message.chat.id, call.message.message_id,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ton_'))
def handle_ton_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount = float(parts[2])
    user_id = call.from_user.id
    pending_payments[user_id] = {"days": days}
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Я перевел(а)", callback_data=f"check_{days}_{amount}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    bot.edit_message_text(
        f"💳 **Оплата TON для ALL-SUB**\n\n"
        f"💰 {amount} TON\n"
        f"📅 {days} дней\n"
        f"🌍 16 серверов\n\n"
        f"**Кошелёк:**\n`{TON_WALLET}`\n\n"
        f"Переведите точную сумму и нажмите «✅ Я перевел»\n"
        f"⏰ Время ожидания: 10 минут",
        call.message.chat.id, call.message.message_id,
        reply_markup=keyboard, parse_mode='Markdown'
    )
    bot.send_message(YOUR_ADMIN_ID, f"💳 НАЧАЛО ОПЛАТЫ TON\n👤 {user_id}\n💰 {amount} TON")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stars_'))
def handle_stars_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount = int(parts[2])
    send_stars_invoice(call.from_user.id, days, amount)
    bot.answer_callback_query(call.id, "⭐ Счёт отправлен!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def handle_check_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount = float(parts[2])
    bot.edit_message_text("⏳ Проверяем оплату...\n\nПожалуйста, подождите, это может занять до 10 минут.", call.message.chat.id, call.message.message_id)
    Thread(target=monitor_payment, args=(call.from_user.id, amount, days)).start()
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_payment(call):
    pending_payments.pop(call.from_user.id, None)
    bot.edit_message_text("❌ Оплата отменена", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# ==================== ОСТАЛЬНЫЕ CALLBACKИ ====================
@bot.callback_query_handler(func=lambda call: call.data == 'support')
def support(call):
    support_command(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'profile')
def profile(call):
    class FakeMessage:
        def __init__(self, user_id, chat_id):
            self.from_user = type('obj', (object,), {'id': user_id})()
            self.chat = type('obj', (object,), {'id': chat_id})()
            self.id = None
    fake_msg = FakeMessage(call.from_user.id, call.message.chat.id)
    profile_command(fake_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'refresh_config_profile')
def refresh_profile(call):
    class FakeMessage:
        def __init__(self, user_id, chat_id):
            self.from_user = type('obj', (object,), {'id': user_id})()
            self.chat = type('obj', (object,), {'id': chat_id})()
            self.id = None
    fake_msg = FakeMessage(call.from_user.id, call.message.chat.id)
    refresh_config_command(fake_msg)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'buy_menu')
def buy_menu(call):
    buy_command(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'trial')
def trial(call):
    trial_command(call.message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_main')
def back_main(call):
    start_command(call.message)
    bot.answer_callback_query(call.id)

# ==================== УТИЛИТЫ ====================
def send_user_info_to_admin(message):
    save_user(message.from_user.id)
    user_info = (
        f"🆕 **НОВЫЙ ПОЛЬЗОВАТЕЛЬ!**\n\n"
        f"🆔 **User ID:** `{message.from_user.id}`\n"
        f"👤 **Имя:** {message.from_user.first_name or '❌'}\n"
        f"📛 **Username:** @{message.from_user.username or '❌'}\n"
        f"📅 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
    )
    try:
        bot.send_message(YOUR_ADMIN_ID, user_info, parse_mode='Markdown')
    except:
        pass

# ==================== ВЕБ-СЕРВЕР ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/get_config/<int:user_id>')
def get_user_config(user_id):
    token = request.args.get('token')
    if not token:
        return {"error": "Missing token"}, 403
    expiry_content = github_get_file_content(f"subscriptions/all-sub/user_{user_id}.expiry")
    if not expiry_content:
        return {"error": "Subscription not found"}, 404
    expiry_timestamp = int(expiry_content.strip())
    if time.time() > expiry_timestamp:
        return {"error": "Subscription expired"}, 403
    if not verify_user_token(user_id, token, expiry_timestamp):
        return {"error": "Invalid token"}, 403
    content = github_get_file_content(f"subscriptions/all-sub/user_{user_id}.txt")
    if not content:
        return {"error": "Config not found"}, 404
    return Response(content, mimetype='text/plain', headers={'Cache-Control': 'no-cache', 'Content-Disposition': f'inline; filename="config_{user_id}.txt"'})

def run_web_server():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    setup_main_menu_button()
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("🌐 Веб-сервер запущен на порту 10000")
    print("🤖 Бот запущен. Репозиторий должен быть ПУБЛИЧНЫМ!")
    print("📦 ALL-SUB — 16 серверов в одном конфиге, выбор в приложении")
    print("💰 Цена: 2 TON / 200⭐ / 200💵 (30 дней)")
    print("🎁 Пробный период 1 день")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)
