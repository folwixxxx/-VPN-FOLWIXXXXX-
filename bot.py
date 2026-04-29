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

# ==================== ЦЕНЫ ДЛЯ ПОДПИСКИ ALL-SUB ====================
PRICE_TON = 2.0
PRICE_STARS = 200
PRICE_BALANCE = 200

# ==================== КАНАЛ ДЛЯ ПРОВЕРКИ ПОДПИСКИ ====================
REQUIRED_CHANNEL = "folwixxxvpn"
CHANNEL_URL = f"https://t.me/{REQUIRED_CHANNEL}"

# Проверка
if not all([TELEGRAM_TOKEN, GITHUB_TOKEN, GITHUB_REPO, TON_WALLET, TON_API_KEY]):
    raise Exception("❌ Ошибка: не все переменные окружения заданы!")

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
bot = telebot.TeleBot(TELEGRAM_TOKEN)
pending_payments = {}

YOUR_ADMIN_ID = 8684879669
YOUR_USERNAME = "ylvvvl"

BANNER_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/banner.jpg"
LOCATIONS_IMAGE_URL = "https://raw.githubusercontent.com/folwixxxx/-VPN-FOLWIXXXXX-/main/locations.jpg"

# Шаблон конфига ALL-SUB (все серверы из твоего JSON)
ALL_SUB_CONFIG_TEMPLATE = '''{
  "log": {
    "loglevel": "warning"
  },
  "dns": {
    "queryStrategy": "UseIPv4",
    "servers": [
      "1.1.1.1",
      "1.0.0.1",
      "8.8.8.8",
      "8.8.4.4"
    ]
  },
  "inbounds": [
    {
      "tag": "socks",
      "port": 10808,
      "listen": "127.0.0.1",
      "protocol": "socks",
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"],
        "routeOnly": true
      },
      "settings": {
        "auth": "noauth",
        "udp": true
      }
    },
    {
      "tag": "http",
      "port": 10809,
      "listen": "127.0.0.1",
      "protocol": "http",
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls", "quic"],
        "routeOnly": true
      },
      "settings": {
        "allowTransparent": false
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    },
    {
      "tag": "eu-01",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "se1.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "api-maps.yandex.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/sQY4PvWWhy-j63WD"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-02",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "nl1.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/I7E9lOYqn_zKCIrH"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-03",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "nl2.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/I7E9lOYqn_zKCIrH"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-04",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "nl3.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/I7E9lOYqn_zKCIrH"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-05",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "us.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "smartcaptcha.yandexcloud.net",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/GAdLkgm4EIWmGloo"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-06",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "de1.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/lMeBktGz_X4CrJW4"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-07",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "de3.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/lMeBktGz_X4CrJW4"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-08",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "de5.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "max.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/lMeBktGz_X4CrJW4"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-09",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "fi2.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "5post-gate.x5.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/FBpmkpJEzwiJNY49"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-10",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "fi3.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "5post-gate.x5.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/FBpmkpJEzwiJNY49"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-11",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "pl1.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "5post-gate.x5.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/-HJtn9M1T1z65cFq"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-12",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "pl2.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "5post-gate.x5.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/-HJtn9M1T1z65cFq"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-13",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "pl3.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "5post-gate.x5.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/-HJtn9M1T1z65cFq"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-14",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "cz.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "ya.ru",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/D-hYPVL7F0EXf0lD"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-15",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "lv1.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "sun9-37.userapi.com",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/SLBpDI4hSZpKOIdZ"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "eu-16",
      "protocol": "vless",
      "settings": {
        "vnext": [
          {
            "address": "lv2.hellahillz.net",
            "port": 443,
            "users": [
              {
                "id": "f14b71e0-38cf-487c-ab14-47a227d8519d",
                "security": "auto",
                "encryption": "none",
                "email": "user@hellahillz.net",
                "alterId": 0,
                "flow": "xtls-rprx-vision",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "serverName": "sun9-37.userapi.com",
          "fingerprint": "randomized",
          "show": false,
          "publicKey": "XvCnLU7hoBeYN9KloeaEvgSVnCCbrnMc3cl3NSHaeSo",
          "shortId": "ad921688161df51c",
          "spiderX": "/SLBpDI4hSZpKOIdZ"
        },
        "sockopt": {
          "domainStrategy": "UseIP",
          "tcpMaxSeg": 1440
        }
      }
    },
    {
      "tag": "dialer",
      "protocol": "freedom",
      "settings": {
        "fragment": {
          "packets": "tlshello",
          "length": "50-100",
          "interval": "10-20",
          "maxSplit": "100-200"
        },
        "noises": [
          {
            "type": "rand",
            "packet": "10-20",
            "delay": "10-16",
            "applyTo": "ipv4"
          }
        ]
      }
    }
  ],
  "routing": {
    "domainMatcher": "hybrid",
    "domainStrategy": "IPIfNonMatch",
    "balancers": [
      {
        "tag": "lb_best",
        "selector": [
          "eu-01", "eu-02", "eu-03", "eu-04", "eu-05", "eu-06", "eu-07", "eu-08",
          "eu-09", "eu-10", "eu-11", "eu-12", "eu-13", "eu-14", "eu-15", "eu-16"
        ],
        "fallbackTag": "eu-01",
        "strategy": {
          "type": "leastLoad",
          "settings": {
            "costs": [
              {"regexp": false, "match": "eu-01", "value": 1000},
              {"regexp": false, "match": "eu-05", "value": 1000}
            ],
            "baselines": ["300ms", "600ms"],
            "expected": 2,
            "maxRTT": "5s"
          }
        }
      }
    ],
    "rules": [
      {"outboundTag": "block", "protocol": ["bittorrent"], "type": "field"},
      {"outboundTag": "block", "port": "6881-6999", "type": "field"},
      {"balancerTag": "lb_best", "inboundTag": ["socks", "http"], "network": "tcp,udp", "type": "field"}
    ]
  },
  "burstObservatory": {
    "pingConfig": {
      "connectivity": "https://www.gstatic.com/generate_204",
      "destination": "https://www.gstatic.com/generate_204",
      "interval": "300s",
      "sampling": 3,
      "timeout": "5s"
    },
    "subjectSelector": [
      "eu-01", "eu-02", "eu-03", "eu-04", "eu-05", "eu-06", "eu-07", "eu-08",
      "eu-09", "eu-10", "eu-11", "eu-12", "eu-13", "eu-14", "eu-15", "eu-16"
    ]
  },
  "remarks": "🇪🇺 ALL-SUB ⚡ 16 серверов",
  "policy": {
    "levels": {
      "8": {
        "handshake": 4,
        "connIdle": 300,
        "uplinkOnly": 5,
        "downlinkOnly": 5
      }
    }
  }
}'''

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
    if github_get_file_content(f"subscriptions/all-sub/user_{user_id}.expiry"):
        return "all-sub"
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

