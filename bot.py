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

# ==================== ТОКЕНЫ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ====================
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
TON_WALLET = os.environ.get("TON_WALLET")
TON_API_KEY = os.environ.get("TON_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY", "default_secret_key_change_me_12345")

# ==================== ЦЕНЫ ДЛЯ КАСТОМНОЙ ПОДПИСКИ ====================
CUSTOM_PRICE_TON = 0.5
CUSTOM_PRICE_STARS = 50
CUSTOM_PRICE_BALANCE = 50

# ==================== КАНАЛ ДЛЯ ПРОВЕРКИ ПОДПИСКИ ====================
REQUIRED_CHANNEL = "folwixxxvpn"
CHANNEL_URL = f"https://t.me/{REQUIRED_CHANNEL}"

# Проверка
if not all([TELEGRAM_TOKEN, GITHUB_TOKEN, GITHUB_REPO, TON_WALLET, TON_API_KEY]):
    raise Exception("❌ Ошибка: не все переменные окружения заданы!")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = telebot.TeleBot(TELEGRAM_TOKEN)
pending_payments = {}
user_vless_links = {}

YOUR_ADMIN_ID = 8684879669
YOUR_USERNAME = "ylvvvl"

BANNER_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/banner.jpg"
LOCATIONS_IMAGE_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/locations.jpg"

