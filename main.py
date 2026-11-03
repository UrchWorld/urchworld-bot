import os
import threading
import logging
from flask import Flask
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster")
VIP_LINK = "https://t.me/+fVTpAYIqIhNiYjFk"
OFFICIAL = "https://t.me/protipsofficialchannel"
ADMIN_ID = 6652933614
REQUIRED_REF = 6
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

# === FIX FOR TERMUX DNS ===
# If SRV fails, fallback to standard URI
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.server_info()
except Exception as e:
    print(f"SRV failed, trying workaround: {e}")
    # Fallback - Use same URI but with dnspython already installed it should work after resolv.conf fix
    client = MongoClient(MONGO_URI)

db = client["UrchWorldDB"]
users = db["users"]

def get_user(uid):
    return users.find_one({"user_id": uid})

def get_progress(uid):
    u = get_user(uid)
    return len(u.get("referrals", [])) if u else 0

def get_ref_link(uid):
    return f"https://t.me/ProTipsVIPbot?start={uid}"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Invites", callback_data="myinvites"),
         InlineKeyboardButton("🔓 Unlock VIP", callback_data="vip")],
        [InlineKeyboardButton("📢 Official Channel", url=OFFICIAL),
         InlineKeyboardButton("❓ Help", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    args = context.args

    # Create user if not exists
    if not get_user(uid):
        users.insert_one({"user_id": uid, "username": user.username, "referrals": [], "referred_by": None})
    
    # Handle referral
    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != uid:
            ref_user = get_user(ref_id)
            if ref_user and uid not in ref_user.get("referrals", []) and get_user(uid).get("referred_by") is None:
                users.update_one({"user_id": ref_id}, {"$push": {"referrals": uid}})
                users.update_one({"user_id": uid}, {"$set": {"referred_by": ref_id}})
                try:
                    await context.bot.send_message(ref_id, f"🎉 New referral! {user.first_name} joined via your link!\nProgress: {get_progress(ref_id)}/{REQUIRED_REF}")
                except: pass

    progress = get_progress(uid)
    text = f"👋 Welcome {user.first_name}!\n\n🔥 Unlock 55 ODDS VIP by inviting {REQUIRED_REF} friends. 100% free, auto system.\n\n📊 Your Progress: {progress}/{REQUIRED_REF}\n🔗 Your Link:\n{get_ref_link(uid)}"
    if progress >= REQUIRED_REF:
        text += f"\n\n✅ UNLOCKED! Join VIP:\n{VIP_LINK}"
    
    await update.message.reply_text(text, reply_markup=main_menu(), disable_web_page_preview=True)

async def myinvites(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query: await query.answer()
    uid = update.effective_user.id
    progress = get_progress(uid)
    u = get_user(uid)
    refs = u.get("referrals", []) if u else []
    
    text = f"🔒 VIP Access {'Unlocked ✅' if progress >= REQUIRED_REF else 'Locked'}\n\nYour Progress: {progress}/{REQUIRED_REF} referrals\nRequirement: {REQUIRED_REF} referrals to unlock\n\nYour Link:\n{get_ref_link(uid)}\n\n{'✅ You can now join: ' + VIP_LINK if progress >= REQUIRED_REF else 'Please continue sharing your referral link to gain access.'}"
    
    markup = main_menu()
    if query:
        await query.edit_message_text(text, reply_markup=markup, disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, reply_markup=markup, disable_web_page_preview=True)

async def vip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await myinvites(update, context)

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = "❓ HOW IT WORKS\n\n1. Get your referral link with /start\n2. Share to 6 friends\n3. They must click your link and start bot\n4. Check /myinvites\n5. At 6 referrals, VIP unlocks auto!\n\nNeed help? Contact @protipsofficialchannel"
    await query.edit_message_text(text, reply_markup=main_menu())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "❓ HOW IT WORKS\n\n1. Get your referral link with /start\n2. Share to 6 friends\n3. They must click your link and start bot\n4. Check /myinvites\n5. At 6 referrals, VIP unlocks auto!"
    await update.message.reply_text(text, reply_markup=main_menu())

# === FLASK HEALTH SERVER FOR RENDER 24/7 ===
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ PRO TIPS VIP Bot is Alive! Production V3"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# === MAIN ===
if __name__ == "__main__":
    # Start Flask in background thread (keeps Render alive)
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"✅ Flask health server running on port {PORT}")
    print("✅ Bot running PRO V3 Production Ready!")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myinvites", myinvites))
    application.add_handler(CommandHandler("vip", myinvites))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CallbackQueryHandler(myinvites, pattern="myinvites"))
    application.add_handler(CallbackQueryHandler(vip_callback, pattern="vip"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="help"))
    
    application.run_polling()
