import os
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- DIRECT CREDENTIALS (FIXED - Boss said no revoke) ---
BOT_TOKEN = "9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw"
MONGO_URI = "mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster"

# --- YOUR FIXED CONFIG ---
VIP_LINK = "https://t.me/+fVTpAYIqIhNiYjFk"
OFFICIAL = "https://t.me/protipsofficialchannel"
ADMIN_ID = 6652933614
REQUIRED_REF = 6

# Override with ENV if exists on Render (secure)
BOT_TOKEN = os.getenv("BOT_TOKEN", BOT_TOKEN)
MONGO_URI = os.getenv("MONGO_URI", MONGO_URI)

client = MongoClient(MONGO_URI)
users = client["UrchWorldDB"]["users"]

def get_user(uid):
    return users.find_one({"user_id": uid})

def get_progress(uid):
    u = get_user(uid)
    return len(u.get("referrals", [])) if u else 0

def get_ref_link(uid):
    return f"https://t.me/ProTipsVIPbot?start={uid}"

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 My Referral Link", callback_data="mylink")],
        [InlineKeyboardButton("📊 My Progress", callback_data="progress")],
        [InlineKeyboardButton("📢 Official Channel", url=OFFICIAL)],
        [InlineKeyboardButton("🔥 VIP Channel", url=VIP_LINK)]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    args = context.args
    if not get_user(uid):
        users.insert_one({"user_id": uid, "name": name, "referrals": []})
    if args:
        try:
            ref_id = int(args[0])
            if ref_id != uid:
                ref_user = get_user(ref_id)
                if ref_user and uid not in ref_user.get("referrals", []):
                    users.update_one({"user_id": ref_id}, {"$push": {"referrals": uid}})
                    prog = get_progress(ref_id) + 1
                    try:
                        await context.bot.send_message(ref_id, f"🎉 New referral! {name} joined!\n📊 Progress: {prog}/{REQUIRED_REF}")
                        if prog >= REQUIRED_REF:
                            await context.bot.send_message(ref_id, f"✅ UNLOCKED VIP!\n🔥 {VIP_LINK}")
                    except: pass
        except: pass
    total = users.count_documents({})
    progress = get_progress(uid)
    percent = int((progress / REQUIRED_REF) * 100)
    bar = "█" * (percent // 20) + "─" * (5 - percent // 20)
    link = get_ref_link(uid)
    if progress >= REQUIRED_REF:
        msg = f"✅ Welcome {name}!\n\n🎉 VIP UNLOCKED!\n📊 {progress}/{REQUIRED_REF} [{bar}]\n🔥 VIP: {VIP_LINK}\n👥 Total: {total}"
    else:
        msg = f"👋 Welcome {name}!\n\n🔒 VIP Locked\n📊 Progress: {progress}/{REQUIRED_REF} ({percent}%)\n[{bar}]\n🎯 Need {REQUIRED_REF-progress} more referrals\n\n🔗 Your Link:\n{link}\n\n👥 Total Members: {total}\n\nShare your link to unlock!"
    await update.message.reply_text(msg, reply_markup=main_menu())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    progress = get_progress(uid)
    percent = int((progress / REQUIRED_REF) * 100)
    bar = "█" * (percent // 20) + "─" * (5 - percent // 20)
    total = users.count_documents({})
    if q.data == "mylink":
        await q.message.reply_text(f"🔗 Your Link:\n{get_ref_link(uid)}\n\nShare to {REQUIRED_REF} friends!", reply_markup=main_menu())
    elif q.data == "progress":
        if progress >= REQUIRED_REF:
            await q.message.reply_text(f"✅ UNLOCKED!\n{progress}/{REQUIRED_REF} [{bar}]\n🔥 {VIP_LINK}", reply_markup=main_menu())
        else:
            await q.message.reply_text(f"📊 Progress: {progress}/{REQUIRED_REF} ({percent}%) [{bar}]\nNeed {REQUIRED_REF-progress} more!\nLink: {get_ref_link(uid)}", reply_markup=main_menu())
    elif q.data == "stats":
        await q.message.reply_text(f"📊 Stats\nTotal: {total}\nYour ID: {uid}\nProgress: {progress}/{REQUIRED_REF}\nVIP: {VIP_LINK if progress>=REQUIRED_REF else 'Locked 🔒'}")

async def advertise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Use: /advertise YOUR MESSAGE")
        return
    c=0
    for u in users.find():
        try:
            await context.bot.send_message(u["user_id"], msg)
            c+=1
        except: pass
    await update.message.reply_text(f"Sent to {c} users!")

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    progress = get_progress(uid)
    if progress >= REQUIRED_REF:
        await update.message.reply_text(f"✅ VIP UNLOCKED!\n🔥 {VIP_LINK}", reply_markup=main_menu())
    else:
        await update.message.reply_text(f"🔒 VIP Locked\n📊 Progress: {progress}/{REQUIRED_REF}\n👉 Use /start for Menu\nYour Link: {get_ref_link(uid)}", reply_markup=main_menu())

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("advertise", advertise))
app.add_handler(CallbackQueryHandler(handle_buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))
print("Bot running PRO SECURE FIXED!")
app.run_polling()
