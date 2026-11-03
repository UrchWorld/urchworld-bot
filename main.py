import os, threading
from flask import Flask
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
BOT_TOKEN = os.getenv("BOT_TOKEN", "9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster")
VIP_LINK = os.getenv("VIP_LINK", "https://t.me/+fVTpAYIqIhNiYjFk")
OFFICIAL_URL = "https://t.me/protipsofficialchannel"
ADMIN_ID = int(os.getenv("ADMIN_ID", "6652933614"))
PORT = int(os.getenv("PORT", 10000))
REQUIRED_REF = 6
client = MongoClient(MONGO_URI)
db = client["UrchWorldDB"]
users = db["users"]
def get_user(uid): return users.find_one({"user_id": uid})
def get_progress(uid):
    u = get_user(uid)
    return len(u.get("referrals", [])) if u else 0
def get_ref_link(uid): return f"https://t.me/ProTipsVIPbot?start={uid}"
def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 My Invites", callback_data="myinvites"), InlineKeyboardButton("🔓 Unlock VIP", callback_data="vip")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"), InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("📢 Official Channel", url=OFFICIAL_URL)]
    ])
async def start(update, context):
    uid = update.effective_user.id
    user = update.effective_user
    if not get_user(uid):
        users.insert_one({"user_id": uid, "username": user.username, "first_name": user.first_name, "referrals": [], "referred_by": None})
    args = context.args
    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != uid:
            ru = get_user(ref_id)
            me = get_user(uid)
            if ru and me.get("referred_by") is None and uid not in ru.get("referrals", []):
                users.update_one({"user_id": ref_id}, {"$push": {"referrals": uid}})
                users.update_one({"user_id": uid}, {"$set": {"referred_by": ref_id}})
                try:
                    prog = get_progress(ref_id)
                    await context.bot.send_message(ref_id, f"🎉 New referral! {user.first_name} joined! Progress {prog}/{REQUIRED_REF}")
                    if prog >= REQUIRED_REF:
                        await context.bot.send_message(ref_id, f"🏆 UNLOCKED! Join VIP: {VIP_LINK}")
                except: pass
    p = get_progress(uid)
    txt = f"👋 Welcome {user.first_name}!\n\n🔥 Unlock 55 ODDS VIP by inviting {REQUIRED_REF} friends.\n\n📊 Progress: {p}/{REQUIRED_REF}\n🔗 Your Link: {get_ref_link(uid)}"
    if p >= REQUIRED_REF: txt += f"\n\n✅ UNLOCKED! Join VIP: {VIP_LINK}"
    txt += "\n\n👇 Use buttons below:"
    await update.message.reply_text(txt, reply_markup=menu(), disable_web_page_preview=True)

async def myinvites(update, context):
    print("CMD myinvites")
    uid = update.effective_user.id
    p = get_progress(uid)
    txt = f"🔒 VIP Access {'Unlocked ✅' if p >= REQUIRED_REF else 'Locked 🔒'}\n\nProgress: {p}/{REQUIRED_REF}\nNeed {REQUIRED_REF} to unlock\n\nYour Link: {get_ref_link(uid)}"
    if p >= REQUIRED_REF: txt += f"\n\n✅ Join VIP: {VIP_LINK}"
    else: txt += f"\n\nNeed {REQUIRED_REF-p} more! Keep sharing!"
    await update.message.reply_text(txt, reply_markup=menu(), disable_web_page_preview=True)

async def vip(update, context):
    print("CMD vip")
    uid = update.effective_user.id
    p = get_progress(uid)
    if p >= REQUIRED_REF:
        txt = f"🏆 UNLOCKED! You have {p} referrals!\n\nJoin VIP NOW:\n{VIP_LINK}"
    else:
        txt = f"🔒 Locked {p}/{REQUIRED_REF}\nNeed {REQUIRED_REF-p} more!\nYour Link: {get_ref_link(uid)}"
    await update.message.reply_text(txt, reply_markup=menu(), disable_web_page_preview=True)

async def leaderboard(update, context):
    print("CMD leaderboard")
    all_u = list(users.find())
    all_u.sort(key=lambda x: len(x.get("referrals", [])), reverse=True)
    top = all_u[:10]
    txt = "🏆 LEADERBOARD Top 10\n\n"
    for i,u in enumerate(top,1):
        txt += f"{i}. {u.get('first_name','User')} - {len(u.get('referrals',[]))} invites\n"
    if not top: txt += "No inviters yet! Be first!"
    await update.message.reply_text(txt, reply_markup=menu())

async def help_cmd(update, context):
    print("CMD help")
    txt = "❓ HOW IT WORKS\n\n1️⃣ Get your link with /start\n2️⃣ Share link to friends\n3️⃣ Friends click link + start bot\n4️⃣ Check /myinvites\n5️⃣ At 6 referrals, VIP unlocks auto!\n\n📢 Official: @protipsofficialchannel\n🎯 Required: 6 friends"
    await update.message.reply_text(txt, reply_markup=menu())

async def admin(update, context):
    print("CMD admin")
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not admin - Your ID: " + str(update.effective_user.id))
        return
    total = users.count_documents({})
    all_u = list(users.find())
    total_refs = sum(len(u.get("referrals", [])) for u in all_u)
    txt = f"👑 ADMIN PANEL\n\nUsers: {total}\nTotal Referrals: {total_refs}\nRequired: {REQUIRED_REF}\n\nCommands:\n/broadcast <message>\n/stats\n/users"
    await update.message.reply_text(txt)

async def broadcast(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast Your message")
        return
    msg = " ".join(context.args)
    all_u = list(users.find())
    sent = 0
    await update.message.reply_text(f"📢 Broadcasting to {len(all_u)}...")
    for u in all_u:
        try:
            await context.bot.send_message(u["user_id"], f"📢 Announcement\n\n{msg}")
            sent += 1
        except: pass
    await update.message.reply_text(f"✅ Done! Sent to {sent}/{len(all_u)}")

async def callbacks(update, context):
    q = update.callback_query
    await q.answer()
    print(f"Callback {q.data}")
    uid = q.from_user.id
    p = get_progress(uid)
    data = q.data
    if data in ["myinvites", "vip"]:
        txt = f"🔒 VIP {'Unlocked' if p >= REQUIRED_REF else 'Locked'} {p}/{REQUIRED_REF}\nYour Link: {get_ref_link(uid)}"
        if p >= REQUIRED_REF: txt += f"\nJoin: {VIP_LINK}"
        await q.edit_message_text(txt, reply_markup=menu(), disable_web_page_preview=True)
    elif data == "leaderboard":
        all_u = list(users.find())
        all_u.sort(key=lambda x: len(x.get("referrals", [])), reverse=True)
        top = all_u[:10]
        txt = "🏆 Top 10\n\n"
        for i,u in enumerate(top,1):
            txt += f"{i}. {u.get('first_name','User')} - {len(u.get('referrals',[]))}\n"
        await q.edit_message_text(txt, reply_markup=menu())
    elif data == "help":
        txt = "HOW IT WORKS\n1. Get link /start\n2. Share to 6\n3. Check /myinvites\n4. VIP unlocks at 6!"
        await q.edit_message_text(txt, reply_markup=menu())

app = Flask(__name__)
@app.route("/")
def home(): return "V6 FINAL - All commands separate!"
@app.route("/health")
def health(): return "OK", 200
def run_flask(): app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"Flask V6 on {PORT}")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myinvites", myinvites))
    application.add_handler(CommandHandler("vip", vip))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("stats", admin))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(callbacks))
    print("Bot polling V6 - Separate handlers...")
    application.run_polling(drop_pending_updates=True)
