import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
NAGAD_NUM = "01932231862"

ADMIN_USERNAMES = ["nasmul01930"]
ADMIN_IDS = [] 

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
        return {
            "user_id": row[0],
            "name": row[1],
            "balance": row[2],
            "is_active": bool(row[3]),
            "payment_status": row[4],
            "trx_id": row[5],
            "level_income": {1: row[6], 2: row[7], 3: row[8], 4: row[9]},
            "referred_by": row[10]
        }
    return None

def save_user(user_data):
    conn = sqlite3.connect('bot_database.db', timeout=30)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, balance, is_active, payment_status, trx_id, l1_inc, l2_inc, l3_inc, l4_inc, referred_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data["user_id"], user_data["name"], user_data["balance"],
        1 if user_data["is_active"] else 0, user_data["payment_status"], user_data["trx_id"],
        user_data["level_income"][1], user_data["level_income"][2], user_data["level_income"][3], user_data["level_income"][4],
        user_data["referred_by"]
    ))
    conn.commit()
    conn.close()

def init_user(user_id, name):
    user = get_user(user_id)
    if not user:
        user = {
            "user_id": user_id, "name": name, "balance": 0.0,
            "is_active": False, "payment_status": "None", "trx_id": "",
            "level_income": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}, "referred_by": None
        }
        save_user(user)
    return user

