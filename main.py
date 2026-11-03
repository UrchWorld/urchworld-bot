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
client = MongoClient(MONGO_URI)
db = client["UrchWorldDB"]
users = db["users"]
def get_progress(uid):
    u = users.find_one({"user_id": uid})
    return len(u.get("referrals", [])) if u else 0
def get_ref_link(uid): return f"https://t.me/ProTipsVIPbot?start={uid}"
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("My Invites", callback_data="myinvites"), InlineKeyboardButton("VIP", callback_data="vip")],
        [InlineKeyboardButton("Leaderboard", callback_data="leaderboard"), InlineKeyboardButton("Help", callback_data="help")]
    ])
async def start(update, context):
    uid = update.effective_user.id
    if not users.find_one({"user_id": uid}):
        users.insert_one({"user_id": uid, "first_name": update.effective_user.first_name, "referrals": [], "referred_by": None})
    p = get_progress(uid)
    await update.message.reply_text(f"START WORKS! Progress {p}/{REQUIRED_REF} Link: {get_ref_link(uid)}", reply_markup=menu())
async def myinvites(update, context):
    uid = update.effective_user.id
    p = get_progress(uid)
    await update.message.reply_text(f"MYINVITES WORKS! Progress {p}/{REQUIRED_REF} Link: {get_ref_link(uid)}", reply_markup=menu())
async def vip(update, context):
    uid = update.effective_user.id
    p = get_progress(uid)
    await update.message.reply_text(f"VIP WORKS! Progress {p}/{REQUIRED_REF} " + (f"UNLOCKED {VIP_LINK}" if p>=REQUIRED_REF else f"Need {REQUIRED_REF-p} more"), reply_markup=menu())
async def leaderboard(update, context):
    await update.message.reply_text(f"LEADERBOARD WORKS! Top inviters loading...", reply_markup=menu())
async def help_cmd(update, context):
    await update.message.reply_text(f"HELP WORKS! How it works: 1. Get link /start 2. Share to 6 friends 3. Check /myinvites 4. VIP unlocks!", reply_markup=menu())
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(f"ADMIN CHECK WORKS! You are not admin. Your ID: {update.effective_user.id} Admin ID: {ADMIN_ID}")
        return
    await update.message.reply_text(f"ADMIN WORKS! Users: {users.count_documents({})} refs working!", reply_markup=menu())
async def callbacks(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(f"BUTTON {q.data} WORKS!", reply_markup=menu())
app = Flask(__name__)
@app.route("/")
def home(): return "V6 FINAL - Each command separate text!"
@app.route("/health")
def health(): return "OK", 200
def run_flask(): app.run(host="0.0.0.0", port=PORT)
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print("Flask V6 - ALL COMMANDS SEPARATE")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myinvites", myinvites))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(callbacks))
    print("Polling V6...")
    application.run_polling(drop_pending_updates=True)
