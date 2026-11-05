import os
import urllib.parse, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import logging
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

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
CHANNEL_ID = "@protipsofficialchannel"  # must match your channel username
SUPPORT_USERNAME = "@protipsofficial_support_bot"
ADMIN_ID = 6652933614

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


def admin_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("👑 VIPs", callback_data="admin_vips"),
         InlineKeyboardButton("🏆 Top Inviters", callback_data="admin_top")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ])
def admin_stats_text():
    if users is None:
        return "📊 Admin Stats - DB not connected."
    total = users.count_documents({})
    vips = users.count_documents({"invites": {"$gte": REQUIRED_INVITES}})
    total_inv = sum([u.get("invites",0) for u in users.find({}, {"invites":1})])
    return f"📊 PRO TIPS VIP - Admin Panel\n\n👥 Total Users: {total}\n✅ VIP Unlocked: {vips}\n📨 Total Invites: {total_inv}\n⏳ Waiting: {total-vips}"

def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Invites", callback_data="myinvites"),
         InlineKeyboardButton("👑 VIP", callback_data="vip")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("💬 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@','')}")],
    ])

async def is_member(bot, user_id):
    try:
        m = await bot.get_chat_member(CHANNEL_ID, user_id)
        return m.status in ["member", "administrator", "creator"]
    except Exception:
        return False

def join_keyboard():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_ID.replace('@','')}")],
        [InlineKeyboardButton("✅ I Have Joined - Verify", callback_data="verify_join")],
    ])

# --- Professional Texts ---

