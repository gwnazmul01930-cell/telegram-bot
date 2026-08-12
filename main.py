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

# Database to store user info
users_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Register user if not already exists
    if user_id not in users_db:
        users_db[user_id] = {
            "name": user.first_name,
            "balance": 0.0,
            "referred_by": None,
            "referrals": []
        }
    
    # Check for 4-level referral tracking via /start <inviter_id>
    if context.args:
        try:
            inviter_id = int(context.args[0])
            if inviter_id in users_db and users_db[user_id]["referred_by"] is None and inviter_id != user_id:
                users_db[user_id]["referred_by"] = inviter_id
                
                # Level 1 -> ৳500
                if user_id not in users_db[inviter_id]["referrals"]:
                    users_db[inviter_id]["referrals"].append(user_id)
                    users_db[inviter_id]["balance"] += 500.0
                
                # Level 2 -> ৳100
                l2_inviter = users_db[inviter_id]["referred_by"]
                if l2_inviter and l2_inviter in users_db:
                    users_db[l2_inviter]["balance"] += 100.0
                    
                    # Level 3 -> ৳50
                    l3_inviter = users_db[l2_inviter]["referred_by"]
                    if l3_inviter and l3_inviter in users_db:
                        users_db[l3_inviter]["balance"] += 50.0
                        
                        # Level 4 -> ৳50
                        l4_inviter = users_db[l3_inviter]["referred_by"]
                        if l4_inviter and l4_inviter in users_db:
                            users_db[l4_inviter]["balance"] += 50.0
        except ValueError:
            pass

    # Stylish Menu buttons
    keyboard = [
        [InlineKeyboardButton("🔗 My Referral Link", callback_data="ref_link")],
        [InlineKeyboardButton("📊 My Balance & Stats", callback_data="balance"),
         InlineKeyboardButton("💎 Commission Levels", callback_data="levels")],
        [InlineKeyboardButton("⚙️ Settings & Info", callback_data="settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        f"🌟 **স্বাগতম, Admin {user.first_name}!** 🌟\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 **আপনার প্রিমিয়াম অ্যাফিলিয়েট বট সফলভাবে সচল রয়েছে!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎁 **আমাদের আকর্ষণীয় ৪-লেভেল কমিশন স্ট্রাকচার:**\n"
        f"  🔹 **Level 1 (Direct):** ৳৫০০.০০\n"
        f"  🔸 **Level 2:** ৳১০০.০০\n"
        f"  🔸 **Level 3:** ৳৫০.০০\n"
        f"  🔸 **Level 4:** ৳৫০.০০\n\n"
        f"✨ নিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় তথ্য দেখে নিন:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in users_db:
        users_db[user_id] = {"balance": 0.0, "referred_by": None, "referrals": []}
        
    user_data = users_db[user_id]
    bot_username = context.bot.username

    if query.data == "ref_link":
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            f"🔗 **আপনার ইউনিক রেফারেল লিংক:**\n\n"
            f"`{ref_link}`\n\n"
            f"💡 *এই লিংকটি আপনার বন্ধুদের সাথে শেয়ার করুন। তারা জয়েন করলেই ৪ লেভেল পর্যন্ত আকর্ষণীয় কমিশন আপনার অ্যাকাউন্টে জমা হয়ে যাবে!*"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "balance":
        balance = user_data["balance"]
        total_refs = len(user_data["referrals"])
        text = (
            f"📊 **অ্যাকাউন্ট স্ট্যাটাস ও ড্যাশবোর্ড**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 **বর্তমান ব্যালেন্স:** ৳{balance:.2f}\n"
            f"👥 **ডাইরেক্ট রেফারেল (Level 1):** {total_refs} জন\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✨ আপনার আয় বাড়াতে বেশি বেশি শেয়ার করুন!"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "levels":
        text = (
            f"💎 **৪-লেভেল কমিশন বিবরণী**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🥇 **Level 1:** ৳৫০০ (যাকে আপনি নিজে রেফার করবেন)\n"
            f"🥈 **Level 2:** ৳১০০ (আপনার রেফারকৃত ব্যক্তি যাকে করবে)\n"
            f"🥉 **Level 3:** ৳৫০ (তৃতীয় ধাপের রেফারেল)\n"
            f"🏅 **Level 4:** ৳৫০ (চতুর্থ ধাপের রেফারেল)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "settings":
        text = (
            f"⚙️ **বট সেটিংস ও তথ্য**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛠️ **সিস্টেম:** Active (Multi-Level Affiliate)\n"
            f"🔒 **সিকিউরিটি:** Secure & Fast\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_home")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif query.data == "back_home":
        keyboard = [
            [InlineKeyboardButton("🔗 My Referral Link", callback_data="ref_link")],
            [InlineKeyboardButton("📊 My Balance & Stats", callback_data="balance"),
             InlineKeyboardButton("💎 Commission Levels", callback_data="levels")],
            [InlineKeyboardButton("⚙️ Settings & Info", callback_data="settings")]
        ]
        welcome_text = (
            f"🌟 **মূল মেনুতে স্বাগতম!** 🌟\n\n"
            f"নিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় সেবাটি বেছে নিন:"
        )
        await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN is not set in environment variables.")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
  
