
#!/usr/bin/env python3

import os
import sqlite3
import openai
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("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")
BOT_TOKEN = os.getenv("7546350640:AAFt81hehXlMAbLhERmcupIgJXG0eic_nK4")
TON_API_URL = os.getenv("TON_API_URL", "https://tonapi.io")
RLC_CONTRACT_ADDRESS = os.getenv("RLC_CONTRACT_ADDRESS")

def initialize_database():
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            category TEXT,
            file_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            answered INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def save_question(user_id, question, category=None, file_path=None):
    conn = sqlite3.connect('questions.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions (user_id, question, category, file_path)
        VALUES (?, ?, ?, ?)
    ''', (user_id, question, category, file_path))
    conn.commit()
    conn.close()

async def check_wallet_balance(wallet_address, token="TON"):
    try:
        url = f"{TON_API_URL}/v2/accounts/{wallet_address}/balances"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        balance = data.get(token, 0)
        return f"موجودی {token} شما: {balance}"
    except Exception:
        return "خطا در بازیابی موجودی کیف پول. لطفاً بعداً تلاش کنید."

async def send_transaction(sender_wallet, receiver_wallet, amount, token="TON"):
    return f"تراکنش {amount} {token} از {sender_wallet} به {receiver_wallet} با موفقیت شبیه‌سازی شد."

async def connect_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = " ".join(context.args)
    if not wallet_address:
        await update.message.reply_text("لطفاً آدرس کیف پول خود را بعد از دستور /connect وارد کنید.")
        return
    context.user_data["wallet_address"] = wallet_address
    await update.message.reply_text(f"کیف پول شما با آدرس {wallet_address} متصل شد.")

async def check_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = context.user_data.get("wallet_address")
    if wallet_address:
        await update.message.reply_text(f"کیف پول شما با آدرس {wallet_address} متصل است.")
    else:
        await update.message.reply_text("کیف پول شما متصل نیست. لطفاً ابتدا دستور /connect را اجرا کنید.")

async def buy_rlc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = context.user_data.get("wallet_address")
    if not wallet_address:
        await update.message.reply_text("ابتدا کیف پول خود را متصل کنید.")
        return
    try:
        amount_ton = float(context.args[0]) if context.args else None
        if not amount_ton:
            await update.message.reply_text("فرمت صحیح: /buy_rlc [مقدار TON]")
            return
        rlc_amount = amount_ton * 10
        response = await send_transaction(wallet_address, RLC_CONTRACT_ADDRESS, amount_ton, token="TON")
        await update.message.reply_text(f"{rlc_amount} RLC به کیف پول شما اضافه شد. 
{response}")
    except Exception as e:
        await update.message.reply_text("خطا در خرید RLC. لطفاً مقدار وارد شده را بررسی کنید.")

async def ai_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = " ".join(context.args)
    if not question:
        await update.message.reply_text("لطفاً سوال خود را بعد از دستور /ai بنویسید.")
        return
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": question}]
        )
        ai_answer = response.choices[0].message.content
        await update.message.reply_text(f"پاسخ هوش مصنوعی:
{ai_answer}")
    except Exception:
        await update.message.reply_text("خطا در ارتباط با سرور هوش مصنوعی. لطفاً بعداً تلاش کنید.")

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wallet_address = context.user_data.get("wallet_address")
    if not wallet_address:
        await update.message.reply_text("ابتدا کیف پول خود را متصل کنید.")
        return
    balance_message = await check_wallet_balance(wallet_address)
    await update.message.reply_text(balance_message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به RebLawBot خوش آمدید.
برای شروع، از منوی زیر استفاده کنید یا دستور /help را ارسال کنید.",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
    لیست دستورات:
    /start - شروع
    /help - راهنما
    /connect - اتصال کیف پول
    /check - بررسی اتصال
    /buy_rlc - خرید RLC
    /wallet - موجودی کیف پول
    /ai - سوال حقوقی با هوش مصنوعی
    """)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "خرید RLC":
        await update.message.reply_text("فرمت صحیح: /buy_rlc [مقدار TON]")
    elif text == "بررسی موجودی RLC":
        wallet_address = context.user_data.get("wallet_address")
        if wallet_address:
            balance = await check_wallet_balance(wallet_address, token="RLC")
            await update.message.reply_text(balance)
        else:
            await update.message.reply_text("ابتدا کیف پول خود را متصل کنید.")
    elif text == "پاسخ هوش مصنوعی":
        await update.message.reply_text("لطفاً سوال خود را بعد از دستور /ai بنویسید.")

def get_main_menu():
    keyboard = [
        ["خرید RLC", "بررسی موجودی RLC"],
        ["پاسخ هوش مصنوعی"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def main():
    initialize_database()
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set.")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("connect", connect_wallet))
    application.add_handler(CommandHandler("check", check_connection))
    application.add_handler(CommandHandler("buy_rlc", buy_rlc))
    application.add_handler(CommandHandler("wallet", wallet))
    application.add_handler(CommandHandler("ai", ai_response))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("ربات در حال اجراست...")
    application.run_polling()

if __name__ == "__main__":
    main()