# ==================== ФУНКЦИЯ ПРОВЕРКИ ПОДПИСКИ НА КАНАЛ ====================
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(f"@{REQUIRED_CHANNEL}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

def require_subscription(func):
    def wrapper(message):
        user_id = message.from_user.id
        if not is_subscribed(user_id):
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
            keyboard.add(InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription"))
            bot.send_message(
                message.chat.id,
                f"❌ **Доступ ограничен!**\n\n"
                f"Для использования бота вы должны быть подписаны на наш новостной канал.\n\n"
                f"👉 Подпишитесь и нажмите «✅ Я подписался».",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return
        return func(message)
    return wrapper

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_subscription_callback(call):
    user_id = call.from_user.id
    if is_subscribed(user_id):
        bot.edit_message_text(
            "✅ Спасибо за подписку! Теперь вы можете пользоваться ботом.\n\n"
            "Введите /start чтобы начать.",
            call.message.chat.id, call.message.message_id
        )
        bot.answer_callback_query(call.id, "Подписка подтверждена!")
    else:
        bot.answer_callback_query(call.id, "Вы до сих пор не подписаны. Пожалуйста, подпишитесь и нажмите снова.", show_alert=True)

# ==================== ФУНКЦИИ ДЛЯ ГЕНЕРАЦИИ ТОКЕНОВ ====================
def generate_user_token(user_id, expiry_timestamp):
    message = f"{user_id}_{expiry_timestamp}_{SECRET_KEY}"
    return hashlib.md5(message.encode()).hexdigest()[:32]

def verify_user_token(user_id, token, expiry_timestamp):
    expected = generate_user_token(user_id, expiry_timestamp)
    return hmac.compare_digest(expected, token)

def get_user_subscription_folder(user_id):
    for folder in ["def-sub", "ultra-sub", "full-sub", "fast-sub", "trial-sub", "custom-sub"]:
        if github_get_file_content(f"subscriptions/{folder}/user_{user_id}.expiry"):
            return folder
    return None

# ==================== НАСТРОЙКА КНОПКИ ГЛАВНОГО МЕНЮ ====================
def setup_main_menu_button():
    try:
        commands = [
            BotCommand("start", "🏠 Главное меню"),
            BotCommand("profile", "👤 Мой профиль"),
            BotCommand("buy", "💰 Купить VPN"),
            BotCommand("trial", "🎁 Пробный период"),
            BotCommand("support", "🛠️ Поддержка"),
            BotCommand("refresh_config", "🔄 Обновить конфиг"),
        ]
        bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        print("✅ Кнопка главного меню установлена!")
    except Exception as e:
        print(f"⚠️ Ошибка установки кнопки меню: {e}")

# ==================== ВЕБ-СЕРВЕР ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive! VPN subscription bot is running.", 200

@app.route('/health')
def health():
    return "OK", 200

@app.route('/get_config/<int:user_id>')
def get_user_config(user_id):
    token = request.args.get('token')
    if not token:
        return {"error": "Missing token"}, 403
    folder = get_user_subscription_folder(user_id)
    if not folder:
        return {"error": "Subscription not found"}, 404
    expiry_content = github_get_file_content(f"subscriptions/{folder}/user_{user_id}.expiry")
    if not expiry_content:
        return {"error": "Subscription expired"}, 403
    expiry_timestamp = int(expiry_content.strip())
    now = int(time.time())
    if now > expiry_timestamp:
        return {"error": "Subscription expired"}, 403
    if not verify_user_token(user_id, token, expiry_timestamp):
        return {"error": "Invalid token"}, 403
    content = github_get_file_content(f"subscriptions/{folder}/user_{user_id}.txt")
    if not content:
        return {"error": "Config not found"}, 404
    return Response(content, mimetype='text/plain', headers={
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Content-Disposition': f'inline; filename="config_{user_id}.txt"'
    })

def run_web_server():
    app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)

# ==================== GITHUB ФУНКЦИИ ====================
def github_upload_file(filename, content, folder=""):
    if folder:
        full_path = f"{folder}/{filename}"
    else:
        full_path = filename
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{full_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    response = requests.get(url, headers=headers)
    data = {"message": f"Update {full_path}", "content": content_b64}
    if response.status_code == 200:
        data["sha"] = response.json()["sha"]
    result = requests.put(url, headers=headers, json=data)
    return result.status_code in [200, 201]

def github_get_file_content(filepath):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return None
    try:
        content = base64.b64decode(response.json()["content"]).decode('utf-8')
        return content
    except:
        return None

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ====================
def get_all_users():
    content = github_get_file_content("users.json")
    if content is None:
        return []
    try:
        users = json.loads(content)
        return users
    except:
        return []

def save_user(user_id):
    users = get_all_users()
    if user_id not in users:
        users.append(user_id)
        github_upload_file("users.json", json.dumps(users, indent=2), folder="")
        return True
    return False

def get_subscription_folder_by_type(sub_type):
    folder_map = {
        "def": "def-sub",
        "ultra": "ultra-sub",
        "full": "full-sub",
        "fast": "fast-sub",
        "trial": "trial-sub",
        "custom": "custom-sub"
    }
    return folder_map.get(sub_type, "full-sub")

def get_user_subscription_type(user_id):
    for folder in ["def-sub", "ultra-sub", "full-sub", "fast-sub", "trial-sub", "custom-sub"]:
        content = github_get_file_content(f"subscriptions/{folder}/user_{user_id}.type")
        if content:
            return content.strip()
    return None

def force_update_user_config(user_id, sub_type):
    if sub_type == "custom":
        return True
    template_file = f"{sub_type}-sub.txt"
    if sub_type == "full":
        template_file = "template.txt"
    url = f"{RAW_BASE}/{template_file}"
    response = requests.get(url)
    if response.status_code != 200:
        return False
    template_content = response.text
    folder = get_subscription_folder_by_type(sub_type)
    template_content = template_content.replace(
        "❀VPN USER❀",
        f"❀{sub_type.upper()}-SUB {user_id}❀"
    )
    template_content += f"\n# Обновлено вручную: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    success = github_upload_file(f"user_{user_id}.txt", template_content, folder=f"subscriptions/{folder}")
    if not success:
        return False
    github_upload_file(f"user_{user_id}.type", sub_type, folder=f"subscriptions/{folder}")
    return True

# ==================== ФУНКЦИИ БАЛАНСА ====================
def get_balance(user_id):
    content = github_get_file_content(f"balances/balance_{user_id}.json")
    if content is None:
        return 0
    try:
        data = json.loads(content)
        return data.get("balance", 0)
    except:
        return 0

def update_balance(user_id, amount):
    filename = f"balance_{user_id}.json"
    current_balance = get_balance(user_id)
    new_balance = current_balance + amount
    data = {
        "user_id": user_id,
        "balance": new_balance,
        "last_updated": datetime.now().isoformat()
    }
    success = github_upload_file(filename, json.dumps(data, indent=2), folder="balances")
    return success, new_balance

def deduct_balance(user_id, amount):
    current_balance = get_balance(user_id)
    if current_balance < amount:
        return False, current_balance
    new_balance = current_balance - amount
    filename = f"balance_{user_id}.json"
    data = {
        "user_id": user_id,
        "balance": new_balance,
        "last_updated": datetime.now().isoformat()
    }
    success = github_upload_file(filename, json.dumps(data, indent=2), folder="balances")
    if success:
        return True, new_balance
    return False, current_balance

# ==================== ФУНКЦИИ ПРОВЕРКИ TON ====================
def check_ton_transaction(amount_ton, user_id):
    API_URL = "https://toncenter.com/api/v2/getTransactions"
    params = {"address": TON_WALLET, "limit": 20, "api_key": TON_API_KEY}
    try:
        response = requests.get(API_URL, params=params, timeout=30)
        data = response.json()
        if not data.get("ok"):
            return False
        for tx in data.get("result", []):
            in_msg = tx.get("in_msg", {})
            if in_msg.get("destination") != TON_WALLET:
                continue
            amount_nano = int(in_msg.get("value", 0))
            amount_tx = amount_nano / 1e9
            if amount_tx >= amount_ton - 0.05:
                return True
    except:
        return False
    return False

def monitor_payment(user_id, amount_ton, days, sub_type):
    start_time = time.time()
    while time.time() - start_time < 600:
        if check_ton_transaction(amount_ton, user_id):
            bot.send_message(user_id, f"✅ Оплата {amount_ton} TON получена! Создаю подписку...")
            link = create_user_subscription(user_id, days, sub_type, is_trial=False)
            if link:
                bot.send_message(user_id, f"✅ **Подписка создана!**\n\n🔗 {link}\n\n📅 Действует: {days} дней\n\n📱 Добавьте ссылку в v2rayNG")
                bot.send_message(YOUR_ADMIN_ID, f"✅ **УСПЕШНАЯ ОПЛАТА!**\n\n👤 Пользователь: `{user_id}`\n💰 Сумма: {amount_ton} TON\n📅 Период: {days} дней\n📦 Тип: {sub_type}")
            else:
                bot.send_message(user_id, "❌ Ошибка при создании подписки")
            return True
        time.sleep(15)
    bot.send_message(user_id, "⏰ Время ожидания оплаты истекло. Попробуйте снова /start")
    return False

def monitor_custom_payment(chat_id, user_id):
    start_time = time.time()
    while time.time() - start_time < 600:
        if check_ton_transaction(CUSTOM_PRICE_TON, user_id):
            links = user_vless_links.get(user_id, [])
            link = create_custom_subscription(user_id, links)
            if link:
                bot.send_message(chat_id, f"✅ **Кастомный конфиг создан!**\n📊 {len(links)} серверов\n\n🔗 {link}")
                bot.send_message(YOUR_ADMIN_ID, f"⚙️ КАСТОМНЫЙ КОНФИГ (TON)\n👤 {user_id}")
                user_vless_links.pop(user_id, None)
                pending_payments.pop(user_id, None)
            else:
                bot.send_message(chat_id, "❌ Ошибка")
            return
        time.sleep(15)
    bot.send_message(chat_id, "⏰ Время ожидания оплаты истекло")
    user_vless_links.pop(user_id, None)
    pending_payments.pop(user_id, None)

# ==================== ОПЛАТА STARS ====================
def send_stars_invoice(user_id, days, stars_amount, sub_type):
    if sub_type == "def":
        title = f"💵 DEF-SUB {days}д"
    elif sub_type == "ultra":
        title = f"⭐ ULTRA-SUB {days}д"
    elif sub_type == "full":
        title = f"🔑 FULL-SUB {days}д"
    else:
        title = f"🛡️ FAST-SUB {days}д"
    prices = [LabeledPrice(label="VPN подписка", amount=stars_amount)]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"⭐ Оплатить {stars_amount} Stars", pay=True))
    try:
        bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=f"VPN подписка на {days} дней\n\n✅ Безлимитный трафик\n✅ Обход блокировок",
            invoice_payload=f"stars_{days}_{stars_amount}_{sub_type}",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="vpn_sub",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            reply_markup=keyboard
        )
        return True
    except Exception as e:
        print(f"❌ Ошибка инвойса: {e}")
        return False

@bot.pre_checkout_query_handler(func=lambda query: True)
def handle_pre_checkout(query):
    try:
        bot.answer_pre_checkout_query(query.id, ok=True)
        print(f"✅ Pre-checkout подтверждён: {query.invoice_payload}")
    except Exception as e:
        print(f"❌ Pre-checkout error: {e}")

