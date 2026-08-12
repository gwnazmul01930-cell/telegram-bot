import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get Token from Railway environment variables
TOKEN = os.getenv("BOT_TOKEN")

# আপনার নগদ পার্সোনাল নম্বর
NAGAD_NUM = "01932231862"

# আপনার অ্যাডমিন ইউজারনেম এবং আইডি
ADMIN_USERNAMES = ["nasmul01930"]
ADMIN_IDS = [123456789] # আপনার সঠিক নিউমেরিক আইডি এখানে দিতে পারেন

# ----------------- DATABASE SETUP -----------------
def init_db():
    conn = sqlite3.connect('bot_database.db')
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
    conn = sqlite3.connect('bot_database.db')
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
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, balance, is_active, payment_status, trx_id, l1_inc, l2_inc, l3_inc, l4_inc, referred_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_data["user_id"],
        user_data["name"],
        user_data["balance"],
        1 if user_data["is_active"] else 0,
        user_data["payment_status"],
        user_data["trx_id"],
        user_data["level_income"][1],
        user_data["level_income"][2],
        user_data["level_income"][3],
        user_data["level_income"][4],
        user_data["referred_by"]
    ))
    conn.commit()
    conn.close()

def init_user(user_id, name):
    user = get_user(user_id)
    if not user:
        user = {
            "user_id": user_id,
            "name": name,
            "balance": 0.0,
            "is_active": False,
            "payment_status": "None",
            "trx_id": "",
            "level_income": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            "referred_by": None
        }
        save_user(user)
    return user

def is_admin(user):
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        return True
    return False

