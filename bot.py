#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SELF DARK | سلف دارک — ربات سازنده سلف + تبچی + الماس + خرید با گرام
نسخه: SELF-DARK-V1 | اجرا روی Render با Webhook + Telethon (سلف‌ها)
تک‌فایل، آماده گیت‌هاب و رندر.
"""
import os
import re
import sys
import json
import time
import html
import random
import sqlite3
import traceback
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types
from flask import Flask, request

try:
    from telethon.sync import TelegramClient, events
    from telethon.sessions import StringSession
    from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
    from telethon.tl.functions.account import UpdateProfileRequest
    TELETHON_OK = True
except Exception as _e:
    TELETHON_OK = False
    TelegramClient = None
    events = None
    StringSession = None
    print("[SELF-DARK] Telethon import failed:", _e, flush=True)

try:
    import requests
    REQUESTS_OK = True
except Exception:
    REQUESTS_OK = False

# ============================================================
# تنظیمات اصلی (با مقادیر پیش‌فرض داخل کد؛ بدون نیاز به Env)
# ============================================================
BOT_VERSION = "SELF-DARK-V1.1"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8315326974:AAGnH1KEiDKw93u-JBV23OrPOe_jQYpTwXw").strip()
try:
    ADMIN_ID = int(os.environ.get("ADMIN_ID", "8248647747"))
except Exception:
    ADMIN_ID = 8248647747
BOT_USERNAME = os.environ.get("BOT_USERNAME", "@selfbuilddarkbot").strip()
try:
    API_ID = int(os.environ.get("API_ID", "32063619"))
except Exception:
    API_ID = 32063619
API_HASH = os.environ.get("API_HASH", "9a80695b6e3fdfdae22ec69dc110b954").strip()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")

# پیش‌فرض‌های اقتصادی
D_SELF_COST = 10.0        # هزینه فعال‌سازی سلف (الماس)
D_REF_REWARD = 5.0        # پاداش هر زیرمجموعه (الماس)
D_DIAMOND_PRICE = 0.0005  # قیمت هر ۱ الماس به گرام
D_MIN_BUY = 30.0          # حداقل خرید الماس
D_HOURLY_FEE = 4.0        # کسر ساعتی سلف روشن (الماس)
D_TRANSFER_FEE = 0.03     # کارمزد انتقال گروهی (۳٪)
D_WALLET = "UQxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # آدرس ولت گرام (ادمین عوضش می‌کند)

SELF_PREFIXES = (".", "سلف ", "/", "!")

# ۳۰ قابلیت سلف (۱۰تایی در هر صفحه)
FEATURES = [
    ("auto_reply", 1, "پاسخگویی خودکار هوشمند", "جواب خودکار و هوشمند به پیام‌های ورودی"),
    ("bio_rotate", 2, "تغییر خودکار بیوگرافی", "چرخش خودکار بیو با ساعت و تاریخ"),
    ("name_rotate", 3, "تغییر خودکار نام اکانت", "نام اکانت + ساعت زنده"),
    ("profile_schedule", 4, "زمان‌بندی تغییر پروفایل", "یادآور و چرخه هوشمند پروفایل"),
    ("account_status", 5, "مدیریت وضعیت اکانت", "حالت آنلاین/روح (خوانده‌نشده نگه‌داشتن)"),
    ("auto_translate", 6, "ترجمه خودکار پیام‌ها", "ترجمه پیام با دستور tr"),
    ("voice_to_text", 7, "تبدیل ویس به متن", "متن‌کردن پیام صوتی (نسخه پایه)"),
    ("summarize", 8, "خلاصه‌سازی پیام‌های طولانی", "خلاصه خودکار متن‌های بلند"),
    ("categorize", 9, "دسته‌بندی هوشمند پیام‌ها", "برچسب موضوعی خودکار"),
    ("save_deleted", 10, "ذخیره پیام‌های حذف‌شده", "ضدحذف: ذخیره در سیو مسج"),
    ("save_edits", 11, "ذخیره تاریخچه ویرایش پیام‌ها", "ثبت قبل/بعد ویرایش"),
    ("backup_chats", 12, "پشتیبان‌گیری از گفتگوها", "خروجی متنی گفتگوها"),
    ("adv_search", 13, "جستجوی پیشرفته پیام‌ها", "جستجو در پیام‌های اخیر"),
    ("auto_archive", 14, "بایگانی خودکار گفتگوها", "آرشیو خودکار گروه‌های ساکت"),
    ("chat_notes", 15, "یادداشت خصوصی برای هر گفتگو", "نکته اختصاصی هر چت"),
    ("auto_pin", 16, "سنجاق خودکار پیام‌های مهم", "پین خودکار پیام‌های #مهم"),
    ("reminders", 17, "یادآوری پیام‌ها", "یادآور زمانی داخل سلف"),
    ("quick_cmds", 18, "دستورات سریع اختصاصی", "میانبرهای آماده ارسال"),
    ("multi_account", 19, "مدیریت چند اکانت", "تا ۳ اکانت سلف همزمان"),
    ("reply_style", 20, "پاسخ با سبک دلخواه", "رسمی/دوستانه/فان/کوتاه"),
    ("sticker_suggest", 21, "پیشنهاد خودکار استیکر", "استیکر مناسب حال‌وهوای پیام"),
    ("emoji_suggest", 22, "پیشنهاد هوشمند شکلک", "اموجی مناسب هر پیام"),
    ("personal_cmds", 23, "ساخت دستورات شخصی", "دستور اختصاصی خودت را بساز"),
    ("notebook", 24, "دفترچه یادداشت خصوصی", "یادداشت‌های سریع شخصی"),
    ("daily_report", 25, "گزارش فعالیت روزانه", "آمار روزانه خودکار"),
    ("chat_stats", 26, "آمار گفتگوها و پیام‌ها", "شمارش پیام و چت‌ها"),
    ("scheduled_send", 27, "ارسال زمان‌بندی‌شده پیام‌ها", "ارسال در ساعت مشخص"),
    ("notif_manage", 28, "مدیریت هوشمند اعلان‌ها", "بی‌صدا کردن خودکار گروه‌های شلوغ"),
    ("tabchi", 29, "تبچی خودکار گروه‌ها", "ارسال خودکار بنر و متن"),
    ("smart_guard", 30, "نگهبان هوشمند سلف", "محافظت از سلف + هشدار ورود"),
]
FEATURE_KEYS = {k for k, _, _, _ in FEATURES}
FEATURE_BY_KEY = {k: (n, t, d) for k, n, t, d in FEATURES}

# متن‌های پیش‌فرض پاسخ خودکار
AUTO_REPLY_TEXTS = {
    "default": "سلام عزیز! 🌙 پیامت رسید، الان آنلاین نیستم ولی حتماً جواب میدم. ✨",
    "doostane": "سلام رفیق! 💜 پیامتو دیدم، یکم صبر کن الان جواب میدم 😊",
    "rasmi": "با سلام؛ پیام شما دریافت شد و در اولین فرصت پاسخ داده می‌شود. 🌙",
    "fun": "عه سلام! 😎 سلف دارک پیامتو قاپید! صاحب اکانت الان نیست ولی برمی‌گرده 🚀",
    "kootah": "رسید ✅",
}
BIO_ROTATE_LIST = [
    "🌙 | سلف دارک فعال است ✨",
    "💎 آنلاین با Self Dark 🚀",
    "🕒 {time} | {date} 🌙",
    "⚡ قدرت گرفته از SELF DARK",
    "💜 در دسترس نیستم، پیام بدید",
]


def log(*a):
    print(f"[{BOT_VERSION}]", *a, flush=True)


def now_tehran():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Tehran"))
    except Exception:
        return datetime.now() + timedelta(hours=3, minutes=30)


def now_str():
    return now_tehran().strftime("%Y-%m-%d %H:%M")


def today_str():
    return now_tehran().strftime("%Y-%m-%d")


def fmt_num(x):
    try:
        f = float(x)
    except Exception:
        return str(x)
    if f == int(f):
        return f"{int(f):,}"
    s = f"{f:,.4f}".rstrip("0").rstrip(".")
    return s


def fmt_gram(x):
    try:
        f = float(x)
    except Exception:
        return str(x)
    s = f"{f:.6f}".rstrip("0").rstrip(".")
    return s if s else "0"


def esc(s):
    return html.escape(str(s or ""), quote=False)


# ============================================================
# دیتابیس
# ============================================================
_db_lock = threading.RLock()


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=DELETE;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn


def init_db():
    with _db_lock:
        conn = get_conn()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
            diamonds REAL DEFAULT 0, referrals INTEGER DEFAULT 0, earned_ref REAL DEFAULT 0,
            total_bought REAL DEFAULT 0, total_spent REAL DEFAULT 0, total_transferred REAL DEFAULT 0,
            referrer_id INTEGER DEFAULT 0, pending_referrer INTEGER DEFAULT 0,
            join_date TEXT DEFAULT '', is_active INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0, join_confirmed INTEGER DEFAULT 0, created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS channels(
            id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT UNIQUE, title TEXT DEFAULT '', url TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS diamond_orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, diamonds REAL, gram_amount REAL,
            price_each REAL, wallet TEXT DEFAULT '', photo_file_id TEXT DEFAULT '',
            status TEXT DEFAULT 'pending', created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS transfers(
            id INTEGER PRIMARY KEY AUTOINCREMENT, from_id INTEGER, to_id INTEGER,
            amount REAL, fee REAL, created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS self_accounts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, phone TEXT DEFAULT '',
            session_string TEXT DEFAULT '', is_on INTEGER DEFAULT 0,
            activated_at TEXT DEFAULT '', last_billing TEXT DEFAULT '',
            login_step TEXT DEFAULT 'none', phone_code_hash TEXT DEFAULT '',
            temp_phone TEXT DEFAULT '', label TEXT DEFAULT '', created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS self_toggles(
            user_id INTEGER, feature_key TEXT, is_on INTEGER DEFAULT 0, extra TEXT DEFAULT '',
            PRIMARY KEY(user_id, feature_key))""")
        c.execute("""CREATE TABLE IF NOT EXISTS tabchi_groups(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, account_id INTEGER DEFAULT 0,
            chat_id TEXT DEFAULT '', title TEXT DEFAULT '', banner_file_id TEXT DEFAULT '',
            banner_type TEXT DEFAULT '', text TEXT DEFAULT '', interval_min INTEGER DEFAULT 30,
            delay_sec INTEGER DEFAULT 5, is_on INTEGER DEFAULT 1,
            last_sent TEXT DEFAULT '', created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS notes(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chat_key TEXT DEFAULT '',
            note TEXT DEFAULT '', created TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS reminders(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, text TEXT DEFAULT '',
            remind_at TEXT DEFAULT '', done INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS scheduled_msgs(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, account_id INTEGER DEFAULT 0,
            chat_id TEXT DEFAULT '', text TEXT DEFAULT '', send_at TEXT DEFAULT '',
            sent INTEGER DEFAULT 0, repeat_min INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS activity_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, kind TEXT DEFAULT '',
            count INTEGER DEFAULT 0, day TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY, value TEXT)""")
        # مایگریشن ستون‌های احتمالی قدیمی
        try:
            cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
            for col, ddl in [("pending_referrer", "ALTER TABLE users ADD COLUMN pending_referrer INTEGER DEFAULT 0"),
                              ("total_transferred", "ALTER TABLE users ADD COLUMN total_transferred REAL DEFAULT 0"),
                              ("total_spent", "ALTER TABLE users ADD COLUMN total_spent REAL DEFAULT 0")]:
                if col not in cols:
                    try:
                        c.execute(ddl)
                    except Exception:
                        pass
        except Exception:
            pass
        try:
            scols = [r[1] for r in c.execute("PRAGMA table_info(self_accounts)").fetchall()]
            if "created" not in scols:
                try:
                    c.execute("ALTER TABLE self_accounts ADD COLUMN created TEXT DEFAULT ''")
                except Exception:
                    pass
        except Exception:
            pass
        defaults = {
            "bot_on": "1", "force_join_on": "1", "referral_on": "1",
            "ref_reward": str(D_REF_REWARD), "diamond_price": str(D_DIAMOND_PRICE),
            "wallet_address": D_WALLET, "self_cost": str(D_SELF_COST),
            "hourly_fee": str(D_HOURLY_FEE), "min_buy": str(D_MIN_BUY),
            "transfer_fee": str(D_TRANSFER_FEE), "support_username": "",
        }
        for k, v in defaults.items():
            try:
                c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
            except Exception:
                pass
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_self_user ON self_accounts(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_tabchi_user ON tabchi_groups(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON diamond_orders(status)")
        except Exception:
            pass
        conn.commit()
        conn.close()


def get_setting(key, default=""):
    try:
        conn = get_conn()
        r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        conn.close()
        if r and r["value"] is not None:
            return r["value"]
    except Exception:
        pass
    return default


def set_setting(key, value):
    with _db_lock:
        try:
            conn = get_conn()
            conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
            conn.commit()
            conn.close()
        except Exception:
            pass


def f_setting(key, default):
    try:
        return float(get_setting(key, str(default)))
    except Exception:
        return float(default)


def get_user(uid):
    try:
        conn = get_conn()
        r = conn.execute("SELECT * FROM users WHERE user_id=?", (int(uid),)).fetchone()
        conn.close()
        return dict(r) if r else None
    except Exception:
        return None


def ensure_user(u):
    """ساخت/به‌روزرسانی رکورد کاربر از آبجکت تلگرام. همیشه dict برمی‌گرداند."""
    uid = int(u.id)
    uname = (getattr(u, "username", "") or "").strip()
    fname = (getattr(u, "first_name", "") or "").strip()
    with _db_lock:
        conn = get_conn()
        try:
            r = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
            if not r:
                conn.execute(
                    "INSERT INTO users(user_id,username,first_name,diamonds,referrals,earned_ref,"
                    "total_bought,total_spent,total_transferred,referrer_id,pending_referrer,"
                    "join_date,is_active,banned,join_confirmed,created) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (uid, uname, fname, 0, 0, 0, 0, 0, 0, 0, 0, now_str(), 0, 0, 0, now_str()))
            else:
                conn.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", (uname, fname, uid))
            conn.commit()
            r = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
            conn.close()
            return dict(r) if r else {"user_id": uid, "username": uname, "first_name": fname,
                                      "diamonds": 0, "referrals": 0, "earned_ref": 0, "total_bought": 0,
                                      "total_spent": 0, "total_transferred": 0, "referrer_id": 0,
                                      "pending_referrer": 0, "join_date": now_str(), "is_active": 0,
                                      "banned": 0, "join_confirmed": 0}
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return {"user_id": uid, "username": uname, "first_name": fname, "diamonds": 0,
                    "referrals": 0, "earned_ref": 0, "total_bought": 0, "total_spent": 0,
                    "total_transferred": 0, "referrer_id": 0, "pending_referrer": 0,
                    "join_date": now_str(), "is_active": 0, "banned": 0, "join_confirmed": 0}


def update_user(uid, **kw):
    if not kw:
        return
    with _db_lock:
        try:
            conn = get_conn()
            cols = []
            vals = []
            for k, v in kw.items():
                cols.append(f"{k}=?")
                vals.append(v)
            vals.append(int(uid))
            conn.execute(f"UPDATE users SET {','.join(cols)} WHERE user_id=?", vals)
            conn.commit()
            conn.close()
        except Exception:
            pass


def add_diamonds(uid, amount):
    """افزودن (مثبت) یا کم‌کردن (منفی) الماس. خروجی: موجودی جدید."""
    with _db_lock:
        conn = get_conn()
        try:
            r = conn.execute("SELECT diamonds FROM users WHERE user_id=?", (int(uid),)).fetchone()
            bal = float(r["diamonds"] or 0) if r else 0.0
            bal += float(amount)
            if r:
                conn.execute("UPDATE users SET diamonds=? WHERE user_id=?", (bal, int(uid)))
            else:
                conn.execute("INSERT INTO users(user_id,diamonds,join_date,created) VALUES(?,?,?,?)",
                             (int(uid), bal, now_str(), now_str()))
            conn.commit()
            conn.close()
            return bal
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return 0.0


def get_channels():
    try:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM channels ORDER BY id").fetchall()
        conn.close()
        out = []
        for r in rows:
            d = dict(r)
            cid = str(d.get("chat_id", "") or "").strip()
            url = str(d.get("url", "") or "").strip()
            if not url and cid.startswith("@"):
                url = "https://t.me/" + cid[1:]
            d["chat_id"] = cid
            d["url"] = url
            out.append(d)
        return out
    except Exception:
        return []


def add_channel_db(chat_id, title, url):
    with _db_lock:
        conn = get_conn()
        try:
            conn.execute("INSERT OR REPLACE INTO channels(chat_id,title,url) VALUES(?,?,?)",
                         (chat_id, title, url))
            conn.commit()
        except Exception:
            pass
        conn.close()


def del_channel_db(chat_id):
    with _db_lock:
        conn = get_conn()
        try:
            conn.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))
            conn.commit()
        except Exception:
            pass
        conn.close()


def reset_join_confirmations():
    with _db_lock:
        try:
            conn = get_conn()
            conn.execute("UPDATE users SET join_confirmed=0 WHERE user_id!=?", (ADMIN_ID,))
            conn.commit()
            conn.close()
        except Exception:
            pass


def bump_activity(uid, kind, n=1):
    with _db_lock:
        try:
            conn = get_conn()
            day = today_str()
            r = conn.execute("SELECT id,count FROM activity_log WHERE user_id=? AND kind=? AND day=?",
                             (int(uid), kind, day)).fetchone()
            if r:
                conn.execute("UPDATE activity_log SET count=? WHERE id=?", (int(r["count"] or 0) + n, r["id"]))
            else:
                conn.execute("INSERT INTO activity_log(user_id,kind,count,day) VALUES(?,?,?,?)",
                             (int(uid), kind, n, day))
            conn.commit()
            conn.close()
        except Exception:
            pass


def get_toggle(uid, key):
    try:
        conn = get_conn()
        r = conn.execute("SELECT is_on,extra FROM self_toggles WHERE user_id=? AND feature_key=?",
                         (int(uid), key)).fetchone()
        conn.close()
        if r:
            return (int(r["is_on"] or 0), str(r["extra"] or ""))
    except Exception:
        pass
    return (0, "")


def set_toggle(uid, key, is_on, extra=None):
    with _db_lock:
        try:
            conn = get_conn()
            r = conn.execute("SELECT is_on,extra FROM self_toggles WHERE user_id=? AND feature_key=?",
                             (int(uid), key)).fetchone()
            ex = str(r["extra"] or "") if r else ""
            if extra is not None:
                ex = str(extra)
            conn.execute("INSERT OR REPLACE INTO self_toggles(user_id,feature_key,is_on,extra) VALUES(?,?,?,?)",
                         (int(uid), key, 1 if is_on else 0, ex))
            conn.commit()
            conn.close()
        except Exception:
            pass


def get_self_accounts(uid):
    try:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM self_accounts WHERE user_id=? ORDER BY id", (int(uid),)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_self_account_by_id(acc_id):
    try:
        conn = get_conn()
        r = conn.execute("SELECT * FROM self_accounts WHERE id=?", (int(acc_id),)).fetchone()
        conn.close()
        return dict(r) if r else None
    except Exception:
        return None


def update_self_account(acc_id, **kw):
    if not kw:
        return
    with _db_lock:
        try:
            conn = get_conn()
            cols = ",".join(f"{k}=?" for k in kw)
            conn.execute(f"UPDATE self_accounts SET {cols} WHERE id=?", (*list(kw.values()), int(acc_id)))
            conn.commit()
            conn.close()
        except Exception:
            pass

# ============================================================
# بخش دوم: ربات اصلی، منوها، جوین اجباری، حساب، خرید الماس
# ============================================================
bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
app = Flask(__name__)
user_state = {}
_state_lock = threading.RLock()


def set_state(uid, step, **kw):
    with _state_lock:
        d = {"step": step}
        d.update(kw)
        user_state[int(uid)] = d


def get_state(uid):
    with _state_lock:
        return dict(user_state.get(int(uid), {}))


def clear_state(uid):
    with _state_lock:
        user_state.pop(int(uid), None)


def is_admin(uid):
    return int(uid) == int(ADMIN_ID)


def bot_is_on():
    return get_setting("bot_on", "1") == "1"


def force_on():
    return get_setting("force_join_on", "1") == "1"


def referral_on():
    return get_setting("referral_on", "1") == "1"


def ref_link(uid):
    uname = (BOT_USERNAME or "").lstrip("@")
    return f"https://t.me/{uname}?start=ref_{int(uid)}"


def gb(t):
    """دکمه شیشه‌ای (استایل ✦)."""
    return f"✦ {t} ✦"


def panel_box(title, rows):
    L = ["╭━━━ ✦ " + str(title) + " ✦ ━━━╮"]
    for r in rows:
        L.append("┃ " + str(r))
    L.append("╰━━━━━━━━━━━━━━━╯")
    return "\n".join(L)


def main_menu_kb(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(types.KeyboardButton("💎 خرید الماس"), types.KeyboardButton("🤖 ساخت سلف"))
    kb.add(types.KeyboardButton("👤 حساب کاربری"), types.KeyboardButton("🎁 زیرمجموعه‌گیری"))
    kb.add(types.KeyboardButton("📖 راهنما"), types.KeyboardButton("📞 پشتیبانی"))
    if is_admin(uid):
        kb.add(types.KeyboardButton("🛠 پنل ادمین"))
    return kb


def back_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(types.KeyboardButton("🔙 بازگشت به منو"))
    return kb


def check_membership(uid):
    """بررسی عضویت؛ خروجی: (all_ok, missing_list). خطای فنی = عبور با لاگ."""
    if not force_on():
        return True, []
    chs = get_channels()
    if not chs:
        return None, []
    missing = []
    for ch in chs:
        cid = ch.get("chat_id", "")
        try:
            m = bot.get_chat_member(cid, int(uid))
            st = getattr(m, "status", "")
            if st in ("creator", "administrator", "member"):
                continue
            if st == "restricted":
                try:
                    if bool(getattr(m, "is_member", False)):
                        continue
                except Exception:
                    pass
            missing.append(ch)
        except Exception as e:
            log("membership check error", cid, uid, repr(e)[:120])
            continue
    return (len(missing) == 0), missing


def join_kb(chs):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for ch in chs:
        title = (ch.get("title") or ch.get("chat_id") or "کانال").strip()[:60]
        url = (ch.get("url") or "").strip()
        if url:
            kb.add(types.InlineKeyboardButton(f"📢 {title}", url=url))
        else:
            kb.add(types.InlineKeyboardButton(f"📢 {title} (بدون لینک!)", callback_data="join_nolink"))
    kb.add(types.InlineKeyboardButton(gb("✅ بررسی عضویت"), callback_data="join_check"))
    return kb


def send_join_message(chat_id, chs, first=False):
    if first:
        head = ("🌙 <b>به سلف دارک خوش اومدی!</b> 💎\n\n"
                "برای فعال‌سازی حسابت، اول باید عضو کانال‌های زیر بشی:\n")
    else:
        head = ("🔒 <b>دسترسی قفل است!</b>\n\n"
                "برای ادامه کار با ربات، در همه کانال‌های زیر عضو شو:\n")
    txt = head + "\n👇 بعد از عضویت، دکمه «✅ بررسی عضویت» رو بزن."
    try:
        bot.send_message(chat_id, txt, reply_markup=join_kb(chs), parse_mode="HTML")
    except Exception as e:
        log("join kb failed:", repr(e)[:200])
        lines = [head, ""]
        for ch in chs:
            t = (ch.get("title") or ch.get("chat_id") or "").strip()
            u = (ch.get("url") or "").strip()
            lines.append(f"📢 {esc(t)}: {esc(u) if u else '—'}")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(gb("✅ بررسی عضویت"), callback_data="join_check"))
        try:
            bot.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass


def access_gate(uid, chat_id):
    """دروازه دسترسی. True = مجاز."""
    u = get_user(uid) or {}
    if int(u.get("banned", 0) or 0):
        try:
            bot.send_message(chat_id, "🚫 حساب شما مسدود شده است.")
        except Exception:
            pass
        return False
    if not bot_is_on() and not is_admin(uid):
        try:
            bot.send_message(chat_id, "🛠 ربات در حال حاضر خاموش است. لطفاً بعداً تلاش کنید. 🌙")
        except Exception:
            pass
        return False
    if is_admin(uid):
        return True
    if not force_on():
        return True
    ok, missing = check_membership(uid)
    if ok is None:
        try:
            bot.send_message(chat_id, "🛠 ربات در حال تکمیل راه‌اندازی است. لطفاً دقایقی بعد برگردید. 🌙")
        except Exception:
            pass
        try:
            bot.send_message(ADMIN_ID, "⚠️ <b>هشدار:</b> جوین اجباری روشن است ولی هیچ کانالی ثبت نشده!",
                             parse_mode="HTML")
        except Exception:
            pass
        return False
    if ok and int(u.get("join_confirmed", 0) or 0):
        return True
    if ok and not int(u.get("join_confirmed", 0) or 0):
        send_join_message(chat_id, get_channels(), first=False)
        return False
    send_join_message(chat_id, missing or get_channels(), first=False)
    try:
        update_user(uid, join_confirmed=0)
    except Exception:
        pass
    return False


def try_referral_credit(new_uid):
    try:
        u = get_user(new_uid) or {}
        if int(u.get("referrer_id", 0) or 0):
            return
        ref = int(u.get("pending_referrer", 0) or 0)
        if not ref or ref == int(new_uid):
            return
        if not referral_on():
            update_user(new_uid, pending_referrer=0)
            return
        r = get_user(ref)
        if not r or int(r.get("banned", 0) or 0):
            update_user(new_uid, pending_referrer=0)
            return
        reward = f_setting("ref_reward", D_REF_REWARD)
        add_diamonds(ref, reward)
        update_user(ref, referrals=int(r.get("referrals", 0) or 0) + 1,
                    earned_ref=float(r.get("earned_ref", 0) or 0) + reward)
        update_user(new_uid, referrer_id=ref, pending_referrer=0)
        try:
            bot.send_message(ref, f"🎉 <b>زیرمجموعه جدید!</b>\n💎 {fmt_num(reward)} الماس به حسابت اضافه شد.",
                             parse_mode="HTML")
        except Exception:
            pass
    except Exception:
        log("referral credit error", traceback.format_exc()[-300:])


# ---------- متن‌ها ----------
def account_text(uid):
    u = get_user(uid) or {}
    accs = get_self_accounts(uid)
    on_n = sum(1 for a in accs if int(a.get("is_on", 0) or 0))
    ref = int(u.get("referrer_id", 0) or 0)
    status = "🚫 مسدود" if int(u.get("banned", 0) or 0) else ("✅ فعال" if int(u.get("is_active", 0) or 0) else "⏳ در انتظار جوین")
    rows = [
        f"🆔 آیدی عددی: <code>{uid}</code>",
        f"👤 نام: {esc(u.get('first_name') or '-')}",
        f"🔗 یوزرنیم: @{esc(u.get('username') or '-')}",
        f"💎 موجودی الماس: <b>{fmt_num(u.get('diamonds', 0))}</b>",
        f"🎁 زیرمجموعه‌ها: <b>{fmt_num(u.get('referrals', 0))}</b>",
        f"💰 درآمد از زیرمجموعه: <b>{fmt_num(u.get('earned_ref', 0))}</b> 💎",
        f"🛒 مجموع خرید الماس: <b>{fmt_num(u.get('total_bought', 0))}</b> 💎",
        f"💸 مجموع هزینه‌کرد: <b>{fmt_num(u.get('total_spent', 0))}</b> 💎",
        f"📤 مجموع انتقال: <b>{fmt_num(u.get('total_transferred', 0))}</b> 💎",
        f"🤖 سلف‌های فعال: <b>{on_n}</b> از {len(accs)}",
        f"📅 عضویت: {esc(u.get('join_date') or '-')}",
        f"📌 وضعیت: {status}",
        f"👥 معرف: {'—' if not ref else f'<code>{ref}</code>'}",
        f"🔗 لینک دعوت:\n<code>{ref_link(uid)}</code>",
    ]
    return panel_box("👤 حساب کاربری", rows)


def ref_text(uid):
    u = get_user(uid) or {}
    rw = f_setting("ref_reward", D_REF_REWARD)
    on = referral_on()
    rows = [
        f"🎁 پاداش هر دعوت: <b>{fmt_num(rw)} الماس</b>",
        f"👥 دعوت‌شده‌ها: <b>{fmt_num(u.get('referrals', 0))}</b>",
        f"💰 درآمد کل: <b>{fmt_num(u.get('earned_ref', 0))}</b> 💎",
        "",
        "✅ زیرمجموعه وقتی حساب می‌شود که در همه کانال‌های جوین اجباری عضو شود.",
        ("🟢 زیرمجموعه‌گیری روشن است." if on else "🔴 زیرمجموعه‌گیری فعلاً خاموش است."),
        "",
        f"🔗 لینک دعوت تو:\n<code>{ref_link(uid)}</code>",
    ]
    return panel_box("🎁 زیرمجموعه‌گیری", rows)


def guide_text():
    return panel_box("📖 راهنمای سلف دارک", [
        "🤖 <b>ساخت سلف:</b> با ۱۰ الماس سلف روی اکانتت فعال می‌شود؛",
        "شماره → کد ورود → (رمز دومرحله‌ای) → سلف روشن! ⚡",
        "",
        "💎 <b>خرید الماس:</b> پرداخت فقط با ارز <b>گرام</b>؛",
        f"قیمت هر الماس: {fmt_gram(f_setting('diamond_price', D_DIAMOND_PRICE))} گرام | حداقل {fmt_num(f_setting('min_buy', D_MIN_BUY))} الماس",
        "",
        "🎁 <b>زیرمجموعه:</b> با لینک دعوت، بعد از جوین کامل، ۵ الماس بگیر.",
        "",
        "👥 <b>انتقال گروهی:</b> روی پیام طرف ریپلای کن و بنویس:",
        "<code>انتقال 10</code>  (کارمزد ۳٪)",
        "",
        "⚡ <b>تبچی:</b> داخل سلف با دستور <code>تنظیم چت</code> گروه را ثبت کن،",
        "متن و بنر بده و ارسال خودکار را روشن کن.",
        "",
        "⏳ سلف روشن ساعتی ۴ الماس کم می‌کند؛ موجودی تمام شود سلف خاموش می‌شود.",
    ])


def buy_intro_text():
    price = f_setting("diamond_price", D_DIAMOND_PRICE)
    mn = f_setting("min_buy", D_MIN_BUY)
    return panel_box("💎 خرید الماس با گرام", [
        f"💠 قیمت هر ۱ الماس: <b>{fmt_gram(price)} گرام</b>",
        f"📦 حداقل خرید: <b>{fmt_num(mn)} الماس</b>",
        "",
        "1️⃣ تعداد الماس درخواستی را بفرست؛",
        "2️⃣ مبلغ گرام + آدرس ولت نمایش داده می‌شود؛",
        "3️⃣ واریز کن و <b>عکس تراکنش</b> را همینجا بفرست؛",
        "4️⃣ بعد از تأیید ادمین، خودکار شارژ می‌شوی. ⚡",
        "",
        "✍️ تعداد الماس را به عدد بفرست:",
    ])


# ---------- ساخت سلف: منو و قابلیت‌ها ----------
def self_main_text(uid):
    cost = f_setting("self_cost", D_SELF_COST)
    fee = f_setting("hourly_fee", D_HOURLY_FEE)
    accs = get_self_accounts(uid)
    on_n = sum(1 for a in accs if int(a.get("is_on", 0) or 0))
    rows = [
        f"🤖 سلف‌ها: <b>{on_n}</b> روشن از {len(accs)}",
        f"💎 هزینه فعال‌سازی هر سلف: <b>{fmt_num(cost)}</b>",
        f"⏳ هزینه ساعتی سلف روشن: <b>{fmt_num(fee)}</b>",
        "",
        "روی اکانتت لاگین می‌کنیم و ۳۰ قابلیت + تبچی کامل فعال می‌شود. ⚡",
    ]
    for a in accs[:3]:
        st = "🟢 روشن" if int(a.get("is_on", 0) or 0) else "🔴 خاموش"
        ph = esc((a.get("phone") or a.get("temp_phone") or "؟"))
        step = (a.get("login_step") or "")
        extra = "" if step in ("done", "none", "") else " (⏳ نیمه‌تمام)"
        rows.append(f"• {ph} — {st}{extra}")
    return panel_box("🤖 ساخت سلف", rows)


def self_main_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton(gb("➕ فعال‌سازی سلف جدید"), callback_data="s:new"))
    accs = get_self_accounts(uid)
    for a in accs[:3]:
        aid = a["id"]
        if int(a.get("is_on", 0) or 0):
            kb.add(types.InlineKeyboardButton(f"🔴 خاموش: {a.get('phone') or aid}", callback_data=f"s:off:{aid}"))
        else:
            if (a.get("session_string") or ""):
                kb.add(types.InlineKeyboardButton(f"🟢 روشن: {a.get('phone') or aid}", callback_data=f"s:on:{aid}"))
    kb.add(types.InlineKeyboardButton(gb("⚙️ قابلیت‌های سلف"), callback_data="f:0"),
           types.InlineKeyboardButton(gb("⚡ مدیریت تبچی"), callback_data="tb:list"))
    if accs:
        kb.add(types.InlineKeyboardButton("🗑 حذف سلف", callback_data="s:delmenu"))
    kb.add(types.InlineKeyboardButton(gb("🔙 منوی اصلی"), callback_data="m:home"))
    return kb