def welcome_text(user_id):
    return (
        f"👑 Welcome to PRO TIPS VIP - Where Winners Are Made! ⚽🔥\n\n"
        f"🎁 WHAT YOU GET FREE:\n"
        f"✅ Daily Free Tips (2-3 Odds)\n"
        f"✅ Yesterday's Results & Proof\n"
        f"✅ VIP Access: 55+ Odds, Private Folder & Daily Big Tips\n\n"
        f"🚀 HOW TO UNLOCK VIP (100% FREE, 2 mins):\n"
        f"1️⃣ Tap START & Join Channel\n"
        f"2️⃣ Share your link below with 6 friends\n"
        f"3️⃣ VIP unlocks AUTOMATICALLY - No payment!\n\n"
        f"🔗 YOUR PERSONAL VIP LINK:\n{get_invite_link(user_id)}\n\n"
        f"👇 Tap Share My Link below to copy & send to friends.\n"
        f"📊 You: 0/{REQUIRED_INVITES} - Your VIP is waiting!"
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
    f"Support: {SUPPORT}\n\n⚖️ Fair Play: 1 person = 1 account. Fake / self invites = ban, no VIP."
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
    # FORCE JOIN - must join channel first
    if not await is_member(context.bot, user.id):
        await update.message.reply_text(
            "📢 Join Our Channel First!\n\nTo get your invite link, you must join @protipsofficialchannel first.\n\nTap Join, then tap Verify.",
            reply_markup=join_keyboard()
        )
        return
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
                # Notify referrer + celebration
                try:
                    ref_user = users.find_one({"user_id": referrer_id})
                    ref_count = int(ref_user.get("invites", 0)) if ref_user else 1
                    if ref_count >= REQUIRED_INVITES:
                        await context.bot.send_message(chat_id=referrer_id, text=f"🎉 CONGRATULATIONS! VIP UNLOCKED!\n\nYou have invited {ref_count}/{REQUIRED_INVITES} friends!\n\n👑 Your VIP access is ready! Tap /vip to claim it now!")
                    else:
                        await context.bot.send_message(chat_id=referrer_id, text=f"🎉 +1 New Invite!\n\nYou now have {ref_count}/{REQUIRED_INVITES}.\nYou need {REQUIRED_INVITES - ref_count} more to unlock VIP! Keep sharing!")
                except Exception:
                    pass

    me = get_user(user.id)
    await update.message.reply_text(
        welcome_text(user.id),
        reply_markup=main_keyboard()
    )


async def admin_handle(query, context, data, user):
    if user.id != ADMIN_ID:
        await query.answer("❌ Not an admin", show_alert=True)
        return True
    if data == "admin_stats":
        await query.edit_message_text(admin_stats_text(), reply_markup=admin_keyboard())
    elif data == "admin_users":
        last = list(users.find().sort("_id", -1).limit(10)) if users is not None else []
        txt = "👥 Last 10 Users:\n\n" + "\n".join([f"• {u.get('user_id')} - {u.get('invites',0)} invites" for u in last]) if last else "No users yet."
        await query.edit_message_text(txt, reply_markup=admin_keyboard())
    elif data == "admin_vips":
        vips = list(users.find({"invites": {"$gte": REQUIRED_INVITES}}).limit(20)) if users is not None else []
        txt = "👑 VIP Users:\n\n" + "\n".join([f"• {u.get('user_id')} - {u.get('invites',0)} invites" for u in vips]) if vips else "No VIPs yet."
        await query.edit_message_text(txt, reply_markup=admin_keyboard())
    elif data == "admin_top":
        top = list(users.find().sort("invites", -1).limit(10)) if users is not None else []
        txt = "🏆 Top Inviters:\n\n" + "\n".join([f"{i}. {u.get('user_id')} - {u.get('invites',0)}" for i, u in enumerate(top,1)]) if top else "No invites yet."
        await query.edit_message_text(txt, reply_markup=admin_keyboard())
    elif data == "admin_broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("📣 Broadcast Mode\n\nType the message to send to ALL users now.", reply_markup=admin_keyboard())
    elif data == "admin_broadcast_yes":
        msg = context.user_data.get("broadcast_text", "")
        await query.edit_message_text("⏳ Sending broadcast...")
        sent, failed = 0, 0
        if users is not None:
            for u in users.find({}, {"user_id": 1}):
                try:
                    await context.bot.send_message(chat_id=u.get("user_id"), text=msg)
                    sent += 1
                except Exception:
                    failed += 1
        await query.edit_message_text(f"✅ Broadcast Done\n\nSent: {sent}\nFailed: {failed}", reply_markup=admin_keyboard())
    elif data == "admin_broadcast_no":
        context.user_data["broadcast_text"] = ""
        await query.edit_message_text("❌ Broadcast cancelled.", reply_markup=admin_keyboard())
    elif data == "admin_back":
        await query.edit_message_text(welcome_text(user.id), reply_markup=main_keyboard())
    return True

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    me = get_user(user_id)
    count = int(me.get("invites", 0))
    data = query.data

    if data == "verify_join":
        if await is_member(context.bot, user_id):
            await query.edit_message_text(welcome_text(user_id), reply_markup=main_keyboard())
        else:
            await query.answer("❌ You have not joined yet. Join first!", show_alert=True)
        return

    if data.startswith("share_"):
        base = "https://" + "t.me" + "/UrchWorldBot?start=" + str(user_id)
        txt = "Share UrchWorld:\n" + base
        await query.answer(txt, show_alert=True)
        return
    if data.startswith("admin_"):
        await admin_handle(query, context, data, query.from_user)
        return

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

    kb = share_kb(get_invite_link(user_id)) if data == 'myinvites' else main_keyboard()
    try:
        await query.edit_message_text(text, reply_markup=kb)
    except Exception:
        # If message is identical, Telegram throws error - ignore it
        pass

async def myinvites_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    is_new = update.effective_user.id not in [u.get("user_id") for u in [get_user(update.effective_user.id)] if u.get("created_at") is None] if False else False
    me = get_user(update.effective_user.id)
    await update.message.reply_text(
        myinvites_text(update.effective_user.id, int(me.get("invites", 0))),
        reply_markup=share_kb(get_invite_link(update.effective_user.id))
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
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not an admin.")
        return
    await update.message.reply_text(admin_stats_text(), reply_markup=admin_keyboard())

async def handle_any_text(update, context):
    user = update.effective_user
    if user.id == ADMIN_ID and context.user_data.get("awaiting_broadcast"):
        txt = update.message.text
        context.user_data["broadcast_text"] = txt
        context.user_data["awaiting_broadcast"] = False
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes, Send to All", callback_data="admin_broadcast_yes")],[InlineKeyboardButton("❌ Cancel", callback_data="admin_broadcast_no")]])
        await update.message.reply_text(f"📣 Preview:\n\n{txt}\n\nSend to ALL users?", reply_markup=kb)
        return

    try:
        await update.message.reply_text("Got it 👍\n\nI do not reply to typed messages here - I work with buttons so your invites count correctly.\n\nPlease use the menu below 👇\n\n📊 Tap My Invites to see your progress\n👑 Tap VIP to check your VIP status\n🏆 Tap Leaderboard to see top inviters\n❓ Tap Help if you are stuck\n\nTo get your invite link, tap Start first, then share it with 6 friends to unlock VIP.", reply_markup=main_keyboard())
    except Exception as e:
        print(f"Fallback error: {e}")

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_text))
    logger.info("PRO TIPS VIP Bot started")
    app.run_polling(drop_pending_updates=False)
    



if __name__ == "__main__":
    main()

# PART 2 - share buttons
def share_kb(link="hi"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from urllib.parse import quote
    msg = quote("Join UrchWorld VIP - Free! " + link)
    wa = "https://" + "wa.me" + "/?text=" + msg
    x = "https://" + "twitter.com" + "/intent/tweet?text=" + msg
    fb = "https://" + "www.facebook.com" + "/sharer/sharer.php?u=" + quote(link)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Share TG", switch_inline_query=link)],
        [InlineKeyboardButton("WA", url=wa), InlineKeyboardButton("X", url=x)],
        [InlineKeyboardButton("FB", url=fb)],
    ])

# share handlers below