# ----------------- BOT HANDLERS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data = init_user(user_id, user.first_name)
    
    # রেফারেল ট্র্যাক করার লজিক
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
            text = (
                f"⏳ **পেমেন্ট পেন্ডিং রয়েছে!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"আপনার দেওয়া TrxID (`{user_data['trx_id']}`) অ্যাডমিনের পর্যালোচনার অপেক্ষায় আছে।\n"
                f"অ্যাডমিন ভেরিফাই করলেই অ্যাকাউন্ট **Active** হয়ে যাবে।"
            )
            keyboard = [[InlineKeyboardButton("🔄 Refresh Status", callback_data="check_status")]]
        else:
            text = (
                f"⚠️ **স্বাগতম, {user.first_name}!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ **আপনার অ্যাকাউন্টটি ইনঅ্যাক্টিভ (Inactive)!**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💡 কাজ শুরু করতে এবং ৪-লেভেল অ্যাফিলিয়েট সিস্টেম চালু করতে **৳১০০০** পেমেন্ট করে অ্যাকাউন্ট একটিভ করুন।"
            )
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

    welcome_text = (
        f"🌟 **স্বাগতম, {user.first_name}!** 🌟\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ **অ্যাকাউন্ট স্ট্যাটাস: Active (সক্রিয়)**\n"
        f"🚀 **অ্যাফিলিয়েট বট সচল রয়েছে!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 **৪-লেভেল কমিশন স্ট্রাকচার:**\n"
        f"  🥇 **Level 1:** ৳৫০০\n"
        f"  🥈 **Level 2:** ৳১০০\n"
        f"  🥉 **Level 3:** ৳৫০\n"
        f"  🏅 **Level 4:** ৳৫০"
    )
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_data = init_user(user_id, user.first_name)
    
    if not user_data["is_active"] and not is_admin(user):
        trx_text = update.message.text.strip()
        user_data["trx_id"] = trx_text
        user_data["payment_status"] = "Pending"
        save_user(user_data)
        
        text = (
            f"✅ **আপনার ট্রানজেকশন আইডি জমা হয়েছে!**\n\n"
            f"📝 **TrxID:** `{trx_text}`\n"
            f"⏳ **স্ট্যাটাস:** Pending"
        )
        keyboard = [[InlineKeyboardButton("🔄 Check Status", callback_data="check_status")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        # অ্যাডমিনকে নোটিফিকেশন পাঠানো
        for admin_id in ADMIN_IDS:
            try:
                admin_msg = (
                    f"🔔 **নতুন পেমেন্ট রিকোয়েস্ট!**\n\n"
                    f"👤 **নাম:** {user.first_name}\n"
                    f"🆔 **ID:** `{user_id}`\n"
                    f"📝 **TrxID:** `{trx_text}`"
                )
                kb_admin = [[InlineKeyboardButton("✅ Active Now", callback_data=f"activate_{user_id}")]]
                await context.bot.send_message(chat_id=admin_id, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb_admin), parse_mode="Markdown")
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
        text = (
            f"💳 **অ্যাকাউন্ট অ্যাক্টিভেশন পেমেন্ট**\n\n"
            f"অ্যাকাউন্ট একটিভ করতে ফি বাবদ **৳১০০০** পাঠান:\n\n"
            f"📱 **Nagad (Personal):** `{NAGAD_NUM}`\n\n"
            f"📌 টাকা পাঠিয়ে আপনার **TrxID** সরাসরি এই চ্যাটে লিখে পাঠান।"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Check Status", callback_data="check_status")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "check_status":
        if user_data["is_active"]:
            status = "Active ✅ (সক্রিয়)"
        elif user_data["payment_status"] == "Pending":
            status = "Pending ⏳ (পর্যালোচনায় আছে)"
        else:
            status = "Inactive ❌"
        text = f"🔄 বর্তমান স্ট্যাটাস: **{status}**"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "ref_link":
        if not user_data["is_active"] and not user_is_admin:
            await query.message.edit_text("❌ আগে অ্যাকাউন্ট একটিভ করুন!")
            return
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = f"🔗 **আপনার রেফারেল লিংক:**\n\n`{ref_link}`"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "balance":
        text = f"📊 **ব্যালেন্স:** ৳{user_data['balance']:.2f}"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "levels":
        inc = user_data["level_income"]
        total = sum(inc.values())
        text = (
            f"💎 **কমিশন ইনকাম রিপোর্ট**\n\n"
            f"🥇 L1: ৳{inc[1]:.2f}\n"
            f"🥈 L2: ৳{inc[2]:.2f}\n"
            f"🥉 L3: ৳{inc[3]:.2f}\n"
            f"🏅 L4: ৳{inc[4]:.2f}\n\n"
            f"💰 **মোট:** ৳{total:.2f}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "withdraw_menu":
        bal = user_data["balance"]
        if bal < 500.0:
            text = f"❌ মিনিমাম উইথড্র ৳৫০০ (আপনার আছে: ৳{bal:.2f})"
        else:
            text = f"💸 উইথড্র করার যোগ্য ব্যালেন্স: ৳{bal:.2f}"
            keyboard = [[InlineKeyboardButton("✅ Confirm Withdraw", callback_data="confirm_withdraw")]]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_home")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "confirm_withdraw":
        if user_data["balance"] >= 500.0:
            amt = user_data["balance"]
            user_data["balance"] = 0.0
            save_user(user_data)
            text = f"✅ ৳{amt:.2f} সফলভাবে উইথড্র রিকোয়েস্ট করা হয়েছে!"
        else:
            text = "❌ পর্যাপ্ত ব্যালেন্স নেই!"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "settings":
        text = "⚙️ সিস্টেম সচল রয়েছে।"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "admin_panel" and user_is_admin:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 0 AND payment_status = 'Pending'")
        pending_count = cursor.fetchone()[0]
        conn.close()

        text = f"👑 **অ্যাডমিন প্যানেল**\n\n👥 মোট ইউজার: {total_users}\n⏳ পেন্ডিং পেমেন্ট: {pending_count}"
        keyboard = [
            [InlineKeyboardButton("📋 View Pending", callback_data="list_pending")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "list_pending" and user_is_admin:
        conn = sqlite3.connect('bot_database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, name, trx_id FROM users WHERE is_active = 0 AND payment_status = 'Pending'")
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            text = "✅ কোনো পেন্ডিং পেমেন্ট নেই!"
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        text = "⏳ **পেন্ডিং পেমেন্ট তালিকা:**\n"
        keyboard = []
        for r in rows:
            uid, name, trx = r[0], r[1], r[2]
            keyboard.append([InlineKeyboardButton(f"✅ {name} | Trx: {trx}", callback_data=f"activate_{uid}")])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("activate_") and user_is_admin:
        target_uid = int(query.data.split("_")[1])
        target_user = get_user(target_uid)
        
        if target_user and not target_user["is_active"]:
            target_user["is_active"] = True
            target_user["payment_status"] = "Active"
            save_user(target_user)

            # ----------------- ৪-লেভেল কমিশন ডিস্ট্রিবিউশন লজিক -----------------
            l1_id = target_user["referred_by"]
            if l1_id:
                l1_user = get_user(l1_id)
                if l1_user:
                    l1_user["balance"] += 500.0
                    l1_user["level_income"][1] += 500.0
                    save_user(l1_user)

                    l2_id = l1_user["referred_by"]
                    if l2_id:
                        l2_user = get_user(l2_id)
                        if l2_user:
                            l2_user["balance"] += 100.0
                            l2_user["level_income"][2] += 100.0
                            save_user(l2_user)

                            l3_id = l2_user["referred_by"]
                            if l3_id:
                                l3_user = get_user(l3_id)
                                if l3_user:
                                    l3_user["balance"] += 50.0
                                    l3_user["level_income"][3] += 50.0
                                    save_user(l3_user)

                                    l4_id = l3_user["referred_by"]
                                    if l4_id:
                                        l4_user = get_user(l4_id)
                                        if l4_user:
                                            l4_user["balance"] += 50.0
                                            l4_user["level_income"][4] += 50.0
                                            save_user(l4_user)
            # -------------------------------------------------------------

            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text="🎉 **অভিনন্দন!** আপনার পেমেন্ট সফলভাবে ভেরিফাই করা হয়েছে এবং আপনার অ্যাকাউন্টটি Active (সক্রিয়) করা হয়েছে!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
            text = f"✅ সফলভাবে **{target_user['name']}** এর অ্যাকাউন্ট একটিভ করা হয়েছে এবং ৪ লেভেল পর্যন্ত কমিশন ডিস্ট্রিবিউট হয়েছে!"
        else:
            text = "⚠️ ইউজার পাওয়া যায়নি বা ইতিমধ্যে একটিভ রয়েছে!"

        keyboard = [
            [InlineKeyboardButton("📋 Pending List", callback_data="list_pending")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]
        try:
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "back_home":
        if not user_data["is_active"] and not user_is_admin:
            text = "❌ আপনার অ্যাকাউন্ট ইনঅ্যাক্টিভ।"
            keyboard = [
                [InlineKeyboardButton("💳 Pay ৳1000 to Activate", callback_data="pay_activate")],
                [InlineKeyboardButton("🔄 Check Status", callback_data="check_status")]
            ]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
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
        await query.message.edit_text("🌟 মূল মেনু:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN is not set.")
        return

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot with SQLite Database is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
