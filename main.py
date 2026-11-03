import os
from pymongo import MongoClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, filters, ApplicationBuilder, CommandHandler, CallbackQueryHandler

BOT_TOKEN = os.getenv("9105634913:AAFxlV32_AGcA1_PZS0NFLZ1vCNo_WVBxlw")
MONGO_URI = os.getenv("mongodb+srv://urchworld:lawrence0814@urchworldcluster.vvkfgxp.mongodb.net/?retryWrites=true&w=majority&appName=UrchWorldCluster")
VIP_LINK = "https://t.me/+fVTpAYIqIhNiYjFk"
OFFICIAL = "https://t.me/protipsofficialchannel"
ADMIN_ID = 6652933614

client = MongoClient(MONGO_URI)
users = client["UrchWorldDB"]["users"]

async def start(update, context):
    uid = update.effective_user.id
    if not users.find_one({"user_id": uid}):
        users.insert_one({"user_id": uid, "name": update.effective_user.first_name})
    total = users.count_documents({})
    kb = [[InlineKeyboardButton("📢 Official", url=OFFICIAL)], [InlineKeyboardButton("🔥 VIP", url=VIP_LINK)], [InlineKeyboardButton("💰 Stats", callback_data="stats")]]
    await update.message.reply_text(f"Welcome {update.effective_user.first_name}!\n\n✅ Saved FOREVER!\n👥 Members: {total}", reply_markup=InlineKeyboardMarkup(kb))

async def stats_btn(update, context):
    await update.callback_query.answer()
    total = users.count_documents({})
    await update.callback_query.message.reply_text(f"Total: {total}\nYour ID: {update.callback_query.from_user.id}\nVIP: {VIP_LINK}")

async def advertise(update, context):
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

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("advertise", advertise))
app.add_handler(CallbackQueryHandler(stats_btn))
print("Bot running 24/7 FOREVER secure mode!")

async def handle_any_message(update, context):
    user_id = update.effective_user.id
    link = f"https://t.me/ProTipsVIPbot?start={user_id}"
    await update.message.reply_text(
        f"🔒 VIP Access Locked\n\n"
        f"Your Progress: 0/6 referrals\n"
        f"Requirement: 6 referrals to unlock\n\n"
        f"Your Link:\n{link}\n\n"
        f"Please continue sharing your referral link to gain access.\n\n"
        f"👉 Use the Menu button below or type /start"
    )

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_any_message))

app.run_polling()
