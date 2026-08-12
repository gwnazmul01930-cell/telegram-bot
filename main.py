import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get Token from Railway environment variables
TOKEN = os.getenv("BOT_TOKEN")

# আপনার নগদ পার্সোনাল নম্বর
NAGAD_NUM = "01932231862"

# Database to store user info
users_db = {}

# আপনার অ্যাডমিন টেলিগ্রাম আইডি অথবা ইউজারনেম 
# (এখানে আপনার ইউজারনেম 'nasmul01930' যুক্ত করা হয়েছে যাতে কোনো এরর না আসে)
ADMIN_IDS = [123456789]
ADMIN_USERNAMES = ["nasmul01930"]

def is_admin(user):
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        return True
    return False

def init_user(user_id, name):
    if user_id not in users_db:
        users_db[user_id] = {
            "name": name,
            "balance": 0.0,
            "is_active": False,
            "level_income": {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0},
            "referred_by": None,
            "referrals": []
        }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    init_user(user_id, user.first_name)
    
    if context.args:
        try:
            inviter_id = int(context.args[0])
            if inviter_id in users_db and users_db[user_id]["referred_by"] is None and inviter_id != user_id:
                users_db[user_id]["referred_by"] = inviter_id
                
                inviter = users_db[inviter_id]
                if inviter["is_active"]:
                    if user_id not in inviter["referrals"]:
                        inviter["referrals"].append(user_id)
                        inviter["balance"] += 500.0
                        inviter["level_income"][1] += 500.0
                    
                    l2_id = inviter["referred_by"]
                    if l2_id and l2_id in users_db and users_db[l2_id]["is_active"]:
                        users_db[l2_id]["balance"] += 100.0
                        users_db[l2_id]["level_income"][2] += 100.0
                        
                        l3_id = users_db[l2_id]["referred_by"]
                        if l3_id and l3_id in users_db and users_db[l3_id]["is_active"]:
                            users_db[l3_id]["balance"] += 50.0
                            users_db[l3_id]["level_income"][3] += 50.0
                            
                            l4_id = users_db[l3_id]["referred_by"]
                            if l4_id and l4_id in users_db and users_db[l4_id]["is_active"]:
                                users_db[l4_id]["balance"] += 50.0
                                users_db[l4_id]["level_income"][4] += 50.0
        except ValueError:
            pass

    user_data = users_db[user_id]
    user_is_admin = is_admin(user)

    if not user_data["is_active"] and not user_is_admin:
        keyboard = [
            [InlineKeyboardButton("💳 Pay ৳1000 to Activate", callback_data="pay_activate")],
            [InlineKeyboardButton("🔄 Check Activation Status", callback_data="check_status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            f"⚠️ **স্বাগতম, {user.first_name}!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ **আপনার অ্যাকাউন্টটি বর্তমানে ইনঅ্যাক্টিভ (Inactive) রয়েছে!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💡 কাজ শুরু করতে এবং ৪-লেভেল অ্যাফিলিয়েট সিস্টেম চালু করতে আপনার অ্যাকাউন্টটি **৳১০০০** দিয়ে একটিভ করতে হবে।"
        )
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
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

    reply_markup = InlineKeyboardMarkup(keyboard)
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
        f"  🏅 **Level 4:** ৳৫০\n\n"
        f"✨ নিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় সেবাটি বেছে নিন:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    user_id = user.id
    init_user(user_id, user.first_name)
    user_data = users_db[user_id]
    bot_username = context.bot.username
    user_is_admin = is_admin(user)

    if query.data == "pay_activate":
        text = (
            f"💳 **অ্যাকাউন্ট অ্যাক্টিভেশন পেমেন্ট**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"অ্যাকাউন্ট একটিভ করতে ফি বাবদ **৳১০০০** পাঠান নিচের নম্বরে:\n\n"
            f"📱 **Nagad (Personal):** `{NAGAD_NUM}`\n\n"
            f"📌 টাকা পাঠিয়ে আপনার **TrxID** সহ অ্যাডমিনকে মেসেজ দিন।\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("🔄 Check Status", callback_data="check_status")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "check_status":
        status = "Active ✅" if user_data["is_active"] else "Inactive ❌"
        text = f"🔄 আপনার বর্তমান অ্যাকাউন্ট স্ট্যাটাস: **{status}**"
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "ref_link":
        if not user_data["is_active"] and not user_is_admin:
            await query.message.edit_text("❌ আপনার অ্যাকাউন্ট ইনঅ্যাক্টিভ! আগে অ্যাকাউন্ট একটিভ করুন।")
            return
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            f"🔗 **আপনার ইউনিক রেফারেল লিংক:**\n\n"
            f"`{ref_link}`\n\n"
            f"💡 *এই লিংকটি শেয়ার করুন এবং ৪ লেভেল পর্যন্ত কমিশন আয় করুন!*"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "balance":
        balance = user_data["balance"]
        text = (
            f"📊 **অ্যাকাউন্ট ব্যালেন্স**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **বর্তমান ব্যালেন্স:** ৳{balance:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "levels":
        inc = user_data["level_income"]
        total_inc = sum(inc.values())
        text = (
            f"💎 **কমিশন ইনকাম রিপোর্ট**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🥇 **Level 1:** ৳{inc[1]:.2f}\n"
            f"🥈 **Level 2:** ৳{inc[2]:.2f}\n"
            f"🥉 **Level 3:** ৳{inc[3]:.2f}\n"
            f"🏅 **Level 4:** ৳{inc[4]:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **মোট কমিশন আয়:** ৳{total_inc:.2f}"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "withdraw_menu":
        balance = user_data["balance"]
        if balance < 500.0:
            text = (
                f"❌ **উইথড্র করতে পারবেন না!**\n\n"
                f"💰 আপনার বর্তমান ব্যালেন্স: ৳{balance:.2f}\n"
                f"⚠️ **মিনিমাম উইথড্র লিমিট:** ৳৫০০.০০\n\n"
                f"অন্তত ৳৫০০ টাকা না হওয়া পর্যন্ত আপনি উইথড্র করতে পারবেন না।"
            )
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        else:
            text = (
                f"💸 **উইথড্র সেকশন**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 আপনার বর্তমান ব্যালেন্স: ৳{balance:.2f}\n"
                f"✅ আপনি উইথড্র করার যোগ্য!\n\n"
                f"উইথড্র করতে নিচের বাটনে ক্লিক করুন:"
            )
            keyboard = [
                [InlineKeyboardButton("✅ Confirm Withdraw (Request)", callback_data="confirm_withdraw")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]
            ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "confirm_withdraw":
        if user_data["balance"] >= 500.0:
            with_amount = user_data["balance"]
            user_data["balance"] = 0.0
            text = (
                f"✅ **উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে!**\n\n"
                f"উইথড্রকৃত পরিমাণ: ৳{with_amount:.2f}\n"
                f"অ্যাডমিন খুব শীঘ্রই আপনার পেমেন্টটি চেক করে আপনার নগদ নম্বরে পাঠিয়ে দেবেন।"
            )
        else:
            text = "❌ আপনার পর্যাপ্ত ব্যালেন্স নেই!"
            
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "settings":
        text = (
            f"⚙️ **বট সেটিংস ও তথ্য**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛠️ সিস্টেম: Active (Affiliate Bot)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "admin_panel" and user_is_admin:
        inactive_users = [uid for uid, data in users_db.items() if not data["is_active"]]
        text = (
            f"👑 **অ্যাডমিন কন্ট্রোল প্যানেল**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👥 মোট ইউজার: {len(users_db)} জন\n"
            f"❌ ইনঅ্যাক্টিভ ইউজার: {len(inactive_users)} জন\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [
            [InlineKeyboardButton("📋 View Inactive Users", callback_data="list_inactive")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "list_inactive" and user_is_admin:
        inactive_users = {uid: data for uid, data in users_db.items() if not data["is_active"]}
        if not inactive_users:
            text = "✅ বর্তমানে কোনো ইনঅ্যাক্টিভ ইউজার নেই!"
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        text = "❌ **ইনঅ্যাক্টিভ ইউজারদের তালিকা:**\nপেমেন্ট ভেরিফাই করে একটিভ করুন:\n\n"
        keyboard = []
        for uid, data in inactive_users.items():
            name = data.get("name", "User")
            keyboard.append([InlineKeyboardButton(f"✅ Active: {name} ({uid})", callback_data=f"activate_{uid}")])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data.startswith("activate_") and user_is_admin:
        target_uid = int(query.data.split("_")[1])
        if target_uid in users_db:
            users_db[target_uid]["is_active"] = True
            target_name = users_db[target_uid].get("name", "User")
            text = f"✅ সফলভাবে **{target_name}** (`{target_uid}`)-এর অ্যাকাউন্ট অ্যাক্টিভ করা হয়েছে!"
        else:
            text = "⚠️ ইউজার পাওয়া যায়নি!"
        keyboard = [
            [InlineKeyboardButton("📋 Inactive List", callback_data="list_inactive")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "back_home":
        if not user_data["is_active"] and not user_is_admin:
            keyboard = [
                [InlineKeyboardButton("💳 Pay ৳1000 to Activate", callback_data="pay_activate")],
                [InlineKeyboardButton("🔄 Check Activation Status", callback_data="check_status")]
            ]
            text = "❌ আপনার অ্যাকাউন্টটি ইনঅ্যাক্টিভ রয়েছে। দয়া করে পেমেন্ট করুন।"
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
            
        welcome_text = "🌟 **মূল মেনুতে স্বাগতম!** 🌟\n\nনিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় সেবাটি বেছে নিন:"
        await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN is not set in environment variables.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is starting polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
