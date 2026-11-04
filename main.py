import os, threading
from flask import Flask
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Config ---
TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
CHANNEL = "@protipsofficialchannel"
SUPPORT = "@protipsofficial_support_bot"
REQUIRED_INVITES = 6

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database ---
client = MongoClient(MONGO_URI) if MONGO_URI else None
db = client["urchworld"] if client is not None else None
users = db["users"] if db is not None else None

def get_user(user_id):
    if users is None:
        return {"user_id": user_id, "invites": 0, "invited_by": None}
    u = users.find_one({"user_id": user_id})
    if not u:
        u = {"user_id": user_id, "invites": 0, "invited_by": None}
        users.insert_one(u)
    return u

def get_invite_link(user_id):
    return f"https://t.me/ProTipsVIPbot?start={user_id}"

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Invites", callback_data="myinvites"),
         InlineKeyboardButton("👑 VIP", callback_data="vip")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
    ])

# --- Professional Texts ---

def welcome_text(user_id):
    return (
        f"👑 Welcome to PRO TIPS VIP\n\n"
        f"Get access to 55+ Odds, VIP Tips & Private Folder.\n\n"
        f"🔗 Your invite link:\n{get_invite_link(user_id)}\n\n"
        f"Invite {REQUIRED_INVITES} friends to unlock VIP automatically."
    )

def myinvites_text(user_id, count):
    remaining = max(0, REQUIRED_INVITES - count)
    if count >= REQUIRED_INVITES:
        return (
            f"📊 Your Invites\n\n"
            f"You have invited {count} of {REQUIRED_INVITES} friends.\n"
            f"✅ VIP Unlocked!\n\n"
            f"Join VIP here: {CHANNEL}"
        )
    return (
        f"📊 Your Invites\n\n"
        f"You have invited {count} of {REQUIRED_INVITES} friends.\n"
        f"You need {remaining} more to unlock VIP.\n\n"
        f"🔗 Share your link:\n{get_invite_link(user_id)}"
    )

def vip_text(count):
    if count >= REQUIRED_INVITES:
        return (
            f"✅ VIP Unlocked - Welcome!\n\n"
            f"You now have access to 55+ Odds + Private Folder.\n\n"
            f"Join here: {CHANNEL}"
        )
    remaining = REQUIRED_INVITES - count
    return (
        f"🔒 VIP Locked\n\n"
        f"You need {REQUIRED_INVITES} invites to unlock VIP.\n"
        f"Current progress: {count} / {REQUIRED_INVITES}\n"
        f"You need {remaining} more.\n\n"
        f"Share your link to continue."
    )

HELP_TEXT = (
    f"❓ Need Help?\n\n"
    f"1. Tap Start to get your invite link\n"
    f"2. Share it with {REQUIRED_INVITES} friends\n"
    f"3. Check your progress in My Invites\n"
    f"4. VIP unlocks automatically at {REQUIRED_INVITES} invites\n\n"
    f"Support: {SUPPORT}"
)

def leaderboard_text(top_users):
    if not top_users:
        return "🏆 Leaderboard\n\nNo invites yet. Be the first to invite friends!"
    lines = ["🏆 Leaderboard\n\nTop Inviters:"]
    for i, u in enumerate(top_users[:10], 1):
        lines.append(f"{i}. {u.get('invites', 0)} invites")
    lines.append(f"\nInvite friends to climb the leaderboard.")
    return "\n".join(lines)

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    me = get_user(user.id)

    # Handle referral: /start <referrer_id>
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        if referrer_id != user.id and users is not None:
            # Only count once per new user
            if not me.get("invited_by"):
                users.update_one({"user_id": user.id}, {"$set": {"invited_by": referrer_id}})
                users.update_one({"user_id": referrer_id}, {"$inc": {"invites": 1}}, upsert=True)

    me = get_user(user.id)
    await update.message.reply_text(
        welcome_text(user.id),
        reply_markup=main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    me = get_user(user_id)
    count = int(me.get("invites", 0))
    data = query.data

    if data == "myinvites":
        text = myinvites_text(user_id, count)
    elif data == "vip":
        text = vip_text(count)
    elif data == "help":
        text = HELP_TEXT
    elif data == "leaderboard":
        top = []
        if users is not None:
            top = list(users.find().sort("invites", -1).limit(10))
        text = leaderboard_text(top)
    elif data == "back":
        text = welcome_text(user_id)
    else:
        text = welcome_text(user_id)

    try:
        await query.edit_message_text(text, reply_markup=main_keyboard())
    except Exception:
        # If message is identical, Telegram throws error - ignore it
        pass

async def myinvites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = get_user(update.effective_user.id)
    await update.message.reply_text(
        myinvites_text(update.effective_user.id, int(me.get("invites", 0))),
        reply_markup=main_keyboard()
    )

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myinvites", myinvites_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("PRO TIPS VIP Bot started")
    
# --- Flask for Render health check ---
flask_app = Flask(__name__)
@flask_app.route("/")
def home():
    return "ProTips VIP Bot Running", 200
@flask_app.route("/health")
def health():
    return "OK", 200
def run_flask():
    PORT = int(os.getenv("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=PORT)
threading.Thread(target=run_flask, daemon=True).start()
# --- End Flask ---

app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
