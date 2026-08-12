import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from supabase import create_client, Client

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Start Command Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Save or Update User in Supabase Database
    try:
        data = {
            "user_id": user.id,
            "first_name": user.first_name,
            "username": user.username
        }
        # Assuming table name is 'users'
        supabase.table("users").upsert(data).execute()
    except Exception as e:
        logging.error(f"Supabase Error: {e}")

    await update.message.reply_text(
        f"হ্যালো {user.first_name}! NexusAffiliate বটে আপনাকে স্বাগতম।"
    )

# Main Function
def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN পাওয়া যায়নি!")
        
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    
    # Run Bot
    application.run_polling()

if __name__ == "__main__":
    main()
  
