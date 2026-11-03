import os, threading, logging
from flask import Flask
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest
BOT_TOKEN = os.getenv("BOT_TOKEN", "9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster")
VIP_LINK = os.getenv("VIP_LINK", "https://t.me/+fVTpAYIqIhNiYjFk")
OFFICIAL_URL = "https://t.me/protipsofficialchannel"
OFFICIAL_USERNAME = "protipsofficialchannel"
ADMIN_ID = int(os.getenv("ADMIN_ID", "6652933614"))
REQUIRED_REF = 6
PORT = int(os.getenv("PORT", 10000))
logging.basicConfig(level=logging.INFO)
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    client.server_info()
except:
    client = MongoClient(MONGO_URI)
db = client["UrchWorldDB"]
users = db["users"]
def get_user(uid): return users.find_one({"user_id": uid})
def get_progress(uid):
    u = get_user(uid)
    return len(u.get("referrals", [])) if u else 0
def get_ref_link(uid): return f"https://t.me/ProTipsVIPbot?start={uid}"
def main_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("My Invites", callback_data="myinvites"), InlineKeyboardButton("Unlock VIP", callback_data="vip")],[InlineKeyboardButton("Leaderboard", callback_data="leaderboard"), InlineKeyboardButton("Help", callback_data="help")],[InlineKeyboardButton("Official Channel", url=OFFICIAL_URL)]])
def join_required_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("Join Official Channel", url=OFFICIAL_URL)],[InlineKeyboardButton("I Joined - Verify", callback_data="verify_join")]])
async def is_joined(context, user_id):
    try:
        m = await context.bot.get_chat_member(chat_id=f"@{OFFICIAL_USERNAME}", user_id=user_id)
        return m.status in ["member", "administrator", "creator"]
    except BadRequest: return True
    except: return True
async def start(update, context):
    user = update.effective_user
    uid = user.id
    args = context.args
    if not get_user(uid): users.insert_one({"user_id": uid, "username": user.username, "first_name": user.first_name, "referrals": [], "referred_by": None})
    if not await is_joined(context, uid):
        await update.message.reply_text(f"JOIN REQUIRED\nHi {user.first_name}, join Official Channel first!", reply_markup=join_required_markup())
        return
    if args and args[0].isdigit():
        ref_id = int(args[0])
        if ref_id != uid:
            ref_user = get_user(ref_id)
            me = get_user(uid)
            if ref_user and me.get("referred_by") is None and uid not in ref_user.get("referrals", []):
                users.update_one({"user_id": ref_id}, {"$push": {"referrals": uid}})
                users.update_one({"user_id": uid}, {"$set": {"referred_by": ref_id}})
                try:
                    prog = get_progress(ref_id)
                    await context.bot.send_message(ref_id, f"New Referral! {user.first_name} joined! Progress: {prog}/{REQUIRED_REF}")
                    if prog >= REQUIRED_REF: await context.bot.send_message(ref_id, f"UNLOCKED! Join VIP: {VIP_LINK}")
                except: pass
    progress = get_progress(uid)
    text = f"Welcome {user.first_name}!\nProgress: {progress}/{REQUIRED_REF}\nLink: {get_ref_link(uid)}"
    if progress >= REQUIRED_REF: text += f"\nUNLOCKED! {VIP_LINK}"
    await update.message.reply_text(text, reply_markup=main_menu(), disable_web_page_preview=True)
async def verify_join(update, context):
    q = update.callback_query
    await q.answer()
    uid = update.effective_user.id
    if await is_joined(context, uid):
        p = get_progress(uid)
        t = f"Verified! Progress: {p}/{REQUIRED_REF} Link: {get_ref_link(uid)}"
        if p >= REQUIRED_REF: t += f" UNLOCKED: {VIP_LINK}"
        await q.edit_message_text(t, reply_markup=main_menu(), disable_web_page_preview=True)
    else: await q.edit_message_text("Not joined yet!", reply_markup=join_required_markup())
