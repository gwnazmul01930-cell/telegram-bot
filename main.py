# bot.py
# Python 3.11+
# pip install python-telegram-bot==21.6

import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

BOT_TOKEN = "YOUR_BOT_TOKEN"
ADMIN_USERNAME = "nasmul01930"

COMMISSIONS = {
    1: 500,
    2: 100,
    3: 50,
    4: 50
}

MIN_WITHDRAW = 500

db = sqlite3.connect("affiliate.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT,
    referrer_id INTEGER,
    balance INTEGER DEFAULT 0,
    verified INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS commissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    source_user_id INTEGER,
    level INTEGER,
    amount INTEGER,
    UNIQUE(user_id, source_user_id, level)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    method TEXT,
    account TEXT,
    status TEXT DEFAULT 'pending'
)
""")

db.commit()


def get_user(user_id):
    cur.execute("SELECT * FROM users WHERE id=?", (user_id,))
    return cur.fetchone()


def add_user(user_id, username, referrer_id=None):
    if get_user(user_id):
        return

    cur.execute(
        "INSERT INTO users(id, username, referrer_id) VALUES (?, ?, ?)",
        (user_id, username, referrer_id)
    )
    db.commit()


def give_commission(source_user_id):
    """
    source_user_id = নতুন referral user

    তার upline:
    Level 1 -> direct referrer
    Level 2 -> referrer's referrer
    Level 3 -> ...
    Level 4 -> ...
    """

    cur.execute(
        "SELECT referrer_id FROM users WHERE id=?",
        (source_user_id,)
    )

    row = cur.fetchone()
    current = row[0] if row else None

    for level in range(1, 5):

        if not current:
            break

        amount = COMMISSIONS[level]

        try:
            cur.execute("""
                INSERT INTO commissions
                (user_id, source_user_id, level, amount)
                VALUES (?, ?, ?, ?)
            """, (
                current,
                source_user_id,
                level,
                amount
            ))

            cur.execute("""
                UPDATE users
                SET balance = balance + ?
                WHERE id=?
            """, (amount, current))

            db.commit()

        except sqlite3.IntegrityError:
            # একই referral থেকে একই level-এর
            # commission দ্বিতীয়বার দেওয়া হবে না।
            db.rollback()

        cur.execute(
            "SELECT referrer_id FROM users WHERE id=?",
            (current,)
        )

        row = cur.fetchone()
        current = row[0] if row else None


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 আমার ব্যালেন্স", callback_data="balance"),
            InlineKeyboardButton("👥 Referral", callback_data="referral")
        ],
        [
            InlineKeyboardButton("📊 Level Commission", callback_data="levels"),
            InlineKeyboardButton("📜 Commission History", callback_data="history")
        ],
        [
            InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")
        ]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user
    referrer_id = None

    if context.args:
        try:
            possible_referrer = int(context.args[0])

            if possible_referrer != user.id:
                if get_user(possible_referrer):
                    referrer_id = possible_referrer

        except ValueError:
            pass

    is_new = get_user(user.id) is None

    add_user(
        user.id,
        user.username or "",
        referrer_id
    )

    if is_new and referrer_id:
        give_commission(user.id)

    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Affiliate Dashboard থেকে আপনার referral ও commission দেখতে পারবেন।",
        reply_markup=main_menu()
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "balance":

        cur.execute(
            "SELECT balance FROM users WHERE id=?",
            (user_id,)
        )

        balance = cur.fetchone()[0]

        await query.edit_message_text(
            f"💰 Your Balance\n\n"
            f"Available Balance: {balance}৳",
            reply_markup=main_menu()
        )

    elif query.data == "referral":

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id=?",
            (user_id,)
        )

        direct = cur.fetchone()[0]

        link = (
            f"https://t.me/YOUR_BOT_USERNAME"
            f"?start={user_id}"
        )

        await query.edit_message_text(
            f"👥 Referral Dashboard\n\n"
            f"Direct Referrals: {direct}\n\n"
            f"🔗 Your Referral Link:\n{link}",
            reply_markup=main_menu()
        )

    elif query.data == "levels":

        text = "📊 Level Commission\n\n"

        for level in range(1, 5):

            cur.execute("""
                SELECT COUNT(*), COALESCE(SUM(amount),0)
                FROM commissions
                WHERE user_id=? AND level=?
            """, (user_id, level))

            count, total = cur.fetchone()

            text += (
                f"Level {level}: "
                f"{count} referrals → {total}৳\n"
            )

        await query.edit_message_text(
            text,
            reply_markup=main_menu()
        )

    elif query.data == "history":

        cur.execute("""
            SELECT level, amount, source_user_id
            FROM commissions
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT 20
        """, (user_id,))

        rows = cur.fetchall()

        if not rows:
            text = "📜 এখনো কোনো commission history নেই।"

        else:
            text = "📜 Commission History\n\n"

            for level, amount, source in rows:
                text += (
                    f"Level {level} | "
                    f"+{amount}৳ | "
                    f"User: {source}\n"
                )

        await query.edit_message_text(
            text,
            reply_markup=main_menu()
        )

    elif query.data == "withdraw":

        cur.execute(
            "SELECT balance FROM users WHERE id=?",
            (user_id,)
        )

        balance = cur.fetchone()[0]

        await query.edit_message_text(
            f"💸 Withdrawal\n\n"
            f"Available: {balance}৳\n"
            f"Minimum Withdrawal: {MIN_WITHDRAW}৳\n\n"
            f"Withdrawal request দিতে Admin-এর সাথে যোগাযোগ করুন।",
            reply_markup=main_menu()
        )


def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CallbackQueryHandler(buttons)
    )

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
