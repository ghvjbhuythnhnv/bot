# -*- coding: utf-8 -*-
"""
🐶 ربات تلگرامی داگز رایگان | @FREEDOGSDARKBOT
سیستم زیرمجموعه‌گیری + جوین اجباری + کپچا ریاضی + برداشت اولتراولت + پنل ادمین کامل
آماده اجرا روی Render (Webhook) و لوکال (Polling)
"""
import os
import re
import csv
import html
import json
import time
import random
import sqlite3
import threading
from datetime import datetime

import telebot
from telebot import types
from flask import Flask, request

# ============================ تنظیمات اصلی ============================
TOKEN = os.environ.get("BOT_TOKEN", "9153804092:AAHKqmIb34Qeu0BUFbb8ZPz3w3O-0psV-5M")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8248647747"))
BOT_USERNAME = os.environ.get("BOT_USERNAME", "FREEDOGSDARKBOT").replace("@", "")
DB_PATH = os.environ.get("DB_PATH", "data.db")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)
app = Flask(__name__)

user_states = {}      # state های موقت کاربران {user_id: {"step":..., "data":{}}}
captcha_answers = {}  # جواب کپچای هر کاربر

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def today_str():
    return datetime.now().strftime("%Y-%m-%d")

def esc(x):
    return html.escape(str(x)) if x is not None else "—"

# ============================ دیتابیس ============================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
        balance INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0, total_withdrawn INTEGER DEFAULT 0,
        referrer_id INTEGER, referral_counted INTEGER DEFAULT 0,
        captcha_passed INTEGER DEFAULT 0, is_activated INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0, joined_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, title TEXT, url TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER,
        method TEXT, wallet_id TEXT, status TEXT DEFAULT 'pending',
        created_at TEXT, done_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT)""")
    defaults = {
        "referral_reward": "100",   # پاداش هر زیرمجموعه (داگز)
        "min_withdraw": "800",      # حداقل برداشت (داگز)
        "bot_on": "1",              # روشن/خاموش ربات
        "withdraw_on": "1",         # فعال/غیرفعال برداشت
        "captcha_on": "1",          # فعال/غیرفعال کپچا
        "force_join_on": "1",       # فعال/غیرفعال جوین اجباری
        "support_username": "",     # یوزرنیم پشتیبانی مثل @Admin
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()
    conn.close()

def get_setting(key, default=""):
    conn = get_conn()
    r = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return r["value"] if r else default

def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_int_setting(key, default=0):
    try:
        return int(float(get_setting(key, str(default))))
    except Exception:
        return default

def get_user(uid):
    conn = get_conn()
    r = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()
    return dict(r) if r else None

def create_user(uid, username, first_name, referrer_id=None):
    is_admin = 1 if uid == ADMIN_ID else 0
    conn = get_conn()
    conn.execute("""INSERT OR IGNORE INTO users(user_id,username,first_name,referrer_id,
        captcha_passed,is_activated,joined_at) VALUES(?,?,?,?,?,?,?)""",
        (uid, username or "", first_name or "", referrer_id, is_admin, is_admin, now_str()))
    conn.commit()
    conn.close()

def update_user(uid, **kw):
    if not kw:
        return
    cols = ", ".join(f"{k}=?" for k in kw)
    conn = get_conn()
    conn.execute(f"UPDATE users SET {cols} WHERE user_id=?", (*kw.values(), uid))
    conn.commit()
    conn.close()

def inc_user(uid, field, amount):
    conn = get_conn()
    conn.execute(f"UPDATE users SET {field}={field}+? WHERE user_id=?", (amount, uid))
    conn.commit()
    conn.close()

def get_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM channels ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def all_user_ids():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def is_admin(uid):
    return uid == ADMIN_ID

def set_state(uid, step, data=None):
    user_states[uid] = {"step": step, "data": data or {}}

def clear_state(uid):
    user_states.pop(uid, None)

# ============================ کیبوردها ============================
def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("👤 حساب کاربری", "🎁 دعوت دوستان")
    kb.row("💸 برداشت داگز", "📜 سفارش‌های من")
    kb.row("📖 راهنما و قوانین", "🆘 پشتیبانی")
    if is_admin(uid):
        kb.row("🛠 پنل ادمین")
    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📊 آمار کامل ربات", "💸 آمار برداشت‌ها")
    kb.row("➕ افزودن کانال جوین", "➖ حذف کانال جوین")
    kb.row("📋 لیست کانال‌های جوین", "🔍 جستجوی کاربر")
    kb.row("🚫 بن کاربر", "♻️ آنبن کاربر")
    kb.row("📢 پیام همگانی", "📨 فوروارد همگانی")
    kb.row("🎁 تغییر پاداش زیرمجموعه", "💰 تغییر حداقل برداشت")
    kb.row("🔌 خاموش / روشن ربات", "💳 فعال/غیرفعال برداشت")
    kb.row("🧩 فعال/غیرفعال کپچا", "🔒 فعال/غیرفعال جوین اجباری")
    kb.row("💵 افزایش موجودی کاربر", "🧾 کسر موجودی کاربر")
    kb.row("✉️ پیام به یک کاربر", "⏳ سفارش‌های در انتظار")
    kb.row("🏆 برترین دعوت‌کنندگان", "⛔️ لیست کاربران مسدود")
    kb.row("📥 بکاپ‌گیری کامل", "📤 بازگردانی بکاپ")
    kb.row("📑 خروجی CSV کاربران", "🆘 تنظیم پشتیبانی")
    kb.row("🔙 بازگشت به منوی اصلی")
    return kb

# ============================ متن‌ها ============================
WELCOME = """🐶 <b>به ربات داگز رایگان خوش اومدی!</b> 🎉

💎 اینجا می‌تونی بدون هیچ سرمایه‌ای، فقط با دعوت کردن دوستات <b>داگز (DOGS)</b> رایگان بگیری!

🎁 <b>پاداش هر دعوت:</b> {reward} داگز
💸 <b>حداقل برداشت:</b> {minwd} داگز
⚡️ برداشت سریع و مستقیم به <b>اولتراولت (Ultra Wallet)</b>

👇 از منوی پایین استفاده کن و کسب درآمدت رو شروع کن! 🚀"""

GUIDE = """📖 <b>راهنما و قوانین ربات</b>

🔹 <b>چطور داگز بگیرم؟</b>
از بخش «🎁 دعوت دوستان» لینک اختصاصی خودت رو بردار و برای دوستات بفرست. به ازای هر نفری که با لینک تو وارد ربات بشه، عضو کانال‌های اجباری بشه و کپچای امنیتی رو درست حل کنه، <b>{reward} داگز</b> هدیه می‌گیری! 🐶

🔹 <b>چطور برداشت کنم؟</b>
وقتی موجودیت به حداقل <b>{minwd} داگز</b> رسید، از بخش «💸 برداشت داگز» مبلغ رو وارد کن، گزینه برداشت به اولتراولت رو بزن و آیدی عددی اولتراولتت رو بفرست. سفارشت ثبت میشه و بعد از بررسی مدیریت، داگز برات واریز و داخل ربات بهت اطلاع داده میشه. ✅

⚠️ <b>قوانین:</b>
1️⃣ استفاده از اکانت فیک و چند اکانت برای زیرمجموعه‌گیری ممنوعه و باعث مسدودی و حذف موجودی میشه.
2️⃣ عضویت در کانال‌های اجباری برای همه کاربران و در تمام زمان استفاده از ربات الزامیه؛ اگر از هر کانالی خارج بشی، دسترسی‌ات به همه بخش‌های ربات بسته میشه تا وقتی دوباره عضو بشی.
3️⃣ آیدی عددی اولتراولت رو با دقت وارد کن؛ مسئولیت اشتباه وارد کردن با خودته.
4️⃣ سفارش‌ها به ترتیب ثبت بررسی و پرداخت میشن، پس لطفاً صبور باش. 🙏