@bot.pre_checkout_query_handler(func=lambda query: query.invoice_payload == "custom_config")
def handle_custom_pre_checkout(query):
    try:
        bot.answer_pre_checkout_query(query.id, ok=True)
    except Exception as e:
        print(f"❌ Pre-checkout error: {e}")

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload
    print(f"⭐ УСПЕШНАЯ ОПЛАТА! payload={payload}")
    
    if payload == "custom_config":
        links = user_vless_links.get(user_id, [])
        link = create_custom_subscription(user_id, links)
        if link:
            bot.send_message(user_id, f"✅ **Кастомный конфиг создан!**\n⭐ {CUSTOM_PRICE_STARS} Stars\n📊 {len(links)} серверов\n\n🔗 {link}")
            bot.send_message(YOUR_ADMIN_ID, f"⚙️ КАСТОМНЫЙ КОНФИГ (STARS)\n👤 {user_id}")
            user_vless_links.pop(user_id, None)
            pending_payments.pop(user_id, None)
        else:
            bot.send_message(user_id, "❌ Ошибка")
        return
    
    parts = payload.split('_')
    if len(parts) >= 4 and parts[0] == "stars":
        days = int(parts[1])
        stars_amount = int(parts[2])
        sub_type = parts[3]
        link = create_user_subscription(user_id, days, sub_type, is_trial=False)
        if link:
            bot.send_message(
                user_id,
                f"✅ **Подписка создана!**\n\n"
                f"⭐ Оплачено: {stars_amount} Stars\n"
                f"📅 Период: {days} дней\n\n"
                f"🔗 {link}\n\n"
                f"📱 Добавьте ссылку в v2rayNG"
            )
            bot.send_message(YOUR_ADMIN_ID, f"⭐ **ОПЛАТА STARS!**\n👤 {user_id}\n⭐ {stars_amount}\n📅 {days}д")

# ==================== ФУНКЦИИ ПОДПИСОК ====================
def create_custom_subscription(user_id, vless_links):
    filename = f"user_{user_id}"
    folder = "custom-sub"
    
    header = f"""# profile-title: ⚙️ CUSTOM CONFIG {user_id}
# profile-update-interval: 1440
# created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# type: custom

"""
    content = header + "\n".join(vless_links)
    expiry_timestamp = 2147483647
    
    success = github_upload_file(f"{filename}.txt", content, folder=f"subscriptions/{folder}")
    if not success:
        return None
    success = github_upload_file(f"{filename}.expiry", str(expiry_timestamp), folder=f"subscriptions/{folder}")
    if not success:
        return None
    github_upload_file(f"{filename}.type", "custom", folder=f"subscriptions/{folder}")
    
    return f"{RAW_BASE}/subscriptions/{folder}/{filename}.txt?t={int(time.time())}"