def force_update_user_config(user_id):
    """Обновляет конфиг пользователя из шаблона"""
    template_content = ALL_SUB_CONFIG_TEMPLATE
    folder = "all-sub"
    
    template_content = template_content.replace(
        '"remarks": "🇪🇺 ALL-SUB ⚡ 16 серверов"',
        f'"remarks": "🇪🇺 ALL-SUB {user_id}"'
    )
    template_content += f"\n// Обновлено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    success = github_upload_file(f"user_{user_id}.txt", template_content, folder=f"subscriptions/{folder}")
    if not success:
        return False
    github_upload_file(f"user_{user_id}.type", "all", folder=f"subscriptions/{folder}")
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

def monitor_payment(user_id, amount_ton, days):
    start_time = time.time()
    while time.time() - start_time < 600:
        if check_ton_transaction(amount_ton, user_id):
            bot.send_message(user_id, f"✅ Оплата {amount_ton} TON получена! Создаю подписку...")
            link = create_subscription(user_id, days)
            if link:
                bot.send_message(user_id, f"✅ **Подписка ALL-SUB создана!**\n\n🔗 {link}\n\n📅 Действует: {days} дней\n\n🌍 16 серверов с автовыбором\n📱 Добавьте ссылку в v2rayNG")
                bot.send_message(YOUR_ADMIN_ID, f"✅ **УСПЕШНАЯ ОПЛАТА!**\n\n👤 Пользователь: `{user_id}`\n💰 Сумма: {amount_ton} TON\n📅 Период: {days} дней\n📦 Тип: ALL-SUB")
            else:
                bot.send_message(user_id, "❌ Ошибка при создании подписки")
            return True
        time.sleep(15)
    bot.send_message(user_id, "⏰ Время ожидания оплаты истекло. Попробуйте снова /start")
    return False