def is_admin(user):
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data = init_user(user_id, user.first_name)
    
    if context.args and user_data["referred_by"] is None:
        try:
            inviter_id = int(context.args[0])
            if inviter_id != user_id and get_user(inviter_id):
                user_data["referred_by"] = inviter_id
                save_user(user_data)
        except ValueError:
            pass

    user_is_admin = is_admin(user)

    if not user_data["is_active"] and not user_is_admin:
        p_status = user_data["payment_status"]
        if p_status == "Pending":
            text = "⏳ **পেমেন্ট পেন্ডিং রয়েছে!**\n\nআপনার ট্রানজেকশন আইডি অ্যাডমিনের কাছে জমা আছে।"
            keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data="check_status")]]
        else:
            text = f"⚠️ **স্বাগতম, {user.first_name}!**\n\n❌ আপনার অ্যাকাউন্ট ইনঅ্যাক্টিভ। কাজ শুরু করতে **৳১০০০** দিয়ে একটিভ করুন।"
            keyboard = [
                [InlineKeyboardButton("💳 Pay ৳1000 to Activate", callback_data="pay_activate")],
                [InlineKeyboardButton("🔄 Check Status", callback_data="check_status")]
            ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    keyboard = [
        [InlineKeyboardButton("🔗 My Referral Link", callback_data="ref_link")],
        [InlineKeyboardButton("📊 My Balance", callback_data="balance"),
         InlineKeyboardButton("💎 Commission Details", callback_data="levels")],
        [InlineKeyboardButton("💸 Withdraw Money", callback_data="withdraw_menu")],
        [InlineKeyboardButton("⚙️ Settings & Info", callback_data="settings")]
    ]
    if user_is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin Control Panel", callback_data="admin_panel")])

    await update.message.reply_text(f"🌟 **স্বাগতম, {user.first_name}!**\n\n✅ অ্যাকাউন্ট Active রয়েছে।", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data = init_user(user_id, user.first_name)
    
    if not user_data["is_active"] and not is_admin(user):
        trx_text = update.message.text.strip()
        user_data["trx_id"] = trx_text
        user_data["payment_status"] = "Pending"
        save_user(user_data)
        
        await update.message.reply_text(f"✅ ট্রানজেকশন আইডি জমা হয়েছে: `{trx_text}`\n⏳ স্ট্যাটাস: Pending", parse_mode="Markdown")

        for admin_id in ADMIN_IDS:
            try:
                kb_admin = [[InlineKeyboardButton("✅ Active Now", callback_data=f"activate_{user_id}")]]
                await context.bot.send_message(chat_id=admin_id, text=f"🔔 নতুন পেমেন্ট!\nনাম: {user.first_name}\nID: `{user_id}`\nTrxID: `{trx_text}`", reply_markup=InlineKeyboardMarkup(kb_admin), parse_mode="Markdown")
            except Exception:
                pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    user_data = init_user(user_id, user.first_name)
    bot_username = context.bot.username
    user_is_admin = is_admin(user)

    if query.data == "pay_activate":
        text = f"💳 **অ্যাকাউন্ট অ্যাক্টিভেশন**\n\nনগদ পার্সোনাল: `{NAGAD_NUM}`\n\n৳১০০০ পাঠিয়ে TrxID চ্যাটে পাঠান।"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "check_status":
        status = "Active ✅" if user_data["is_active"] else ("Pending ⏳" if user_data["payment_status"] == "Pending" else "Inactive ❌")
        await query.message.edit_text(f"🔄 স্ট্যাটাস: {status}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "ref_link":
        if not user_data["is_active"] and not user_is_admin:
            await query.message.edit_text("❌ আগে অ্যাকাউন্ট একটিভ করুন!")
            return
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.edit_text(f"🔗 **আপনার রেফারেল লিংক:**\n\n`{ref_link}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "balance":
        await query.message.edit_text(f"📊 **ব্যালেন্স:** ৳{user_data['balance']:.2f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "levels":
        inc = user_data["level_income"]
        await query.message.edit_text(f"💎 **৪ লেভেল কমিশন রিপোর্ট**\n\n🥇 L1: ৳{inc[1]:.2f}\n🥈 L2: ৳{inc[2]:.2f}\n🥉 L3: ৳{inc[3]:.2f}\n🏅 L4: ৳{inc[4]:.2f}\n\n💰 মোট: ৳{sum(inc.values()):.2f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "withdraw_menu":
        bal = user_data["balance"]
        if bal < 500.0:
            await query.message.edit_text(f"❌ মিনিমাম উইথড্র ৳৫০০ (আপনার আছে: ৳{bal:.2f})", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")
        else:
            await query.message.edit_text(f"💸 উইথড্র যোগ্য: ৳{bal:.2f}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Confirm Withdraw", callback_data="confirm_withdraw")], [InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "confirm_withdraw":
        if user_data["balance"] >= 500.0:
            user_data["balance"] = 0.0
            save_user(user_data)
            await query.message.edit_text("✅ উইথড্র সফল হয়েছে!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "settings":
        await query.message.edit_text("⚙️ সিস্টেম সচল রয়েছে।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "admin_panel" and user_is_admin:
        conn = sqlite3.connect('bot_database.db', timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 0 AND payment_status = 'Pending'")
        pending = cursor.fetchone()[0]
        conn.close()
        await query.message.edit_text(f"👑 **অ্যাডমিন প্যানেল**\n\n👥 মোট ইউজার: {total}\n⏳ পেন্ডিং: {pending}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 View Pending", callback_data="list_pending")], [InlineKeyboardButton("🔙 Back", callback_data="back_home")]]), parse_mode="Markdown")

    elif query.data == "list_pending" and user_is_admin:
        conn = sqlite3.connect('bot_database.db', timeout=30)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, trx_id FROM users WHERE is_active = 0 AND payment_status = 'Pending'")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            await query.message.edit_text("✅ কোনো পেন্ডিং পেমেন্ট নেই!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")]]), parse_mode="Markdown")
            return
        keyboard = [[InlineKeyboardButton(f"✅ {r[1]} | Trx: {r[2]}", callback_data=f"activate_{r[0]}")] for r in rows]
        keyboard.append([InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")])
        await query.message.edit_text("⏳ পেন্ডিং তালিকা:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("activate_") and user_is_admin:
        target_uid = int(query.data.split("_")[1])
        target_user = get_user(target_uid)
        
        if target_user and not target_user["is_active"]:
            target_user["is_active"] = True
            target_user["payment_status"] = "Active"
            save_user(target_user)

            # --- ৪ লেভেল কমিশন ডিস্ট্রিবিউশন লজিক (স্টেপ বাই স্টেপ) ---
            current_id = target_user["referred_by"]
            levels = {1: 500.0, 2: 100.0, 3: 50.0, 4: 50.0}
            
            for lvl in range(1, 5):
                if current_id:
                    u_obj = get_user(current_id)
                    if u_obj:
                        amt = levels[lvl]
                        u_obj["balance"] += amt
                        u_obj["level_income"][lvl] += amt
                        save_user(u_obj)
                        current_id = u_obj["referred_by"]
                    else:
                        break
                else:
                    break
            # --------------------------------------------------------

            try:
                await context.bot.send_message(chat_id=target_uid, text="🎉 আপনার অ্যাকাউন্ট Active করা হয়েছে!", parse_mode="Markdown")
            except Exception:
                pass
            
            await query.message.edit_text(f"✅ সফলভাবে একটিভ হয়েছে এবং ৪ লেভেল পর্যন্ত কমিশন ডিস্ট্রিবিউট হয়েছে!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")]]), parse_mode="Markdown")

    elif query.data == "back_home":
        if not user_data["is_active"] and not user_is_admin:
            await query.message.edit_text("❌ ইনঅ্যাক্টিভ অ্যাকাউন্ট।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💳 Pay ৳1000", callback_data="pay_activate")]]), parse_mode="Markdown")
            return
        await query.message.edit_text("🌟 মূল মেনু:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    if not TOKEN:
        return
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
