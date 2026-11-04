import os, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Health server for Render ---
class _HC(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *a): pass
def _run_health():
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", 10000))), _HC).serve_forever()
threading.Thread(target=_run_health, daemon=True).start()
print("HEALTH-TEST-123 PORT=" + str(os.getenv("PORT")))
# --- End health ---



# --- Config ---
TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
CHANNEL = "@protipsofficialchannel"
SUPPORT = "@protipsofficial_support_bot"
REQUIRED_INVITES = 6

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database ---
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) if MONGO_URI else None
db = client["urchworld"] if client is not None else None
users = db["users"] if db is not None else None

def get_user(user_id):
    try:
        return _get_user_inner(user_id)
    except Exception as e:
        print("DB FAIL, using memory:", e)
        return {"user_id": user_id, "invites": 0, "invited_by": None}

def _get_user_inner(user_id):
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
    print("GOT /start from", update.effective_user.id if update.effective_user else "?")
    user = update.effective_user
    args = context.args
    me = get_user(user.id)

    # Handle referral: /start <referrer_id>
    print("START_ARGS:", args, "users is None?", users is None, "my invited_by:", me.get("invited_by"))
    if args and args[0].isdigit():
        referrer_id = int(args[0])
        print("REFERRAL_ATTEMPT:", user.id, "->", referrer_id)
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
    is_new = update.effective_user.id not in [u.get("user_id") for u in [get_user(update.effective_user.id)] if u.get("created_at") is None] if False else False
    me = get_user(update.effective_user.id)
    await update.message.reply_text(
        myinvites_text(update.effective_user.id, int(me.get("invites", 0))),
        reply_markup=main_keyboard()
    )


async def vip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = get_user(update.effective_user.id)
    await update.message.reply_text(vip_text(int(me.get("invites", 0))), reply_markup=main_keyboard())

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top = []
    if users is not None:
        try:
            top = list(users.find().sort("invites", -1).limit(10))
        except Exception:
            top = []
    await update.message.reply_text(leaderboard_text(top), reply_markup=main_keyboard())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, reply_markup=main_keyboard())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    me = get_user(update.effective_user.id)
    if int(me.get("invites", 0)) >= 0:
        await update.message.reply_text("Admin panel coming soon.\nUse /leaderboard to see top inviters.", reply_markup=main_keyboard())

def main():

    print("TOKEN_LEN:", len(TOKEN) if TOKEN else 0)
    print("MONGO_SET:", bool(MONGO_URI))
    print("PORT:", os.getenv("PORT"))
    if not TOKEN:
        raise ValueError("BOT_TOKEN is not set")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("myinvites", myinvites_cmd))
    app.add_handler(CommandHandler("vip", vip_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    logger.info("PRO TIPS VIP Bot started")
    
async def handle_any_text(update, context):
    try:
        await update.message.reply_text(
            "👋 Hi! I only understand commands and buttons.\n\n"
            "Use /start to see the menu, /myinvites to check your invites, or tap the buttons below."
        )
    except Exception as e:
        print(f"Fallback error: {e}")


app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text))
app.run_polling(drop_pending_updates=False)

if __name__ == "__main__":
    main()