# ==================== ОПЛАТА STARS ====================
def send_stars_invoice(user_id, days, stars_amount):
    title = f"⭐ ALL-SUB {days}д"
    prices = [LabeledPrice(label="VPN подписка ALL-SUB (16 серверов)", amount=stars_amount)]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(f"⭐ Оплатить {stars_amount} Stars", pay=True))
    try:
        bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=f"Подписка ALL-SUB на {days} дней\n\n✅ 16 серверов\n✅ Автовыбор лучшего\n✅ Безлимитный трафик\n✅ Обход блокировок",
            invoice_payload=f"stars_{days}_{stars_amount}",
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

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    payment = message.successful_payment
    user_id = message.from_user.id
    payload = payment.invoice_payload
    print(f"⭐ УСПЕШНАЯ ОПЛАТА! payload={payload}")
    
    parts = payload.split('_')
    if len(parts) >= 3 and parts[0] == "stars":
        days = int(parts[1])
        stars_amount = int(parts[2])
        link = create_subscription(user_id, days)
        if link:
            bot.send_message(
                user_id,
                f"✅ **Подписка ALL-SUB создана!**\n\n"
                f"⭐ Оплачено: {stars_amount} Stars\n"
                f"📅 Период: {days} дней\n"
                f"🌍 16 серверов с автовыбором\n\n"
                f"🔗 {link}\n\n"
                f"📱 Добавьте ссылку в v2rayNG"
            )
            bot.send_message(YOUR_ADMIN_ID, f"⭐ **ОПЛАТА STARS!**\n👤 {user_id}\n⭐ {stars_amount}\n📅 {days}д\n📦 ALL-SUB")