def features_kb(uid, page):
    page = max(0, min(2, int(page)))
    kb = types.InlineKeyboardMarkup(row_width=1)
    chunk = FEATURES[page * 10:(page + 1) * 10]
    for key, num, title, _d in chunk:
        on, _ex = get_toggle(uid, key)
        mark = "🟢" if on else "🔴"
        kb.add(types.InlineKeyboardButton(f"{mark} {num}. {title}", callback_data=f"t:{key}:{page}"))
    nav = []
    if page > 0:
        nav.append(types.InlineKeyboardButton("◀️ قبلی", callback_data=f"f:{page - 1}"))
    if page < 2:
        nav.append(types.InlineKeyboardButton("بعدی ▶️", callback_data=f"f:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.add(types.InlineKeyboardButton(gb("🔙 سلف"), callback_data="m:self"))
    return kb


def features_text(page):
    page = max(0, min(2, int(page)))
    names = ["اول", "دوم", "سوم"]
    rows = [f"📄 صفحه {names[page]} (۱۰ قابلیت) — برای روشن/خاموش روی هرکدام بزن:", ""]
    for key, num, title, desc in FEATURES[page * 10:(page + 1) * 10]:
        rows.append(f"<b>{num}. {esc(title)}</b>\n   <i>{esc(desc)}</i>")
    return panel_box("⚙️ قابلیت‌های سلف", rows)


def tabchi_list_text(uid):
    rows = get_tabchi_groups(uid)
    L = [f"⚡ گروه‌های تبچی ثبت‌شده: <b>{len(rows)}</b>", "",
         "📌 ثبت سریع: داخل گروه، با اکانت سلف بنویس: <code>تنظیم چت</code>", ""]
    if not rows:
        L.append("هنوز گروهی ثبت نشده است.")
    for g in rows[:15]:
        st = "🟢" if int(g.get("is_on", 0) or 0) else "🔴"
        has_b = "🖼" if (g.get("banner_file_id") or "") else "📝"
        tx = (g.get("text") or "—")[:30]
        L.append(f"{st} {has_b} <b>#{g['id']}</b> {esc(g.get('title') or g.get('chat_id') or '')} | ⏱{g.get('interval_min', 30)}د | {esc(tx)}")
    return panel_box("⚡ مدیریت تبچی", L)


def tabchi_list_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    rows = get_tabchi_groups(uid)
    for g in rows[:10]:
        gid = g["id"]
        st = "🔴 خاموش" if int(g.get("is_on", 0) or 0) else "🟢 روشن"
        kb.add(types.InlineKeyboardButton(f"#{gid} {esc((g.get('title') or '')[:12])}", callback_data=f"tb:v:{gid}"),
               types.InlineKeyboardButton(st, callback_data=f"tb:t:{gid}"))
    kb.add(types.InlineKeyboardButton(gb("📝 راهنمای تبچی"), callback_data="tb:help"))
    kb.add(types.InlineKeyboardButton(gb("🔙 سلف"), callback_data="m:self"))
    return kb


def tabchi_help_text():
    return panel_box("⚡ راهنمای تبچی داخل سلف", [
        "با اکانت سلف (نه ربات!) این دستورات را بفرست:",
        "",
        "🔹 <code>تنظیم چت</code> — ثبت همین گروه",
        "🔹 <code>متن تبچی</code> + ریپلای روی متن",
        "🔹 <code>بنر</code> + ریپلای روی عکس/استیکر",
        "🔹 <code>زمان 30</code> — هر ۳۰ دقیقه",
        "🔹 <code>فاصله 5</code> — ۵ ثانیه مکث بین گروه‌ها",
        "🔹 <code>تبچی روشن / تبچی خاموش</code>",
        "🔹 <code>تبچی</code> — لیست گروه‌ها",
        "🔹 <code>حذف چت</code> — حذف همین گروه",
        "",
        "✅ بنر + متن، خودکار و سر وقت ارسال می‌شود.",
    ])


# ============================================================
# هندلرهای اصلی
# ============================================================
@bot.message_handler(commands=["start"])
def cmd_start(m):
    try:
        uid = int(m.from_user.id)
        u = ensure_user(m.from_user)
        if int(u.get("banned", 0) or 0):
            bot.send_message(m.chat.id, "🚫 حساب شما مسدود شده است.")
            return
        if not bot_is_on() and not is_admin(uid):
            bot.send_message(m.chat.id, "🛠 ربات در حال حاضر خاموش است. 🌙")
            return
        # رفرال
        try:
            parts = (m.text or "").split()
            if len(parts) > 1 and parts[1].startswith("ref_"):
                try:
                    ref = int(parts[1][4:])
                    if ref != uid and not int(u.get("referrer_id", 0) or 0) and not int(u.get("pending_referrer", 0) or 0):
                        update_user(uid, pending_referrer=ref)
                except Exception:
                    pass
        except Exception:
            pass
        if is_admin(uid):
            bot.send_message(m.chat.id, panel_box("🌙 سلف دارک", ["👑 سلام ادمین!", "به ربات سلف دارک خوش اومدی ⚡"]),
                             reply_markup=main_menu_kb(uid), parse_mode="HTML")
            return
        ok, missing = check_membership(uid)
        if force_on() and ok is None:
            bot.send_message(m.chat.id, "🛠 ربات در حال تکمیل راه‌اندازی است. 🌙")
            return
        if force_on() and (not ok or not int(u.get("join_confirmed", 0) or 0)):
            send_join_message(m.chat.id, get_channels(), first=True)
            return
        bot.send_message(m.chat.id, panel_box("🌙 سلف دارک", [
            f"سلام {esc(u.get('first_name') or 'عزیز')}! 💎",
            "به <b>سلف دارک</b> خوش اومدی ⚡",
            "از منوی زیر انتخاب کن: 👇",
        ]), reply_markup=main_menu_kb(uid), parse_mode="HTML")
    except Exception:
        log("start error", traceback.format_exc()[-500:])
        try:
            bot.send_message(m.chat.id, "⚠️ خطای موقت! لطفاً دوباره تلاش کنید.")
        except Exception:
            pass


@bot.message_handler(commands=["cancel"])
def cmd_cancel(m):
    try:
        clear_state(m.from_user.id)
        bot.send_message(m.chat.id, "❌ عملیات لغو شد.", reply_markup=main_menu_kb(m.from_user.id))
    except Exception:
        pass


@bot.message_handler(commands=["id"])
def cmd_id(m):
    try:
        bot.send_message(m.chat.id, f"🆔 آیدی عددی شما: <code>{m.from_user.id}</code>", parse_mode="HTML")
    except Exception:
        pass


STATE_TEXT_HANDLERS = {}


def register_state(step):
    def deco(fn):
        STATE_TEXT_HANDLERS[step] = fn
        return fn
    return deco


@register_state("buy_amount")
def st_buy_amount(uid, text, m):
    try:
        amt = float(text.strip().replace(",", "").replace("٬", ""))
    except Exception:
        bot.send_message(m.chat.id, "⚠️ فقط عدد بفرست! مثلاً: <code>50</code>", parse_mode="HTML")
        return
    mn = f_setting("min_buy", D_MIN_BUY)
    if amt < mn:
        bot.send_message(m.chat.id, f"⚠️ حداقل خرید {fmt_num(mn)} الماس است!")
        return
    price = f_setting("diamond_price", D_DIAMOND_PRICE)
    total = amt * price
    wallet = get_setting("wallet_address", D_WALLET)
    set_state(uid, "buy_receipt", amount=amt, gram=total, price=price)
    bot.send_message(m.chat.id, panel_box("💎 فاکتور خرید", [
        f"📦 تعداد: <b>{fmt_num(amt)} الماس</b>",
        f"💠 مبلغ قابل پرداخت: <b>{fmt_gram(total)} گرام</b>",
        "",
        f"👛 واریز به ولت:\n<code>{esc(wallet)}</code>",
        "",
        "بعد از واریز، <b>عکس/اسکرین‌شات تراکنش</b> را همینجا بفرست 📸",
        "(/cancel برای لغو)",
    ]), parse_mode="HTML")


@register_state("support_msg")
def st_support_msg(uid, text, m):
    clear_state(uid)
    u = get_user(uid) or {}
    try:
        bot.send_message(ADMIN_ID, panel_box("📞 پیام پشتیبانی", [
            f"👤 {esc(u.get('first_name') or '')} (@{esc(u.get('username') or '-')})",
            f"🆔 <code>{uid}</code>", "", esc(text[:1000]),
        ]), parse_mode="HTML")
        bot.send_message(m.chat.id, "✅ پیامت به پشتیبانی رسید. به‌زودی جواب می‌گیری! 💜",
                         reply_markup=main_menu_kb(uid))
    except Exception:
        bot.send_message(m.chat.id, "⚠️ خطا! دوباره تلاش کن.", reply_markup=main_menu_kb(uid))


@bot.message_handler(content_types=["text"])
def main_handler(m):
    try:
        if (m.chat.type or "") in ("group", "supergroup"):
            handle_group_text(m)
            return
        uid = int(m.from_user.id)
        ensure_user(m.from_user)
        text = (m.text or "").strip()
        st = get_state(uid)
        if text == "🔙 بازگشت به منو":
            clear_state(uid)
            bot.send_message(m.chat.id, "🏠 منوی اصلی:", reply_markup=main_menu_kb(uid))
            return
        if st.get("step") and text not in ("💎 خرید الماس", "🤖 ساخت سلف", "👤 حساب کاربری",
                                           "🎁 زیرمجموعه‌گیری", "📖 راهنما", "📞 پشتیبانی", "🛠 پنل ادمین"):
            fn = STATE_TEXT_HANDLERS.get(st["step"])
            if fn:
                fn(uid, text, m)
                return
            clear_state(uid)
        if text == "👤 حساب کاربری":
            if not access_gate(uid, m.chat.id):
                return
            bot.send_message(m.chat.id, account_text(uid), parse_mode="HTML")
        elif text == "🎁 زیرمجموعه‌گیری":
            if not access_gate(uid, m.chat.id):
                return
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton(gb("📤 اشتراک لینک دعوت"),
                                              url=f"https://t.me/share/url?url={ref_link(uid)}&text=💎 بیا تو سلف دارک الماس بگیر!"))
            bot.send_message(m.chat.id, ref_text(uid), reply_markup=kb, parse_mode="HTML")
        elif text == "📖 راهنما":
            if not access_gate(uid, m.chat.id):
                return
            bot.send_message(m.chat.id, guide_text(), parse_mode="HTML")
        elif text == "💎 خرید الماس":
            if not access_gate(uid, m.chat.id):
                return
            set_state(uid, "buy_amount")
            bot.send_message(m.chat.id, buy_intro_text(), reply_markup=back_kb(), parse_mode="HTML")
        elif text == "🤖 ساخت سلف":
            if not access_gate(uid, m.chat.id):
                return
            clear_state(uid)
            bot.send_message(m.chat.id, self_main_text(uid), reply_markup=self_main_kb(uid), parse_mode="HTML")
        elif text == "📞 پشتیبانی":
            if not access_gate(uid, m.chat.id):
                return
            sup = get_setting("support_username", "")
            if sup:
                bot.send_message(m.chat.id, f"📞 پشتیبانی: @{esc(sup.lstrip('@'))}", parse_mode="HTML")
            set_state(uid, "support_msg")
            bot.send_message(m.chat.id, "✍️ پیامت را بفرست تا به پشتیبانی برسونم: (/cancel برای لغو)",
                             reply_markup=back_kb())
        elif text == "🛠 پنل ادمین" and is_admin(uid):
            send_admin_panel(m.chat.id)
        elif text == "🛠 پنل ادمین":
            bot.send_message(m.chat.id, "🚫 فقط ادمین!")
        else:
            if not access_gate(uid, m.chat.id):
                return
            bot.send_message(m.chat.id, "از منوی زیر انتخاب کن 👇", reply_markup=main_menu_kb(uid))
    except Exception:
        log("main_handler error", traceback.format_exc()[-500:])
        try:
            bot.send_message(m.chat.id, "⚠️ خطای موقت! دوباره تلاش کنید.")
        except Exception:
            pass


@bot.message_handler(content_types=["photo"])
def photo_handler(m):
    try:
        uid = int(m.from_user.id)
        st = get_state(uid)
        if st.get("step") == "buy_receipt":
            amt = float(st.get("amount", 0))
            gram = float(st.get("gram", 0))
            price = float(st.get("price", 0))
            wallet = get_setting("wallet_address", D_WALLET)
            fid = m.photo[-1].file_id
            with _db_lock:
                conn = get_conn()
                cur = conn.execute("INSERT INTO diamond_orders(user_id,diamonds,gram_amount,price_each,"
                                   "wallet,photo_file_id,status,created) VALUES(?,?,?,?,?,?,?,?)",
                                   (uid, amt, gram, price, wallet, fid, "pending", now_str()))
                oid = cur.lastrowid
                conn.commit()
                conn.close()
            clear_state(uid)
            u = get_user(uid) or {}
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("✅ تأیید و شارژ", callback_data=f"ord:y:{oid}"),
                   types.InlineKeyboardButton("❌ رد", callback_data=f"ord:n:{oid}"))
            try:
                bot.send_photo(ADMIN_ID, fid, caption=panel_box("💎 سفارش خرید الماس", [
                    f"🧾 شماره: <b>#{oid}</b>",
                    f"👤 {esc(u.get('first_name') or '')} (@{esc(u.get('username') or '-')})",
                    f"🆔 <code>{uid}</code>",
                    f"📦 {fmt_num(amt)} الماس = {fmt_gram(gram)} گرام",
                    f"📅 {now_str()}",
                ]), reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                log("notify admin order failed", repr(e)[:150])
            bot.send_message(m.chat.id, panel_box("✅ رسید دریافت شد", [
                f"🧾 سفارش <b>#{oid}</b> ثبت شد.",
                "بعد از تأیید ادمین، خودکار شارژ می‌شوی ⚡",
            ]), reply_markup=main_menu_kb(uid), parse_mode="HTML")
        else:
            bot.send_message(m.chat.id, "📸 برای خرید الماس اول از منوی «💎 خرید الماس» شروع کن.",
                             reply_markup=main_menu_kb(uid))
    except Exception:
        log("photo error", traceback.format_exc()[-400:])


@bot.message_handler(content_types=["document"])
def doc_handler(m):
    try:
        uid = int(m.from_user.id)
        st = get_state(uid)
        if is_admin(uid) and st.get("step") == "adm_restore":
            handle_restore_file(m)
        else:
            bot.send_message(m.chat.id, "📄 فایل دریافت شد ولی عملیاتی در انتظار نیست.")
    except Exception:
        log("doc error", traceback.format_exc()[-400:])


@bot.callback_query_handler(func=lambda c: True)
def all_callbacks(call):
    try:
        uid = int(call.from_user.id)
        data = (call.data or "")
        if data == "join_check":
            if is_admin(uid):
                bot.answer_callback_query(call.id, "👑 ادمین نیازی به جوین ندارد!")
                return
            ok, missing = check_membership(uid)
            if ok and not missing:
                update_user(uid, join_confirmed=1, is_active=1)
                try_referral_credit(uid)
                try:
                    bot.answer_callback_query(call.id, "✅ عضویت تأیید شد!")
                except Exception:
                    pass
                try:
                    bot.send_message(call.message.chat.id, panel_box("🎉 فعال شدی!", [
                        "حسابت فعال شد! از منوی زیر استفاده کن 👇",
                    ]), reply_markup=main_menu_kb(uid), parse_mode="HTML")
                except Exception:
                    pass
            else:
                update_user(uid, join_confirmed=0)
                try:
                    bot.answer_callback_query(call.id, "❌ هنوز عضو همه کانال‌ها نشدی!", show_alert=True)
                except Exception:
                    pass
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                  reply_markup=join_kb(missing or get_channels()))
                except Exception:
                    pass
            return
        if data == "join_nolink":
            bot.answer_callback_query(call.id, "این کانال لینک ندارد! به ادمین خبر بده.", show_alert=True)
            return
        # گیت دسترسی برای بقیه دکمه‌ها
        if not is_admin(uid):
            u = get_user(uid) or {}
            if int(u.get("banned", 0) or 0):
                bot.answer_callback_query(call.id, "🚫 مسدود!", show_alert=True)
                return
            if force_on() and (not int(u.get("join_confirmed", 0) or 0)):
                ok2, _m2 = check_membership(uid)
                if not ok2:
                    bot.answer_callback_query(call.id, "🔒 اول عضو کانال‌ها شو!", show_alert=True)
                    return
                update_user(uid, join_confirmed=1, is_active=1)
                try_referral_credit(uid)
        if data.startswith("ord:") or data.startswith("a:"):
            handle_admin_callback(call)
            return
        if data == "m:home":
            try:
                bot.edit_message_text("🏠 منوی اصلی — از دکمه‌های پایین استفاده کن 👇",
                                      call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data == "m:self":
            try:
                bot.edit_message_text(self_main_text(uid), call.message.chat.id, call.message.message_id,
                                      reply_markup=self_main_kb(uid), parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data == "s:new":
            self_begin_login(uid, call)
            return
        if data.startswith("s:on:"):
            self_turn_on(uid, int(data.split(":")[2]), call)
            return
        if data.startswith("s:off:"):
            self_turn_off(uid, int(data.split(":")[2]), call)
            return
        if data == "s:delmenu":
            accs = get_self_accounts(uid)
            kb = types.InlineKeyboardMarkup(row_width=1)
            for a in accs:
                kb.add(types.InlineKeyboardButton(f"🗑 حذف {a.get('phone') or a['id']}",
                                                  callback_data=f"s:del:{a['id']}"))
            kb.add(types.InlineKeyboardButton(gb("🔙 سلف"), callback_data="m:self"))
            try:
                bot.edit_message_text("🗑 کدوم سلف حذف بشه؟", call.message.chat.id,
                                      call.message.message_id, reply_markup=kb)
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data.startswith("s:del:"):
            self_delete(uid, int(data.split(":")[2]), call)
            return
        if data.startswith("f:"):
            page = int(data.split(":")[1])
            try:
                bot.edit_message_text(features_text(page), call.message.chat.id, call.message.message_id,
                                      reply_markup=features_kb(uid, page), parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data.startswith("t:"):
            _p, key, page = data.split(":")
            if key in FEATURE_KEYS:
                on, _ex = get_toggle(uid, key)
                set_toggle(uid, key, 0 if on else 1)
                n, title, _d = FEATURE_BY_KEY[key]
                try:
                    bot.answer_callback_query(call.id, f"{'🟢 روشن' if not on else '🔴 خاموش'}: {title}")
                except Exception:
                    pass
                try:
                    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id,
                                                  reply_markup=features_kb(uid, int(page)))
                except Exception:
                    pass
            return
        if data == "tb:list":
            try:
                bot.edit_message_text(tabchi_list_text(uid), call.message.chat.id, call.message.message_id,
                                      reply_markup=tabchi_list_kb(uid), parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data == "tb:help":
            try:
                bot.edit_message_text(tabchi_help_text(), call.message.chat.id, call.message.message_id,
                                      reply_markup=types.InlineKeyboardMarkup().add(
                                          types.InlineKeyboardButton(gb("🔙 تبچی"), callback_data="tb:list")),
                                      parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data.startswith("tb:t:"):
            gid = int(data.split(":")[2])
            with _db_lock:
                conn = get_conn()
                r = conn.execute("SELECT is_on FROM tabchi_groups WHERE id=? AND user_id=?", (gid, uid)).fetchone()
                if r:
                    conn.execute("UPDATE tabchi_groups SET is_on=? WHERE id=?", (0 if r["is_on"] else 1, gid))
                    conn.commit()
                conn.close()
            try:
                bot.edit_message_text(tabchi_list_text(uid), call.message.chat.id, call.message.message_id,
                                      reply_markup=tabchi_list_kb(uid), parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ اعمال شد")
            return
        if data.startswith("tb:v:"):
            g = get_tabchi_group(int(data.split(":")[2]), uid)
            if not g:
                bot.answer_callback_query(call.id, "پیدا نشد!")
                return
            kb = types.InlineKeyboardMarkup(row_width=2)
            kb.add(types.InlineKeyboardButton("📝 متن", callback_data=f"tb:e:text:{g['id']}"),
                   types.InlineKeyboardButton("⏱ زمان", callback_data=f"tb:e:time:{g['id']}"))
            kb.add(types.InlineKeyboardButton("⏳ فاصله", callback_data=f"tb:e:delay:{g['id']}"),
                   types.InlineKeyboardButton("🗑 حذف", callback_data=f"tb:del:{g['id']}"))
            kb.add(types.InlineKeyboardButton(gb("🔙 تبچی"), callback_data="tb:list"))
            txt = panel_box(f"⚡ تبچی #{g['id']}", [
                f"📌 {esc(g.get('title') or g.get('chat_id') or '')}",
                f"⏱ هر {g.get('interval_min', 30)} دقیقه | فاصله {g.get('delay_sec', 5)} ثانیه",
                f"🖼 بنر: {'دارد ✅' if (g.get('banner_file_id') or '') else 'ندارد'}",
                f"📝 متن: {esc((g.get('text') or '—')[:200])}",
            ])
            try:
                bot.edit_message_text(txt, call.message.chat.id, call.message.message_id,
                                      reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id)
            return
        if data.startswith("tb:e:"):
            _p, _e, field, gid = data.split(":")
            set_state(uid, "tb_edit", field=field, gid=int(gid))
            msg = {"text": "📝 متن جدید تبچی را بفرست:", "time": "⏱ فاصله ارسال به دقیقه را بفرست (مثلاً 30):",
                   "delay": "⏳ فاصله بین گروه‌ها به ثانیه را بفرست (مثلاً 5):"}.get(field, "بفرست:")
            bot.send_message(call.message.chat.id, msg)
            bot.answer_callback_query(call.id)
            return
        if data.startswith("tb:del:"):
            gid = int(data.split(":")[2])
            with _db_lock:
                conn = get_conn()
                conn.execute("DELETE FROM tabchi_groups WHERE id=? AND user_id=?", (gid, uid))
                conn.commit()
                conn.close()
            try:
                bot.edit_message_text(tabchi_list_text(uid), call.message.chat.id, call.message.message_id,
                                      reply_markup=tabchi_list_kb(uid), parse_mode="HTML")
            except Exception:
                pass
            bot.answer_callback_query(call.id, "🗑 حذف شد")
            return
        bot.answer_callback_query(call.id)
    except Exception:
        log("callback error", traceback.format_exc()[-500:])
        try:
            bot.answer_callback_query(call.id, "⚠️ خطا!")
        except Exception:
            try:
                if getattr(call, "message", None):
                    bot.send_message(call.message.chat.id, "⚠️ خطای موقت! دوباره تلاش کنید.")
            except Exception:
                pass


@register_state("tb_edit")
def st_tb_edit(uid, text, m):
    st = get_state(uid)
    field, gid = st.get("field"), int(st.get("gid", 0))
    g = get_tabchi_group(gid, uid)
    if not g:
        clear_state(uid)
        bot.send_message(m.chat.id, "⚠️ گروه پیدا نشد!", reply_markup=main_menu_kb(uid))
        return
    with _db_lock:
        conn = get_conn()
        if field == "text":
            conn.execute("UPDATE tabchi_groups SET text=? WHERE id=?", (text[:1000], gid))
        elif field == "time":
            try:
                v = max(1, int(text.strip()))
            except Exception:
                bot.send_message(m.chat.id, "⚠️ فقط عدد! مثلاً 30")
                conn.close()
                return
            conn.execute("UPDATE tabchi_groups SET interval_min=? WHERE id=?", (v, gid))
        elif field == "delay":
            try:
                v = max(1, int(text.strip()))
            except Exception:
                bot.send_message(m.chat.id, "⚠️ فقط عدد! مثلاً 5")
                conn.close()
                return
            conn.execute("UPDATE tabchi_groups SET delay_sec=? WHERE id=?", (v, gid))
        conn.commit()
        conn.close()
    clear_state(uid)
    bot.send_message(m.chat.id, "✅ ذخیره شد!", reply_markup=main_menu_kb(uid))
    try:
        bot.send_message(m.chat.id, tabchi_list_text(uid), reply_markup=tabchi_list_kb(uid), parse_mode="HTML")
    except Exception:
        pass

# ============================================================
# بخش سوم: تبچی (مدل)، پنل ادمین، سفارش‌ها، انتقال گروهی
# ============================================================
def get_tabchi_groups(uid):
    try:
        conn = get_conn()
        rows = conn.execute("SELECT * FROM tabchi_groups WHERE user_id=? ORDER BY id", (int(uid),)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_tabchi_group(gid, uid=None):
    try:
        conn = get_conn()
        if uid is None:
            r = conn.execute("SELECT * FROM tabchi_groups WHERE id=?", (int(gid),)).fetchone()
        else:
            r = conn.execute("SELECT * FROM tabchi_groups WHERE id=? AND user_id=?", (int(gid), int(uid))).fetchone()
        conn.close()
        return dict(r) if r else None
    except Exception:
        return None


# ---------- انتقال گروهی ----------
TRANSFER_RE = re.compile(r"^\s*انتقال\s+(\d+(?:\.\d+)?)\s*$")


def handle_group_text(m):
    try:
        text = (m.text or "").strip()
        if text == "موجودی":
            u = ensure_user(m.from_user)
            bot.reply_to(m, f"💎 موجودی شما: <b>{fmt_num(u.get('diamonds', 0))}</b> الماس", parse_mode="HTML")
            return
        mt = TRANSFER_RE.match(text)
        if not mt:
            return
        if not m.reply_to_message or not m.reply_to_message.from_user:
            bot.reply_to(m, "⚠️ روی پیام گیرنده ریپلای کن! مثلاً:\n<code>انتقال 10</code>", parse_mode="HTML")
            return
        to_u = m.reply_to_message.from_user
        from_id, to_id = int(m.from_user.id), int(to_u.id)
        if to_u.is_bot:
            bot.reply_to(m, "⚠️ به ربات نمی‌شود الماس داد!")
            return
        if from_id == to_id:
            bot.reply_to(m, "⚠️ به خودت نمی‌توانی انتقال بدهی!")
            return
        amt = float(mt.group(1))
        if amt < 1:
            bot.reply_to(m, "⚠️ حداقل انتقال ۱ الماس است!")
            return
        fr = ensure_user(m.from_user)
        to = ensure_user(to_u)
        if int(fr.get("banned", 0) or 0):
            bot.reply_to(m, "🚫 حساب شما مسدود است!")
            return
        fee_rate = f_setting("transfer_fee", D_TRANSFER_FEE)
        fee = round(amt * fee_rate, 4)
        total = amt + fee
        bal = float(fr.get("diamonds", 0) or 0)
        if bal < total:
            bot.reply_to(m, f"⚠️ موجودی کافی نیست!\n💎 موجودی: {fmt_num(bal)}\n💸 لازم: {fmt_num(total)} (با کارمزد ۳٪)")
            return
        add_diamonds(from_id, -total)
        add_diamonds(to_id, amt)
        update_user(from_id, total_transferred=float(fr.get("total_transferred", 0) or 0) + amt,
                    total_spent=float(fr.get("total_spent", 0) or 0) + total)
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO transfers(from_id,to_id,amount,fee,created) VALUES(?,?,?,?,?)",
                         (from_id, to_id, amt, fee, now_str()))
            conn.commit()
            conn.close()
        bot.reply_to(m, panel_box("✅ انتقال موفق", [
            f"📤 فرستنده: {esc(fr.get('first_name') or from_id)}",
            f"📥 گیرنده: {esc(to.get('first_name') or to_id)}",
            f"💎 مبلغ: <b>{fmt_num(amt)}</b> الماس",
            f"🧾 کارمزد (۳٪): <b>{fmt_num(fee)}</b>",
            f"💰 موجودی جدید شما: <b>{fmt_num(bal - total)}</b>",
        ]), parse_mode="HTML")
    except Exception:
        log("group transfer error", traceback.format_exc()[-400:])


# ---------- پنل ادمین ----------
def send_admin_panel(chat_id):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton(gb("📊 آمار کامل"), callback_data="a:stats"),
           types.InlineKeyboardButton(gb("💎 آمار الماس"), callback_data="a:dstat"))
    kb.add(types.InlineKeyboardButton(gb("🔍 جستجوی کاربر"), callback_data="a:search"),
           types.InlineKeyboardButton(gb("➕ افزودن الماس"), callback_data="a:addd"))
    kb.add(types.InlineKeyboardButton(gb("🎁 پاداش رفرال"), callback_data="a:refr"),
           types.InlineKeyboardButton(gb("🔛 رفرال روشن/خاموش"), callback_data="a:reft"))
    kb.add(types.InlineKeyboardButton(gb("💠 قیمت الماس"), callback_data="a:price"),
           types.InlineKeyboardButton(gb("👛 ولت گرام"), callback_data="a:wallet"))
    kb.add(types.InlineKeyboardButton(gb("🤖 هزینه سلف"), callback_data="a:selfcost"),
           types.InlineKeyboardButton(gb("⏳ هزینه ساعتی"), callback_data="a:hourly"))
    kb.add(types.InlineKeyboardButton(gb("📦 حداقل خرید"), callback_data="a:minbuy"),
           types.InlineKeyboardButton(gb("🧾 سفارش‌ها"), callback_data="a:orders"))
    kb.add(types.InlineKeyboardButton(gb("📣 پیام همگانی"), callback_data="a:bc"),
           types.InlineKeyboardButton(gb("📮 فوروارد همگانی"), callback_data="a:fwd"))
    kb.add(types.InlineKeyboardButton(gb("📢 کانال‌ها"), callback_data="a:chs"),
           types.InlineKeyboardButton(gb("🤖 سلف‌های روشن"), callback_data="a:selfs"))
    kb.add(types.InlineKeyboardButton(gb("💾 بکاپ کامل"), callback_data="a:backup"),
           types.InlineKeyboardButton(gb("♻️ بازگردانی بکاپ"), callback_data="a:restore"))
    kb.add(types.InlineKeyboardButton(gb("🔌 ربات روشن/خاموش"), callback_data="a:bot"),
           types.InlineKeyboardButton(gb("🔒 جوین روشن/خاموش"), callback_data="a:force"))
    kb.add(types.InlineKeyboardButton(gb("🏆 برترین‌ها"), callback_data="a:top"),
           types.InlineKeyboardButton(gb("🔁 انتقالات اخیر"), callback_data="a:transfers"))
    kb.add(types.InlineKeyboardButton(gb("📞 پشتیبانی"), callback_data="a:sup"))
    chs = get_channels()
    ver = panel_box("👑 پنل ادمین", [
        f"🧩 نسخه: <b>{BOT_VERSION}</b>",
        f"📢 کانال‌های جوین: <b>{len(chs)}</b>",
        f"🔌 ربات: {'🟢 روشن' if bot_is_on() else '🔴 خاموش'} | 🔒 جوین: {'🟢' if force_on() else '🔴'} | 🎁 رفرال: {'🟢' if referral_on() else '🔴'}",
        f"💠 قیمت: {fmt_gram(f_setting('diamond_price', D_DIAMOND_PRICE))} گرام | 🎁 پاداش: {fmt_num(f_setting('ref_reward', D_REF_REWARD))}💎",
    ])
    try:
        bot.send_message(chat_id, ver, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        log("admin panel send failed", repr(e)[:150])


def admin_stats_text():
    conn = get_conn()
    try:
        n_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        n_active = conn.execute("SELECT COUNT(*) c FROM users WHERE is_active=1").fetchone()["c"]
        n_banned = conn.execute("SELECT COUNT(*) c FROM users WHERE banned=1").fetchone()["c"]
        tot_d = conn.execute("SELECT COALESCE(SUM(diamonds),0) s FROM users").fetchone()["s"]
        tot_ref = conn.execute("SELECT COALESCE(SUM(referrals),0) s FROM users").fetchone()["s"]
        tot_earn = conn.execute("SELECT COALESCE(SUM(earned_ref),0) s FROM users").fetchone()["s"]
        tot_bought = conn.execute("SELECT COALESCE(SUM(total_bought),0) s FROM users").fetchone()["s"]
        tot_spent = conn.execute("SELECT COALESCE(SUM(total_spent),0) s FROM users").fetchone()["s"]
        n_orders = conn.execute("SELECT COUNT(*) c FROM diamond_orders WHERE status='pending'").fetchone()["c"]
        n_self = conn.execute("SELECT COUNT(*) c FROM self_accounts WHERE is_on=1").fetchone()["c"]
        n_tb = conn.execute("SELECT COUNT(*) c FROM tabchi_groups WHERE is_on=1").fetchone()["c"]
    except Exception:
        (n_users, n_active, n_banned, tot_d, tot_ref, tot_earn, tot_bought, tot_spent,
         n_orders, n_self, n_tb) = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    conn.close()
    return panel_box("📊 آمار کامل ربات", [
        f"👥 کاربران: <b>{n_users:,}</b> | ✅ فعال: <b>{n_active:,}</b> | 🚫 بن: <b>{n_banned:,}</b>",
        f"💎 مجموع موجودی: <b>{fmt_num(tot_d)}</b>",
        f"🎁 مجموع رفرال‌ها: <b>{fmt_num(tot_ref)}</b> | درآمد رفرال: <b>{fmt_num(tot_earn)}</b>💎",
        f"🛒 خرید کل: <b>{fmt_num(tot_bought)}</b>💎 | 💸 هزینه‌کرد کل: <b>{fmt_num(tot_spent)}</b>💎",
        f"🧾 سفارش در انتظار: <b>{n_orders}</b>",
        f"🤖 سلف‌های روشن: <b>{n_self}</b> | ⚡ تبچی‌های فعال: <b>{n_tb}</b>",
        f"🧩 نسخه: {BOT_VERSION}",
    ])


def admin_dstat_text():
    conn = get_conn()
    try:
        rows = conn.execute("SELECT status, COUNT(*) c, COALESCE(SUM(diamonds),0) s FROM diamond_orders GROUP BY status").fetchall()
        tot_gram = conn.execute("SELECT COALESCE(SUM(gram_amount),0) s FROM diamond_orders WHERE status='approved'").fetchone()["s"]
        n_tr = conn.execute("SELECT COUNT(*) c FROM transfers").fetchone()["c"]
        s_tr = conn.execute("SELECT COALESCE(SUM(amount),0) s FROM transfers").fetchone()["s"]
        s_fee = conn.execute("SELECT COALESCE(SUM(fee),0) s FROM transfers").fetchone()["s"]
    except Exception:
        rows, tot_gram, n_tr, s_tr, s_fee = [], 0, 0, 0, 0
    conn.close()
    L = [f"💠 قیمت فعلی: <b>{fmt_gram(f_setting('diamond_price', D_DIAMOND_PRICE))}</b> گرام",
         f"👛 ولت: <code>{esc(get_setting('wallet_address', D_WALLET))}</code>", ""]
    for r in rows:
        L.append(f"• {r['status']}: {r['c']} سفارش / {fmt_num(r['s'])}💎")
    L += ["", f"💰 درآمد تأییدشده: <b>{fmt_gram(tot_gram)}</b> گرام",
          f"🔁 انتقالات گروهی: {n_tr} بار / {fmt_num(s_tr)}💎 (کارمزد {fmt_num(s_fee)}💎)"]
    return panel_box("💎 آمار الماس و فروش", L)


def user_card_text(uid):
    u = get_user(uid)
    if not u:
        return "⚠️ کاربر پیدا نشد!"
    accs = get_self_accounts(uid)
    on_n = sum(1 for a in accs if int(a.get("is_on", 0) or 0))
    return panel_box(f"👤 کاربر {uid}", [
        f"👤 {esc(u.get('first_name') or '')} (@{esc(u.get('username') or '-')})",
        f"💎 {fmt_num(u.get('diamonds', 0))} | 🎁 {fmt_num(u.get('referrals', 0))} رفرال ({fmt_num(u.get('earned_ref', 0))}💎)",
        f"🛒 خرید {fmt_num(u.get('total_bought', 0))} | 💸 خرج {fmt_num(u.get('total_spent', 0))} | 📤 انتقال {fmt_num(u.get('total_transferred', 0))}",
        f"🤖 سلف روشن: {on_n}/{len(accs)} | 📅 {esc(u.get('join_date') or '-')}",
        f"📌 {'🚫 بن' if int(u.get('banned', 0) or 0) else '✅ آزاد'} | معرف: {u.get('referrer_id') or '—'}",
    ])


def user_card_kb(uid):
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("➕ الماس", callback_data=f"a:ua:{uid}"),
           types.InlineKeyboardButton("➖ کسر", callback_data=f"a:ud:{uid}"))
    kb.add(types.InlineKeyboardButton("✉️ پیام", callback_data=f"a:um:{uid}"),
           types.InlineKeyboardButton("🚫 بن/رفع", callback_data=f"a:ub:{uid}"))
    kb.add(types.InlineKeyboardButton(gb("🔙 پنل"), callback_data="a:panel"))
    return kb


def back_panel_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(gb("🔙 پنل ادمین"), callback_data="a:panel"))
    return kb


def edit_admin(call, text, kb=None):
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=kb or back_panel_kb(), parse_mode="HTML")
    except Exception:
        try:
            bot.send_message(call.message.chat.id, text, reply_markup=kb or back_panel_kb(), parse_mode="HTML")
        except Exception:
            pass


def handle_admin_callback(call):
    uid = int(call.from_user.id)
    data = (call.data or "")
    if not is_admin(uid):
        try:
            bot.answer_callback_query(call.id, "🚫 فقط ادمین!", show_alert=True)
        except Exception:
            pass
        return
    # --- سفارش‌ها ---
    if data.startswith("ord:"):
        _o, act, oid = data.split(":")
        oid = int(oid)
        conn = get_conn()
        o = conn.execute("SELECT * FROM diamond_orders WHERE id=?", (oid,)).fetchone()
        conn.close()
        if not o:
            bot.answer_callback_query(call.id, "پیدا نشد!")
            return
        o = dict(o)
        if o["status"] != "pending":
            bot.answer_callback_query(call.id, f"قبلاً {o['status']} شده!")
            return
        if act == "y":
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE diamond_orders SET status='approved' WHERE id=?", (oid,))
                conn.commit()
                conn.close()
            add_diamonds(o["user_id"], float(o["diamonds"]))
            u = get_user(o["user_id"]) or {}
            update_user(o["user_id"], total_bought=float(u.get("total_bought", 0) or 0) + float(o["diamonds"]))
            try:
                bot.send_message(o["user_id"], panel_box("🎉 شارژ شدی!", [
                    f"💎 {fmt_num(o['diamonds'])} الماس به حسابت اضافه شد!",
                    f"🧾 سفارش #{oid} تأیید شد ✅",
                    f"💰 موجودی: {fmt_num((u.get('diamonds', 0) or 0) + float(o['diamonds']))}💎",
                ]), parse_mode="HTML")
            except Exception:
                pass
            try:
                bot.edit_message_caption(f"✅ تأیید و شارژ شد (#{oid})", call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ شارژ شد")
        else:
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE diamond_orders SET status='rejected' WHERE id=?", (oid,))
                conn.commit()
                conn.close()
            try:
                bot.send_message(o["user_id"], f"❌ سفارش #{oid} رد شد. اگر واریز کردی با پشتیبانی در تماس باش.")
            except Exception:
                pass
            try:
                bot.edit_message_caption(f"❌ رد شد (#{oid})", call.message.chat.id, call.message.message_id)
            except Exception:
                pass
            bot.answer_callback_query(call.id, "رد شد")
        return
    # --- پنل ---
    if data == "a:panel":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        send_admin_panel(call.message.chat.id)
        bot.answer_callback_query(call.id)
        return
    if data == "a:stats":
        edit_admin(call, admin_stats_text())
    elif data == "a:dstat":
        edit_admin(call, admin_dstat_text())
    elif data == "a:search":
        set_state(uid, "adm_search")
        bot.send_message(call.message.chat.id, "🔍 آیدی عددی کاربر را بفرست:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:addd":
        set_state(uid, "adm_addd")
        bot.send_message(call.message.chat.id, "➕ به فرمت زیر بفرست:\n<code>آیدی مبلغ</code>\nمثلاً: <code>123456 50</code>\n(مبلغ منفی = کسر)", parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:refr":
        set_state(uid, "adm_refr")
        bot.send_message(call.message.chat.id, f"🎁 پاداش فعلی هر رفرال: {fmt_num(f_setting('ref_reward', D_REF_REWARD))}💎\nعدد جدید را بفرست:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:reft":
        set_setting("referral_on", "0" if referral_on() else "1")
        edit_admin(call, f"🎁 زیرمجموعه‌گیری: {'🟢 روشن' if referral_on() else '🔴 خاموش'} شد.")
    elif data == "a:price":
        set_state(uid, "adm_price")
        bot.send_message(call.message.chat.id, f"💠 قیمت فعلی هر الماس: {fmt_gram(f_setting('diamond_price', D_DIAMOND_PRICE))} گرام\nعدد جدید را بفرست (مثلاً 0.0005):")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:wallet":
        set_state(uid, "adm_wallet")
        bot.send_message(call.message.chat.id, f"👛 ولت فعلی:\n<code>{esc(get_setting('wallet_address', D_WALLET))}</code>\nآدرس جدید را بفرست:", parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:selfcost":
        set_state(uid, "adm_selfcost")
        bot.send_message(call.message.chat.id, f"🤖 هزینه فعلی فعال‌سازی: {fmt_num(f_setting('self_cost', D_SELF_COST))}💎\nعدد جدید:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:hourly":
        set_state(uid, "adm_hourly")
        bot.send_message(call.message.chat.id, f"⏳ هزینه ساعتی فعلی: {fmt_num(f_setting('hourly_fee', D_HOURLY_FEE))}💎\nعدد جدید:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:minbuy":
        set_state(uid, "adm_minbuy")
        bot.send_message(call.message.chat.id, f"📦 حداقل خرید فعلی: {fmt_num(f_setting('min_buy', D_MIN_BUY))}💎\nعدد جدید:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:bc":
        set_state(uid, "adm_bc")
        bot.send_message(call.message.chat.id, "📣 متن پیام همگانی را بفرست:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:fwd":
        set_state(uid, "adm_fwd")
        bot.send_message(call.message.chat.id, "📮 پیام (متن یا فوروارد) را بفرست تا به همه فوروارد شود:")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:orders":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM diamond_orders WHERE status='pending' ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        if not rows:
            edit_admin(call, "🧾 سفارش در انتظاری نیست. ✅")
        else:
            kb = types.InlineKeyboardMarkup(row_width=2)
            L = ["🧾 <b>سفارش‌های در انتظار:</b>", ""]
            for r in rows:
                r = dict(r)
                L.append(f"#{r['id']} | 👤 <code>{r['user_id']}</code> | 💎 {fmt_num(r['diamonds'])} ({fmt_gram(r['gram_amount'])} گرام)")
                kb.add(types.InlineKeyboardButton(f"✅ #{r['id']}", callback_data=f"ord:y:{r['id']}"),
                       types.InlineKeyboardButton(f"❌ #{r['id']}", callback_data=f"ord:n:{r['id']}"))
            kb.add(types.InlineKeyboardButton(gb("🔙 پنل"), callback_data="a:panel"))
            edit_admin(call, "\n".join(L), kb)
    elif data == "a:chs":
        chs = get_channels()
        L = [f"📢 کانال‌ها ({len(chs)}) | جوین: {'🟢' if force_on() else '🔴'}", ""]
        kb = types.InlineKeyboardMarkup(row_width=1)
        for ch in chs:
            L.append(f"• {esc(ch.get('title') or '')} — <code>{esc(ch.get('chat_id') or '')}</code>")
            kb.add(types.InlineKeyboardButton(f"🗑 {ch.get('title') or ch.get('chat_id')}",
                                              callback_data=f"a:chdel:{ch['id']}"))
        kb.add(types.InlineKeyboardButton(gb("➕ افزودن کانال"), callback_data="a:chadd"))
        kb.add(types.InlineKeyboardButton(gb("🔙 پنل"), callback_data="a:panel"))
        edit_admin(call, "\n".join(L) if L else "خالی", kb)
    elif data == "a:chadd":
        set_state(uid, "adm_chadd")
        bot.send_message(call.message.chat.id, "➕ به فرمت زیر بفرست:\n<code>@channel | اسم کانال | https://t.me/...</code>\n(آیدی عددی هم می‌شود)", parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    elif data.startswith("a:chdel:"):
        cid = int(data.split(":")[2])
        conn = get_conn()
        r = conn.execute("SELECT chat_id FROM channels WHERE id=?", (cid,)).fetchone()
        conn.close()
        if r:
            del_channel_db(r["chat_id"])
            reset_join_confirmations()
        edit_admin(call, "🗑 کانال حذف شد و تأیید جوین‌ها ریست شد.")
    elif data == "a:backup":
        do_backup(call.message.chat.id)
    elif data == "a:restore":
        set_state(uid, "adm_restore")
        bot.send_message(call.message.chat.id, "♻️ فایل بکاپ (<code>data.db</code>) را همینجا بفرست:", parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:bot":
        set_setting("bot_on", "0" if bot_is_on() else "1")
        edit_admin(call, f"🔌 ربات {'🟢 روشن' if bot_is_on() else '🔴 خاموش'} شد.")
    elif data == "a:force":
        set_setting("force_join_on", "0" if force_on() else "1")
        if force_on():
            reset_join_confirmations()
        edit_admin(call, f"🔒 جوین اجباری {'🟢 روشن' if force_on() else '🔴 خاموش'} شد.")
    elif data == "a:sup":
        set_state(uid, "adm_sup")
        bot.send_message(call.message.chat.id, "📞 یوزرنیم پشتیبانی را بفرست (بدون @) — برای حذف: <code>-</code>", parse_mode="HTML")
        bot.answer_callback_query(call.id)
        return
    elif data == "a:top":
        conn = get_conn()
        rows = conn.execute("SELECT user_id,first_name,referrals,earned_ref FROM users ORDER BY referrals DESC LIMIT 10").fetchall()
        conn.close()
        L = ["🏆 <b>برترین دعوت‌کنندگان:</b>", ""]
        for i, r in enumerate(rows, 1):
            L.append(f"{i}. {esc(r['first_name'] or r['user_id'])} — <code>{r['user_id']}</code> | {r['referrals']} نفر ({fmt_num(r['earned_ref'])}💎)")
        edit_admin(call, "\n".join(L) if len(L) > 2 else "هنوز دعوتی ثبت نشده.")
    elif data == "a:transfers":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM transfers ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        L = ["🔁 <b>انتقالات اخیر:</b>", ""]
        for r in rows:
            L.append(f"<code>{r['from_id']}</code> → <code>{r['to_id']}</code> | {fmt_num(r['amount'])}💎 + {fmt_num(r['fee'])} کارمزد")
        edit_admin(call, "\n".join(L) if len(L) > 2 else "انتقالی ثبت نشده.")
    elif data == "a:selfs":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM self_accounts WHERE is_on=1 ORDER BY id DESC LIMIT 15").fetchall()
        conn.close()
        kb = types.InlineKeyboardMarkup(row_width=1)
        L = [f"🤖 <b>سلف‌های روشن ({len(rows)}):</b>", ""]
        for r in rows:
            L.append(f"• 👤 <code>{r['user_id']}</code> | 📱 {esc(r['phone'] or '?')} | ⏳ {esc(r['last_billing'] or '-')}")
            kb.add(types.InlineKeyboardButton(f"🔴 خاموش اجباری #{r['id']}", callback_data=f"a:soff:{r['id']}"))
        kb.add(types.InlineKeyboardButton(gb("🔙 پنل"), callback_data="a:panel"))
        edit_admin(call, "\n".join(L), kb)
    elif data.startswith("a:soff:"):
        acc = get_self_account_by_id(int(data.split(":")[2]))
        if acc:
            update_self_account(acc["id"], is_on=0)
            stop_self_client(acc["id"])
            try:
                bot.send_message(acc["user_id"], "🔴 سلف شما توسط ادمین خاموش شد.")
            except Exception:
                pass
        edit_admin(call, "🔴 سلف خاموش شد.")
    elif data.startswith("a:u:"):
        tuid = int(data.split(":")[2])
        edit_admin(call, user_card_text(tuid), user_card_kb(tuid))
    elif data.startswith("a:ua:"):
        set_state(uid, "adm_ua", target=int(data.split(":")[2]))
        bot.send_message(call.message.chat.id, "➕ مقدار الماس برای افزودن:")
        bot.answer_callback_query(call.id)
        return
    elif data.startswith("a:ud:"):
        set_state(uid, "adm_ud", target=int(data.split(":")[2]))
        bot.send_message(call.message.chat.id, "➖ مقدار الماس برای کسر:")
        bot.answer_callback_query(call.id)
        return
    elif data.startswith("a:um:"):
        set_state(uid, "adm_um", target=int(data.split(":")[2]))
        bot.send_message(call.message.chat.id, "✉️ متن پیام به کاربر:")
        bot.answer_callback_query(call.id)
        return
    elif data.startswith("a:ub:"):
        tuid = int(data.split(":")[2])
        u = get_user(tuid) or {}
        update_user(tuid, banned=0 if int(u.get("banned", 0) or 0) else 1)
        edit_admin(call, user_card_text(tuid), user_card_kb(tuid))
    try:
        bot.answer_callback_query(call.id, "✅")
    except Exception:
        pass


# ---------- استیت‌های ادمین ----------
@register_state("adm_search")
def s_adm_search(uid, text, m):
    clear_state(uid)
    try:
        t = int(text.strip())
    except Exception:
        bot.send_message(m.chat.id, "⚠️ آیدی عددی بفرست!")
        return
    bot.send_message(m.chat.id, user_card_text(t), reply_markup=user_card_kb(t), parse_mode="HTML")


@register_state("adm_addd")
def s_adm_addd(uid, text, m):
    clear_state(uid)
    try:
        p = text.strip().split()
        t, amt = int(p[0]), float(p[1])
    except Exception:
        bot.send_message(m.chat.id, "⚠️ فرمت: <code>آیدی مبلغ</code>", parse_mode="HTML")
        return
    new = add_diamonds(t, amt)
    try:
        bot.send_message(t, f"💎 {fmt_num(abs(amt))} الماس {'به حسابت اضافه' if amt > 0 else 'از حسابت کم'} شد!\n💰 موجودی: {fmt_num(new)}💎")
    except Exception:
        pass
    bot.send_message(m.chat.id, f"✅ انجام شد. موجودی جدید: {fmt_num(new)}💎")


@register_state("adm_refr")
def s_adm_refr(uid, text, m):
    clear_state(uid)
    try:
        v = float(text.strip())
        assert v >= 0
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد معتبر بفرست!")
        return
    set_setting("ref_reward", str(v))
    bot.send_message(m.chat.id, f"✅ پاداش رفرال شد: {fmt_num(v)}💎")


@register_state("adm_price")
def s_adm_price(uid, text, m):
    clear_state(uid)
    try:
        v = float(text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد معتبر! مثلاً 0.0005")
        return
    set_setting("diamond_price", str(v))
    bot.send_message(m.chat.id, f"✅ قیمت هر الماس شد: {fmt_gram(v)} گرام")


@register_state("adm_wallet")
def s_adm_wallet(uid, text, m):
    clear_state(uid)
    set_setting("wallet_address", text.strip())
    bot.send_message(m.chat.id, "✅ آدرس ولت ذخیره شد.")


@register_state("adm_selfcost")
def s_adm_selfcost(uid, text, m):
    clear_state(uid)
    try:
        v = float(text.strip())
        assert v >= 0
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد معتبر!")
        return
    set_setting("self_cost", str(v))
    bot.send_message(m.chat.id, f"✅ هزینه فعال‌سازی سلف: {fmt_num(v)}💎")


@register_state("adm_hourly")
def s_adm_hourly(uid, text, m):
    clear_state(uid)
    try:
        v = float(text.strip())
        assert v >= 0
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد معتبر!")
        return
    set_setting("hourly_fee", str(v))
    bot.send_message(m.chat.id, f"✅ هزینه ساعتی سلف: {fmt_num(v)}💎")


@register_state("adm_minbuy")
def s_adm_minbuy(uid, text, m):
    clear_state(uid)
    try:
        v = float(text.strip())
        assert v >= 1
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد معتبر (حداقل ۱)!")
        return
    set_setting("min_buy", str(v))
    bot.send_message(m.chat.id, f"✅ حداقل خرید: {fmt_num(v)}💎")


@register_state("adm_bc")
def s_adm_bc(uid, text, m):
    clear_state(uid)
    bot.send_message(m.chat.id, "📣 ارسال همگانی شروع شد...")
    ok = fail = 0
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    conn.close()
    for r in rows:
        try:
            bot.send_message(r["user_id"], f"📣 <b>اطلاعیه:</b>\n\n{text}", parse_mode="HTML")
            ok += 1
        except Exception:
            fail += 1
        time.sleep(0.05)
    bot.send_message(m.chat.id, f"✅ همگانی تمام شد: {ok} موفق / {fail} ناموفق")


@register_state("adm_fwd")
def s_adm_fwd(uid, text, m):
    clear_state(uid)
    bot.send_message(m.chat.id, "📮 فوروارد همگانی شروع شد...")
    ok = fail = 0
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE banned=0").fetchall()
    conn.close()
    for r in rows:
        try:
            bot.forward_message(r["user_id"], m.chat.id, m.message_id)
            ok += 1
        except Exception:
            fail += 1
        time.sleep(0.05)
    bot.send_message(m.chat.id, f"✅ فوروارد تمام شد: {ok} موفق / {fail} ناموفق")


@register_state("adm_ua")
def s_adm_ua(uid, text, m):
    t = get_state(uid).get("target")
    clear_state(uid)
    try:
        v = abs(float(text.strip()))
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد!")
        return
    new = add_diamonds(t, v)
    try:
        bot.send_message(t, f"💎 {fmt_num(v)} الماس از طرف ادمین گرفتی!\n💰 موجودی: {fmt_num(new)}💎")
    except Exception:
        pass
    bot.send_message(m.chat.id, f"✅ موجودی جدید کاربر: {fmt_num(new)}💎")


@register_state("adm_ud")
def s_adm_ud(uid, text, m):
    t = get_state(uid).get("target")
    clear_state(uid)
    try:
        v = abs(float(text.strip()))
    except Exception:
        bot.send_message(m.chat.id, "⚠️ عدد!")
        return
    new = add_diamonds(t, -v)
    bot.send_message(m.chat.id, f"✅ موجودی جدید کاربر: {fmt_num(new)}💎")


@register_state("adm_um")
def s_adm_um(uid, text, m):
    t = get_state(uid).get("target")
    clear_state(uid)
    try:
        bot.send_message(t, f"✉️ <b>پیام از ادمین:</b>\n\n{text}", parse_mode="HTML")
        bot.send_message(m.chat.id, "✅ ارسال شد.")
    except Exception:
        bot.send_message(m.chat.id, "⚠️ ارسال نشد! (کاربر ربات را بلاک کرده؟)")


@register_state("adm_chadd")
def s_adm_chadd(uid, text, m):
    clear_state(uid)
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        bot.send_message(m.chat.id, "⚠️ فرمت: <code>@channel | اسم | لینک</code>", parse_mode="HTML")
        return
    cid, title = parts[0], parts[1]
    url = parts[2] if len(parts) > 2 else (("https://t.me/" + cid[1:]) if cid.startswith("@") else "")
    try:
        bot.get_chat_member(cid, ADMIN_ID)
    except Exception as e:
        bot.send_message(m.chat.id, f"⚠️ ربات به این چت دسترسی ندارد! اول ربات را ادمین کن.\n({esc(str(e)[:150])})", parse_mode="HTML")
        return
    add_channel_db(cid, title, url)
    reset_join_confirmations()
    bot.send_message(m.chat.id, f"✅ کانال «{esc(title)}» اضافه شد و جوین‌ها ریست شد.", parse_mode="HTML")


@register_state("adm_sup")
def s_adm_sup(uid, text, m):
    clear_state(uid)
    set_setting("support_username", "" if text.strip() == "-" else text.strip().lstrip("@"))
    bot.send_message(m.chat.id, "✅ ذخیره شد.")


# ---------- بکاپ و بازگردانی ----------
def do_backup(chat_id):
    try:
        bot.send_message(chat_id, "💾 در حال آماده‌سازی بکاپ کامل...")
        conn = get_conn()
        info = {}
        for t in ("users", "channels", "settings", "diamond_orders", "transfers", "self_accounts",
                  "self_toggles", "tabchi_groups", "notes", "reminders", "scheduled_msgs", "activity_log"):
            try:
                info[t] = conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
            except Exception:
                info[t] = 0
        conn.close()
        cap = panel_box("💾 بکاپ کامل سلف دارک", [
            f"📅 {now_str()} | 🧩 {BOT_VERSION}",
            f"👥 کاربران: {info.get('users', 0)} | 📢 کانال: {info.get('channels', 0)}",
            f"🧾 سفارش: {info.get('diamond_orders', 0)} | 🔁 انتقال: {info.get('transfers', 0)}",
            f"🤖 سلف: {info.get('self_accounts', 0)} | ⚡ تبچی: {info.get('tabchi_groups', 0)}",
            "♻️ برای بازگردانی: پنل → بازگردانی بکاپ → ارسال همین فایل",
        ])
        with open(DB_PATH, "rb") as f:
            bot.send_document(chat_id, f, caption=cap, parse_mode="HTML", visible_file_name="selfdark-backup.db")
    except Exception as e:
        log("backup error", repr(e)[:200])
        try:
            bot.send_message(chat_id, "⚠️ بکاپ ناموفق بود!")
        except Exception:
            pass


def handle_restore_file(m):
    clear_state(m.from_user.id)
    try:
        if not m.document:
            bot.send_message(m.chat.id, "⚠️ فایل معتبر بفرست!")
            return
        if m.document.file_size and m.document.file_size > 40 * 1024 * 1024:
            bot.send_message(m.chat.id, "⚠️ فایل خیلی بزرگ است!")
            return
        fi = bot.get_file(m.document.file_id)
        data = bot.download_file(fi.file_path)
        if len(data) < 100 or not data[:16].startswith(b"SQLite format 3"):
            bot.send_message(m.chat.id, "⚠️ این فایل دیتابیس معتبر نیست!")
            return
        bak = DB_PATH + f".before-restore-{int(time.time())}.db"
        try:
            if os.path.exists(DB_PATH):
                os.replace(DB_PATH, bak)
        except Exception:
            pass
        with open(DB_PATH, "wb") as f:
            f.write(data)
        init_db()
        bot.send_message(m.chat.id, panel_box("♻️ بازگردانی موفق", [
            "✅ بکاپ جایگزین شد و ربات با اطلاعات جدید کار می‌کند.",
            f"📦 فایل قبلی نگه داشته شد: {os.path.basename(bak)}",
            "⚠️ سلف‌های روشن: از پنل → سلف‌های روشن بررسی کن.",
        ]), parse_mode="HTML")
    except Exception as e:
        log("restore error", traceback.format_exc()[-400:])
        try:
            bot.send_message(m.chat.id, "⚠️ بازگردانی ناموفق بود!")
        except Exception:
            pass

# ============================================================
# بخش چهارم: موتور سلف (Telethon)، زمان‌بندها، وب‌هوک، اجرا
# ============================================================
import asyncio
import io

self_clients = {}
self_clients_lock = threading.RLock()
msg_cache = {}
msg_cache_lock = threading.RLock()
MAX_LOGIN_ACCOUNTS = 3
FA_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def fa_to_en(s):
    return str(s or "").translate(FA_DIGITS)


def ensure_extra_tables():
    with _db_lock:
        try:
            conn = get_conn()
            conn.execute("CREATE TABLE IF NOT EXISTS banner_data(gid INTEGER PRIMARY KEY, data BLOB, ext TEXT DEFAULT 'jpg')")
            conn.commit()
            conn.close()
        except Exception:
            pass


def save_banner(gid, data, ext="jpg"):
    with _db_lock:
        try:
            conn = get_conn()
            conn.execute("INSERT OR REPLACE INTO banner_data(gid,data,ext) VALUES(?,?,?)", (int(gid), data, ext))
            conn.commit()
            conn.close()
        except Exception:
            pass


def load_banner(gid):
    try:
        conn = get_conn()
        r = conn.execute("SELECT data,ext FROM banner_data WHERE gid=?", (int(gid),)).fetchone()
        conn.close()
        if r and r["data"]:
            return bytes(r["data"]), (r["ext"] or "jpg")
    except Exception:
        pass
    return None


def xcall(client, fname, *a, **k):
    """اجرای امن متد async کلاینت از ترد دیگر."""
    from telethon import TelegramClient as _A
    coro = getattr(_A, fname)(client, *a, **k)
    return asyncio.run_coroutine_threadsafe(coro, client.loop).result(timeout=90)


def normalize_phone(s):
    s = fa_to_en(s).strip().replace(" ", "").replace("-", "")
    if s.startswith("00"):
        s = "+" + s[2:]
    if s.startswith("0") and len(s) == 11:
        s = "+98" + s[1:]
    if not s.startswith("+"):
        s = "+" + s
    digits = "".join(c for c in s if c.isdigit())
    if 10 <= len(digits) <= 15:
        return "+" + digits
    return ""


def cache_put(acc_id, chat_id, mid, text):
    try:
        with msg_cache_lock:
            d = msg_cache.setdefault(acc_id, {})
            c = d.setdefault(str(chat_id), {})
            c[int(mid)] = (str(text or "")[:2000])
            while len(c) > 300:
                c.pop(next(iter(c)))
    except Exception:
        pass


def cache_pop(acc_id, mids):
    found = []
    try:
        with msg_cache_lock:
            d = msg_cache.get(acc_id, {})
            for chat_k, c in d.items():
                for mid in list(mids):
                    if int(mid) in c:
                        found.append((chat_k, c.pop(int(mid))))
    except Exception:
        pass
    return found


def summarize_text(t):
    t = (t or "").strip()
    if not t:
        return "متن خالی است."
    words = t.split()
    sents = re.split(r"[.!?؟\n]+", t)
    sents = [s.strip() for s in sents if s.strip()]
    head = " ".join(sents[:2])[:600] if sents else t[:600]
    return f"📝 <b>خلاصه:</b> {esc(head)}\n\n📊 {len(words)} کلمه | {len(sents)} جمله"


def translate_text(q, target="fa"):
    q = (q or "").strip()[:900]
    if not q:
        return "متن خالی است."
    if not REQUESTS_OK:
        return "⚠️ سرویس ترجمه در دسترس نیست."
    try:
        r = requests.get("https://api.mymemory.translated.net/get",
                         params={"q": q, "langpair": f"auto|{target}"}, timeout=8)
        j = r.json()
        t = (j.get("responseData") or {}).get("translatedText", "")
        if t:
            return f"🌍 <b>ترجمه:</b>\n{esc(t)}"
    except Exception as e:
        log("translate err", repr(e)[:150])
    return "⚠️ ترجمه ناموفق بود! بعداً تلاش کن."


EMOJI_MAP = [("سلام", "👋"), ("عشق", "❤️"), ("تبریک", "🎉"), ("تولد", "🎂"), ("خداحافظ", "👋"),
             ("ممنون", "🙏"), ("مرسی", "🙏"), ("عالی", "🔥"), ("شب بخیر", "🌙"), ("صبح بخیر", "☀️"),
             ("موفق", "🚀"), ("پول", "💰"), ("الماس", "💎"), ("گل", "🌹")]
CAT_WORDS = {"کاری": ["کار", "پروژه", "جلسه", "مدیر"], "مالی": ["پول", "قیمت", "خرید", "واریز", "تومان"],
             "تبلیغات": ["تبلیغ", "کانال", "جوین", "عضو شو"], "خانوادگی": ["مامان", "بابا", "خانواده"]}


def emoji_for(t):
    t = t or ""
    for w, e in EMOJI_MAP:
        if w in t:
            return e
    return "✨"


def cat_for(t):
    t = t or ""
    for cat, words in CAT_WORDS.items():
        for w in words:
            if w in t:
                return cat
    return "عمومی"


def get_tabchi_by_chat(uid, chat_id):
    try:
        conn = get_conn()
        r = conn.execute("SELECT * FROM tabchi_groups WHERE user_id=? AND chat_id=?", (int(uid), str(chat_id))).fetchone()
        conn.close()
        return dict(r) if r else None
    except Exception:
        return None


def self_account_label(a):
    return (a.get("phone") or a.get("temp_phone") or f"#{a.get('id')}") if a else "؟"


# ---------- شروع لاگین ----------
def self_begin_login(uid, call):
    try:
        _self_begin_login_inner(uid, call)
    except Exception:
        log("self_begin FATAL", traceback.format_exc()[-800:])
        try:
            cid = call.message.chat.id if getattr(call, "message", None) else uid
            bot.send_message(cid, "⚠️ خطای موقت در ساخت سلف! دوباره تلاش کن. (کد: SELFNEW)")
        except Exception:
            pass
        try:
            bot.send_message(ADMIN_ID, f"⚠️ خطای ساخت سلف برای <code>{uid}</code>:\n{esc(traceback.format_exc()[-800:])}",
                             parse_mode="HTML")
        except Exception:
            pass


def _self_begin_login_inner(uid, call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id, "⏳ در حال آماده‌سازی سلف...")
    except Exception:
        pass
    log(f"s:new uid={uid} telethon={TELETHON_OK}")
    if not TELETHON_OK:
        bot.send_message(chat_id, "⚠️ موتور سلف روی سرور فعال نیست! به ادمین خبر بده.")
        return
    accs = get_self_accounts(uid)
    real_accs = [a for a in accs if (a.get("session_string") or "") or (a.get("login_step") or "none") not in ("none", "done")]
    if len(real_accs) >= MAX_LOGIN_ACCOUNTS:
        bot.send_message(chat_id, f"⚠️ سقف {MAX_LOGIN_ACCOUNTS} اکانت! یکی را حذف کن.")
        return
    if len([a for a in accs if (a.get("session_string") or "")]) >= 1:
        on_multi, _e = get_toggle(uid, "multi_account")
        if not on_multi:
            bot.send_message(chat_id, "⚠️ برای اکانت دوم، اول قابلیت «مدیریت چند اکانت» را روشن کن! (شماره ۱۹)")
            return
    for a in accs:
        if (a.get("login_step") or "") in ("await_phone", "await_code", "await_2fa"):
            bot.send_message(chat_id, "⏳ یک ورود نیمه‌تمام داری! ادامه‌اش بده یا /cancel بزن.")
            return
    cost = f_setting("self_cost", D_SELF_COST)
    u = get_user(uid) or {}
    bal = float(u.get("diamonds", 0) or 0)
    if bal < cost:
        bot.send_message(chat_id, panel_box("⚠️ موجودی ناکافی", [
            f"💎 هزینه فعال‌سازی: <b>{fmt_num(cost)}</b>",
            f"💰 موجودی تو: <b>{fmt_num(bal)}</b>",
            "از «💎 خرید الماس» شارژ کن یا زیرمجموعه بگیر! 🎁",
        ]), parse_mode="HTML")
        return
    with _db_lock:
        conn = get_conn()
        cur = conn.execute("INSERT INTO self_accounts(user_id,login_step,created) VALUES(?, ?, ?)",
                           (int(uid), "await_phone", now_str()))
        acc_id = cur.lastrowid
        conn.commit()
        conn.close()
    set_state(uid, "self_phone", acc_id=acc_id)
    bot.send_message(chat_id, panel_box("📱 فعال‌سازی سلف", [
        f"💎 هزینه (پس از ورود موفق): <b>{fmt_num(cost)}</b> الماس",
        f"⏳ شارژ ساعتی: <b>{fmt_num(f_setting('hourly_fee', D_HOURLY_FEE))}</b> الماس",
        "",
        "📞 <b>شماره اکانتی که می‌خواهی سلف واردش بشه رو بفرست:</b>",
        "مثلاً: <code>+989123456789</code>",
        "",
        "🔐 <i>کد ورود فقط برای لاگین سلف خودت استفاده می‌شود.</i>",
    ]), parse_mode="HTML")


@register_state("self_phone")
def st_self_phone(uid, text, m):
    st = get_state(uid)
    acc_id = int(st.get("acc_id", 0))
    phone = normalize_phone(text)
    if not phone:
        bot.send_message(m.chat.id, "⚠️ شماره معتبر بفرست! مثلاً: <code>+989123456789</code>", parse_mode="HTML")
        return
    bot.send_message(m.chat.id, "⏳ در حال ارسال کد ورود به اکانتت...")
    threading.Thread(target=self_do_send_code, args=(uid, acc_id, phone, m.chat.id), daemon=True).start()


def self_do_send_code(uid, acc_id, phone, chat_id):
    if not TELETHON_OK:
        return
    client = None
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        client.connect()
        if not client.is_connected():
            raise RuntimeError("اتصال به تلگرام برقرار نشد")
        sent = client.send_code_request(phone)
        update_self_account(acc_id, phone=phone, temp_phone=phone,
                            phone_code_hash=sent.phone_code_hash, login_step="await_code")
        set_state(uid, "self_code", acc_id=acc_id)
        bot.send_message(chat_id, panel_box("🔑 کد ورود", [
            f"📱 کد ورود به <code>{esc(phone)}</code> ارسال شد.",
            "",
            "✍️ <b>کد ورود را بفرست:</b> (با فاصله یا بدون فاصله)",
            "مثلاً: <code>4 2 8 1 9</code>",
        ]), parse_mode="HTML")
    except Exception as e:
        log("send_code err", repr(e)[:300])
        msg = str(e)
        if "PHONE_NUMBER_INVALID" in msg:
            t = "⚠️ شماره نامعتبر است! دوباره بفرست."
        elif "FLOOD" in msg:
            t = "⚠️ محدودیت تلگرام! چند دقیقه بعد تلاش کن."
        else:
            t = f"⚠️ خطا در ارسال کد! ({esc(msg[:150])})"
        try:
            bot.send_message(chat_id, t, parse_mode="HTML")
        except Exception:
            pass
    finally:
        try:
            if client:
                client.disconnect()
        except Exception:
            pass


@register_state("self_code")
def st_self_code(uid, text, m):
    st = get_state(uid)
    acc_id = int(st.get("acc_id", 0))
    code = fa_to_en(text).strip().replace(" ", "").replace("-", "")
    if not code.isdigit() or len(code) < 4:
        bot.send_message(m.chat.id, "⚠️ کد را درست بفرست! مثلاً: <code>42819</code>", parse_mode="HTML")
        return
    bot.send_message(m.chat.id, "⏳ در حال ورود به اکانت...")
    threading.Thread(target=self_do_sign_in, args=(uid, acc_id, code, m.chat.id), daemon=True).start()


def self_do_sign_in(uid, acc_id, code, chat_id):
    client = None
    try:
        acc = get_self_account_by_id(acc_id)
        if not acc:
            return
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        client.connect()
        try:
            client.sign_in(acc["phone"] or acc["temp_phone"], code, phone_code_hash=acc["phone_code_hash"])
        except SessionPasswordNeededError:
            update_self_account(acc_id, login_step="await_2fa")
            with _db_lock:
                conn = get_conn()
                conn.execute("UPDATE self_accounts SET label=? WHERE id=?", (code[-8:], acc_id))
                conn.commit()
                conn.close()
            set_state(uid, "self_2fa", acc_id=acc_id)
            bot.send_message(chat_id, "🔐 اکانتت <b>رمز دومرحله‌ای</b> دارد!\n✍️ رمزش را بفرست:", parse_mode="HTML")
            return
        except PhoneCodeInvalidError:
            bot.send_message(chat_id, "❌ کد اشتباه است! دوباره بفرست:")
            return
        self_finalize_login(uid, acc_id, client, chat_id)
        client = None
    except Exception as e:
        log("sign_in err", repr(e)[:300])
        try:
            bot.send_message(chat_id, f"⚠️ ورود ناموفق! ({esc(str(e)[:150])})\n/cancel برای شروع دوباره", parse_mode="HTML")
        except Exception:
            pass
    finally:
        try:
            if client:
                client.disconnect()
        except Exception:
            pass


@register_state("self_2fa")
def st_self_2fa(uid, text, m):
    st = get_state(uid)
    acc_id = int(st.get("acc_id", 0))
    bot.send_message(m.chat.id, "⏳ در حال تأیید رمز دومرحله‌ای...")
    threading.Thread(target=self_do_2fa, args=(uid, acc_id, text.strip(), m.chat.id), daemon=True).start()


def self_do_2fa(uid, acc_id, pw, chat_id):
    client = None
    try:
        acc = get_self_account_by_id(acc_id)
        if not acc:
            return
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        client.connect()
        try:
            client.sign_in(acc["phone"] or acc["temp_phone"], acc.get("label") or "", phone_code_hash=acc["phone_code_hash"])
        except SessionPasswordNeededError:
            client.sign_in(password=pw)
        self_finalize_login(uid, acc_id, client, chat_id)
        client = None
    except Exception as e:
        log("2fa err", repr(e)[:300])
        try:
            bot.send_message(chat_id, "❌ رمز دومرحله‌ای اشتباه است! دوباره بفرست:")
        except Exception:
            pass
    finally:
        try:
            if client:
                client.disconnect()
        except Exception:
            pass


def self_finalize_login(uid, acc_id, client, chat_id):
    try:
        session_str = client.session.save()
        me = client.get_me()
        my_name = getattr(me, "first_name", "") or ""
    except Exception as e:
        log("finalize err", repr(e)[:200])
        try:
            bot.send_message(chat_id, "⚠️ ذخیره نشست ناموفق بود! دوباره تلاش کن.")
        except Exception:
            pass
        return
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
    cost = f_setting("self_cost", D_SELF_COST)
    u = get_user(uid) or {}
    bal = float(u.get("diamonds", 0) or 0)
    if bal < cost:
        update_self_account(acc_id, session_string=session_str, is_on=0, login_step="done",
                            activated_at=now_str(), label="")
        clear_state(uid)
        bot.send_message(chat_id, "⚠️ موجودیت برای فعال‌سازی کافی نیست! شارژ کن بعد روشنش کن.")
        return
    add_diamonds(uid, -cost)
    update_user(uid, total_spent=float(u.get("total_spent", 0) or 0) + cost)
    update_self_account(acc_id, session_string=session_str, is_on=1, login_step="done",
                        activated_at=now_str(), last_billing=now_str(), label="")
    for key, _n, _t, _d in FEATURES:
        if get_toggle(uid, key) == (0, ""):
            pass
    for k in ("save_deleted", "save_edits", "smart_guard", "chat_stats", "tabchi"):
        on, ex = get_toggle(uid, k)
        if not on:
            set_toggle(uid, k, 1, ex)
    clear_state(uid)
    try:
        bot.send_message(chat_id, panel_box("🎉 سلف فعال شد!", [
            f"👤 اکانت: {esc(my_name)}",
            f"📱 {esc(get_self_account_by_id(acc_id).get('phone') or '')}",
            f"💎 هزینه کم شد: {fmt_num(cost)} | ⏳ ساعتی: {fmt_num(f_setting('hourly_fee', D_HOURLY_FEE))}",
            "",
            "⚙️ قابلیت‌ها را از «🤖 ساخت سلف» مدیریت کن.",
            "💬 داخل اکانتت بنویس: <code>.راهنما</code>",
        ]), parse_mode="HTML")
        bot.send_message(chat_id, self_main_text(uid), reply_markup=self_main_kb(uid), parse_mode="HTML")
    except Exception:
        pass
    start_self_client(acc_id)


# ---------- روشن/خاموش/حذف ----------
def self_turn_on(uid, acc_id, call):
    acc = get_self_account_by_id(acc_id)
    if not acc or int(acc["user_id"]) != int(uid):
        bot.answer_callback_query(call.id, "پیدا نشد!")
        return
    if not (acc.get("session_string") or ""):
        bot.answer_callback_query(call.id, "⚠️ ورود کامل نشده! دوباره فعال‌سازی کن.", show_alert=True)
        return
    update_self_account(acc_id, is_on=1, last_billing=now_str())
    start_self_client(acc_id)
    try:
        bot.edit_message_text(self_main_text(uid), call.message.chat.id, call.message.message_id,
                              reply_markup=self_main_kb(uid), parse_mode="HTML")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "🟢 سلف روشن شد")


def self_turn_off(uid, acc_id, call=None):
    acc = get_self_account_by_id(acc_id)
    if acc and int(acc["user_id"]) == int(uid):
        update_self_account(acc_id, is_on=0)
        stop_self_client(acc_id)
    if call:
        try:
            bot.edit_message_text(self_main_text(uid), call.message.chat.id, call.message.message_id,
                                  reply_markup=self_main_kb(uid), parse_mode="HTML")
        except Exception:
            pass
        try:
            bot.answer_callback_query(call.id, "🔴 سلف خاموش شد")
        except Exception:
            pass


def self_delete(uid, acc_id, call):
    acc = get_self_account_by_id(acc_id)
    if acc and int(acc["user_id"]) == int(uid):
        stop_self_client(acc_id)
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM self_accounts WHERE id=?", (acc_id,))
            rows = conn.execute("SELECT id FROM tabchi_groups WHERE user_id=? AND account_id=?", (uid, acc_id)).fetchall()
            for r in rows:
                conn.execute("DELETE FROM banner_data WHERE gid=?", (r["id"],))
            conn.execute("DELETE FROM tabchi_groups WHERE user_id=? AND account_id=?", (uid, acc_id))
            conn.commit()
            conn.close()
    try:
        bot.edit_message_text(self_main_text(uid), call.message.chat.id, call.message.message_id,
                              reply_markup=self_main_kb(uid), parse_mode="HTML")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "🗑 حذف شد")


def stop_self_client(acc_id):
    with self_clients_lock:
        info = self_clients.pop(int(acc_id), None)
    if info and info.get("client"):
        try:
            xcall(info["client"], "disconnect")
        except Exception:
            pass


def start_self_client(acc_id):
    acc = get_self_account_by_id(acc_id)
    if not acc or not int(acc.get("is_on", 0) or 0) or not (acc.get("session_string") or ""):
        return
    with self_clients_lock:
        if int(acc_id) in self_clients:
            return
    t = threading.Thread(target=run_self_client, args=(int(acc_id),), daemon=True)
    t.start()


def run_self_client(acc_id):
    if not TELETHON_OK:
        return
    acc = get_self_account_by_id(acc_id)
    if not acc:
        return
    uid = int(acc["user_id"])
    client = None
    try:
        client = TelegramClient(StringSession(acc["session_string"]), API_ID, API_HASH)
        client.connect()
        if not client.is_user_authorized():
            log("self", acc_id, "session invalid -> off")
            update_self_account(acc_id, is_on=0)
            try:
                bot.send_message(uid, "⚠️ نشست سلف منقضی شد! دوباره فعال‌سازی کن.")
            except Exception:
                pass
            return
        with self_clients_lock:
            self_clients[int(acc_id)] = {"client": client, "user_id": uid}

        @client.on(events.NewMessage(incoming=True))
        async def _in(event):
            try:
                txt = event.raw_text or ""
                try:
                    cache_put(acc_id, event.chat_id, event.id, txt)
                except Exception:
                    pass
                bump_activity(uid, "in")
                if event.is_private:
                    bump_activity(uid, "pv")
                on_reply, ex = get_toggle(uid, "auto_reply")
                style, _e2 = get_toggle(uid, "reply_style")
                style_name = (_e2 or "default").strip() or "default"
                if on_reply and event.is_private and txt and not (event.via_bot_id or event.forward):
                    base = AUTO_REPLY_TEXTS.get(style_name, AUTO_REPLY_TEXTS["default"])
                    on_em, _e = get_toggle(uid, "emoji_suggest")
                    if on_em:
                        base += f" {emoji_for(txt)}"
                    await event.reply(base)
                    bump_activity(uid, "autoreply")
                on_v, _e = get_toggle(uid, "voice_to_text")
                if on_v and (event.voice or event.audio):
                    d = getattr(event.voice, "duration", "?") if event.voice else "?"
                    await event.reply(f"🎙 <b>ویس دریافت شد</b> ({d} ثانیه)\n<i>متن خودکار (نسخه پایه):</i> «پیام صوتی — برای متن کامل، فایل را نگه دار»",
                                      parse_mode="HTML")
                on_s, _e = get_toggle(uid, "summarize")
                if on_s and txt and len(txt) > 600 and event.is_private:
                    await event.reply(summarize_text(txt), parse_mode="HTML")
                on_c, _e = get_toggle(uid, "categorize")
                if on_c and txt:
                    bump_activity(uid, "cat:" + cat_for(txt))
                on_p, _e = get_toggle(uid, "auto_pin")
                if on_p and txt and "#مهم" in txt:
                    try:
                        await event.pin()
                    except Exception:
                        pass
                on_st, _e = get_toggle(uid, "sticker_suggest")
                if on_st and txt and event.is_private and len(txt) < 100:
                    await event.reply(f"✨ استیکر پیشنهادی: {emoji_for(txt)}  (جستجو: {esc(txt[:20])})", parse_mode="HTML")
                ghost, _e = get_toggle(uid, "account_status")
                if not ghost:
                    try:
                        await client.send_read_acknowledge(event.chat_id, event.message)
                    except Exception:
                        pass
                on_cs, _e = get_toggle(uid, "chat_stats")
                if on_cs:
                    bump_activity(uid, "msg")
            except Exception:
                log("self-in err", traceback.format_exc()[-300:])

        @client.on(events.MessageDeleted)
        async def _del(event):
            try:
                on, _e = get_toggle(uid, "save_deleted")
                if not on:
                    return
                mids = getattr(event, "deleted_ids", []) or []
                found = cache_pop(acc_id, mids)
                if not found:
                    return
                for chat_k, text in found[:5]:
                    if text:
                        await client.send_message("me", f"🗑 <b>پیام حذف‌شده</b> (چت {esc(str(chat_k))}):\n{esc(text[:1500])}",
                                                  parse_mode="HTML")
                        bump_activity(uid, "saved_del")
            except Exception:
                pass

        @client.on(events.MessageEdited)
        async def _edit(event):
            try:
                on, _e = get_toggle(uid, "save_edits")
                if not on:
                    return
                new_t = event.raw_text or ""
                with msg_cache_lock:
                    d = msg_cache.get(acc_id, {}).get(str(event.chat_id), {})
                    old_t = d.get(int(event.id), "")
                cache_put(acc_id, event.chat_id, event.id, new_t)
                if old_t and old_t != new_t:
                    await client.send_message("me", f"✏️ <b>ویرایش پیام:</b>\nقبل: {esc(old_t[:800])}\nبعد: {esc(new_t[:800])}",
                                              parse_mode="HTML")
            except Exception:
                pass

        @client.on(events.NewMessage(outgoing=True))
        async def _out(event):
            try:
                txt = (event.raw_text or "").strip()
                if not txt:
                    return
                used = None
                for p in SELF_PREFIXES:
                    if txt.startswith(p):
                        used = p
                        break
                if used is None:
                    return
                cmd = txt[len(used):].strip()
                if not cmd:
                    return
                await handle_self_command(client, acc_id, uid, event, cmd)
            except Exception:
                log("self-out err", traceback.format_exc()[-300:])

        log("self client started", acc_id, "uid", uid)
        client.run_until_disconnected()
    except Exception as e:
        log("self client", acc_id, "died:", repr(e)[:250])
    finally:
        with self_clients_lock:
            self_clients.pop(int(acc_id), None)
        try:
            if client:
                client.disconnect()
        except Exception:
            pass


SELF_HELP = """🌙 <b>راهنمای سلف دارک</b> ⚡
(همه با نقطه یا «سلف » اولش — مثل <code>.آمار</code>)

📊 <code>.آمار</code> — آمار امروز
⚙️ <code>.قابلیت‌ها</code> — وضعیت ۳۰ قابلیت
🔛 <code>.قابلیت 1 روشن</code> — روشن/خاموش با شماره یا نام
🎭 <code>.سبک فان</code> — رسمی/دوستانه/فان/کوتاه
🌍 <code>.ترجمه en</code> + ریپلای — ترجمه پیام
📝 <code>.خلاصه</code> + ریپلای — خلاصه متن
🔍 <code>.جستجو کلمه</code> — جستجو در همین چت
💾 <code>.بکاپ 100</code> — پشتیبان ۱۰۰ پیام همین چت
📌 <code>.یادداشت متن</code> — یادداشت همین گفتگو
📓 <code>.دفترچه متن</code> — یادداشت خصوصی
⏰ <code>.یادآوری 30 متن</code> — یادآور دقیقه‌ای
📤 <code>.زمانبندی 60 متن</code> — ارسال بعداً در همین چت
🛠 <code>.دستور سلام سلام رفیق!</code> — ساخت دستور شخصی
▶️ <code>.سلام</code> — اجرای دستور شخصی
📋 <code>.دستورات</code> — لیست دستورات
🖼 <code>.پروفایل</code> + ریپلای عکس — تغییر عکس پروفایل
📌 <code>.پین</code> + ریپلای — سنجاق پیام

⚡ <b>تبچی:</b>
<code>تنظیم چت</code> — ثبت همین گروه (بدون نقطه هم کار می‌کند)
<code>متن تبچی ...</code> یا ریپلای متن
<code>بنر</code> + ریپلای عکس/استیکر
<code>زمان 30</code> — هر ۳۰ دقیقه
<code>فاصله 5</code> — مکث ۵ ثانیه‌ای
<code>تبچی روشن / تبچی خاموش</code>
<code>تبچی</code> — لیست | <code>حذف چت</code> — حذف
"""


async def handle_self_command(client, acc_id, uid, event, cmd):
    async def say(t):
        try:
            await event.edit(t, parse_mode="HTML")
        except Exception:
            try:
                await event.respond(t, parse_mode="HTML")
            except Exception:
                pass
    low = cmd.strip()
    # دستورات شخصی (.نام)
    try:
        on_pc, pc_ex = get_toggle(uid, "personal_cmds")
        if on_pc and pc_ex:
            try:
                pc = json.loads(pc_ex) if pc_ex.startswith("{") else {}
            except Exception:
                pc = {}
            if low in pc:
                await say(esc(pc[low])[:3000])
                return
    except Exception:
        pass
    if low in ("راهنما", "help", "هلپ"):
        await say(SELF_HELP)
        return
    if low in ("آمار", "stats"):
        try:
            conn = get_conn()
            rows = conn.execute("SELECT kind,COALESCE(SUM(count),0) s FROM activity_log WHERE user_id=? AND day=? GROUP BY kind",
                                (uid, today_str())).fetchall()
            conn.close()
            L = [f"📊 <b>آمار امروز ({today_str()}):</b>", ""]
            for r in rows:
                L.append(f"• {esc(r['kind'])}: {r['s']}")
            u = get_user(uid) or {}
            L += ["", f"💎 موجودی: {fmt_num(u.get('diamonds', 0))}"]
            await say("\n".join(L) if len(L) > 2 else "📊 امروز فعالیتی ثبت نشده.")
        except Exception:
            await say("⚠️ خطا!")
        return
    if low in ("قابلیت‌ها", "قابلیتها"):
        L = ["⚙️ <b>وضعیت قابلیت‌ها:</b>", ""]
        for key, num, title, _d in FEATURES:
            on, _e = get_toggle(uid, key)
            L.append(f"{'🟢' if on else '🔴'} {num}. {esc(title)}")
        await say("\n".join(L))
        return
    if low.startswith("قابلیت "):
        parts = low.split()
        if len(parts) >= 3:
            target, act = parts[1], parts[2]
            key = None
            if target.isdigit():
                for k, n, _t, _d in FEATURES:
                    if n == int(target):
                        key = k
            else:
                for k, _n, t, _d in FEATURES:
                    if target in t.replace(" ", "") or t.replace(" ", "") in target.replace(" ", ""):
                        key = k
                        break
            if key:
                set_toggle(uid, key, 1 if act in ("روشن", "on", "1") else 0)
                await say(f"✅ قابلیت «{esc(FEATURE_BY_KEY[key][1])}» {'🟢 روشن' if act in ('روشن','on','1') else '🔴 خاموش'} شد.")
                return
        await say("⚠️ مثلاً: <code>.قابلیت 1 روشن</code>")
        return
    if low.startswith("سبک "):
        st = low[3:].strip()
        mp = {"رسمی": "rasmi", "دوستانه": "doostane", "فان": "fun", "کوتاه": "kootah"}
        if st in mp:
            _o, _e = get_toggle(uid, "reply_style")
            set_toggle(uid, "reply_style", 1, mp[st])
            await say(f"🎭 سبک پاسخ شد: <b>{st}</b>")
        else:
            await say("⚠️ سبک: رسمی / دوستانه / فان / کوتاه")
        return
    if low.startswith("ترجمه ") or low.startswith("tr "):
        tgt = (low.split()[1] if len(low.split()) > 1 else "fa")
        rp = await event.get_reply_message()
        if not rp or not (rp.raw_text or rp.text or ""):
            await say("⚠️ روی یک پیام ریپلای کن!")
            return
        await say("⏳ در حال ترجمه...")
        await say(translate_text(rp.raw_text or rp.text, tgt))
        return
    if low == "خلاصه":
        rp = await event.get_reply_message()
        if not rp:
            await say("⚠️ روی یک پیام ریپلای کن!")
            return
        await say(summarize_text(rp.raw_text or rp.text or ""))
        return
    if low.startswith("جستجو "):
        q = low[6:].strip()
        if not q:
            await say("⚠️ کلمه را بنویس!")
            return
        try:
            msgs = await client.get_messages(event.chat_id, limit=300, search=q)
            L = [f"🔍 <b>{len(msgs)} نتیجه برای «{esc(q)}»:</b>", ""]
            for m_ in msgs[:10]:
                t = (m_.raw_text or "")[:80].replace("\n", " ")
                L.append(f"• {esc(t)}")
            await say("\n".join(L))
        except Exception:
            await say("⚠️ جستجو ناموفق بود!")
        return
    if low.startswith("بکاپ"):
        n = 100
        try:
            p = low.split()
            if len(p) > 1:
                n = max(10, min(500, int(p[1])))
        except Exception:
            pass
        try:
            msgs = await client.get_messages(event.chat_id, limit=n)
            buf = io.StringIO()
            buf.write(f"بکاپ گفتگو {event.chat_id} — {now_str()} — {len(msgs)} پیام\n{'='*30}\n")
            for m_ in reversed(msgs):
                buf.write(f"\n[{m_.date}] {(m_.raw_text or '')[:500]}\n---")
            data = buf.getvalue().encode("utf-8", "ignore")
            await client.send_file("me", io.BytesIO(data), caption=f"💾 بکاپ {len(msgs)} پیام", attributes=[])
            await say(f"✅ بکاپ {len(msgs)} پیام به سیو مسج ارسال شد.")
        except Exception as e:
            await say(f"⚠️ بکاپ ناموفق! ({esc(str(e)[:100])})")
        return
    if low.startswith("یادداشت‌ها"):
        try:
            conn = get_conn()
            rows = conn.execute("SELECT note,created FROM notes WHERE user_id=? AND chat_key=? ORDER BY id DESC LIMIT 10",
                                (uid, str(event.chat_id))).fetchall()
            conn.close()
            L = ["📌 <b>یادداشت‌های این گفتگو:</b>", ""]
            for r in rows:
                L.append(f"• {esc(r['note'][:200])} <i>({esc(r['created'])})</i>")
            await say("\n".join(L) if len(L) > 2 else "📌 یادداشتی نیست.")
        except Exception:
            await say("⚠️ خطا!")
        return
    if low.startswith("یادداشت "):
        note = low[8:].strip()[:800]
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO notes(user_id,chat_key,note,created) VALUES(?,?,?,?)",
                         (uid, str(event.chat_id), note, now_str()))
            conn.commit()
            conn.close()
        await say("📌 ذخیره شد ✅")
        return
    if low.startswith("دفترچه‌ها"):
        try:
            conn = get_conn()
            rows = conn.execute("SELECT note,created FROM notes WHERE user_id=? AND chat_key='notebook' ORDER BY id DESC LIMIT 10",
                                (uid,)).fetchall()
            conn.close()
            L = ["📓 <b>دفترچه:</b>", ""]
            for r in rows:
                L.append(f"• {esc(r['note'][:200])} <i>({esc(r['created'])})</i>")
            await say("\n".join(L) if len(L) > 2 else "📓 دفترچه خالی است.")
        except Exception:
            await say("⚠️ خطا!")
        return
    if low.startswith("دفترچه "):
        note = low[6:].strip()[:800]
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO notes(user_id,chat_key,note,created) VALUES(?,?,?,?)", (uid, "notebook", note, now_str()))
            conn.commit()
            conn.close()
        await say("📓 در دفترچه ذخیره شد ✅")
        return
    if low.startswith("دستورات"):
        _o, ex = get_toggle(uid, "personal_cmds")
        try:
            pc = json.loads(ex) if ex.startswith("{") else {}
        except Exception:
            pc = {}
        L = ["🛠 <b>دستورات شخصی:</b>", ""]
        for k in pc:
            L.append(f"• <code>.{esc(k)}</code>")
        await say("\n".join(L) if len(L) > 2 else "هنوز دستوری نساختی.")
        return
    if low.startswith("حذف دستور "):
        name = low[10:].strip()
        _o, ex = get_toggle(uid, "personal_cmds")
        try:
            pc = json.loads(ex) if ex.startswith("{") else {}
        except Exception:
            pc = {}
        pc.pop(name, None)
        set_toggle(uid, "personal_cmds", 1, json.dumps(pc, ensure_ascii=False))
        await say("🗑 حذف شد.")
        return
    if low.startswith("دستور "):
        rest = low[5:].strip().split(" ", 1)
        if len(rest) < 2:
            await say("⚠️ مثلاً: <code>.دستور سلام سلام رفیق!</code>")
            return
        _o, ex = get_toggle(uid, "personal_cmds")
        try:
            pc = json.loads(ex) if ex.startswith("{") else {}
        except Exception:
            pc = {}
        pc[rest[0][:30]] = rest[1][:1000]
        set_toggle(uid, "personal_cmds", 1, json.dumps(pc, ensure_ascii=False))
        await say(f"✅ دستور <code>.{esc(rest[0][:30])}</code> ساخته شد!")
        return
    if low.startswith("یادآوری "):
        parts = low[7:].strip().split(" ", 1)
        try:
            mins = int(fa_to_en(parts[0]))
            assert mins > 0
        except Exception:
            await say("⚠️ مثلاً: <code>.یادآوری 30 خرید نون</code>")
            return
        txt = parts[1] if len(parts) > 1 else "یادآور!"
        at = (now_tehran() + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO reminders(user_id,text,remind_at,done) VALUES(?,?,?,0)", (uid, txt[:500], at))
            conn.commit()
            conn.close()
        await say(f"⏰ یادآور ثبت شد: {mins} دقیقه بعد.")
        return
    if low.startswith("زمانبندی "):
        parts = low[8:].strip().split(" ", 1)
        try:
            mins = int(fa_to_en(parts[0]))
            assert mins > 0
        except Exception:
            await say("⚠️ مثلاً: <code>.زمانبندی 60 سلام بچه‌ها</code>")
            return
        txt = parts[1] if len(parts) > 1 else "..."
        at = (now_tehran() + timedelta(minutes=mins)).strftime("%Y-%m-%d %H:%M")
        with _db_lock:
            conn = get_conn()
            conn.execute("INSERT INTO scheduled_msgs(user_id,account_id,chat_id,text,send_at,sent,repeat_min) VALUES(?,?,?,?,?,0,0)",
                         (uid, acc_id, str(event.chat_id), txt[:1000], at))
            conn.commit()
            conn.close()
        await say(f"📤 زمان‌بندی شد: {mins} دقیقه بعد در همین چت.")
        return
    if low == "پروفایل":
        rp = await event.get_reply_message()
        if not rp or not rp.photo:
            await say("⚠️ روی یک عکس ریپلای کن!")
            return
        try:
            b = await rp.download_media(bytes)
            from telethon.tl.functions.photos import UploadProfilePhotoRequest
            await client(UploadProfilePhotoRequest(file=await client.upload_file(io.BytesIO(b), file_name="p.jpg")))
            await say("🖼 عکس پروفایل عوض شد ✅")
        except Exception as e:
            await say(f"⚠️ ناموفق! ({esc(str(e)[:120])})")
        return
    if low == "پین":
        rp = await event.get_reply_message()
        if not rp:
            await say("⚠️ روی پیام ریپلای کن!")
            return
        try:
            await rp.pin()
            await say("📌 سنجاق شد ✅")
        except Exception:
            await say("⚠️ دسترسی سنجاق نداری!")
        return
    # ---- تبچی ----
    if low == "تنظیم چت":
        g = get_tabchi_by_chat(uid, event.chat_id)
        if g:
            await say(f"⚠️ این گروه قبلاً ثبت شده (#{g['id']}).")
            return
        try:
            ent = await client.get_entity(event.chat_id)
            title = getattr(ent, "title", "") or getattr(ent, "first_name", "") or str(event.chat_id)
        except Exception:
            title = str(event.chat_id)
        with _db_lock:
            conn = get_conn()
            cur = conn.execute("INSERT INTO tabchi_groups(user_id,account_id,chat_id,title,text,interval_min,delay_sec,is_on,created)"
                               " VALUES(?,?,?,?,?,?,?,1,?)",
                               (uid, acc_id, str(event.chat_id), str(title)[:120], "", 30, 5, now_str()))
            gid = cur.lastrowid
            conn.commit()
            conn.close()
        await say(f"⚡ گروه ثبت شد! <b>#{gid}</b>\nحالا متن بده: <code>متن تبچی سلام...</code>\nو بنر: ریپلای عکس + <code>بنر</code>")
        return
    if low == "حذف چت":
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ این چت ثبت نشده!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("DELETE FROM tabchi_groups WHERE id=?", (g["id"],))
            conn.execute("DELETE FROM banner_data WHERE gid=?", (g["id"],))
            conn.commit()
            conn.close()
        await say("🗑 حذف شد.")
        return
    if low == "تبچی":
        rows = get_tabchi_groups(uid)
        L = [f"⚡ <b>گروه‌ها ({len(rows)}):</b>", ""]
        for g in rows[:20]:
            st = "🟢" if int(g.get("is_on", 0) or 0) else "🔴"
            L.append(f"{st} #{g['id']} {esc(g.get('title') or '')} | ⏱{g.get('interval_min', 30)}د | {(g.get('text') or '—')[:25]}")
        await say("\n".join(L))
        return
    if low.startswith("متن تبچی"):
        rest = low[8:].strip()
        if not rest:
            rp = await event.get_reply_message()
            rest = (rp.raw_text or "") if rp else ""
        if not rest.strip():
            await say("⚠️ متن را بنویس یا ریپلای کن!")
            return
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ اول <code>تنظیم چت</code> بزن!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE tabchi_groups SET text=? WHERE id=?", (rest.strip()[:1000], g["id"]))
            conn.commit()
            conn.close()
        await say(f"📝 متن تبچی #{g['id']} ذخیره شد ✅")
        return
    if low == "بنر":
        rp = await event.get_reply_message()
        if not rp or not (rp.photo or rp.sticker or rp.document):
            await say("⚠️ روی عکس/استیکر ریپلای کن!")
            return
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ اول <code>تنظیم چت</code> بزن!")
            return
        try:
            b = await rp.download_media(bytes)
            save_banner(g["id"], b, "jpg")
            await say(f"🖼 بنر #{g['id']} ثبت شد ✅")
        except Exception:
            await say("⚠️ ذخیره بنر ناموفق بود!")
        return
    if low.startswith("زمان "):
        try:
            v = max(1, int(fa_to_en(low[4:].strip())))
        except Exception:
            await say("⚠️ مثلاً: <code>زمان 30</code>")
            return
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ اول <code>تنظیم چت</code> بزن!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE tabchi_groups SET interval_min=? WHERE id=?", (v, g["id"]))
            conn.commit()
            conn.close()
        await say(f"⏱ هر {v} دقیقه ✅")
        return
    if low.startswith("فاصله "):
        try:
            v = max(1, int(fa_to_en(low[5:].strip())))
        except Exception:
            await say("⚠️ مثلاً: <code>فاصله 5</code>")
            return
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ اول <code>تنظیم چت</code> بزن!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE tabchi_groups SET delay_sec=? WHERE id=?", (v, g["id"]))
            conn.commit()
            conn.close()
        await say(f"⏳ فاصله {v} ثانیه ✅")
        return
    if low in ("تبچی روشن", "تبچی خاموش"):
        g = get_tabchi_by_chat(uid, event.chat_id)
        if not g:
            await say("⚠️ این چت ثبت نشده!")
            return
        with _db_lock:
            conn = get_conn()
            conn.execute("UPDATE tabchi_groups SET is_on=? WHERE id=?", (1 if low == "تبچی روشن" else 0, g["id"]))
            conn.commit()
            conn.close()
        await say(f"⚡ تبچی #{g['id']} {'🟢 روشن' if low == 'تبچی روشن' else '🔴 خاموش'} شد.")
        return
    await say("❓ دستور نامعتبر! <code>.راهنما</code> را ببین.")


# ============================================================
# زمان‌بندها
# ============================================================
def parse_dt(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        return None


def billing_loop():
    while True:
        try:
            time.sleep(60)
            fee = f_setting("hourly_fee", D_HOURLY_FEE)
            conn = get_conn()
            rows = conn.execute("SELECT * FROM self_accounts WHERE is_on=1").fetchall()
            conn.close()
            for r in rows:
                r = dict(r)
                try:
                    last = parse_dt(r.get("last_billing") or "")
                    if last and (now_tehran().replace(tzinfo=None) - last).total_seconds() < 3600:
                        continue
                    u = get_user(r["user_id"]) or {}
                    bal = float(u.get("diamonds", 0) or 0)
                    if bal >= fee:
                        add_diamonds(r["user_id"], -fee)
                        update_user(r["user_id"], total_spent=float(u.get("total_spent", 0) or 0) + fee)
                        update_self_account(r["id"], last_billing=now_str())
                    else:
                        update_self_account(r["id"], is_on=0)
                        stop_self_client(r["id"])
                        try:
                            bot.send_message(r["user_id"], panel_box("🔴 سلف خاموش شد", [
                                "💎 موجودی الماست برای شارژ ساعتی کافی نبود!",
                                f"⏳ هزینه ساعتی: {fmt_num(fee)} الماس",
                                "شارژ کن و دوباره روشنش کن ⚡",
                            ]), parse_mode="HTML")
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            time.sleep(60)


def tabchi_loop():
    while True:
        try:
            time.sleep(20)
            conn = get_conn()
            rows = conn.execute("SELECT * FROM tabchi_groups WHERE is_on=1").fetchall()
            conn.close()
            for r in rows:
                r = dict(r)
                try:
                    on_tb, _e = get_toggle(r["user_id"], "tabchi")
                    if not on_tb:
                        continue
                    last = parse_dt(r.get("last_sent") or "")
                    mins = int(r.get("interval_min", 30) or 30)
                    if last and (now_tehran().replace(tzinfo=None) - last).total_seconds() < mins * 60:
                        continue
                    if not (r.get("text") or "") and not load_banner(r["id"]):
                        continue
                    with self_clients_lock:
                        info = self_clients.get(int(r.get("account_id") or 0))
                        if not info:
                            for _aid, _inf in self_clients.items():
                                if _inf.get("user_id") == int(r["user_id"]):
                                    info = _inf
                                    break
                    if not info:
                        continue
                    client = info["client"]
                    b = load_banner(r["id"])
                    if b:
                        xcall(client, "send_file", str(r["chat_id"]), io.BytesIO(b[0]), caption=(r.get("text") or "")[:1000] or None)
                    else:
                        xcall(client, "send_message", str(r["chat_id"]), r.get("text") or "")
                    with _db_lock:
                        conn = get_conn()
                        conn.execute("UPDATE tabchi_groups SET last_sent=? WHERE id=?", (now_str(), r["id"]))
                        conn.commit()
                        conn.close()
                    bump_activity(r["user_id"], "tabchi")
                    time.sleep(max(1, int(r.get("delay_sec", 5) or 5)))
                except Exception as e:
                    log("tabchi send err", repr(e)[:200])
        except Exception:
            time.sleep(20)


def bio_name_loop():
    n = 0
    while True:
        try:
            time.sleep(600)
            n += 1
            with self_clients_lock:
                items = list(self_clients.items())
            for acc_id, info in items:
                try:
                    uid = info["user_id"]
                    client = info["client"]
                    on_b, _e = get_toggle(uid, "bio_rotate")
                    if on_b:
                        t = now_tehran()
                        bio = BIO_ROTATE_LIST[n % len(BIO_ROTATE_LIST)].format(
                            time=t.strftime("%H:%M"), date=t.strftime("%Y/%m/%d"))
                        try:
                            xcall(client, "__call__", UpdateProfileRequest(about=bio[:70]))
                        except Exception:
                            pass
                    on_nm, _e = get_toggle(uid, "name_rotate")
                    if on_nm and n % 6 == 0:
                        try:
                            me = xcall(client, "get_me")
                            base = (getattr(me, "first_name", "") or "🌙").split("🕒")[0].strip()[:40]
                            xcall(client, "__call__", UpdateProfileRequest(
                                first_name=f"{base} 🕒{now_tehran().strftime('%H:%M')}"))
                        except Exception:
                            pass
                    on_pf, _e = get_toggle(uid, "profile_schedule")
                    if on_pf and now_tehran().hour == 9 and n % 6 == 1:
                        try:
                            xcall(client, "send_message", "me", "⏰ یادآور سلف دارک: وقت تغییر عکس پروفایل! (ریپلای عکس + <code>.پروفایل</code>)")
                        except Exception:
                            pass
                    on_ar, _e = get_toggle(uid, "auto_archive")
                    if on_ar and n % 6 == 2:
                        try:
                            dialogs = xcall(client, "get_dialogs", limit=60)
                            for d in dialogs:
                                try:
                                    if getattr(d, "archived", False) or getattr(d, "pinned", False):
                                        continue
                                    if not getattr(d, "is_group", False):
                                        continue
                                    if getattr(d, "unread_count", 0):
                                        continue
                                    xcall(client, "edit_folder", d, 1)
                                except Exception:
                                    continue
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            time.sleep(300)


def reminders_loop():
    while True:
        try:
            time.sleep(30)
            conn = get_conn()
            rows = conn.execute("SELECT * FROM reminders WHERE done=0").fetchall()
            conn.close()
            now = now_tehran().replace(tzinfo=None)
            for r in rows:
                r = dict(r)
                at = parse_dt(r.get("remind_at") or "")
                if not at or at > now:
                    continue
                with _db_lock:
                    conn = get_conn()
                    conn.execute("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
                on, _e = get_toggle(r["user_id"], "reminders")
                if not on:
                    continue
                try:
                    bot.send_message(r["user_id"], f"⏰ <b>یادآور سلف:</b>\n{esc(r.get('text') or '')}", parse_mode="HTML")
                except Exception:
                    pass
        except Exception:
            time.sleep(30)


def scheduled_loop():
    while True:
        try:
            time.sleep(30)
            conn = get_conn()
            rows = conn.execute("SELECT * FROM scheduled_msgs WHERE sent=0").fetchall()
            conn.close()
            now = now_tehran().replace(tzinfo=None)
            for r in rows:
                r = dict(r)
                at = parse_dt(r.get("send_at") or "")
                if not at or at > now:
                    continue
                on, _e = get_toggle(r["user_id"], "scheduled_send")
                if not on:
                    on, _e = (1, "")
                with self_clients_lock:
                    info = self_clients.get(int(r.get("account_id") or 0))
                if info and on:
                    try:
                        xcall(info["client"], "send_message", str(r["chat_id"]), r.get("text") or "")
                    except Exception as e:
                        log("sched send err", repr(e)[:150])
                        continue
                else:
                    continue
                with _db_lock:
                    conn = get_conn()
                    if int(r.get("repeat_min", 0) or 0) > 0:
                        nxt = (now + timedelta(minutes=int(r["repeat_min"]))).strftime("%Y-%m-%d %H:%M")
                        conn.execute("UPDATE scheduled_msgs SET send_at=? WHERE id=?", (nxt, r["id"]))
                    else:
                        conn.execute("UPDATE scheduled_msgs SET sent=1 WHERE id=?", (r["id"],))
                    conn.commit()
                    conn.close()
        except Exception:
            time.sleep(30)


def daily_loop():
    while True:
        try:
            time.sleep(300)
            day = today_str()
            conn = get_conn()
            uids = conn.execute("SELECT DISTINCT user_id FROM self_accounts WHERE is_on=1").fetchall()
            conn.close()
            for rr in uids:
                uid = int(rr["user_id"])
                try:
                    on, _e = get_toggle(uid, "daily_report")
                    if not on:
                        continue
                    key = f"daily_{uid}_{day}"
                    if get_setting(key, ""):
                        continue
                    if now_tehran().hour < 23:
                        continue
                    conn = get_conn()
                    rows = conn.execute("SELECT kind,COALESCE(SUM(count),0) s FROM activity_log WHERE user_id=? AND day=? GROUP BY kind",
                                        (uid, day)).fetchall()
                    conn.close()
                    L = [f"📊 <b>گزارش روزانه سلف ({day}):</b>", ""]
                    for r2 in rows:
                        L.append(f"• {esc(r2['kind'])}: {r2['s']}")
                    u = get_user(uid) or {}
                    L += ["", f"💎 موجودی: {fmt_num(u.get('diamonds', 0))}"]
                    bot.send_message(uid, "\n".join(L), parse_mode="HTML")
                    set_setting(key, "1")
                except Exception:
                    pass
        except Exception:
            time.sleep(300)


def restore_saved_selfs():
    time.sleep(8)
    try:
        conn = get_conn()
        rows = conn.execute("SELECT id FROM self_accounts WHERE is_on=1").fetchall()
        conn.close()
        for r in rows:
            try:
                start_self_client(int(r["id"]))
                time.sleep(2)
            except Exception:
                pass
        log("restored selfs:", len(rows))
    except Exception as e:
        log("restore selfs err", repr(e)[:200])


# ============================================================
# وب‌هوک و اجرا
# ============================================================
@app.route("/", methods=["GET"])
def _index():
    try:
        conn = get_conn()
        nu = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        ns = conn.execute("SELECT COUNT(*) c FROM self_accounts WHERE is_on=1").fetchone()["c"]
        conn.close()
    except Exception:
        nu, ns = -1, -1
    return f"{BOT_VERSION} running ✅ | users={nu} selfs_on={ns} | telethon={'on' if TELETHON_OK else 'off'}", 200


@app.route("/health", methods=["GET"])
def _health():
    return {"ok": True, "version": BOT_VERSION, "telethon": TELETHON_OK,
            "clients": len(self_clients), "time": now_str()}, 200


@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def _webhook():
    try:
        data = request.get_data(as_text=True)
        upd = telebot.types.Update.de_json(json.loads(data))
        log("webhook update", getattr(upd, "update_id", "?"))
        bot.process_new_updates([upd])
    except Exception:
        log("webhook err", traceback.format_exc()[-600:])
    return "OK", 200


if __name__ == "__main__":
    init_db()
    ensure_extra_tables()
    log("starting", BOT_VERSION, "| telethon:", TELETHON_OK, "| admin:", ADMIN_ID)
    for fn, name in [(billing_loop, "billing"), (tabchi_loop, "tabchi"), (bio_name_loop, "bio"),
                     (reminders_loop, "reminders"), (scheduled_loop, "scheduled"), (daily_loop, "daily")]:
        threading.Thread(target=fn, name=name, daemon=True).start()
    threading.Thread(target=restore_saved_selfs, daemon=True).start()
    base = os.environ.get("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    port = int(os.environ.get("PORT", "10000"))
    try:
        bot.remove_webhook()
    except Exception:
        pass
    if base:
        url = f"{base}/webhook/{BOT_TOKEN}"
        bot.set_webhook(url=url)
        log("webhook set:", base + "/webhook/<token>")
        app.run(host="0.0.0.0", port=port, threaded=True)
    else:
        log("no RENDER_EXTERNAL_URL -> polling mode")
        bot.infinity_polling(skip_pending=True, timeout=20)
