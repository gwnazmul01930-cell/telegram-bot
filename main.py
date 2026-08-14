import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
NAGAD_NUM = "01932231862"
ADMIN_IDS = [123456789] # আপনার আইডি এখানে দিবেন

def init_db():
    conn = sqlite3.connect('bot_database.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            balance REAL DEFAULT 0.0,
            is_active INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'None',
            trx_id TEXT DEFAULT '',
            l1_inc REAL DEFAULT 0.0,
            l2_inc REAL DEFAULT 0.0,
            l3_inc REAL DEFAULT 0.0,
            l4_inc REAL DEFAULT 0.0,
            referred_by INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_user(user_id):
    conn = sqlite3.connect('bot_database.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"user_id": row[0], "name": row[1], "balance": row[2], "is_active": bool(row[3]), "payment_status": row[4], "trx_id": row[5], "level_income": {1: row[6], 2: row[7], 3: row[8], 4: row[9]}, "referred_by": row[10]}
    return None

def save_user(user_data):
    conn = sqlite3.connect('bot_database.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?,?,?,?,?)', (user_data["user_id"], user_data["name"], user_data["balance"], 1 if user_data["is_active"] else 0, user_data["payment_status"], user_data["trx_id"], user_data["level_income"][1], user_data["level_income"][2], user_data["level_income"][3], user_data["level_income"][4], user_data["referred_by"]))
    conn.commit()
    conn.close()

def init_user(user_id, name):
    user = get_user(user_id)
    if not user:
        user = {"user_id": user_id, "name": name, "balance": 0.0, "is_active": False, "payment_status": "None", "trx_id": "", "level_income": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}, "referred_by": None}
        save_user(user)
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = init_user(user.id, user.first_name)
    
    if context.args and user_data["referred_by"] is None:
        try:
            inviter = int(context.args[0])
            if inviter != user.id:
                user_data["referred_by"] = inviter
                save_user(user_data)
        except: pass

    if not user_data["is_active"] and user.id not in ADMIN_IDS:
        if user_data["payment_status"] == "Pending":
            await update.message.reply_text("⏳ পেমেন্ট পেন্ডিং! অ্যাডমিন চেক করলে একটিভ হয়ে যাবে।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="check_status")]]))
        else:
            await update.message.reply_text("⚠️ আপনার অ্যাকাউন্ট ইনঅ্যাক্টিভ।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay ৳1000", callback_data="pay_activate")]]))
    else:
        await show_main_menu(update, context)

async def show_main_menu(update_or_query, context):
    user = update_or_query.effective_user
    keyboard = [
        [InlineKeyboardButton("🔗 রেফারেল লিংক", callback_data="ref_link")],
        [InlineKeyboardButton("📊 ব্যালেন্স", callback_data="balance"), InlineKeyboardButton("💎 কমিশন", callback_data="levels")],
        [InlineKeyboardButton("💸 উইথড্র", callback_data="withdraw_menu")]
    ]
    if update_or_query.callback_query:
        await update_or_query.callback_query.message.edit_text("🌟 মূল মেনু:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.message.reply_text("🌟 মূল মেনু:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_data = init_user(user.id, user.first_name)

    if query.data == "pay_activate":
        await query.message.edit_text(f"💳 পেমেন্ট করুন: `{NAGAD_NUM}`\nপাঠিয়ে TrxID দিন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")
    elif query.data == "back_home":
        if not user_data["is_active"]:
             await query.message.edit_text("⚠️ অ্যাকাউন্ট ইনঅ্যাক্টিভ।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay ৳1000", callback_data="pay_activate")]]))
        else:
             await show_main_menu(query, context)
    elif query.data == "ref_link":
        await query.message.edit_text(f"🔗 লিংক: `https://t.me/{context.bot.username}?start={user.id}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")
    elif query.data == "balance":
        await query.message.edit_text(f"📊 ব্যালেন্স: ৳{user_data['balance']:.2f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]))
    elif query.data == "levels":
        inc = user_data["level_income"]
        await query.message.edit_text(f"💎 কমিশন:\nL1: {inc[1]}\nL2: {inc[2]}\nL3: {inc[3]}\nL4: {inc[4]}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]))
    elif query.data == "withdraw_menu":
        await query.message.edit_text(f"💸 উইথড্র করুন। ব্যালেন্স: {user_data['balance']}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm", callback_data="confirm_withdraw")], [InlineKeyboardButton("🔙 Back", callback_data="back_home")]]))
    elif query.data == "confirm_withdraw":
        user_data["balance"] = 0.0
        save_user(user_data)
        await query.message.edit_text("✅ উইথড্র রিকোয়েস্ট সাকসেস!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]))

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT, lambda u, c: None)) # পেমেন্ট আইডি হ্যান্ডল করতে আগের হ্যান্ডলার ব্যবহার করবেন
app.run_polling()