def create_user_subscription(user_id, days=30, sub_type="full", is_trial=False):
    filename = f"user_{user_id}"
    
    if is_trial:
        template_file = "trial-sub.txt"
        sub_name = "TRIAL (🎁 Пробный период)"
        folder = "trial-sub"
    else:
        if sub_type == "def":
            template_file = "def-sub.txt"
            sub_name = "DEF-SUB (VPN💵)"
            folder = "def-sub"
        elif sub_type == "ultra":
            template_file = "ultra-sub.txt"
            sub_name = "ULTRA-SUB (⭐ Лучшие серверы)"
            folder = "ultra-sub"
        elif sub_type == "full":
            template_file = "template.txt"
            sub_name = "FULL-SUB (🔑Обход БС и VPN💵)"
            folder = "full-sub"
        elif sub_type == "fast":
            template_file = "fast-sub.txt"
            sub_name = "FAST-SUB (🛡️ Максимальная скорость)"
            folder = "fast-sub"
        elif sub_type == "custom":
            return create_custom_subscription(user_id, user_vless_links.get(user_id, []))
        else:
            template_file = "template.txt"
            sub_name = "FULL-SUB (🔑Обход БС и VPN💵)"
            folder = "full-sub"
    
    url = f"{RAW_BASE}/{template_file}"
    response = requests.get(url)
    if response.status_code != 200:
        bot.send_message(user_id, f"❌ Ошибка: не найден шаблон {template_file}")
        return None
    
    template_content = response.text
    expiry_date = datetime.now() + timedelta(days=days)
    expiry_date_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    expiry_timestamp = int(expiry_date.timestamp())
    
    header = f"""#subscription-userinfo: upload=0; download=0; total=0; expire={expiry_timestamp}
# profile-title: {sub_name} {user_id}
# profile-update-interval: 1440
# expire: {expiry_date_str}
# days: {days}
# created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    template_content = header + template_content
    template_content = template_content.replace(
        "❀VPN USER❀",
        f"❀{sub_name} {user_id} ({days} дней до {expiry_date_str})❀"
    )
    
    success = github_upload_file(f"{filename}.txt", template_content, folder=f"subscriptions/{folder}")
    if not success:
        return None
    success = github_upload_file(f"{filename}.expiry", str(expiry_timestamp), folder=f"subscriptions/{folder}")
    if not success:
        return None
    if not is_trial and sub_type != "custom":
        github_upload_file(f"{filename}.type", sub_type, folder=f"subscriptions/{folder}")
    
    return f"{RAW_BASE}/subscriptions/{folder}/{filename}.txt?t={int(time.time())}"

def get_user_subscription_info(user_id):
    for folder in ["def-sub", "ultra-sub", "full-sub", "fast-sub", "trial-sub", "custom-sub"]:
        content = github_get_file_content(f"subscriptions/{folder}/user_{user_id}.expiry")
        if content:
            try:
                expiry_timestamp = int(content.strip())
                now = int(time.time())
                if now > expiry_timestamp:
                    continue
                days_left = (expiry_timestamp - now) // 86400
                if days_left > 999:
                    days_left = "∞"
                expiry_date = datetime.fromtimestamp(expiry_timestamp).strftime("%d.%m.%Y %H:%M:%S") if expiry_timestamp < 2147483647 else "Бессрочно"
                subscription_link = f"{RAW_BASE}/subscriptions/{folder}/user_{user_id}.txt?t={int(time.time())}"
                return days_left, expiry_date, subscription_link
            except Exception as e:
                print(f"Ошибка: {e}")
                return None, None, None
    return None, None, None

# ==================== КАСТОМНЫЙ КОНФИГУРАТОР (ПОДРОБНАЯ ИНФОРМАЦИЯ) ====================
@bot.callback_query_handler(func=lambda call: call.data == 'custom_config')
def custom_config_start(call):
    user_id = call.from_user.id
    user_vless_links[user_id] = []
    
    info_text = (
        "⚙️ **КАСТОМНЫЙ КОНФИГУРАТОР**\n\n"
        "📝 **Что это такое?**\n"
        "Вы можете собрать свой собственный VPN конфиг из любых VLESS-серверов!\n\n"
        "💰 **Стоимость:** 50⭐ / 0.5 TON / 50💵\n"
        "⏰ **Срок действия:** БЕССРОЧНО!\n\n"
        "📌 **Как это работает:**\n"
        "1️⃣ Отправьте мне ВСЕ ваши vless:// ссылки одним сообщением\n"
        "2️⃣ Каждая ссылка должна быть на новой строке\n"
        "3️⃣ После отправки нажмите «Продолжить»\n"
        "4️⃣ Выберите способ оплаты\n"
        "5️⃣ Получите готовый конфиг со всеми серверами\n\n"
        "📱 **Пример правильной отправки:**\n"
        "```\n"
        "vless://abc123@example.com:443?encryption=none#Server1\n"
        "vless://def456@example2.com:443?encryption=none#Server2\n"
        "```\n\n"
        "⚠️ **ВАЖНО:**\n"
        "• Принимаются ТОЛЬКО vless:// ссылки\n"
        "• Поддерживается БЕЗЛИМИТНОЕ количество серверов\n"
        "• После оплаты вы получите одну ссылку со ВСЕМИ серверами\n\n"
        "✅ **Готовы? Отправьте ваши vless:// ссылки!**"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Продолжить (после отправки ссылок)", callback_data="custom_proceed"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="custom_cancel"))
    
    bot.send_message(
        call.message.chat.id,
        info_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: message.from_user.id in user_vless_links and user_vless_links[message.from_user.id] is not None)
def collect_vless_links(message):
    user_id = message.from_user.id
    text = message.text.strip()
    lines = text.split('\n')
    vless_found = [line.strip() for line in lines if line.strip().startswith('vless://')]
    
    if not vless_found:
        bot.reply_to(message, "❌ Не найдено vless:// ссылок!\n\nПожалуйста, отправьте ссылки в формате:\n`vless://...`\nКаждая ссылка с новой строки.", parse_mode='Markdown')
        return
    
    user_vless_links[user_id] = vless_found
    
    servers_list = "\n".join([f"{i+1}. `{link[:50]}...`" for i, link in enumerate(vless_found[:5])])
    if len(vless_found) > 5:
        servers_list += f"\n... и ещё {len(vless_found) - 5} серверов"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Продолжить к оплате", callback_data="custom_proceed"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="custom_cancel"))
    
    bot.send_message(
        user_id,
        f"✅ **Добавлено {len(vless_found)} серверов!**\n\n"
        f"📋 **Список серверов:**\n{servers_list}\n\n"
        f"💰 К оплате: {CUSTOM_PRICE_STARS}⭐ / {CUSTOM_PRICE_TON} TON / {CUSTOM_PRICE_BALANCE}💵\n\n"
        f"Нажмите «Продолжить» для выбора способа оплаты",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'custom_proceed')
def custom_proceed(call):
    user_id = call.from_user.id
    links = user_vless_links.get(user_id, [])
    if not links:
        bot.answer_callback_query(call.id, "❌ Сначала отправьте vless:// ссылки!\nИспользуйте /start и выберите «⚙️ Собрать конфиг»", show_alert=True)
        return
    
    pending_payments[user_id] = {"type": "custom", "links": links}
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("💎 TON (0.5)", callback_data="custom_ton"),
        InlineKeyboardButton("⭐ Stars (50)", callback_data="custom_stars"),
        InlineKeyboardButton("💰 Баланс (50💵)", callback_data="custom_balance")
    )
    keyboard.row(InlineKeyboardButton("❌ Отменить всё", callback_data="custom_cancel_full"))
    keyboard.row(InlineKeyboardButton("◀️ Назад в меню", callback_data="buy_menu"))
    
    bot.send_message(
        call.message.chat.id,
        f"⚙️ **КАСТОМНЫЙ КОНФИГ**\n\n"
        f"📊 **Серверов:** {len(links)}\n"
        f"⏰ **Срок:** Бессрочно\n"
        f"💰 **Цена:** {CUSTOM_PRICE_TON} TON / {CUSTOM_PRICE_STARS}⭐ / {CUSTOM_PRICE_BALANCE}💵\n\n"
        f"💳 **Выберите способ оплаты:**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'custom_cancel')
def custom_cancel(call):
    user_id = call.from_user.id
    user_vless_links.pop(user_id, None)
    pending_payments.pop(user_id, None)
    bot.send_message(call.message.chat.id, "❌ **Сборка конфига отменена**\n\nВы можете начать заново через /start", parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'custom_cancel_full')
def custom_cancel_full(call):
    user_id = call.from_user.id
    user_vless_links.pop(user_id, None)
    pending_payments.pop(user_id, None)
    bot.send_message(call.message.chat.id, "❌ **Всё отменено!**\n\nВаши ссылки удалены из памяти бота.\n\nЧтобы начать заново - используйте /start", parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# ==================== ОПЛАТА КАСТОМНОГО КОНФИГА ====================
@bot.callback_query_handler(func=lambda call: call.data == 'custom_ton')
def custom_ton_pay(call):
    user_id = call.from_user.id
    links = user_vless_links.get(user_id, [])
    if not links:
        bot.answer_callback_query(call.id, "❌ Ошибка: ссылки не найдены", show_alert=True)
        return
    
    pending_payments[user_id] = {"type": "custom", "method": "ton", "links": links}
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Я перевел(а)", callback_data="custom_check_ton"))
    keyboard.add(InlineKeyboardButton("❌ Отменить оплату", callback_data="custom_cancel_payment"))
    
    bot.send_message(
        call.message.chat.id,
        f"💳 **Оплата TON для кастомного конфига**\n\n"
        f"💰 **Сумма:** {CUSTOM_PRICE_TON} TON\n"
        f"📊 **Серверов:** {len(links)}\n"
        f"⏰ **Срок:** Бессрочно\n\n"
        f"💎 **Кошелёк:**\n`{TON_WALLET}`\n\n"
        f"❗️ Переведите точную сумму и нажмите «✅ Я перевел»\n"
        f"⏰ Время ожидания: 10 минут\n\n"
        f"⚠️ Не забудьте указать ваш TELEGRAM ID в комментарии к переводу (опционально)",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    bot.send_message(YOUR_ADMIN_ID, f"💳 НАЧАЛО ОПЛАТЫ КАСТОМНОГО КОНФИГА (TON)\n👤 {user_id}\n💰 {CUSTOM_PRICE_TON} TON\n📊 {len(links)} серверов")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'custom_stars')
def custom_stars_pay(call):
    user_id = call.from_user.id
    links = user_vless_links.get(user_id, [])
    if not links:
        bot.answer_callback_query(call.id, "❌ Ошибка: ссылки не найдены", show_alert=True)
        return
    
    pending_payments[user_id] = {"type": "custom", "method": "stars", "links": links}
    
    try:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(f"⭐ Оплатить {CUSTOM_PRICE_STARS} Stars", pay=True))
        keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data="custom_cancel_payment"))
        
        bot.send_invoice(
            chat_id=user_id,
            title="⚙️ Кастомный конфиг VPN",
            description=f"Свой конфиг из {len(links)} серверов\nБессрочная подписка",
            invoice_payload="custom_config",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{len(links)} серверов (бессрочно)", amount=CUSTOM_PRICE_STARS)],
            start_parameter="custom_sub",
            need_name=False,
            need_phone_number=False,
            need_email=False,
            reply_markup=keyboard
        )
        bot.send_message(YOUR_ADMIN_ID, f"⭐ НАЧАЛО ОПЛАТЫ КАСТОМНОГО КОНФИГА (STARS)\n👤 {user_id}\n⭐ {CUSTOM_PRICE_STARS}\n📊 {len(links)} серверов")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при создании счёта: {e}")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'custom_balance')
def custom_balance_pay(call):
    user_id = call.from_user.id
    links = user_vless_links.get(user_id, [])
    if not links:
        bot.answer_callback_query(call.id, "❌ Ошибка: ссылки не найдены", show_alert=True)
        return
    
    balance = get_balance(user_id)
    if balance < CUSTOM_PRICE_BALANCE:
        bot.answer_callback_query(call.id, f"❌ Недостаточно средств! Ваш баланс: {balance} 💵\nПополните баланс через админа", show_alert=True)
        return
    
    success, new_balance = deduct_balance(user_id, CUSTOM_PRICE_BALANCE)
    if not success:
        bot.answer_callback_query(call.id, "❌ Ошибка при списании средств", show_alert=True)
        return
    
    link = create_custom_subscription(user_id, links)
    if link:
        bot.send_message(
            call.message.chat.id,
            f"✅ **КАСТОМНЫЙ КОНФИГ СОЗДАН!**\n\n"
            f"💰 **Оплачено:** {CUSTOM_PRICE_BALANCE} 💵\n"
            f"💰 **Остаток на балансе:** {new_balance} 💵\n"
            f"📊 **Серверов:** {len(links)}\n"
            f"⏰ **Срок:** Бессрочно\n\n"
            f"🔗 **Ваша ссылка для v2rayNG:**\n`{link}`\n\n"
            f"📱 Просто добавьте эту ссылку в приложение v2rayNG и все сервера появятся автоматически!",
            parse_mode='Markdown'
        )
        bot.send_message(YOUR_ADMIN_ID, f"⚙️ КАСТОМНЫЙ КОНФИГ (БАЛАНС)\n👤 {user_id}\n💰 {CUSTOM_PRICE_BALANCE} 💵\n📊 {len(links)} серверов")
        user_vless_links.pop(user_id, None)
        pending_payments.pop(user_id, None)
        bot.answer_callback_query(call.id, "✅ Конфиг создан!")
    else:
        update_balance(user_id, CUSTOM_PRICE_BALANCE)
        bot.answer_callback_query(call.id, "❌ Ошибка при создании конфига", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == 'custom_check_ton')
def custom_check_payment(call):
    user_id = call.from_user.id
    pending = pending_payments.get(user_id, {})
    if pending.get("type") != "custom" or pending.get("method") != "ton":
        bot.answer_callback_query(call.id, "❌ Нет активного платежа", show_alert=True)
        return
    
    bot.send_message(call.message.chat.id, "⏳ **Проверяем оплату...**\n\nПожалуйста, подождите, это может занять до 10 минут.\nПроверка происходит каждые 15 секунд.", parse_mode='Markdown')
    Thread(target=monitor_custom_payment, args=(call.message.chat.id, user_id)).start()
    bot.answer_callback_query(call.id, "🔍 Начинаем проверку...")

@bot.callback_query_handler(func=lambda call: call.data == 'custom_cancel_payment')
def custom_cancel_payment(call):
    user_id = call.from_user.id
    user_vless_links.pop(user_id, None)
    pending_payments.pop(user_id, None)
    bot.send_message(call.message.chat.id, "❌ **Оплата отменена!**\n\nВаши ссылки удалены из памяти.\n\nЧтобы начать заново - используйте /start", parse_mode='Markdown')
    bot.answer_callback_query(call.id, "✅ Отменено")

# ==================== ЛОКАЦИИ ====================
@bot.callback_query_handler(func=lambda call: call.data == 'locations')
def locations_info(call):
    caption = (
        "📍 **ЛОКАЦИИ И ИХ НАЗНАЧЕНИЕ**\n\n"
        "Мы подготовили для вас статью, которая подробно разбирает,\n"
        "как выбрать локацию в вашей подписке под разные задачи.\n\n"
        "📖 В статье вы узнаете:\n"
        "• Какие локации лучше для ютуба\n"
        "• Где самый быстрый интернет\n"
        "• Какую страну выбрать для игр\n"
        "• Оптимальные настройки для разных задач\n\n"
        "👇 **Нажмите на кнопку ниже, чтобы прочитать статью**"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📖 Читать статью о локациях", url="https://teletype.in/@ylvv/location"))
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    
    try:
        with open("locations.jpg", "rb") as photo:
            bot.send_photo(call.message.chat.id, photo, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    except:
        bot.send_photo(call.message.chat.id, LOCATIONS_IMAGE_URL, caption=caption, reply_markup=keyboard, parse_mode='Markdown')
    
    bot.answer_callback_query(call.id)

# ==================== ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ ====================
@bot.callback_query_handler(func=lambda call: call.data == 'privacy_policy')
def privacy_policy(call):
    text = (
        "📚 **ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ**\n\n"
        "Мы серьезно относимся к защите ваших персональных данных.\n\n"
        "В нашей политике конфиденциальности вы найдете информацию о:\n"
        "• Какие данные мы собираем\n"
        "• Как мы используем ваши данные\n"
        "• Как мы защищаем вашу информацию\n"
        "• Ваши права как пользователя\n\n"
        "👇 **Нажмите на кнопку ниже, чтобы ознакомиться с полной версией**"
    )
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📄 Читать политику конфиденциальности", url="https://teletype.in/@ylvv/politica"))
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    
    bot.send_message(call.message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# ==================== КОМАНДЫ ПОЛЬЗОВАТЕЛЯ ====================
@bot.message_handler(commands=['start'])
@require_subscription
def start_command(message):
    send_user_info_to_admin(message)
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Ряд 1: Профиль и Купить VPN
    keyboard.row(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Купить VPN", callback_data="buy_menu")
    )
    
    # Ряд 2: Пробный период и Собрать конфиг
    keyboard.row(
        InlineKeyboardButton("🎁 Пробный период", callback_data="trial"),
        InlineKeyboardButton("⚙️ Собрать конфиг", callback_data="custom_config")
    )
    
    # Ряд 3: Соглашение и Политика конфиденциальности
    keyboard.row(
        InlineKeyboardButton("📖 Соглашение", url="https://teletype.in/@ylvv/editor/folwixxxvpn"),
        InlineKeyboardButton("📚 Политика конфиденциальности", callback_data="privacy_policy")
    )
    
    # Ряд 4: Канал с новостями и Инструкция
    keyboard.row(
        InlineKeyboardButton("⚠️ Канал с новостями", url=CHANNEL_URL),
        InlineKeyboardButton("📱 Инструкция", web_app=WebAppInfo(url=f"https://folwixxxx.github.io/-VPN-FOLWIXXXXX-/instructions.html?user_id={message.from_user.id}"))
    )
    
    # Ряд 5: Поддержка и Локации
    keyboard.row(
        InlineKeyboardButton("🛠️ Поддержка", callback_data="support"),
        InlineKeyboardButton("📍 Локации", callback_data="locations")
    )
    
    caption = (
        "💻 **Добро пожаловать в FOLWIXXX VPN сервис!**\n\n"
        "✅ Быстрые серверы\n"
        "✅ Обход ограничений\n"
        "✅ Безлимитный трафик\n\n"
        "**Тарифы (30 дней):**\n"
        "🪙 DEF-SUB — 0.5 TON / 50⭐ / 50💵\n"
        "⭐ ULTRA-SUB — 0.7 TON / 75⭐ / 75💵\n"
        "🔑 FULL-SUB — 1 TON / 100⭐ / 100💵\n"
        "🛡️ FAST-SUB — 1.5 TON / 150⭐ / 150💵\n\n"
        "⚙️ **Собрать свой конфиг** — 0.5 TON / 50⭐ / 50💵 (бессрочно)\n\n"
        "🎁 Пробный период 3 дня — бесплатно!\n\n"
        "Выберите действие 👇"
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
    days_left, expiry_date, subscription_link = get_user_subscription_info(user_id)
    keyboard = InlineKeyboardMarkup()
    if days_left and days_left != "expired" and days_left is not None:
        keyboard.add(InlineKeyboardButton("🔄 Обновить конфиг", callback_data="refresh_config_profile"))
    keyboard.add(InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main"))
    
    text = f"👤 **ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ**\n\n"
    text += f"🆔 ID: `{user_id}`\n"
    text += f"💰 Баланс: {balance} 💵\n"
    if days_left is None:
        text += "📅 Статус: ❌ **Нет активной подписки**"
    elif days_left == "expired":
        text += "📅 Статус: ⏰ **Подписка истекла**"
    else:
        text += f"📅 Статус: ✅ **Активна**\n"
        text += f"📅 Осталось дней: {days_left}\n"
        text += f"📅 Действует до: `{expiry_date}`\n"
        text += f"🔗 Ссылка для v2rayNG:\n`{subscription_link}`\n\n"
        text += f"🔄 Конфиг обновляется автоматически каждые 6 часов\n"
        text += f"⚠️ Если подписка не работает - удалите старую и добавьте эту ссылку заново"
    bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='Markdown')

@bot.message_handler(commands=['buy'])
@require_subscription
def buy_command(message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("💵 DEF-SUB", callback_data="sub_def"),
        InlineKeyboardButton("⭐ ULTRA-SUB", callback_data="sub_ultra")
    )
    keyboard.row(
        InlineKeyboardButton("🔑 FULL-SUB", callback_data="sub_full"),
        InlineKeyboardButton("🛡️ FAST-SUB", callback_data="sub_fast")
    )
    keyboard.row(
        InlineKeyboardButton("⚙️ CUSTOM (свой конфиг)", callback_data="custom_config"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")
    )
    bot.send_message(
        message.chat.id,
        "💎 **Выберите тип подписки:**\n\n"
        "🪙 DEF-SUB — Только VPN 0.5 TON / 50⭐ / 50💵\n"
        "⭐ ULTRA-SUB — Лучшие серверы 0.7 TON / 75⭐ / 75💵\n"
        "🔑 FULL-SUB — Все серверы 1 TON / 100⭐ / 100💵\n"
        "🛡️ FAST-SUB — Максимальная скорость 1.5 TON / 150⭐ / 150💵\n"
        "⚙️ CUSTOM — Свой конфиг 0.5 TON / 50⭐ / 50💵 (бессрочно)",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['trial'])
@require_subscription
def trial_command(message):
    user_id = message.from_user.id
    if github_get_file_content(f"trials/trial_{user_id}"):
        bot.reply_to(message, "❌ Вы уже использовали пробный период!")
        return
    days_left, _, _ = get_user_subscription_info(user_id)
    if days_left is not None and days_left != "expired":
        bot.reply_to(message, "❌ У вас уже есть активная подписка!")
        return
    # ИСПРАВЛЕНО: теперь 3 дня вместо 7
    link = create_user_subscription(user_id, 3, sub_type="", is_trial=True)
    if link:
        github_upload_file(f"trial_{user_id}", "used", folder="trials")
        bot.send_message(
            user_id,
            f"🎁 **Пробный период активирован!**\n\n"
            f"📅 Действует: 3 дня\n\n"
            f"🔗 **Ваша ссылка:**\n{link}\n\n"
            f"📱 Добавьте ссылку в v2rayNG"
        )
        bot.send_message(YOUR_ADMIN_ID, f"🎁 **ПРОБНЫЙ ПЕРИОД**\n👤 {user_id}")
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
        "🛠️ **Поддержка**\n\n"
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
    days_left, expiry_date, subscription_link = get_user_subscription_info(user_id)
    if days_left is None or days_left == "expired":
        bot.reply_to(message, "❌ У вас нет активной подписки! Используйте /start чтобы купить")
        return
    sub_type = get_user_subscription_type(user_id)
    if not sub_type:
        bot.reply_to(message, "❌ Не удалось определить тип подписки")
        return
    success = force_update_user_config(user_id, sub_type)
    if success:
        _, _, new_link = get_user_subscription_info(user_id)
        bot.reply_to(
            message,
            f"✅ **Ваш конфиг обновлен до последней версии!**\n\n"
            f"📱 Пожалуйста, обновите ссылку в приложении:\n{new_link}\n\n🔄 Новые сервера добавлены автоматически!\n\n⚠️ Удалите старую подписку и добавьте эту новую ссылку!",
            parse_mode='Markdown'
        )
        bot.send_message(YOUR_ADMIN_ID, f"🔄 Пользователь {user_id} обновил конфиг вручную")
    else:
        bot.reply_to(message, "❌ Ошибка при обновлении конфига. Попробуйте позже")

# ==================== КОМАНДЫ АДМИНА ====================
@bot.message_handler(commands=['pay'])
def admin_add_balance(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав для этой команды")
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
                bot.send_message(user_id, f"🎉 **Баланс пополнен!**\n\n💰 Сумма: {amount} 💵\n💰 Баланс: {new_balance} 💵", parse_mode='Markdown')
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

@bot.message_handler(commands=['update_all_configs'])
def admin_update_all_configs(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа")
        return
    bot.reply_to(message, "🔄 Начинаю обновление всех активных подписок... Это может занять время")
    Thread(target=update_all_active_subscriptions, args=(message.chat.id,)).start()

def update_all_active_subscriptions(admin_chat_id):
    updated = 0
    errors = 0
    skipped = 0
    users = get_all_users()
    bot.send_message(admin_chat_id, f"📊 Найдено {len(users)} пользователей. Начинаю обновление...")
    for user_id in users:
        days_left, _, _ = get_user_subscription_info(user_id)
        if days_left is None or days_left == "expired":
            skipped += 1
            continue
        sub_type = get_user_subscription_type(user_id)
        if not sub_type:
            sub_type = "full"
        if sub_type != "custom":
            if force_update_user_config(user_id, sub_type):
                updated += 1
                time.sleep(0.1)
            else:
                errors += 1
        else:
            skipped += 1
    report = f"✅ **ОБНОВЛЕНИЕ ЗАВЕРШЕНО**\n\n🔄 Обновлено: {updated}\n⏭️ Пропущено (неактивны/кастомные): {skipped}\n❌ Ошибок: {errors}\n📊 Всего проверено: {len(users)}"
    bot.send_message(admin_chat_id, report, parse_mode='Markdown')

@bot.message_handler(commands=['renew_all_links'])
def renew_all_links(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа")
        return
    bot.reply_to(message, "🔄 Обновляю ссылки для всех активных пользователей...")
    users = get_all_users()
    updated = 0
    for user_id in users:
        days_left, expiry_date, _ = get_user_subscription_info(user_id)
        if days_left and days_left != "expired" and days_left != "∞":
            sub_type = get_user_subscription_type(user_id)
            if not sub_type:
                sub_type = "full"
            if sub_type != "custom":
                new_link = create_user_subscription(user_id, days_left, sub_type, is_trial=False)
                if new_link:
                    bot.send_message(
                        user_id,
                        f"🔄 **Ежемесячное обновление VPN**\n\n"
                        f"Ваша новая ссылка (старая больше не действительна):\n{new_link}\n\n"
                        f"Пожалуйста, удалите старую подписку в v2rayNG и добавьте эту новую ссылку.\n"
                        f"Действует до: {expiry_date}"
                    )
                    updated += 1
                    time.sleep(0.3)
    bot.reply_to(message, f"✅ Обновлено ссылок для {updated} пользователей.")

@bot.message_handler(commands=['check'])
def check_subs(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа")
        return
    user_id = message.from_user.id
    reply = f"🔍 ДИАГНОСТИКА ДЛЯ user_id: {user_id}\n\n"
    found = False
    for folder in ["def-sub", "ultra-sub", "full-sub", "fast-sub", "trial-sub", "custom-sub"]:
        test_file = f"subscriptions/{folder}/user_{user_id}.expiry"
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{test_file}", headers={"Authorization": f"token {GITHUB_TOKEN}"})
        if r.status_code == 200:
            content = base64.b64decode(r.json()["content"]).decode('utf-8')
            reply += f"✅ Файл найден в папке {folder}/\n📅 Содержимое: {content}\n"
            now, expiry = int(time.time()), int(content.strip())
            reply += f"⏰ ПОДПИСКА ИСТЕКЛА\n" if now > expiry else f"✅ ПОДПИСКА АКТИВНА, осталось {(expiry - now) // 86400} дней\n"
            found = True
            break
    if not found:
        reply += f"❌ Файл НЕ НАЙДЕН ни в одной папке\n"
    bot.reply_to(message, reply)

# ==================== CALLBACK ОБРАБОТЧИКИ ====================
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

@bot.callback_query_handler(func=lambda call: call.data == 'sub_def')
def sub_def_menu(call):
    text = "💵 **DEF-SUB** — Только VPN\n\n💰 **Цены:**\n• 30 дней — 0.5 TON / 50⭐ / 50💵\n• 60 дней — 0.9 TON / 85⭐ / 90💵\n• 90 дней — 1.25 TON / 120⭐ / 135💵\n\nВыберите период:"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📆 30", callback_data="def_30"), InlineKeyboardButton("📆 60", callback_data="def_60"), InlineKeyboardButton("📆 90", callback_data="def_90"))
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="buy_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'sub_ultra')
def sub_ultra_menu(call):
    text = "⭐ **ULTRA-SUB** — Лучшие серверы\n\n💰 **Цены:**\n• 30 дней — 0.7 TON / 75⭐ / 75💵\n• 60 дней — 1.2 TON / 120⭐ / 130💵\n• 90 дней — 1.7 TON / 170⭐ / 190💵\n\nВыберите период:"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📆 30", callback_data="ultra_30"), InlineKeyboardButton("📆 60", callback_data="ultra_60"), InlineKeyboardButton("📆 90", callback_data="ultra_90"))
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="buy_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'sub_full')
def sub_full_menu(call):
    text = "🔑 **FULL-SUB** — Все серверы\n\n💰 **Цены:**\n• 30 дней — 1 TON / 100⭐ / 100💵\n• 60 дней — 1.75 TON / 170⭐ / 170💵\n• 90 дней — 2.5 TON / 250⭐ / 275💵\n\nВыберите период:"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📆 30", callback_data="full_30"), InlineKeyboardButton("📆 60", callback_data="full_60"), InlineKeyboardButton("📆 90", callback_data="full_90"))
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="buy_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'sub_fast')
def sub_fast_menu(call):
    text = "🛡️ **FAST-SUB** — Максимальная скорость\n\n💰 **Цены:**\n• 30 дней — 1.5 TON / 150⭐ / 150💵\n• 60 дней — 2.5 TON / 250⭐ / 250💵\n• 90 дней — 3.5 TON / 350⭐ / 350💵\n\nВыберите период:"
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📆 30", callback_data="fast_30"), InlineKeyboardButton("📆 60", callback_data="fast_60"), InlineKeyboardButton("📆 90", callback_data="fast_90"))
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data="buy_menu"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# ==================== ПЕРИОДЫ ====================
def process_period(call, sub_type, days, ton, stars, bal):
    pending_payments[call.from_user.id] = {"days": days, "sub_type": sub_type}
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("💎 TON", callback_data=f"ton_{days}_{ton}"), InlineKeyboardButton("⭐ Stars", callback_data=f"stars_{days}_{stars}"))
    keyboard.row(InlineKeyboardButton("💰 Баланс", callback_data=f"balance_{days}_{bal}"))
    keyboard.row(InlineKeyboardButton("◀️ Назад", callback_data=f"sub_{sub_type}"))
    bot.edit_message_text(f"💳 **Способ оплаты**\n\n📅 {days} дней\n💎 TON: {ton}\n⭐ Stars: {stars}\n💰 Баланс: {bal} 💵",
                          call.message.chat.id, call.message.message_id, reply_markup=keyboard, parse_mode='Markdown')
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('def_'))
def def_period(call):
    days = int(call.data.split('_')[1])
    prices = {30: (0.5,50,50), 60: (0.9,85,90), 90: (1.25,120,135)}
    process_period(call, "def", days, *prices[days])

@bot.callback_query_handler(func=lambda call: call.data.startswith('ultra_'))
def ultra_period(call):
    days = int(call.data.split('_')[1])
    prices = {30: (0.7,75,75), 60: (1.2,120,130), 90: (1.7,170,190)}
    process_period(call, "ultra", days, *prices[days])

@bot.callback_query_handler(func=lambda call: call.data.startswith('full_'))
def full_period(call):
    days = int(call.data.split('_')[1])
    prices = {30: (1,100,100), 60: (1.75,170,170), 90: (2.5,250,275)}
    process_period(call, "full", days, *prices[days])

@bot.callback_query_handler(func=lambda call: call.data.startswith('fast_'))
def fast_period(call):
    days = int(call.data.split('_')[1])
    prices = {30: (1.5,150,150), 60: (2.5,250,250), 90: (3.5,350,350)}
    process_period(call, "fast", days, *prices[days])

# ==================== ОБРАБОТЧИКИ ОПЛАТЫ ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('balance_') and not call.data.startswith('balance_custom'))
def handle_balance_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    balance_amount = int(parts[2])
    user_id = call.from_user.id
    sub_type = pending_payments.get(user_id, {}).get("sub_type", "full")
    balance = get_balance(user_id)
    if balance < balance_amount:
        bot.answer_callback_query(call.id, f"❌ Недостаточно средств! Баланс: {balance} 💵", show_alert=True)
        return
    success, new_balance = deduct_balance(user_id, balance_amount)
    if not success:
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)
        return
    link = create_user_subscription(user_id, days, sub_type, is_trial=False)
    if link:
        bot.send_message(call.message.chat.id, f"✅ **Подписка создана!**\n💰 {balance_amount} 💵\n💰 Остаток: {new_balance} 💵\n📅 {days} дней\n\n🔗 {link}")
        bot.send_message(YOUR_ADMIN_ID, f"💰 ОПЛАТА БАЛАНСОМ!\n👤 {user_id}\n💰 {balance_amount} 💵")
        bot.answer_callback_query(call.id, "✅ Оплачено!")
    else:
        update_balance(user_id, balance_amount)
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ton_') and not call.data.startswith('ton_custom'))
def handle_ton_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount_ton = float(parts[2])
    user_id = call.from_user.id
    sub_type = pending_payments.get(user_id, {}).get("sub_type", "full")
    pending_payments[user_id] = {"days": days, "ton": amount_ton, "sub_type": sub_type, "start_time": time.time()}
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Я перевел(а)", callback_data=f"check_{days}_{amount_ton}_{sub_type}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    bot.send_message(call.message.chat.id, f"💳 **Оплата TON**\n\n💰 {amount_ton} TON\n📅 {days} дней\n\n**Кошелёк:**\n`{TON_WALLET}`\n\nПереведите и нажмите «✅ Я перевел»\n⏰ 10 минут", reply_markup=keyboard, parse_mode='Markdown')
    bot.send_message(YOUR_ADMIN_ID, f"💳 НАЧАЛО ОПЛАТЫ TON\n👤 {user_id}\n💰 {amount_ton} TON")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stars_') and not call.data.startswith('stars_custom'))
def handle_stars_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    stars_amount = int(parts[2])
    user_id = call.from_user.id
    sub_type = pending_payments.get(user_id, {}).get("sub_type", "full")
    send_stars_invoice(user_id, days, stars_amount, sub_type)
    bot.answer_callback_query(call.id, "⭐ Счёт отправлен!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def handle_check_payment(call):
    parts = call.data.split('_')
    days, amount_ton, sub_type = int(parts[1]), float(parts[2]), parts[3]
    bot.send_message(call.message.chat.id, "⏳ Проверяем оплату...")
    Thread(target=monitor_payment, args=(call.from_user.id, amount_ton, days, sub_type)).start()
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_payment(call):
    pending_payments.pop(call.from_user.id, None)
    bot.send_message(call.message.chat.id, "❌ Оплата отменена")
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

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    setup_main_menu_button()
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("🌐 Веб-сервер запущен на порту 10000")
    print("🤖 Бот запущен. Репозиторий должен быть ПУБЛИЧНЫМ!")
    print("🔒 Включена проверка подписки на канал @" + REQUIRED_CHANNEL)
    print("⚙️ Добавлена функция КАСТОМНОГО КОНФИГУРАТОРА с подробным описанием!")
    print("❌ Добавлены кнопки ОТМЕНЫ для всех этапов оплаты!")
    print("📍 Добавлена кнопка ЛОКАЦИИ с фото и статьей!")
    print("📚 Добавлена кнопка ПОЛИТИКА КОНФИДЕНЦИАЛЬНОСТИ!")
    print("🎁 ИСПРАВЛЕНО: пробный период теперь 3 дня (было 7)!")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)
