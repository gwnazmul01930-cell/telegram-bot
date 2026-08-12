import os
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"স্বাগতম {user.first_name}! বট সফলভাবে চালু হয়েছে।")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    main()
  