async def myinvites_handler(update, context):
    q = update.callback_query
    is_cb = q is not None
    if is_cb: await q.answer()
    uid = update.effective_user.id
    if not await is_joined(context, uid):
        tgt = q.edit_message_text if is_cb else update.message.reply_text
        await tgt("Join Official Channel first!", reply_markup=join_required_markup())
        return
    p = get_progress(uid)
    t = f"VIP {'Unlocked' if p >= REQUIRED_REF else 'Locked'}\nProgress: {p}/{REQUIRED_REF}\nLink: {get_ref_link(uid)}"
    if p >= REQUIRED_REF: t += f"\nJoin: {VIP_LINK}"
    mk = main_menu()
    if is_cb: await q.edit_message_text(t, reply_markup=mk, disable_web_page_preview=True)
    else: await update.message.reply_text(t, reply_markup=mk, disable_web_page_preview=True)
async def leaderboard(update, context):
    q = update.callback_query
    if q: await q.answer()
    all_u = list(users.find())
    all_u.sort(key=lambda x: len(x.get("referrals", [])), reverse=True)
    top = all_u[:10]
    t = "LEADERBOARD Top 10\n\n"
    for i,u in enumerate(top,1):
        t += f"{i}. {u.get('first_name','User')} - {len(u.get('referrals',[]))}\n"
    if not top: t += "No inviters yet!"
    mk = main_menu()
    if q: await q.edit_message_text(t, reply_markup=mk)
    else: await update.message.reply_text(t, reply_markup=mk)
async def help_handler(update, context):
    q = update.callback_query
    if q: await q.answer()
    t = "HOW IT WORKS\n1 Join Channel\n2 Get link /start\n3 Share to 6\n4 Check /myinvites\n5 VIP unlocks!"
    if q: await q.edit_message_text(t, reply_markup=main_menu())
    else: await update.message.reply_text(t, reply_markup=main_menu())
async def admin(update, context):
    if update.effective_user.id != ADMIN_ID: return
    total = users.count_documents({})
    all_u = list(users.find())
    total_refs = sum(len(u.get("referrals", [])) for u in all_u)
    t = f"ADMIN\nUsers: {total}\nRefs: {total_refs}\nReq: {REQUIRED_REF}\n/broadcast <msg>"
    await update.message.reply_text(t)
async def broadcast(update, context):
    if update.effective_user.id != ADMIN_ID: return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast msg")
        return
    msg = " ".join(context.args)
    all_u = list(users.find())
    sent = 0
    await update.message.reply_text(f"Broadcasting to {len(all_u)}...")
    for u in all_u:
        try:
            await context.bot.send_message(u["user_id"], f"Announcement\n{msg}")
            sent += 1
        except: pass
    await update.message.reply_text(f"Done {sent}/{len(all_u)}")
app = Flask(__name__)
@app.route("/")
def home(): return "V4 FINAL Alive!"
@app.route("/health")
def health(): return "OK", 200
def run_flask(): app.run(host="0.0.0.0", port=PORT)
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    print(f"Flask V4 {PORT}")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("myinvites", myinvites_handler))
    application.add_handler(CommandHandler("vip", myinvites_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("stats", admin))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="verify_join"))
    application.add_handler(CallbackQueryHandler(myinvites_handler, pattern="myinvites"))
    application.add_handler(CallbackQueryHandler(myinvites_handler, pattern="vip"))
    application.add_handler(CallbackQueryHandler(help_handler, pattern="help"))
    application.add_handler(CallbackQueryHandler(leaderboard, pattern="leaderboard"))
        # V4.1 Anti-Conflict + Auto Retry
    while True:
        try:
            print("Bot polling started...")
            application.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])
        except Exception as e:
            print(f"Polling crashed: {e} - Restarting in 5 sec...")
            import time
            time.sleep(5)
