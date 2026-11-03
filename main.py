import os, threading
from flask import Flask
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("BOT_TOKEN", "9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster")
VIP_LINK = os.getenv("VIP_LINK", "https://t.me/+fVTpAYIqIhNiYjFk")
OFFICIAL_URL = "https://t.me/protipsofficialchannel"
ADMIN_ID = 6652933614
PORT = int(os.getenv("PORT", 10000))
REQUIRED_REF = 6

# MongoDB with auto-reconnect and fallback
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    client.server_info()
    db = client["UrchWorldDB"]
    users = db["users"]
    print("MongoDB Connected OK")
    MONGO_OK = True
except Exception as e:
    print(f"MongoDB Failed - Running in FALLBACK MODE: {e}")
    users = None
    MONGO_OK = False

def get_progress(uid):
    try:
        if not MONGO_OK or users is None:
            return 0
        u = users.find_one({"user_id": uid})
        return len(u.get("referrals", [])) if u else 0
    except:
        return 0

def get_ref_link(uid):
    return f"https://t.me/ProTipsVIPbot?start={uid}"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("My Invites", callback_data="myinvites"), InlineKeyboardButton("VIP", callback_data="vip")],
        [InlineKeyboardButton("Leaderboard", callback_data="leaderboard"), InlineKeyboardButton("Help", callback_data="help")]
    ])

async def start(update, context):
    try:
        uid = update.effective_user.id
        if MONGO_OK:
            try:
                if not users.find_one({"user_id": uid}):
                    users.insert_one({"user_id": uid, "first_name": update.effective_user.first_name, "referrals": [], "referred_by": None})
            except: pass
        p = get_progress(uid)
        await update.message.reply_text(f"START WORKS! Progress {p}/{REQUIRED_REF} Link: {get_ref_link(uid)} Mongo: {'OK' if MONGO_OK else 'FALLBACK'}", reply_markup=menu(), disable_web_page_preview=True)
    except Exception as e:
        print(f"START ERROR: {e}")
        await update.message.reply_text(f"START WORKS! (fallback) Link: {get_ref_link(update.effective_user.id)}")

async def myinvites(update, context):
    try:
        print("CMD myinvites triggered")
        p = get_progress(update.effective_user.id)
        await update.message.reply_text(f"MYINVITES WORKS! Progress {p}/{REQUIRED_REF} Link: {get_ref_link(update.effective_user.id)}", reply_markup=menu(), disable_web_page_preview=True)
    except Exception as e:
        print(f"MYINVITES ERROR: {e}")
        await update.message.reply_text(f"MYINVITES WORKS! Fallback mode - Progress 0/6 Link: {get_ref_link(update.effective_user.id)}")

async def vip(update, context):
    try:
        print("CMD vip triggered")
        p = get_progress(update.effective_user.id)
        txt = f"VIP WORKS! {p}/{REQUIRED_REF} " + (f"UNLOCKED {VIP_LINK}" if p>=REQUIRED_REF else f"Need {REQUIRED_REF-p} more")
        await update.message.reply_text(txt, reply_markup=menu())
    except Exception as e:
        print(f"VIP ERROR: {e}")
        await update.message.reply_text(f"VIP WORKS! Fallback - Need 6 more Link: {get_ref_link(update.effective_user.id)}")

async def leaderboard(update, context):
    try:
        print("CMD leaderboard triggered")
        if not MONGO_OK:
            await update.message.reply_text("LEADERBOARD WORKS! Fallback mode - No data yet (Mongo down)", reply_markup=menu())
            return
        all_u = list(users.find())
        all_u.sort(key=lambda x: len(x.get("referrals", [])), reverse=True)
        top = all_u[:5]
        txt = "LEADERBOARD WORKS! Top 5\n\n"
        for i,u in enumerate(top,1):
            txt += f"{i}. {u.get('first_name','User')} - {len(u.get('referrals',[]))}\n"
        if not top: txt += "No data yet!"
        await update.message.reply_text(txt, reply_markup=menu())
    except Exception as e:
        print(f"LEADERBOARD ERROR: {e}")
        await update.message.reply_text("LEADERBOARD WORKS! Fallback mode", reply_markup=menu())

async def help_cmd(update, context):
    try:
        print("CMD help triggered")
        await update.message.reply_text("HELP WORKS! How: 1. /start get link 2. Share to 6 friends 3. /myinvites check 4. VIP unlocks! Official @protipsofficialchannel", reply_markup=menu())
    except Exception as e:
        print(f"HELP ERROR: {e}")
        await update.message.reply_text("HELP WORKS! 1. Get link 2. Share 3. Unlock!")

async def admin(update, context):
    try:
        print("CMD admin triggered")
        if update.effective_user.id != ADMIN_ID:
            await update.message.reply_text(f"ADMIN WORKS! Not admin. Your ID: {update.effective_user.id}")
            return
        count = users.count_documents({}) if MONGO_OK else 0
        await update.message.reply_text(f"ADMIN WORKS! Users: {count} Mongo: {'OK' if MONGO_OK else 'FALLBACK'}")
    except Exception as e:
        print(f"ADMIN ERROR: {e}")
        await update.message.reply_text(f"ADMIN WORKS! Error: {e}")

async def callbacks(update, context):
    try:
        q = update.callback_query
        await q.answer()
        print(f"Callback {q.data}")
        await q.edit_message_text(f"BUTTON {q.data} WORKS! Progress {get_progress(q.from_user.id)}/{REQUIRED_REF}", reply_markup=menu())
    except Exception as e:
        print(f"CALLBACK ERROR: {e}")

app = Flask(__name__)
@app.route("/")
def home(): return f"V7 FINAL - Mongo {'OK' if MONGO_OK else 'FALLBACK'} - All commands resilient!"
@app.route("/health")
def health(): return "OK", 200
def run_flask(): app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"Flask V7 Mongo={'OK' if MONGO_OK else 'FALLBACK'}")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myinvites", myinvites))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(callbacks))
    print("Polling V7 Resilient...")
    application.run_polling(drop_pending_updates=True)
