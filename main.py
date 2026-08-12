import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from supabase import create_client, Client

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Environment Variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Commission Rates
COMMISSION_RATES = {
    1: 500,
    2: 100,
    3: 50,
    4: 50
}

# Main Menu Keyboard
def get_main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("👤 আমার একাউন্ট", callback_data="my_account")],
        [InlineKeyboardButton("🔗 রেফারেল লিংক", callback_data="ref_link")],
        [InlineKeyboardButton("💳 উইথড্র", callback_data="withdraw")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ এডমিন প্যানেল", callback_data="admin_panel_main")])
    return InlineKeyboardMarkup(keyboard)

# Start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None

    if args:
        try:
            referrer_id = int(args[0])
        except ValueError:
            pass

    # Save or Update User in Supabase Database
    try:
        existing_user = supabase.table("users").select("*").eq("telegram_id", user.id).execute()
        
        if not existing_user.data:
            supabase.table("users").insert({
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "balance": 0,
                "status": "inactive"
            }).execute()

            # Referral Chain Setup
            if referrer_id and referrer_id != user.id:
                current_ref = referrer_id
                for level in range(1, 5):
                    ref_data = supabase.table("users").select("*").eq("telegram_id", current_ref).execute()
                    if ref_data.data:
                        supabase.table("referrals").insert({
                            "user_id": user.id,
                            "referrer_id": current_ref,
                            "level": level
                        }).execute()
                        
                        next_ref = supabase.table("referrals").select("referrer_id").eq("user_id", current_ref).eq("level", 1).execute()
                        if next_ref.data:
                            current_ref = next_ref.data[0]["referrer_id"]
                        else:
                            break
                    else:
                        break
        
        is_admin = (user.id == ADMIN_ID)
        await update.message.reply_text(
            f"স্বাগতম {user.first_name}! NexusAffiliate বটে আপনাকে স্বাগতম।",
            reply_markup=get_main_menu(is_admin)
        )
    except Exception as e:
        logging.error(f"Supabase Error: {e}")
        await update.message.reply_text("একটি টেকনিক্যাল সমস্যা হয়েছে, দয়া করে একটু পরে চেষ্টা করুন।")

# Callback Query Handler for Buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user

    if query.data == "my_account":
        res = supabase.table("users").select("*").eq("telegram_id", user.id).execute()
        if res.data:
            u_data = res.data[0]
            text = f"👤 **আপনার একাউন্ট তথ্য:**\n\nনাম: {u_data.get('first_name')}\nব্যালেন্স: {u_data.get('balance', 0)} টাকা\nস্ট্যাটাস: {u_data.get('status')}"
            await query.message.edit_text(text, parse_mode="Markdown", reply_markup=get_main_menu(user.id == ADMIN_ID))
            
    elif query.data == "ref_link":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user.id}"
        await query.message.edit_text(f"🔗 **আপনার রেফারেল লিংক:**\n\n`{link}`", parse_mode="Markdown", reply_markup=get_main_menu(user.id == ADMIN_ID))
        
    elif query.data == "withdraw":
        await query.message.edit_text("💳 উইথড্র সিস্টেমটি শীঘ্রই চালু হবে।", reply_markup=get_main_menu(user.id == ADMIN_ID))
        
    elif query.data == "admin_panel_main" and user.id == ADMIN_ID:
        admin_kb = [
            [InlineKeyboardButton("🟢 ইউজার অ্যাক্টিভ করুন", callback_data="admin_active_prompt")],
            [InlineKeyboardButton("🔙 মূল মেনু", callback_data="back_to_menu")]
        ]
        await query.message.edit_text("⚙️ **এডমিন প্যানেল:**", reply_markup=InlineKeyboardMarkup(admin_kb))
        
    elif query.data == "admin_active_prompt" and user.id == ADMIN_ID:
        await query.message.edit_text("ইউজারকে অ্যাক্টিভ করতে চ্যাট বক্সে এই কমান্ড লিখুন:\n`/activate [USER_ID]`", reply_markup=get_main_menu(True))
        
    elif query.data == "back_to_menu":
        await query.message.edit_text("মূল মেনু:", reply_markup=get_main_menu(user.id == ADMIN_ID))

# Admin Command: /activate <user_id>
async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("দুঃখিত, এই কমান্ডটি শুধুমাত্র এডমিনের জন্য!")
        return

    args = context.args
    if not args:
        await update.message.reply_text("দয়া করে ইউজার আইডি দিন। যেমন: `/activate 123456789`", parse_mode="Markdown")
        return

    try:
        target_user_id = int(args[0])
    except ValueError:
        await update.message.reply_text("সঠিক ইউজার আইডি দিন!")
        return

    target_user = supabase.table("users").select("*").eq("telegram_id", target_user_id).execute()
    if not target_user.data:
        await update.message.reply_text("এই আইডির কোনো ইউজার ডেটাবেজে পাওয়া যায়নি!")
        return

    if target_user.data[0]["status"] == "active":
        await update.message.reply_text("এই ইউজার ইতিমধ্যে অ্যাক্টিভ করা আছে!")
        return

    supabase.table("users").update({"status": "active"}).eq("telegram_id", target_user_id).execute()

    ref_chains = supabase.table("referrals").select("*").eq("user_id", target_user_id).execute()
    
    distributed_summary = []
    for row in ref_chains.data:
        lvl = row["level"]
        ref_id = row["referrer_id"]
        amount = COMMISSION_RATES.get(lvl, 0)

        if amount > 0:
            ref_user_data = supabase.table("users").select("balance").eq("telegram_id", ref_id).execute()
            if ref_user_data.data:
                current_balance = ref_user_data.data[0]["balance"]
                new_balance = current_balance + amount
                
                supabase.table("users").update({"balance": new_balance}).eq("telegram_id", ref_id).execute()
                distributed_summary.append(f"লেভেল {lvl} ({ref_id}): +{amount}৳")

    summary_text = f"✅ ইউজার {target_user_id} সফলভাবে অ্যাক্টিভ করা হয়েছে!\n\nকমিশন বিতরণ:\n" + ("\n".join(distributed_summary) if distributed_summary else "কোনো রেফারার নেই।")
    await update.message.reply_text(summary_text)

# Main Function
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN পাওয়া যায়নি!")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("activate", activate_command))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running perfectly...")
    application.run_polling()

if __name__ == "__main__":
    main()