موفق و پرداگز باشی! 🐾💰"""

BOT_OFF_TEXT = "🔌 <b>ربات فعلاً از طرف مدیریت خاموش شده است.</b>\n\n⏳ لطفاً کمی بعد دوباره تلاش کنید. از صبر و همراهی شما سپاسگزاریم 🙏"
BANNED_TEXT = "🚫 <b>حساب شما توسط مدیریت مسدود شده است.</b>\nدر صورت نیاز با پشتیبانی در تماس باشید."

# ============================ کپچا و جوین اجباری ============================
def send_captcha(chat_id, uid):
    a, b = random.randint(2, 9), random.randint(2, 9)
    ans = a + b
    captcha_answers[uid] = ans
    opts = list({ans, ans + 1, ans + 2, max(1, ans - 1)})
    while len(opts) < 4:
        opts.append(ans + random.randint(3, 6))
        opts = list(set(opts))
    random.shuffle(opts)
    kb = types.InlineKeyboardMarkup(row_width=4)
    kb.add(*[types.InlineKeyboardButton(str(o), callback_data=f"cap:{o}") for o in opts])
    bot.send_message(chat_id,
        f"🛡 <b>تأیید امنیتی (کپچا)</b>\n\n"
        f"سلام دوست عزیز! 👋 برای اینکه مطمئن بشیم ربات نیستی و حسابت فعال بشه، "
        f"این جمع ساده ریاضی رو حل کن:\n\n"
        f"🧮 <b>{a} + {b} = ؟</b>\n\n👇 جواب درست رو از دکمه‌های زیر انتخاب کن:",
        reply_markup=kb)

def check_membership(uid):
    """بررسی عضویت در همه کانال‌ها. خروجی: (همه عضو هست؟, لیست کانال‌هایی که عضو نیست)"""
    if get_int_setting("force_join_on", 1) == 0:
        return True, []
    chans = get_channels()
    if not chans:
        return True, []
    not_joined = []
    for ch in chans:
        try:
            m = bot.get_chat_member(ch["chat_id"], uid)
            if m.status not in ("creator", "administrator", "member", "restricted"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return (len(not_joined) == 0), not_joined

def send_join_message(chat_id, uid, not_joined=None):
    chans = not_joined if not_joined is not None else get_channels()
    kb = types.InlineKeyboardMarkup()
    for ch in chans:
        kb.add(types.InlineKeyboardButton(f"📢 عضویت در {ch['title']}", url=ch["url"]))
    kb.add(types.InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join"))
    u = get_user(uid)
    if u and u["is_activated"]:
        text = (
            "🔒 <b>دسترسی شما موقتاً بسته شد!</b>\n\n"
            "⚠️ دوست عزیز، شما از یک یا چند کانال/گروه جوین اجباری خارج شده‌اید یا هنوز عضو کانال جدید اجباری نشده‌اید.\n\n"
            "عضویت در همه کانال‌های اجباری برای استفاده از <b>تمام بخش‌های ربات</b> الزامی است و عضویت شما در هر بار استفاده بررسی می‌شود.\n\n"
            "1️⃣ در کانال‌ها و گروه‌های زیر دوباره عضو شوید\n"
            "2️⃣ سپس دکمه «✅ بررسی عضویت» را بزنید\n\n"
            "💰 نگران نباشید؛ موجودی، زیرمجموعه‌ها و سفارش‌های شما حفظ می‌شود و بعد از عضویت مجدد، دسترسی‌تان فوراً باز خواهد شد ✅"
        )
    else:
        text = (
            "🔒 <b>عضویت اجباری برای همه کاربران</b>\n\n"
            "دوست عزیز، برای ورود و استفاده از تمام بخش‌های ربات و دریافت داگز رایگان 🐶 باید اول در همه کانال‌ها و گروه‌های زیر عضو بشی؛ فرقی نمی‌کنه با لینک دعوت اومده باشی یا مستقیم ربات رو استارت کرده باشی.\n\n"
            "1️⃣ روی هر دکمه بزن و عضو شو\n"
            "2️⃣ بعد دکمه «✅ بررسی عضویت» رو بزن\n"
            "3️⃣ در مرحله بعد کپچای امنیتی ریاضی رو حل کن\n\n"
            "⚠️ تا وقتی عضو همه کانال‌ها نشی و کپچا رو درست حل نکنی، حسابت فعال نمیشه، زیرمجموعه حساب نمیشی و نمی‌تونی از هیچ بخش ربات استفاده کنی.\n"
            "همچنین اگر بعداً از هر کانالی خارج بشی، دسترسی‌ات دوباره بسته میشه تا وقتی مجدد عضو بشی."
        )
    bot.send_message(chat_id, text, reply_markup=kb)

def activate_user(uid, chat_id):
    """فعال‌سازی نهایی کاربر + پرداخت پاداش به معرف (فقط یک بار)"""
    u = get_user(uid)
    if not u:
        return
    if u["is_activated"]:
        bot.send_message(chat_id, "🏠 <b>منوی اصلی</b>", reply_markup=main_menu(uid))
        return
    update_user(uid, is_activated=1)
    # پاداش زیرمجموعه‌گیری
    if u.get("referrer_id") and not u.get("referral_counted"):
        ref_id = u["referrer_id"]
        referrer = get_user(ref_id)
        if referrer and ref_id != uid:
            reward = get_int_setting("referral_reward", 100)
            update_user(uid, referral_counted=1)
            inc_user(ref_id, "balance", reward)
            inc_user(ref_id, "total_earned", reward)
            inc_user(ref_id, "referrals", 1)
            try:
                bot.send_message(ref_id,
                    f"🎉 <b>زیرمجموعه جدید گرفتی!</b> 🐶\n\n"
                    f"👤 یک کاربر جدید با لینک تو وارد ربات شد، عضو کانال‌های اجباری شد و کپچا رو درست حل کرد ✅\n\n"
                    f"🎁 <b>+{reward} داگز</b> به موجودیت اضافه شد!\n"
                    f"💰 موجودی فعلی تو: <b>{get_user(ref_id)['balance']} داگز</b>\n\n"
                    f"🚀 همینطور ادامه بده؛ هرچی دعوت بیشتر، داگز بیشتر!")
            except Exception:
                pass
    reward = get_int_setting("referral_reward", 100)
    minwd = get_int_setting("min_withdraw", 800)
    bot.send_message(chat_id,
        "🎉 <b>آفرین! حسابت با موفقیت فعال شد</b> ✅\n\n" +
        WELCOME.format(reward=reward, minwd=minwd),
        reply_markup=main_menu(uid))

def access_gate(chat_id, uid):
    """🔒 دروازه دسترسی دائمی ربات

    این تابع قبل از پردازش هر پیام، کامند و دکمه شیشه‌ای اجرا می‌شود:
    1) عضویت کاربر در همه کانال‌ها/گروه‌های جوین اجباری — در هر بار استفاده
    2) کپچای کاربران جدید (فقط تا فعال‌سازی اولیه)
    3) فعال‌سازی و ثبت زیرمجموعه (فقط یک بار)

    خروجی True یعنی کاربر اجازه استفاده از بخش درخواستی را دارد.
    خروجی False یعنی پیام جوین اجباری/کپچا/فعال‌سازی ارسال شده و درخواست فعلی
    نباید پردازش شود. فقط ادمین برای جلوگیری از قفل‌شدن مدیریت ربات معاف است.
    """
    if is_admin(uid):
        return True
    u = get_user(uid)
    if not u:
        return False

    # اول: جوین اجباری برای همه؛ هم کاربر عادی، هم زیرمجموعه و هم کاربران قدیمی
    ok, not_joined = check_membership(uid)
    if not ok:
        clear_state(uid)
        captcha_answers.pop(uid, None)
        send_join_message(chat_id, uid, not_joined)
        return False

    # کاربران فعال فقط با عضویت کامل اجازه ادامه دارند و دیگر کپچا نمی‌بینند
    if u["is_activated"]:
        return True

    # دوم: کپچا برای فعال‌سازی اولیه
    if get_int_setting("captcha_on", 1) == 1 and not u["captcha_passed"]:
        clear_state(uid)
        send_captcha(chat_id, uid)
        return False

    # سوم: فعال‌سازی نهایی و پرداخت یک‌باره پاداش معرف
    clear_state(uid)
    activate_user(uid, chat_id)
    return False

def gate(chat_id, uid):
    """نام قدیمی دروازه ورود؛ برای سازگاری نگه داشته شده است."""
    return access_gate(chat_id, uid)

# ============================ کامندها ============================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = message.from_user.id
    clear_state(uid)
    referrer_id = None
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref_"):
        try:
            rid = int(parts[1].replace("ref_", ""))
            if rid != uid and get_user(rid):
                referrer_id = rid
        except Exception:
            pass
    u = get_user(uid)
    if not u:
        create_user(uid, message.from_user.username, message.from_user.first_name, referrer_id)
        u = get_user(uid)
        try:
            bot.send_message(ADMIN_ID,
                f"🆕 <b>کاربر جدید وارد ربات شد</b>\n\n"
                f"👤 نام: {esc(message.from_user.first_name)}\n"
                f"🆔 آیدی عددی: <code>{uid}</code>\n"
                f"📎 یوزرنیم: @{esc(message.from_user.username or '—')}\n"
                f"🎁 معرف: <code>{referrer_id or '—'}</code>")
        except Exception:
            pass
    else:
        update_user(uid, username=message.from_user.username or "",
                    first_name=message.from_user.first_name or "")
    if u["is_banned"] and not is_admin(uid):
        bot.send_message(message.chat.id, BANNED_TEXT)
        return
    if get_int_setting("bot_on", 1) == 0 and not is_admin(uid):
        bot.send_message(message.chat.id, BOT_OFF_TEXT)
        return
    # در هر /start عضویت همه کاربران (عادی، قدیمی و زیرمجموعه) دوباره بررسی می‌شود
    if not is_admin(uid) and not access_gate(message.chat.id, uid):
        return
    reward = get_int_setting("referral_reward", 100)
    minwd = get_int_setting("min_withdraw", 800)
    bot.send_message(message.chat.id, WELCOME.format(reward=reward, minwd=minwd),
                     reply_markup=main_menu(uid))

@bot.message_handler(commands=["admin"])
def cmd_admin(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, admin_panel_text(), reply_markup=admin_menu())

@bot.message_handler(commands=["cancel"])
def cmd_cancel(message):
    uid = message.from_user.id
    if not get_user(uid):
        create_user(uid, message.from_user.username, message.from_user.first_name)
    clear_state(uid)
    bot.send_message(message.chat.id, "❌ عملیات لغو شد.")
    # حتی بعد از لغو هم کاربر غیرعضو به منوی اصلی و بخش‌ها دسترسی ندارد
    if is_admin(uid) or access_gate(message.chat.id, uid):
        bot.send_message(message.chat.id, "🏠 <b>منوی اصلی</b>", reply_markup=main_menu(uid))

@bot.message_handler(commands=["id"])
def cmd_id(message):
    uid = message.from_user.id
    if not get_user(uid):
        create_user(uid, message.from_user.username, message.from_user.first_name)
    u = get_user(uid)
    if not is_admin(uid):
        if u and u["is_banned"]:
            bot.send_message(message.chat.id, BANNED_TEXT)
            return
        if get_int_setting("bot_on", 1) == 0:
            bot.send_message(message.chat.id, BOT_OFF_TEXT)
            return
        if not access_gate(message.chat.id, uid):
            return
    bot.reply_to(message, f"🆔 آیدی عددی شما: <code>{uid}</code>")

def admin_panel_text():
    on = "🟢 روشن" if get_int_setting("bot_on", 1) == 1 else "🔴 خاموش"
    return (f"🛠 <b>پنل مدیریت ربات</b> 🐶\n\n"
            f"وضعیت ربات: {on}\n"
            f"🎁 پاداش زیرمجموعه: <b>{get_int_setting('referral_reward',100)} داگز</b>\n"
            f"💰 حداقل برداشت: <b>{get_int_setting('min_withdraw',800)} داگز</b>\n\n"
            f"👇 یکی از گزینه‌های زیر را انتخاب کنید:")

# ============================ متن حساب کاربری و... ============================
def account_text(u):
    status = "🚫 مسدود" if u["is_banned"] else ("✅ فعال" if u["is_activated"] else "⏳ غیرفعال")
    return (f"👤 <b>حساب کاربری شما</b>\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"📛 نام: <b>{esc(u['first_name'])}</b>\n"
            f"📎 یوزرنیم: @{esc(u['username'] or '—')}\n"
            f"🆔 آیدی عددی: <code>{u['user_id']}</code>\n"
            f"📌 وضعیت حساب: {status}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 <b>موجودی: {u['balance']} داگز 🐶</b>\n"
            f"👥 تعداد زیرمجموعه‌ها: <b>{u['referrals']} نفر</b>\n"
            f"🎁 مجموع درآمد از دعوت: <b>{u['total_earned']} داگز</b>\n"
            f"💸 مجموع برداشت موفق: <b>{u['total_withdrawn']} داگز</b>\n"
            f"🎁 معرف شما: <code>{u['referrer_id'] or '—'}</code>\n"
            f"📅 تاریخ عضویت: {esc(u['joined_at'])}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🔗 لینک دعوت اختصاصی شما:\n<code>https://t.me/{BOT_USERNAME}?start=ref_{u['user_id']}</code>")

def order_status_fa(s):
    return {"pending": "⏳ در حال بررسی", "done": "✅ انجام شده", "rejected": "❌ رد شده (عودت داده شد)"}.get(s, s)

def admin_order_kb(order_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ انجام شد", callback_data=f"order_done:{order_id}"),
           types.InlineKeyboardButton("❌ رد کردن + عودت", callback_data=f"order_reject:{order_id}"))
    return kb

def send_order_to_admin(order, user_before_balance):
    u = get_user(order["user_id"])
    text = (f"🧾 <b>سفارش برداشت جدید ثبت شد!</b> 🐶\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"🔖 شماره سفارش: <b>#{order['id']}</b>\n"
            f"📌 وضعیت: {order_status_fa(order['status'])}\n\n"
            f"👤 <b>مشخصات کاربر:</b>\n"
            f"📛 نام: {esc(u['first_name']) if u else '—'}\n"
            f"📎 یوزرنیم: @{esc(u['username']) if u and u['username'] else '—'}\n"
            f"🆔 آیدی عددی تلگرام: <code>{order['user_id']}</code>\n"
            f"👥 زیرمجموعه‌ها: {u['referrals'] if u else '—'} نفر\n"
            f"🎁 مجموع درآمد از دعوت: {u['total_earned'] if u else '—'} داگز\n"
            f"💸 برداشت‌های موفق قبلی: {u['total_withdrawn'] if u else '—'} داگز\n"
            f"📅 عضویت در ربات: {esc(u['joined_at']) if u else '—'}\n\n"
            f"💰 <b>جزئیات سفارش:</b>\n"
            f"🐶 مبلغ برداشت: <b>{order['amount']} داگز</b>\n"
            f"💎 روش برداشت: اولتراولت (Ultra Wallet)\n"
            f"🔢 آیدی عددی اولتراولت کاربر: <code>{esc(order['wallet_id'])}</code>\n"
            f"💵 موجودی قبل از سفارش: {user_before_balance} داگز\n"
            f"💵 موجودی بعد از ثبت سفارش: {u['balance'] if u else '—'} داگز\n"
            f"🕐 زمان ثبت: {esc(order['created_at'])}\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"👇 بعد از واریز، دکمه «✅ انجام شد» را بزنید تا به کاربر اطلاع‌رسانی شود.")
    bot.send_message(ADMIN_ID, text, reply_markup=admin_order_kb(order["id"]))

# ============================ آمار ============================
def full_stats_text():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
    act = conn.execute("SELECT COUNT(*) c FROM users WHERE is_activated=1").fetchone()["c"]
    ban = conn.execute("SELECT COUNT(*) c FROM users WHERE is_banned=1").fetchone()["c"]
    today = conn.execute("SELECT COUNT(*) c FROM users WHERE substr(joined_at,1,10)=?", (today_str(),)).fetchone()["c"]
    sum_bal = conn.execute("SELECT COALESCE(SUM(balance),0) s FROM users").fetchone()["s"]
    sum_earn = conn.execute("SELECT COALESCE(SUM(total_earned),0) s FROM users").fetchone()["s"]
    refs = conn.execute("SELECT COALESCE(SUM(referrals),0) s FROM users").fetchone()["s"]
    orders = conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"]
    pend = conn.execute("SELECT COUNT(*) c FROM orders WHERE status='pending'").fetchone()["c"]
    conn.close()
    return (f"📊 <b>آمار کامل ربات</b>\n➖➖➖➖➖➖➖➖➖➖\n"
            f"👥 کل کاربران: <b>{total}</b>\n✅ کاربران فعال: <b>{act}</b>\n"
            f"🚫 کاربران مسدود: <b>{ban}</b>\n🆕 عضویت امروز: <b>{today}</b>\n"
            f"🎁 کل زیرمجموعه‌گیری‌ها: <b>{refs}</b>\n"
            f"💰 مجموع موجودی کاربران: <b>{sum_bal} داگز</b>\n"
            f"🎁 مجموع پاداش پرداخت‌شده: <b>{sum_earn} داگز</b>\n"
            f"🧾 کل سفارش‌ها: <b>{orders}</b> | ⏳ در انتظار: <b>{pend}</b>\n"
            f"📢 کانال‌های جوین اجباری: <b>{len(get_channels())}</b>\n"
            f"🔌 ربات: {'🟢 روشن' if get_int_setting('bot_on',1)==1 else '🔴 خاموش'}\n"
            f"💳 برداشت: {'🟢 فعال' if get_int_setting('withdraw_on',1)==1 else '🔴 غیرفعال'}\n"
            f"🧩 کپچا: {'🟢 فعال' if get_int_setting('captcha_on',1)==1 else '🔴 غیرفعال'}\n"
            f"🔒 جوین اجباری: {'🟢 فعال' if get_int_setting('force_join_on',1)==1 else '🔴 غیرفعال'}\n"
            f"🎁 پاداش زیرمجموعه: <b>{get_int_setting('referral_reward',100)} داگز</b>\n"
            f"💰 حداقل برداشت: <b>{get_int_setting('min_withdraw',800)} داگز</b>")

def withdraw_stats_text():
    conn = get_conn()
    def q(sql, p=()):
        return conn.execute(sql, p).fetchone()
    done = q("SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM orders WHERE status='done'")
    pend = q("SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM orders WHERE status='pending'")
    rej = q("SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM orders WHERE status='rejected'")
    td = q("SELECT COALESCE(SUM(amount),0) s FROM orders WHERE status='done' AND substr(done_at,1,10)=?", (today_str(),))
    conn.close()
    return (f"💸 <b>آمار برداشت‌های داگز</b>\n➖➖➖➖➖➖➖➖➖➖\n"
            f"✅ پرداخت‌شده: <b>{done['s']} داگز</b> ({done['c']} سفارش)\n"
            f"📅 پرداخت‌شده امروز: <b>{td['s']} داگز</b>\n"
            f"⏳ در انتظار پرداخت: <b>{pend['s']} داگز</b> ({pend['c']} سفارش)\n"
            f"❌ رد شده و عودت: <b>{rej['s']} داگز</b> ({rej['c']} سفارش)")

def find_user(query):
    query = (query or "").strip()
    conn = get_conn()
    if query.isdigit() or (query.startswith("-") and query[1:].isdigit()):
        r = conn.execute("SELECT * FROM users WHERE user_id=?", (int(query),)).fetchone()
    else:
        r = conn.execute("SELECT * FROM users WHERE lower(username)=lower(?)", (query.replace("@", ""),)).fetchone()
    conn.close()
    return dict(r) if r else None

def send_user_card(chat_id, u):
    kb = types.InlineKeyboardMarkup(row_width=2)
    if u["is_banned"]:
        kb.add(types.InlineKeyboardButton("♻️ آنبن کردن", callback_data=f"sunban:{u['user_id']}"))
    else:
        kb.add(types.InlineKeyboardButton("🚫 بن کردن", callback_data=f"sban:{u['user_id']}"))
    kb.add(types.InlineKeyboardButton("💵 افزایش موجودی", callback_data=f"sadd:{u['user_id']}"),
           types.InlineKeyboardButton("🧾 کسر موجودی", callback_data=f"ssub:{u['user_id']}"))
    kb.add(types.InlineKeyboardButton("✉️ ارسال پیام", callback_data=f"spm:{u['user_id']}"))
    bot.send_message(chat_id, "🔍 <b>نتیجه جستجوی کاربر:</b>\n\n" + account_text(u), reply_markup=kb)

# ============================ بکاپ و بازگردانی ============================
def make_backup_json(path="backup.json"):
    conn = get_conn()
    data = {}
    for t in ("users", "channels", "orders", "settings"):
        rows = conn.execute(f"SELECT * FROM {t}").fetchall()
        data[t] = [dict(r) for r in rows]
    conn.close()
    data["_created_at"] = now_str()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return path

def restore_from_json(file_bytes):
    data = json.loads(file_bytes.decode("utf-8"))
    conn = get_conn()
    c = conn.cursor()
    cols = {
        "users": ["user_id","username","first_name","balance","referrals","total_earned","total_withdrawn","referrer_id","referral_counted","captcha_passed","is_activated","is_banned","joined_at"],
        "channels": ["id","chat_id","title","url"],
        "orders": ["id","user_id","amount","method","wallet_id","status","created_at","done_at"],
        "settings": ["key","value"],
    }
    for t, cl in cols.items():
        if t in data:
            c.execute(f"DELETE FROM {t}")
            for row in data[t]:
                ph = ",".join("?" * len(cl))
                c.execute(f"INSERT OR REPLACE INTO {t}({','.join(cl)}) VALUES({ph})",
                          tuple(row.get(x) for x in cl))
    conn.commit()
    conn.close()

def normalize_chat_id(raw):
    raw = (raw or "").strip()
    m = re.match(r"https?://t\.me/([A-Za-z0-9_]+)", raw)
    if m:
        return "@" + m.group(1)
    return raw

# ============================ پردازش State ها ============================
def handle_state(message, state):
    uid = message.from_user.id
    chat_id = message.chat.id
    step = state["step"]
    data = state["data"]
    text = (message.text or "").strip()

    # --- بازگردانی بکاپ (فایل) ---
    if step == "restore_backup":
        if message.content_type != "document":
            bot.send_message(chat_id, "📄 لطفاً فایل بکاپ (backup.json یا data.db) را ارسال کنید. برای لغو: /cancel")
            return
        try:
            fi = bot.get_file(message.document.file_id)
            fbytes = bot.download_file(fi.file_path)
            fname = (message.document.file_name or "").lower()
            if fname.endswith(".json"):
                restore_from_json(fbytes)
            elif fname.endswith(".db") or fname.endswith(".sqlite"):
                tmp = DB_PATH + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(fbytes)
                test = sqlite3.connect(tmp)
                test.execute("SELECT COUNT(*) FROM users")
                test.close()
                os.replace(tmp, DB_PATH)
                init_db()
            else:
                bot.send_message(chat_id, "❌ فرمت فایل پشتیبانی نمی‌شود. فقط backup.json یا data.db بفرستید.")
                return
            clear_state(uid)
            bot.send_message(chat_id, "✅ <b>بکاپ با موفقیت بازگردانی شد!</b>\nهمه اطلاعات کاربران، کانال‌ها، سفارش‌ها و تنظیمات برگشتند. 🎉", reply_markup=admin_menu())
        except Exception as e:
            clear_state(uid)
            bot.send_message(chat_id, f"❌ خطا در بازگردانی بکاپ:\n<code>{esc(e)}</code>", reply_markup=admin_menu())
        return

    # --- فوروارد همگانی (هر نوع پیام) ---
    if step == "broadcast_fwd":
        clear_state(uid)
        ids = all_user_ids()
        bot.send_message(chat_id, f"📨 در حال ارسال همگانی به {len(ids)} کاربر...")
        ok = fail = 0
        for x in ids:
            try:
                bot.copy_message(x, chat_id, message.message_id)
                ok += 1
            except Exception:
                fail += 1
            time.sleep(0.05)
        bot.send_message(chat_id, f"✅ <b>فوروارد همگانی تمام شد</b>\n📬 موفق: {ok}\n❌ ناموفق: {fail}", reply_markup=admin_menu())
        return

    # --- پیام پشتیبانی کاربر ---
    if step == "support_msg":
        clear_state(uid)
        u = get_user(uid)
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("↩️ پاسخ به این کاربر", callback_data=f"sup_reply:{uid}"))
        try:
            bot.send_message(ADMIN_ID,
                f"🆘 <b>پیام پشتیبانی جدید</b>\n\n👤 {esc(u['first_name'] if u else '')} "
                f"(@{esc(u['username']) if u and u['username'] else '—'})\n🆔 <code>{uid}</code>",
                reply_markup=kb)
            bot.copy_message(ADMIN_ID, chat_id, message.message_id)
        except Exception:
            pass
        bot.send_message(chat_id, "✅ <b>پیامت به پشتیبانی ارسال شد!</b>\nدر اسرع وقت جوابت رو همینجا می‌گیری 🙏", reply_markup=main_menu(uid))
        return

    # از اینجا به بعد متن لازم است
    if not text:
        bot.send_message(chat_id, "✍️ لطفاً متن ارسال کنید. برای لغو: /cancel")
        return

    # --- برداشت: مبلغ ---
    if step == "withdraw_amount":
        u = get_user(uid)
        minwd = get_int_setting("min_withdraw", 800)
        reward = get_int_setting("referral_reward", 100)
        try:
            amount = int(text.replace(",", ""))
        except Exception:
            bot.send_message(chat_id, "❌ لطفاً مبلغ را فقط به صورت <b>عدد</b> وارد کنید. مثال: <code>800</code>")
            return
        if amount < minwd:
            need = max(0, minwd - u["balance"])
            refs = (need + reward - 1) // reward if reward else 0
            bot.send_message(chat_id,
                f"⚠️ مبلغ واردشده (<b>{amount} داگز</b>) کمتر از حداقل برداشت (<b>{minwd} داگز</b>) است!\n\n"
                f"💰 موجودی فعلی شما: <b>{u['balance']} داگز</b>\n"
                f"🎯 برای رسیدن به حداقل برداشت، <b>{need} داگز</b> دیگه لازم داری؛ یعنی حدود <b>{refs} زیرمجموعه</b> جدید!\n\n"
                f"🎁 برو بخش «🎁 دعوت دوستان» و با زیرمجموعه‌گیری موجودیت رو افزایش بده 🚀")
            clear_state(uid)
            return
        if amount > u["balance"]:
            need = amount - u["balance"]
            refs = (need + reward - 1) // reward if reward else 0
            bot.send_message(chat_id,
                f"⚠️ مبلغ واردشده (<b>{amount} داگز</b>) بیشتر از موجودی شما (<b>{u['balance']} داگز</b>) است!\n\n"
                f"🎯 <b>{need} داگز</b> کم داری؛ با گرفتن حدود <b>{refs} زیرمجموعه</b> جدید جبرانش کن.\n\n"
                f"🎁 از بخش «🎁 دعوت دوستان» زیرمجموعه‌گیری کن و دوباره برگرد 🚀")
            clear_state(uid)
            return
        set_state(uid, "withdraw_method", {"amount": amount})
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("💎 برداشت به اولتراولت (Ultra Wallet)", callback_data="wd_ultra"))
        kb.add(types.InlineKeyboardButton("❌ لغو برداشت", callback_data="wd_cancel"))
        bot.send_message(chat_id,
            f"✅ مبلغ <b>{amount} داگز 🐶</b> ثبت شد.\n\n💎 حالا روش برداشت رو انتخاب کن:",
            reply_markup=kb)
        return

    # --- برداشت: آیدی اولتراولت ---
    if step == "withdraw_wallet":
        wallet = text.replace(" ", "")
        if not wallet.isdigit():
            bot.send_message(chat_id, "❌ آیدی اولتراولت باید فقط <b>عدد</b> باشد! لطفاً آیدی عددی اولتراولت خود را دوباره بفرستید 🔢")
            return
        amount = int(data["amount"])
        u = get_user(uid)
        if amount > u["balance"]:
            clear_state(uid)
            bot.send_message(chat_id, "⚠️ موجودی شما کافی نیست. لطفاً دوباره از بخش برداشت شروع کنید.", reply_markup=main_menu(uid))
            return
        before = u["balance"]
        inc_user(uid, "balance", -amount)
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO orders(user_id,amount,method,wallet_id,status,created_at) VALUES(?,?,?,?, 'pending', ?)",
            (uid, amount, "Ultra Wallet", wallet, now_str()))
        oid = cur.lastrowid
        conn.commit()
        row = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        conn.close()
        clear_state(uid)
        bot.send_message(chat_id,
            f"🎉 <b>سفارش برداشت شما با موفقیت ثبت شد!</b> 🐶\n➖➖➖➖➖➖➖➖➖➖\n"
            f"🔖 شماره سفارش: <b>#{oid}</b>\n"
            f"💰 مبلغ: <b>{amount} داگز</b>\n"
            f"💎 روش برداشت: اولتراولت\n"
            f"🔢 آیدی اولتراولت شما: <code>{esc(wallet)}</code>\n"
            f"📌 وضعیت: ⏳ در حال بررسی توسط مدیریت\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"⏳ سفارشت برای مدیریت ارسال شد. بعد از انجام واریز، همینجا داخل ربات بهت اطلاع میدیم ✅\n"
            f"از همراهیت ممنونیم 🙏🐾", reply_markup=main_menu(uid))
        try:
            send_order_to_admin(dict(row), before)
        except Exception:
            pass
        return

    # --- پاسخ ادمین به پشتیبانی ---
    if step == "admin_reply_support":
        target = int(data["target"])
        clear_state(uid)
        try:
            bot.send_message(target, f"💬 <b>پاسخ پشتیبانی:</b>\n\n{esc(text)}")
            bot.send_message(chat_id, "✅ پاسخ برای کاربر ارسال شد.", reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(chat_id, f"❌ ارسال نشد: <code>{esc(e)}</code>", reply_markup=admin_menu())
        return

    # ============ فقط ادمین ============
    if not is_admin(uid):
        clear_state(uid)
        return

    if step == "add_channel_id":
        chat_raw = normalize_chat_id(text)
        title = chat_raw
        try:
            chinfo = bot.get_chat(chat_raw)
            title = chinfo.title or chat_raw
        except Exception:
            pass
        data.update({"chat_id": chat_raw, "title": title})
        set_state(uid, "add_channel_url", data)
        bot.send_message(chat_id,
            f"✅ کانال/گروه: <b>{esc(title)}</b> (<code>{esc(chat_raw)}</code>)\n\n"
            f"🔗 حالا <b>لینک عضویت</b> را بفرستید (مثلاً <code>https://t.me/YourChannel</code> یا لینک دعوت خصوصی).\n"
            f"اگر کانال عمومی است و می‌خواهید لینک خودکار ساخته شود، بنویسید: <code>خودکار</code>\n\n"
            f"⚠️ یادتان نرود ربات باید در آن کانال/گروه <b>ادمین</b> باشد تا عضویت بررسی شود!")
        return

    if step == "add_channel_url":
        url = text
        if url in ("خودکار", "auto"):
            url = "https://t.me/" + str(data["chat_id"]).replace("@", "")
        conn = get_conn()
        conn.execute("INSERT INTO channels(chat_id,title,url) VALUES(?,?,?)",
                     (data["chat_id"], data["title"], url))
        conn.commit()
        conn.close()
        clear_state(uid)
        bot.send_message(chat_id, f"✅ کانال <b>{esc(data['title'])}</b> به جوین اجباری اضافه شد 🎉", reply_markup=admin_menu())
        return

    if step == "search_user":
        clear_state(uid)
        u = find_user(text)
        if not u:
            bot.send_message(chat_id, "❌ کاربری با این مشخصات پیدا نشد.", reply_markup=admin_menu())
        else:
            send_user_card(chat_id, u)
        return

    if step == "ban_user":
        clear_state(uid)
        u = find_user(text)
        if not u:
            bot.send_message(chat_id, "❌ کاربر پیدا نشد.", reply_markup=admin_menu())
            return
        if u["user_id"] == ADMIN_ID:
            bot.send_message(chat_id, "⚠️ نمی‌توانید خودتان (ادمین) را بن کنید!", reply_markup=admin_menu())
            return
        update_user(u["user_id"], is_banned=1)
        try:
            bot.send_message(u["user_id"], BANNED_TEXT)
        except Exception:
            pass
        bot.send_message(chat_id, f"🚫 کاربر <code>{u['user_id']}</code> مسدود شد.", reply_markup=admin_menu())
        return

    if step == "unban_user":
        clear_state(uid)
        u = find_user(text)
        if not u:
            bot.send_message(chat_id, "❌ کاربر پیدا نشد.", reply_markup=admin_menu())
            return
        update_user(u["user_id"], is_banned=0)
        try:
            bot.send_message(u["user_id"], "♻️ <b>حساب شما از مسدودی خارج شد!</b> خوش برگشتی 🎉", reply_markup=main_menu(u["user_id"]))
        except Exception:
            pass
        bot.send_message(chat_id, f"♻️ کاربر <code>{u['user_id']}</code> آنبن شد.", reply_markup=admin_menu())
        return

    if step == "broadcast_text":
        clear_state(uid)
        ids = all_user_ids()
        bot.send_message(chat_id, f"📢 در حال ارسال پیام همگانی به {len(ids)} کاربر...")
        ok = fail = 0
        for x in ids:
            try:
                bot.send_message(x, text)
                ok += 1
            except Exception:
                fail += 1
            time.sleep(0.05)
        bot.send_message(chat_id, f"✅ <b>پیام همگانی تمام شد</b>\n📬 موفق: {ok}\n❌ ناموفق: {fail}", reply_markup=admin_menu())
        return

    if step == "set_reward":
        clear_state(uid)
        try:
            v = int(text)
            assert v >= 0
        except Exception:
            bot.send_message(chat_id, "❌ عدد معتبر وارد کنید.", reply_markup=admin_menu())
            return
        set_setting("referral_reward", v)
        bot.send_message(chat_id, f"✅ پاداش هر زیرمجموعه از این به بعد: <b>{v} داگز 🎁</b>", reply_markup=admin_menu())
        return

    if step == "set_min_withdraw":
        clear_state(uid)
        try:
            v = int(text)
            assert v > 0
        except Exception:
            bot.send_message(chat_id, "❌ عدد معتبر وارد کنید.", reply_markup=admin_menu())
            return
        set_setting("min_withdraw", v)
        bot.send_message(chat_id, f"✅ حداقل مبلغ برداشت جدید: <b>{v} داگز 💰</b>", reply_markup=admin_menu())
        return

    if step in ("add_balance_user", "sub_balance_user", "pm_user"):
        u = find_user(text)
        if not u:
            bot.send_message(chat_id, "❌ کاربر پیدا نشد، دوباره بفرستید یا /cancel بزنید.")
            return
        nxt = {"add_balance_user": "add_balance_amount", "sub_balance_user": "sub_balance_amount", "pm_user": "pm_text"}[step]
        set_state(uid, nxt, {"target": u["user_id"]})
        msg = "✍️ حالا متن پیام را بفرستید:" if step == "pm_user" else f"👤 کاربر: <code>{u['user_id']}</code> | موجودی فعلی: <b>{u['balance']} داگز</b>\n\n💰 مبلغ (به داگز) را بفرستید:"
        bot.send_message(chat_id, msg)
        return

    if step in ("add_balance_amount", "sub_balance_amount"):
        target = int(data["target"])
        try:
            amt = int(text)
            assert amt > 0
        except Exception:
            bot.send_message(chat_id, "❌ مبلغ باید عدد مثبت باشد، دوباره بفرستید یا /cancel بزنید.")
            return
        clear_state(uid)
        if step == "add_balance_amount":
            inc_user(target, "balance", amt)
            try:
                bot.send_message(target, f"🎁 <b>هدیه مدیریت!</b>\n\n💰 <b>+{amt} داگز 🐶</b> به موجودی شما اضافه شد.\nموجودی جدید: <b>{get_user(target)['balance']} داگز</b>")
            except Exception:
                pass
            bot.send_message(chat_id, f"✅ {amt} داگز به کاربر <code>{target}</code> اضافه شد.", reply_markup=admin_menu())
        else:
            tu = get_user(target)
            amt = min(amt, tu["balance"])
            inc_user(target, "balance", -amt)
            try:
                bot.send_message(target, f"ℹ️ توسط مدیریت <b>{amt} داگز</b> از موجودی شما کسر شد.\nموجودی جدید: <b>{get_user(target)['balance']} داگز</b>")
            except Exception:
                pass
            bot.send_message(chat_id, f"✅ {amt} داگز از کاربر <code>{target}</code> کسر شد.", reply_markup=admin_menu())
        return

    if step == "pm_text":
        target = int(data["target"])
        clear_state(uid)
        try:
            bot.send_message(target, f"✉️ <b>پیام مدیریت ربات:</b>\n\n{esc(text)}")
            bot.send_message(chat_id, "✅ پیام ارسال شد.", reply_markup=admin_menu())
        except Exception as e:
            bot.send_message(chat_id, f"❌ ارسال نشد: <code>{esc(e)}</code>", reply_markup=admin_menu())
        return

    if step == "set_support":
        clear_state(uid)
        new_sup = "" if text == "-" else text
        set_setting("support_username", new_sup)
        bot.send_message(chat_id, f"✅ یوزرنیم پشتیبانی ذخیره شد: {esc(new_sup or '—')}", reply_markup=admin_menu())
        return

# ============================ هندلر اصلی پیام‌ها ============================
ADMIN_BUTTONS = {
    "📊 آمار کامل ربات","💸 آمار برداشت‌ها","➕ افزودن کانال جوین","➖ حذف کانال جوین",
    "📋 لیست کانال‌های جوین","🔍 جستجوی کاربر","🚫 بن کاربر","♻️ آنبن کاربر","📢 پیام همگانی",
    "📨 فوروارد همگانی","🎁 تغییر پاداش زیرمجموعه","💰 تغییر حداقل برداشت","🔌 خاموش / روشن ربات",
    "💳 فعال/غیرفعال برداشت","🧩 فعال/غیرفعال کپچا","🔒 فعال/غیرفعال جوین اجباری",
    "💵 افزایش موجودی کاربر","🧾 کسر موجودی کاربر","✉️ پیام به یک کاربر","⏳ سفارش‌های در انتظار",
    "🏆 برترین دعوت‌کنندگان","⛔️ لیست کاربران مسدود","📥 بکاپ‌گیری کامل","📤 بازگردانی بکاپ",
    "📑 خروجی CSV کاربران","🆘 تنظیم پشتیبانی","🛠 پنل ادمین",
}

@bot.message_handler(func=lambda m: True,
                     content_types=["text","photo","video","document","audio","voice","sticker","animation"])
def main_handler(message):
    uid = message.from_user.id
    chat_id = message.chat.id
    text = (message.text or "").strip()

    u = get_user(uid)
    if not u:
        create_user(uid, message.from_user.username, message.from_user.first_name)
        u = get_user(uid)

    if u["is_banned"] and not is_admin(uid):
        bot.send_message(chat_id, BANNED_TEXT)
        return
    if get_int_setting("bot_on", 1) == 0 and not is_admin(uid):
        bot.send_message(chat_id, BOT_OFF_TEXT)
        return

    # 🔒 بررسی دائمی و همگانی جوین اجباری قبل از هر بخش و حتی قبل از ادامه
    # عملیات‌های نیمه‌تمام (مثل واردکردن مبلغ یا آیدی برداشت و پشتیبانی).
    # اگر کاربر از هر کانال خارج شده باشد، همین‌جا متوقف و صفحه عضویت نمایش داده می‌شود.
    if not is_admin(uid) and not access_gate(chat_id, uid):
        return

    # State در جریان — فقط بعد از تأیید عضویت کامل پردازش می‌شود
    if uid in user_states:
        handle_state(message, user_states[uid])
        return

    if not text:
        return

    # ---------- منوی کاربران ----------
    if text == "👤 حساب کاربری":
        bot.send_message(chat_id, account_text(get_user(uid)), reply_markup=main_menu(uid))
        return

    if text == "🎁 دعوت دوستان":
        reward = get_int_setting("referral_reward", 100)
        minwd = get_int_setting("min_withdraw", 800)
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{uid}"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📤 اشتراک‌گذاری لینک دعوت",
            url=f"https://t.me/share/url?url={link}&text=🐶 داگز رایگان بگیر! به ازای دعوت هر دوست {reward} داگز هدیه بگیر و برداشت کن 💰"))
        bot.send_message(chat_id,
            f"🎁 <b>زیرمجموعه‌گیری و دعوت دوستان</b> 🐶\n➖➖➖➖➖➖➖➖➖➖\n"
            f"به ازای دعوت هر دوست، <b>{reward} داگز</b> هدیه می‌گیری! 🎉\n\n"
            f"⚠️ زیرمجموعه وقتی حساب میشه که دوستت:\n"
            f"1️⃣ با لینک تو وارد ربات بشه\n"
            f"2️⃣ عضو همه کانال‌های اجباری بشه\n"
            f"3️⃣ کپچای ریاضی رو درست حل کنه\n\n"
            f"💸 با <b>{(minwd + reward - 1)//reward if reward else 0} زیرمجموعه</b> به حداقل برداشت ({minwd} داگز) می‌رسی!\n\n"
            f"👥 زیرمجموعه‌های الان تو: <b>{get_user(uid)['referrals']} نفر</b>\n\n"
            f"🔗 <b>لینک دعوت اختصاصی تو:</b>\n<code>{link}</code>\n\n"
            f"📤 لینکت رو تو گروه‌ها و برای دوستات بفرست و بار داگز ببند! 🚀🐾",
            reply_markup=kb)
        return

    if text == "💸 برداشت داگز":
        if get_int_setting("withdraw_on", 1) == 0:
            bot.send_message(chat_id, "⏳ <b>بخش برداشت فعلاً توسط مدیریت غیرفعال شده است.</b>\nبه‌زودی دوباره فعال می‌شود، ممنون از صبرت 🙏")
            return
        u2 = get_user(uid)
        minwd = get_int_setting("min_withdraw", 800)
        reward = get_int_setting("referral_reward", 100)
        if u2["balance"] < minwd:
            need = minwd - u2["balance"]
            refs = (need + reward - 1) // reward if reward else 0
            bot.send_message(chat_id,
                f"⚠️ <b>موجودی شما برای برداشت کافی نیست!</b>\n\n"
                f"💰 موجودی فعلی: <b>{u2['balance']} داگز 🐶</b>\n"
                f"🎯 حداقل مبلغ برداشت: <b>{minwd} داگز</b>\n"
                f"📉 مبلغ مورد نیاز: <b>{need} داگز</b> (حدود <b>{refs} زیرمجموعه</b> جدید)\n\n"
                f"🎁 باید زیرمجموعه‌گیری کنید! از بخش «🎁 دعوت دوستان» لینکت رو پخش کن و به ازای هر نفر {reward} داگز بگیر 🚀")
            return
        set_state(uid, "withdraw_amount")
        bot.send_message(chat_id,
            f"💸 <b>برداشت داگز</b> 🐶\n➖➖➖➖➖➖➖➖➖➖\n"
            f"💰 موجودی شما: <b>{u2['balance']} داگز</b>\n"
            f"🎯 حداقل برداشت: <b>{minwd} داگز</b>\n\n"
            f"✍️ مبلغی که می‌خوای برداشت کنی رو به <b>عدد</b> بفرست (مثال: <code>800</code>):\n\n"
            f"برای لغو: /cancel")
        return

    if text == "📜 سفارش‌های من":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (uid,)).fetchall()
        conn.close()
        if not rows:
            bot.send_message(chat_id, "📭 هنوز هیچ سفارش برداشتی ثبت نکردی.\nاز بخش «💸 برداشت داگز» می‌تونی اولین برداشتت رو ثبت کنی 🐶")
            return
        out = "📜 <b>آخرین سفارش‌های برداشت شما:</b>\n➖➖➖➖➖➖➖➖➖➖\n"
        for r in rows:
            out += (f"\n🔖 سفارش <b>#{r['id']}</b>\n💰 مبلغ: {r['amount']} داگز | 💎 اولتراولت: <code>{esc(r['wallet_id'])}</code>\n"
                    f"📌 وضعیت: {order_status_fa(r['status'])}\n🕐 {esc(r['created_at'])}\n")
        bot.send_message(chat_id, out)
        return

    if text == "📖 راهنما و قوانین":
        bot.send_message(chat_id, GUIDE.format(
            reward=get_int_setting("referral_reward", 100),
            minwd=get_int_setting("min_withdraw", 800)))
        return

    if text == "🆘 پشتیبانی":
        sup = get_setting("support_username", "")
        set_state(uid, "support_msg")
        extra = f"\n📎 پشتیبانی تلگرام: {esc(sup)}" if sup else ""
        bot.send_message(chat_id,
            f"🆘 <b>پشتیبانی ربات</b>{extra}\n\n✍️ پیامت رو همینجا بنویس و بفرست؛ مستقیم برای مدیریت ارسال میشه و جوابش رو داخل همین ربات می‌گیری.\n\nبرای لغو: /cancel")
        return

    # ---------- پنل ادمین ----------
    if text in ADMIN_BUTTONS or text == "🔙 بازگشت به منوی اصلی":
        if not is_admin(uid):
            return
        handle_admin_button(message, text)
        return

    bot.send_message(chat_id, "🤔 متوجه نشدم! از دکمه‌های منوی پایین استفاده کن 👇", reply_markup=main_menu(uid))

def handle_admin_button(message, text):
    uid = message.from_user.id
    chat_id = message.chat.id

    if text == "🛠 پنل ادمین":
        bot.send_message(chat_id, admin_panel_text(), reply_markup=admin_menu())
    elif text == "🔙 بازگشت به منوی اصلی":
        bot.send_message(chat_id, "🏠 برگشتید به منوی اصلی.", reply_markup=main_menu(uid))
    elif text == "📊 آمار کامل ربات":
        bot.send_message(chat_id, full_stats_text())
    elif text == "💸 آمار برداشت‌ها":
        bot.send_message(chat_id, withdraw_stats_text())
    elif text == "➕ افزودن کانال جوین":
        set_state(uid, "add_channel_id")
        bot.send_message(chat_id, "➕ <b>افزودن کانال/گروه جوین اجباری</b>\n\nآیدی کانال/گروه را بفرستید:\n• کانال عمومی: <code>@ChannelUsername</code>\n• کانال/گروه خصوصی: <code>-1001234567890</code>\n\n⚠️ ربات حتماً باید در آن چت <b>ادمین</b> شده باشد.\nبرای لغو: /cancel")
    elif text == "➖ حذف کانال جوین":
        chans = get_channels()
        if not chans:
            bot.send_message(chat_id, "📭 هیچ کانال جوین اجباری ثبت نشده است.")
            return
        kb = types.InlineKeyboardMarkup()
        for chch in chans:
            kb.add(types.InlineKeyboardButton(f"🗑 {chch['title']} ({chch['chat_id']})", callback_data=f"delch:{chch['id']}"))
        bot.send_message(chat_id, "➖ کانالی که می‌خواهید حذف شود را انتخاب کنید:", reply_markup=kb)
    elif text == "📋 لیست کانال‌های جوین":
        chans = get_channels()
        if not chans:
            bot.send_message(chat_id, "📭 هیچ کانال جوین اجباری ثبت نشده است.")
            return
        out = "📋 <b>کانال‌ها و گروه‌های جوین اجباری:</b>\n"
        for i, cn in enumerate(chans, 1):
            out += f"\n{i}️⃣ <b>{esc(cn['title'])}</b>\n🆔 <code>{esc(cn['chat_id'])}</code>\n🔗 {esc(cn['url'])}\n"
        bot.send_message(chat_id, out)
    elif text == "🔍 جستجوی کاربر":
        set_state(uid, "search_user")
        bot.send_message(chat_id, "🔍 آیدی عددی یا یوزرنیم (با @) کاربر را بفرستید:\nبرای لغو: /cancel")
    elif text == "🚫 بن کاربر":
        set_state(uid, "ban_user")
        bot.send_message(chat_id, "🚫 آیدی عددی یا یوزرنیم کاربری که می‌خواهید مسدود شود را بفرستید:\nبرای لغو: /cancel")
    elif text == "♻️ آنبن کاربر":
        set_state(uid, "unban_user")
        bot.send_message(chat_id, "♻️ آیدی عددی یا یوزرنیم کاربر برای رفع مسدودی را بفرستید:\nبرای لغو: /cancel")
    elif text == "📢 پیام همگانی":
        set_state(uid, "broadcast_text")
        bot.send_message(chat_id, "📢 متن پیام همگانی را بفرستید (برای همه کاربران ارسال می‌شود):\nبرای لغو: /cancel")
    elif text == "📨 فوروارد همگانی":
        set_state(uid, "broadcast_fwd")
        bot.send_message(chat_id, "📨 هر پیامی (متن، عکس، فیلم، فایل و...) بفرستید یا فوروارد کنید؛ همان پیام برای همه کاربران ارسال می‌شود:\nبرای لغو: /cancel")
    elif text == "🎁 تغییر پاداش زیرمجموعه":
        set_state(uid, "set_reward")
        bot.send_message(chat_id, f"🎁 پاداش فعلی هر زیرمجموعه: <b>{get_int_setting('referral_reward',100)} داگز</b>\n\nمبلغ جدید (به داگز، فقط عدد) را بفرستید:\nبرای لغو: /cancel")
    elif text == "💰 تغییر حداقل برداشت":
        set_state(uid, "set_min_withdraw")
        bot.send_message(chat_id, f"💰 حداقل برداشت فعلی: <b>{get_int_setting('min_withdraw',800)} داگز</b>\n\nمبلغ جدید را بفرستید:\nبرای لغو: /cancel")
    elif text == "🔌 خاموش / روشن ربات":
        cur = get_int_setting("bot_on", 1)
        set_setting("bot_on", 0 if cur == 1 else 1)
        bot.send_message(chat_id, "🔴 ربات <b>خاموش</b> شد! کاربران پیام «ربات فعلاً از طرف مدیریت خاموش شده است» می‌بینند." if cur == 1 else "🟢 ربات <b>روشن</b> شد و برای همه کاربران در دسترس است 🎉")
    elif text == "💳 فعال/غیرفعال برداشت":
        cur = get_int_setting("withdraw_on", 1)
        set_setting("withdraw_on", 0 if cur == 1 else 1)
        bot.send_message(chat_id, "🔴 بخش برداشت <b>غیرفعال</b> شد." if cur == 1 else "🟢 بخش برداشت <b>فعال</b> شد.")
    elif text == "🧩 فعال/غیرفعال کپچا":
        cur = get_int_setting("captcha_on", 1)
        set_setting("captcha_on", 0 if cur == 1 else 1)
        bot.send_message(chat_id, "🔴 کپچای ریاضی <b>غیرفعال</b> شد." if cur == 1 else "🟢 کپچای ریاضی <b>فعال</b> شد.")
    elif text == "🔒 فعال/غیرفعال جوین اجباری":
        cur = get_int_setting("force_join_on", 1)
        set_setting("force_join_on", 0 if cur == 1 else 1)
        bot.send_message(chat_id, "🔴 جوین اجباری <b>غیرفعال</b> شد." if cur == 1 else "🟢 جوین اجباری <b>فعال</b> شد.")
    elif text == "💵 افزایش موجودی کاربر":
        set_state(uid, "add_balance_user")
        bot.send_message(chat_id, "💵 آیدی عددی یا یوزرنیم کاربر را بفرستید:\nبرای لغو: /cancel")
    elif text == "🧾 کسر موجودی کاربر":
        set_state(uid, "sub_balance_user")
        bot.send_message(chat_id, "🧾 آیدی عددی یا یوزرنیم کاربر را بفرستید:\nبرای لغو: /cancel")
    elif text == "✉️ پیام به یک کاربر":
        set_state(uid, "pm_user")
        bot.send_message(chat_id, "✉️ آیدی عددی یا یوزرنیم کاربر گیرنده را بفرستید:\nبرای لغو: /cancel")
    elif text == "⏳ سفارش‌های در انتظار":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM orders WHERE status='pending' ORDER BY id LIMIT 20").fetchall()
        conn.close()
        if not rows:
            bot.send_message(chat_id, "📭 هیچ سفارش در انتظاری وجود ندارد ✅")
            return
        bot.send_message(chat_id, f"⏳ <b>{len(rows)} سفارش در انتظار بررسی:</b>")
        for r in rows:
            u2 = get_user(r["user_id"]) or {}
            bot.send_message(chat_id,
                f"🧾 سفارش <b>#{r['id']}</b>\n👤 {esc(u2.get('first_name',''))} (@{esc(u2.get('username') or '—')})\n"
                f"🆔 تلگرام: <code>{r['user_id']}</code>\n💰 مبلغ: <b>{r['amount']} داگز</b>\n"
                f"💎 اولتراولت: <code>{esc(r['wallet_id'])}</code>\n🕐 {esc(r['created_at'])}",
                reply_markup=admin_order_kb(r["id"]))
    elif text == "🏆 برترین دعوت‌کنندگان":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM users ORDER BY referrals DESC LIMIT 10").fetchall()
        conn.close()
        out = "🏆 <b>برترین دعوت‌کنندگان ربات:</b>\n➖➖➖➖➖➖➖➖➖➖\n"
        medals = ["🥇","🥈","🥉"]
        for i, r in enumerate(rows):
            m = medals[i] if i < 3 else f"{i+1}️⃣"
            out += f"\n{m} {esc(r['first_name'])} (@{esc(r['username'] or '—')})\n👥 {r['referrals']} زیرمجموعه | 🎁 {r['total_earned']} داگز درآمد"
        bot.send_message(chat_id, out)
    elif text == "⛔️ لیست کاربران مسدود":
        conn = get_conn()
        rows = conn.execute("SELECT * FROM users WHERE is_banned=1 LIMIT 50").fetchall()
        conn.close()
        if not rows:
            bot.send_message(chat_id, "📭 هیچ کاربر مسدودی وجود ندارد.")
            return
        out = "⛔️ <b>کاربران مسدود:</b>\n"
        for r in rows:
            out += f"\n🚫 {esc(r['first_name'])} | <code>{r['user_id']}</code> | @{esc(r['username'] or '—')}"
        bot.send_message(chat_id, out)
    elif text == "📥 بکاپ‌گیری کامل":
        bot.send_message(chat_id, "📥 در حال آماده‌سازی بکاپ کامل ربات...")
        p = make_backup_json()
        with open(p, "rb") as f:
            bot.send_document(chat_id, f, caption="💾 بکاپ JSON — شامل همه کاربران، موجودی‌ها، کانال‌ها، سفارش‌ها و تنظیمات")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                bot.send_document(chat_id, f, caption="💾 بکاپ دیتابیس (data.db)\n\n⚠️ این فایل‌ها را جای امن نگه دارید؛ با دکمه «📤 بازگردانی بکاپ» هر فایل را می‌توانید برگردانید.")
        try:
            os.remove(p)
        except Exception:
            pass
    elif text == "📤 بازگردانی بکاپ":
        set_state(uid, "restore_backup")
        bot.send_message(chat_id, "📤 فایل بکاپ (<code>backup.json</code> یا <code>data.db</code>) که قبلاً از ربات گرفته‌اید را ارسال کنید.\n\n⚠️ توجه: اطلاعات فعلی با بکاپ جایگزین می‌شود!\nبرای لغو: /cancel")
    elif text == "📑 خروجی CSV کاربران":
        path = "users_export.csv"
        conn = get_conn()
        rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
        conn.close()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["user_id","username","first_name","balance","referrals","total_earned","total_withdrawn","referrer_id","is_activated","is_banned","joined_at"])
            for r in rows:
                w.writerow([r["user_id"], r["username"], r["first_name"], r["balance"], r["referrals"], r["total_earned"], r["total_withdrawn"], r["referrer_id"] or "", r["is_activated"], r["is_banned"], r["joined_at"]])
        with open(path, "rb") as f:
            bot.send_document(chat_id, f, caption=f"📑 خروجی کامل کاربران ({len(rows)} نفر) — قابل باز شدن در اکسل")
        try:
            os.remove(path)
        except Exception:
            pass
    elif text == "🆘 تنظیم پشتیبانی":
        set_state(uid, "set_support")
        cur = get_setting("support_username", "") or "—"
        bot.send_message(chat_id, f"🆘 یوزرنیم پشتیبانی فعلی: {esc(cur)}\n\nیوزرنیم جدید را بفرستید (مثل <code>@YourSupport</code>)؛ برای حذف، بنویسید <code>-</code> :\nبرای لغو: /cancel")

# ============================ دکمه‌های شیشه‌ای ============================
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    uid = call.from_user.id
    chat_id = call.message.chat.id
    data = call.data or ""

    if not get_user(uid):
        create_user(uid, call.from_user.username, call.from_user.first_name)
    u_cb = get_user(uid)

    # هیچ دکمه شیشه‌ای برای کاربر مسدود یا هنگام خاموشی ربات پردازش نمی‌شود
    if not is_admin(uid):
        if u_cb and u_cb["is_banned"]:
            bot.answer_callback_query(call.id, "🚫 حساب شما مسدود است.", show_alert=True)
            return
        if get_int_setting("bot_on", 1) == 0:
            bot.answer_callback_query(call.id, "🔌 ربات فعلاً از طرف مدیریت خاموش شده است.", show_alert=True)
            return

    # 🔒 همه دکمه‌های شیشه‌ای (به‌جز خود دکمه بررسی عضویت و کپچا که جداگانه
    # کنترل می‌شوند) ابتدا از دروازه جوین اجباری رد می‌شوند. بنابراین کاربری که
    # کانالی را ترک کرده نمی‌تواند با دکمه‌های قدیمی، مثلاً ادامه برداشت، جلو برود.
    if not is_admin(uid) and data != "check_join" and not data.startswith("cap:"):
        if not access_gate(chat_id, uid):
            bot.answer_callback_query(
                call.id,
                "🔒 ابتدا باید عضو همه کانال‌های اجباری شوید تا بتوانید از ربات استفاده کنید.",
                show_alert=True)
            return

    # --- کپچا ---
    if data.startswith("cap:"):
        try:
            chosen = int(data.split(":")[1])
        except Exception:
            return
        # حتی هنگام پاسخ به کپچا هم عضویت دوباره بررسی می‌شود؛ اگر کاربر بین
        # دریافت کپچا و زدن جواب از کانالی خارج شده باشد، اول باید عضو شود.
        ok_member, not_joined_member = check_membership(uid)
        if not ok_member:
            captcha_answers.pop(uid, None)
            clear_state(uid)
            bot.answer_callback_query(
                call.id,
                "🔒 عضویت شما کامل نیست؛ ابتدا در همه کانال‌های اجباری عضو شوید.",
                show_alert=True)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            send_join_message(chat_id, uid, not_joined_member)
            return
        if captcha_answers.get(uid) == chosen:
            captcha_answers.pop(uid, None)
            update_user(uid, captcha_passed=1)
            bot.answer_callback_query(call.id, "✅ آفرین! جواب درست بود", show_alert=False)
            try:
                bot.edit_message_text("✅ <b>کپچا درست حل شد! آفرین 🎉</b>", chat_id, call.message.message_id)
            except Exception:
                pass
            ok, not_joined = check_membership(uid)
            if not ok:
                send_join_message(chat_id, uid, not_joined)
            else:
                activate_user(uid, chat_id)
        else:
            bot.answer_callback_query(call.id, "❌ جواب اشتباهه! دوباره تلاش کن", show_alert=True)
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except Exception:
                pass
            send_captcha(chat_id, uid)
        return

    # --- بررسی عضویت ---
    if data == "check_join":
        ok, not_joined = check_membership(uid)
        if ok:
            bot.answer_callback_query(call.id, "✅ عضویت شما تأیید شد!", show_alert=False)
            try:
                bot.edit_message_text("✅ <b>عضویت شما در همه کانال‌ها تأیید شد 🎉</b>", chat_id, call.message.message_id)
            except Exception:
                pass
            u = get_user(uid)
            if u and u["is_activated"]:
                # کاربر قدیمی بعد از عضویت مجدد بدون فعال‌سازی یا پاداش تکراری
                # مستقیم به منوی اصلی برمی‌گردد و موجودی/اطلاعاتش دست‌نخورده می‌ماند.
                bot.send_message(chat_id,
                    "✅ <b>عضویت مجدد شما تأیید شد و دسترسی‌تان دوباره باز شد!</b> 🎉\n\n"
                    "💰 موجودی، زیرمجموعه‌ها و سفارش‌های شما مثل قبل حفظ شده‌اند.\n"
                    "⚠️ لطفاً توجه داشته باشید اگر دوباره از هر کانال اجباری خارج شوید، دسترسی به ربات تا عضویت مجدد بسته می‌شود.",
                    reply_markup=main_menu(uid))
            elif get_int_setting("captcha_on", 1) == 1 and u and not u["captcha_passed"]:
                send_captcha(chat_id, uid)
            else:
                activate_user(uid, chat_id)
        else:
            names = "، ".join(ch["title"] for ch in not_joined)
            bot.answer_callback_query(call.id, f"❌ هنوز عضو این‌ها نشدی: {names}", show_alert=True)
        return

    # --- روش برداشت: اولتراولت ---
    if data == "wd_ultra":
        st = user_states.get(uid)
        if not st or st["step"] != "withdraw_method":
            bot.answer_callback_query(call.id, "⏳ این درخواست منقضی شده؛ دوباره از بخش برداشت شروع کن.", show_alert=True)
            return
        set_state(uid, "withdraw_wallet", {"amount": st["data"]["amount"]})
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id,
            "💎 <b>برداشت به اولتراولت (Ultra Wallet)</b>\n\n"
            "🔢 لطفاً <b>آیدی عددی اولتراولت</b> خود را بفرستید:\n"
            "⚠️ دقت کنید فقط عدد باشد و اشتباه وارد نکنید؛ واریز دقیقاً به همین آیدی انجام می‌شود.\n\n"
            "برای لغو: /cancel")
        return

    if data == "wd_cancel":
        clear_state(uid)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.send_message(chat_id, "❌ برداشت لغو شد.", reply_markup=main_menu(uid))
        return

    # --- انجام/رد سفارش (فقط ادمین) ---
    if data.startswith("order_done:") or data.startswith("order_reject:"):
        if not is_admin(uid):
            bot.answer_callback_query(call.id, "⛔️ فقط مدیریت!", show_alert=True)
            return
        action, oid = data.split(":")[0], int(data.split(":")[1])
        conn = get_conn()
        r = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        conn.close()
        if not r:
            bot.answer_callback_query(call.id, "سفارش پیدا نشد", show_alert=True)
            return
        if r["status"] != "pending":
            bot.answer_callback_query(call.id, f"این سفارش قبلاً تعیین تکلیف شده: {order_status_fa(r['status'])}", show_alert=True)
            return
        if action == "order_done":
            conn = get_conn()
            conn.execute("UPDATE orders SET status='done', done_at=? WHERE id=?", (now_str(), oid))
            conn.commit()
            conn.close()
            inc_user(r["user_id"], "total_withdrawn", r["amount"])
            bot.answer_callback_query(call.id, "✅ سفارش انجام‌شده ثبت شد")
            try:
                bot.edit_message_text((call.message.text or "") + "\n\n✅✅ <b>انجام شد — توسط مدیریت پرداخت و به کاربر اطلاع داده شد</b> ✅✅",
                                      chat_id, call.message.message_id)
            except Exception:
                pass
            try:
                bot.send_message(r["user_id"],
                    f"🎉💰 <b>خبر خوش! سفارش برداشت شما با موفقیت انجام شد</b> 💰🎉\n"
                    f"➖➖➖➖➖➖➖➖➖➖\n"
                    f"🔖 شماره سفارش: <b>#{oid}</b>\n"
                    f"🐶 مبلغ واریزشده: <b>{r['amount']} داگز</b>\n"
                    f"💎 روش پرداخت: اولتراولت (Ultra Wallet)\n"
                    f"🔢 آیدی اولتراولت شما: <code>{esc(r['wallet_id'])}</code>\n"
                    f"📌 وضعیت: ✅ <b>انجام شده</b>\n"
                    f"➖➖➖➖➖➖➖➖➖➖\n"
                    f"🥳 مبارکت باشه دوست عزیز! ممنون از اعتمادت به ربات ما 🙏\n"
                    f"🎁 برای کسب داگز بیشتر، به دعوت دوستات ادامه بده و دوباره برداشت بزن 🚀🐾")
            except Exception:
                pass
        else:  # رد کردن + عودت موجودی
            conn = get_conn()
            conn.execute("UPDATE orders SET status='rejected', done_at=? WHERE id=?", (now_str(), oid))
            conn.commit()
            conn.close()
            inc_user(r["user_id"], "balance", r["amount"])
            bot.answer_callback_query(call.id, "❌ سفارش رد و مبلغ عودت داده شد")
            try:
                bot.edit_message_text((call.message.text or "") + "\n\n❌ <b>رد شد — مبلغ به موجودی کاربر برگشت داده شد</b>",
                                      chat_id, call.message.message_id)
            except Exception:
                pass
            try:
                bot.send_message(r["user_id"],
                    f"⚠️ <b>سفارش برداشت شما رد شد</b>\n\n🔖 شماره سفارش: <b>#{oid}</b>\n"
                    f"💰 مبلغ <b>{r['amount']} داگز</b> به موجودی حسابتان برگردانده شد ✅\n"
                    f"برای اطلاع از دلیل، با پشتیبانی در تماس باشید 🙏")
            except Exception:
                pass
        return

    # --- حذف کانال جوین ---
    if data.startswith("delch:"):
        if not is_admin(uid):
            return
        cid = int(data.split(":")[1])
        conn = get_conn()
        conn.execute("DELETE FROM channels WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "🗑 کانال حذف شد")
        try:
            bot.edit_message_text("✅ کانال از لیست جوین اجباری حذف شد.", chat_id, call.message.message_id)
        except Exception:
            pass
        return

    # --- پاسخ به پشتیبانی ---
    if data.startswith("sup_reply:"):
        if not is_admin(uid):
            return
        target = int(data.split(":")[1])
        set_state(uid, "admin_reply_support", {"target": target})
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, f"↩️ پاسخ خود برای کاربر <code>{target}</code> را بنویسید:\nبرای لغو: /cancel")
        return

    # --- عملیات سریع روی کاربر جستجوشده ---
    if data.startswith(("sban:", "sunban:", "sadd:", "ssub:", "spm:")):
        if not is_admin(uid):
            return
        act, target = data.split(":")[0], int(data.split(":")[1])
        if act == "sban":
            if target == ADMIN_ID:
                bot.answer_callback_query(call.id, "⚠️ ادمین را نمی‌شود بن کرد!", show_alert=True)
                return
            update_user(target, is_banned=1)
            bot.answer_callback_query(call.id, "🚫 کاربر بن شد")
            bot.send_message(chat_id, f"🚫 کاربر <code>{target}</code> مسدود شد.")
        elif act == "sunban":
            update_user(target, is_banned=0)
            bot.answer_callback_query(call.id, "♻️ کاربر آنبن شد")
            bot.send_message(chat_id, f"♻️ کاربر <code>{target}</code> از مسدودی خارج شد.")
        elif act == "sadd":
            set_state(uid, "add_balance_amount", {"target": target})
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, f"💵 مبلغ اضافه‌کردنی (داگز) برای کاربر <code>{target}</code> را بفرستید:\nبرای لغو: /cancel")
        elif act == "ssub":
            set_state(uid, "sub_balance_amount", {"target": target})
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, f"🧾 مبلغ کسرکردنی (داگز) از کاربر <code>{target}</code> را بفرستید:\nبرای لغو: /cancel")
        elif act == "spm":
            set_state(uid, "pm_text", {"target": target})
            bot.answer_callback_query(call.id)
            bot.send_message(chat_id, f"✉️ متن پیام برای کاربر <code>{target}</code> را بفرستید:\nبرای لغو: /cancel")
        return

# ============================ وب‌سرور Render ============================
@app.route("/", methods=["GET"])
def index():
    return "🐶 DOGS Bot is running ✅", 200

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    try:
        update = types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        print("Webhook error:", e)
    return "ok", 200

init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    external = os.environ.get("RENDER_EXTERNAL_URL", "")
    webhook_url = os.environ.get("WEBHOOK_URL", external)
    if webhook_url:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=webhook_url.rstrip("/") + "/" + TOKEN)
        print("✅ Webhook set:", webhook_url)
        app.run(host="0.0.0.0", port=port)
    else:
        bot.remove_webhook()
        print("✅ Bot started with Polling (local mode)")
        threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True), daemon=True).start()
        app.run(host="0.0.0.0", port=port)
