import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from supabase import create_client, Client

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ৪-লেভেল কমিশন রেট (আপনার দেওয়া হিসাব অনুযায়ী)
COMMISSION_RATES = {
    1: 500,
    2: 100,
    3: 50,
    4: 50
}

# /start কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None

    if args:
        try:
            referrer_id = int(args[0])
        except ValueError:
            pass

    # ইউজার আগে থেকেই ডাটাবেজে আছে কি না চেক করা
    existing_user = supabase.table("users").select("*").eq("telegram_id", user.id).execute()

    if not existing_user.data:
        # নতুন ইউজার হলে ডাটাবেজে ইনসার্ট করা
        supabase.table("users").insert({
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "balance": 0.0,
            "status": "inactive"
        }).execute()

        # রেফারেল চেইন তৈরি করা (যাতে ৪ লেভেল পর্যন্ত ট্র্যাক করা যায়)
        if referrer_id and referrer_id != user.id:
            current_ref = referrer_id
            for level in range(1, 5):
                ref_data = supabase.table("users").select("*").eq("telegram_id", current_ref).execute()
                if ref_data.data:
                    # কে কার রেফারারে জয়েন করেছে তা সেভ করা
                    supabase.table("referrals").insert({
                        "user_id": user.id,
                        "referrer_id": current_ref,
                        "level": level
                    }).execute()
                    
                    # ওপরের লেভেলের রেফারারকে খুঁজে বের করা
                    next_ref = supabase.table("referrals").select("referrer_id").eq("user_id", current_ref).eq("level", 1).execute()
                    if next_ref.data:
                        current_ref = next_ref.data[0]["referrer_id"]
                    else:
                        break
                else:
                    break

    await show_main_menu(update, user.id)

# মেইন মেনু দেখানোর ফাংশন
async def show_main_menu(update: Update, user_id: int):
    keyboard = [
        [InlineKeyboardButton("👤 আমার একাউন্ট", callback_data="my_account"),
         InlineKeyboardButton("🔗 রেফারেল লিংক", callback_data="ref_link")],
        [InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ এডমিন প্যানেল", callback_data="admin_panel_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("স্বাগতম! নিচের অপশনগুলো থেকে বেছে নিন:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.edit_text("মূল মেনু:", reply_markup=reply_markup)

# বাটন এবং এডমিন প্যানেল হ্যান্ডলার
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "my_account":
        res = supabase.table("users").select("*").eq("telegram_id", user.id).execute()
        if res.data:
            u = res.data[0]
            text = f"👤 **আপনার একাউন্ট:**\n\nনাম: {u.get('first_name')}\nব্যালেন্স: ৳{u.get('balance')}\nস্ট্যাটাস: {u.get('status').upper()}"
            await query.message.edit_text(text, parse_mode="Markdown")

    elif query.data == "ref_link":
        link = f"https://t.me/{context.bot.username}?start={user.id}"
        await query.message.edit_text(f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`", parse_mode="Markdown")

    elif query.data == "admin_panel_main" and user.id == ADMIN_ID:
        admin_kb = [
            [InlineKeyboardButton("🟢 ইউজার অ্যাক্টিভ করুন", callback_data="admin_active_prompt")],
            [InlineKeyboardButton("🔙 মূল মেনু", callback_data="back_to_menu")]
        ]
        await query.message.edit_text("⚙️ **এডমিন প্যানেল:**", reply_markup=InlineKeyboardMarkup(admin_kb))

    elif query.data == "admin_active_prompt" and user.id == ADMIN_ID:
        await query.message.edit_text("যে ইউজারের আইডি একটিভ করতে চান, তার টেলিগ্রাম আইডি এভাবে লিখুন:\n`/activate [USER_ID]`", parse_mode="Markdown")

    elif query.data == "back_to_menu":
        await show_main_menu(update, user.id)

# এডমিন কর্তৃক ইউজার অ্যাক্টিভ করার কমান্ড: /activate <user_id>
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("দুঃখিত, এই কমান্ডটি শুধুমাত্র এডমিনের জন্য!")
        return

    args = context.args
    if not args:
        await update.message.reply_text("দয়া করে ইউজারের আইডি দিন। যেমন: `/activate 123456789`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("সঠিক ইউজার আইডি দিন।")
        return

    # ১. ইউজারকে active করা
    target_user = supabase.table("users").select("*").eq("telegram_id", target_user_id).execute()
    if not target_user.data:
        await update.message.reply_text("এই আইডির কোনো ইউজার ডাটাবেজে পাওয়া যায়নি!")
        return

    if target_user.data[0]["status"] == "active":
        await update.message.reply_text("এই ইউজার ইতিমধ্যে অ্যাক্টিভ করা আছে!")
        return

    supabase.table("users").update({"status": "active"}).eq("telegram_id", target_user_id).execute()

    # ২. ৪ লেভেল পর্যন্ত কমিশন ডিস্ট্রিবিউট করা
    ref_chains = supabase.table("referrals").select("*").eq("user_id", target_user_id).execute()
    
    distributed_summary = []
    for row in ref_chains.data:
        lvl = row["level"]
        ref_id = row["referrer_id"]
        amount = COMMISSION_RATES.get(lvl, 0)

        if amount > 0:
            # রেফারারের বর্তমান ব্যালেন্স আনা
            ref_user_data = supabase.table("users").select("balance").eq("telegram_id", ref_id).execute()
            if ref_user_data.data:
                current_balance = ref_user_data.data[0]["balance"]
                new_balance = current_balance + amount
                
                # ব্যালেন্স আপডেট করা
                supabase.table("users").update({"balance": new_balance}).eq("telegram_id", ref_id).execute()
                distributed_summary.append(f"লেভেল {lvl} ({ref_id}): +৳{amount}")

    summary_text = f"✅ ইউজার `{target_user_id}` সফলভাবে অ্যাক্টিভ করা হয়েছে!\n\n**কমিশন বিতরণ:**\n" + ("\n".join(distributed_summary) if distributed_summary else "কোনো রেফারার নেই।")
    await update.message.reply_text(summary_text, parse_mode="Markdown")

# মূল ফাংশন
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("activate", activate_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == "__main__":
    main()
  