# ==================== ФУНКЦИИ ПОДПИСОК ====================
def create_subscription(user_id, days=30):
    filename = f"user_{user_id}"
    folder = "all-sub"
    
    # Создаём конфиг из шаблона
    config_content = ALL_SUB_CONFIG_TEMPLATE
    config_content = config_content.replace(
        '"remarks": "🇪🇺 ALL-SUB ⚡ 16 серверов"',
        f'"remarks": "🇪🇺 ALL-SUB {user_id} ({days} дней)"'
    )
    
    expiry_date = datetime.now() + timedelta(days=days)
    expiry_date_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
    expiry_timestamp = int(expiry_date.timestamp())
    
    header = f"""#subscription-userinfo: upload=0; download=0; total=0; expire={expiry_timestamp}
# profile-title: ALL-SUB {user_id}
# profile-update-interval: 1440
# expire: {expiry_date_str}
# days: {days}
# servers: 16
# created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    full_content = header + config_content
    
    success = github_upload_file(f"{filename}.txt", full_content, folder=f"subscriptions/{folder}")
    if not success:
        return None
    success = github_upload_file(f"{filename}.expiry", str(expiry_timestamp), folder=f"subscriptions/{folder}")
    if not success:
        return None
    github_upload_file(f"{filename}.type", "all", folder=f"subscriptions/{folder}")
    
    return f"{RAW_BASE}/subscriptions/{folder}/{filename}.txt?t={int(time.time())}"

def get_user_subscription_info(user_id):
    content = github_get_file_content(f"subscriptions/all-sub/user_{user_id}.expiry")
    if content:
        try:
            expiry_timestamp = int(content.strip())
            now = int(time.time())
            if now > expiry_timestamp:
                return None, None, None
            days_left = (expiry_timestamp - now) // 86400
            expiry_date = datetime.fromtimestamp(expiry_timestamp).strftime("%d.%m.%Y %H:%M:%S")
            subscription_link = f"{RAW_BASE}/subscriptions/all-sub/user_{user_id}.txt?t={int(time.time())}"
            return days_left, expiry_date, subscription_link
        except Exception as e:
            print(f"Ошибка: {e}")
            return None, None, None
    return None, None, None

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
    
    keyboard.row(
        InlineKeyboardButton("👤 Профиль", callback_data="profile"),
        InlineKeyboardButton("💰 Купить VPN", callback_data="buy_menu")
    )
    keyboard.row(
        InlineKeyboardButton("🎁 Пробный период", callback_data="trial"),
        InlineKeyboardButton("🛠️ Поддержка", callback_data="support")
    )
    keyboard.row(
        InlineKeyboardButton("⚠️ Канал с новостями", url=CHANNEL_URL),
        InlineKeyboardButton("📱 Инструкция", web_app=WebAppInfo(url=f"https://folwixxxx.github.io/-VPN-FOLWIXXXXX-/instructions.html?user_id={message.from_user.id}"))
    )
    keyboard.row(
        InlineKeyboardButton("📍 Локации", callback_data="locations"),
        InlineKeyboardButton("📚 Политика", callback_data="privacy_policy")
    )
    
    caption = (
        "💻 **Добро пожаловать в FOLWIXXX VPN сервис!**\n\n"
        "✅ Быстрые серверы\n"
        "✅ Обход ограничений\n"
        "✅ Безлимитный трафик\n\n"
        "**📦 ЕДИНЫЙ ТАРИФ ALL-SUB**\n"
        "🌍 **16 серверов** (Нидерланды, Германия, Финляндия, Польша, Латвия, Чехия, США)\n"
        "⚡ **Автоматический выбор лучшего сервера**\n"
        "🔒 **Блокировка рекламы и трекеров**\n\n"
        "💰 **Цена:** 2 TON / 200⭐ / 200💵 (30 дней)\n\n"
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
        text += "📅 Статус: ❌ **Нет активной подписки**\n\n💡 Используйте /buy для покупки ALL-SUB"
    else:
        text += f"📦 **ТАРИФ: ALL-SUB**\n"
        text += f"🌍 16 серверов с автовыбором\n"
        text += f"📅 Статус: ✅ **Активна**\n"
        text += f"📅 Осталось дней: {days_left}\n"
        text += f"📅 Действует до: `{expiry_date}`\n"
        text += f"🔗 Ссылка для v2rayNG:\n`{subscription_link}`\n\n"
        text += f"🔄 Конфиг обновляется автоматически\n"
        text += f"⚠️ Если не работает - удалите старую и добавьте эту ссылку заново"
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
        "🌍 **16 серверов:**\n"
        "🇳🇱 Нидерланды (3 сервера)\n"
        "🇩🇪 Германия (3 сервера)\n"
        "🇫🇮 Финляндия (2 сервера)\n"
        "🇵🇱 Польша (3 сервера)\n"
        "🇱🇻 Латвия (2 сервера)\n"
        "🇨🇿 Чехия (1 сервер)\n"
        "🇺🇸 США (1 сервер)\n\n"
        "⚡ **Автовыбор лучшего сервера**\n"
        "🔒 **Встроенная блокировка рекламы и трекеров**\n\n"
        "💰 **Цены:**\n"
        "• 30 дней — 2 TON / 200⭐ / 200💵\n"
        "• 60 дней — 3.5 TON / 350⭐ / 350💵\n"
        "• 90 дней — 5 TON / 500⭐ / 500💵\n\n"
        "📅 Выберите период:",
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
        f"🌍 16 серверов с автовыбором\n\n"
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
    if days_left is not None and days_left != "expired":
        bot.reply_to(message, "❌ У вас уже есть активная подписка!")
        return
    
    link = create_subscription(user_id, 3)
    if link:
        github_upload_file(f"trial_{user_id}", "used", folder="trials")
        bot.send_message(
            user_id,
            f"🎁 **Пробный период ALL-SUB активирован!**\n\n"
            f"🌍 16 серверов с автовыбором\n"
            f"📅 Действует: 3 дня\n\n"
            f"🔗 **Ваша ссылка:**\n{link}\n\n"
            f"📱 Добавьте ссылку в v2rayNG"
        )
        bot.send_message(YOUR_ADMIN_ID, f"🎁 **ПРОБНЫЙ ПЕРИОД ALL-SUB**\n👤 {user_id}")
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
    days_left, exp_date, _ = get_user_subscription_info(user_id)
    if days_left is None:
        bot.reply_to(message, "❌ У вас нет активной подписки!")
        return
    success = force_update_user_config(user_id)
    if success:
        _, _, new_link = get_user_subscription_info(user_id)
        bot.reply_to(
            message,
            f"✅ **Ваш конфиг ALL-SUB обновлен!**\n\n"
            f"📱 Обновите ссылку в приложении:\n{new_link}\n\n"
            f"🌍 Все 16 серверов добавлены автоматически!",
            parse_mode='Markdown'
        )
    else:
        bot.reply_to(message, "❌ Ошибка при обновлении")

# ==================== КОМАНДЫ АДМИНА ====================
@bot.message_handler(commands=['pay'])
def admin_add_balance(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    parts = message.text.split()
    if len(parts) != 3:
        bot.reply_to(message, "❌ Использование: /pay `user_id` `сумма`")
        return
    try:
        user_id = int(parts[1])
        amount = float(parts[2])
        if amount <= 0:
            bot.reply_to(message, "❌ Сумма должна быть положительной")
            return
        success, new_balance = update_balance(user_id, amount)
        if success:
            bot.reply_to(message, f"✅ Баланс `{user_id}` пополнен на {amount} 💵\n💰 Текущий баланс: {new_balance} 💵", parse_mode='Markdown')
            bot.send_message(user_id, f"🎉 **Баланс пополнен!**\n\n💰 Сумма: {amount} 💵\n💰 Баланс: {new_balance} 💵\n\n💡 Используйте /buy для покупки ALL-SUB", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Неверный формат")

@bot.message_handler(commands=['users_count'])
def users_count(message):
    if message.from_user.id != YOUR_ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа")
        return
    users = get_all_users()
    bot.reply_to(message, f"👥 Всего пользователей: {len(users)}")

# ==================== CALLBACK ОБРАБОТЧИКИ ОПЛАТЫ ====================
@bot.callback_query_handler(func=lambda call: call.data.startswith('balance_'))
def handle_balance_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    balance_amount = int(parts[2])
    user_id = call.from_user.id
    balance = get_balance(user_id)
    
    if balance < balance_amount:
        bot.answer_callback_query(call.id, f"❌ Недостаточно средств! Баланс: {balance} 💵", show_alert=True)
        return
    
    success, new_balance = deduct_balance(user_id, balance_amount)
    if not success:
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)
        return
    
    link = create_subscription(user_id, days)
    if link:
        bot.send_message(call.message.chat.id, 
            f"✅ **Подписка ALL-SUB создана!**\n"
            f"💰 {balance_amount} 💵\n"
            f"💰 Остаток: {new_balance} 💵\n"
            f"📅 {days} дней\n"
            f"🌍 16 серверов\n\n"
            f"🔗 {link}")
        bot.send_message(YOUR_ADMIN_ID, f"💰 ОПЛАТА БАЛАНСОМ!\n👤 {user_id}\n💰 {balance_amount} 💵\n📅 {days}д\n📦 ALL-SUB")
        bot.answer_callback_query(call.id, "✅ Оплачено!")
    else:
        update_balance(user_id, balance_amount)
        bot.answer_callback_query(call.id, "❌ Ошибка", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('ton_'))
def handle_ton_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount_ton = float(parts[2])
    user_id = call.from_user.id
    pending_payments[user_id] = {"days": days}
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Я перевел(а)", callback_data=f"check_{days}_{amount_ton}"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    bot.send_message(call.message.chat.id, 
        f"💳 **Оплата TON для ALL-SUB**\n\n"
        f"💰 {amount_ton} TON\n"
        f"📅 {days} дней\n"
        f"🌍 16 серверов\n\n"
        f"**Кошелёк:**\n`{TON_WALLET}`\n\n"
        f"Переведите и нажмите «✅ Я перевел»\n⏰ 10 минут",
        reply_markup=keyboard, parse_mode='Markdown')
    bot.send_message(YOUR_ADMIN_ID, f"💳 НАЧАЛО ОПЛАТЫ TON\n👤 {user_id}\n💰 {amount_ton} TON\n📦 ALL-SUB")
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stars_'))
def handle_stars_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    stars_amount = int(parts[2])
    user_id = call.from_user.id
    send_stars_invoice(user_id, days, stars_amount)
    bot.answer_callback_query(call.id, "⭐ Счёт отправлен!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('check_'))
def handle_check_payment(call):
    parts = call.data.split('_')
    days = int(parts[1])
    amount_ton = float(parts[2])
    bot.send_message(call.message.chat.id, "⏳ Проверяем оплату...")
    Thread(target=monitor_payment, args=(call.from_user.id, amount_ton, days)).start()
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_payment(call):
    pending_payments.pop(call.from_user.id, None)
    bot.send_message(call.message.chat.id, "❌ Оплата отменена")
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

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    setup_main_menu_button()
    web_thread = Thread(target=run_web_server, daemon=True)
    web_thread.start()
    print("🌐 Веб-сервер запущен на порту 10000")
    print("🤖 Бот запущен. Репозиторий должен быть ПУБЛИЧНЫМ!")
    print("📦 ЕДИНЫЙ ТАРИФ ALL-SUB — 16 серверов, цена 2 TON / 200⭐ / 200💵")
    print("🎁 Пробный период 3 дня")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            time.sleep(10)
