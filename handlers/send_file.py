# handlers/send_file.py

import asyncio
from configs import Config
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait
from handlers.database import db 

# সময় সুন্দর করে দেখানোর ফাংশন
def get_readable_time(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} Seconds"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} Minutes"
    hours, min = divmod(minutes, 60)
    return f"{hours} Hours"

# ---------------------------------------------
#           CAPTION COMMANDS (NEW)
# ---------------------------------------------

@Client.on_message(filters.command("set_caption") & filters.private & filters.user(Config.BOT_OWNER))
async def set_caption_command(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("❌ আপনি ক্যাপশন লিখেননি!\n\nউদাহরণ:\n/set_caption আপনার লেখা...")
    
    caption_text = message.text.split(None, 1)[1]
    await db.set_caption(caption_text)
    await message.reply_text(f"✅ **ক্যাপশন সেট করা হয়েছে!**\n\nএখন থেকে ফাইলের নিচে এটি দেখাবে।")

@Client.on_message(filters.command(["del_caption", "rm_caption"]) & filters.private & filters.user(Config.BOT_OWNER))
async def delete_caption_command(client: Client, message: Message):
    await db.set_caption(None)
    await message.reply_text("🗑️ **ক্যাপশন মুছে ফেলা হয়েছে!**")

@Client.on_message(filters.command("see_caption") & filters.private & filters.user(Config.BOT_OWNER))
async def see_caption_command(client: Client, message: Message):
    caption = await db.get_caption()
    if caption:
        await message.reply_text(f"📝 **বর্তমান ক্যাপশন:**\n\n{caption}")
    else:
        await message.reply_text("❌ কোনো কাস্টম ক্যাপশন সেট করা নেই।")

# ---------------------------------------------
#           FILE SENDING LOGIC
# ---------------------------------------------

async def reply_forward(message: Message, file_id: int):
    try:
        delete_time = await db.get_auto_delete_time()
        if delete_time == 0:
            return None
        readable_time = get_readable_time(delete_time)
        msg = await message.reply_text(
            f"⚠️ **Warning:** This file will be auto-deleted in **{readable_time}**. Forward/Save it now!",
            disable_web_page_preview=True,
            quote=True
        )
        return msg
    except FloodWait as e:
        await asyncio.sleep(e.x)
        await reply_forward(message, file_id)

async def media_forward(bot: Client, user_id: int, file_id: int):
    try:
        # ১. অরিজিনাল মেসেজ আনা
        original_msg = await bot.get_messages(chat_id=Config.DB_CHANNEL, message_ids=file_id)
        original_caption = original_msg.caption if original_msg.caption else ""
        
        # ২. কাস্টম ক্যাপশন আনা
        db_caption = await db.get_caption()
        
        # ৩. ক্যাপশন জোড়া লাগানো
        if db_caption:
            final_caption = f"{original_caption}\n\n{db_caption}"
        else:
            final_caption = original_caption

        # ৪. বাটন (প্রয়োজন মতো লিংক পাল্টান)
        buttons = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📢 Join Channel", url="https://t.me/+KqAP3RBBfx8xOWZl")]]
        )

        is_protected = await db.get_protect_content()

        if is_protected:
            return await bot.copy_message(
                chat_id=user_id, 
                from_chat_id=Config.DB_CHANNEL,
                message_id=file_id,
                caption=final_caption[:1024],
                reply_markup=buttons,
                protect_content=True
            )
        elif Config.FORWARD_AS_COPY is True:
            return await bot.copy_message(
                chat_id=user_id, 
                from_chat_id=Config.DB_CHANNEL,
                message_id=file_id,
                caption=final_caption[:1024],
                reply_markup=buttons
            )
        else:
            return await bot.forward_messages(
                chat_id=user_id, 
                from_chat_id=Config.DB_CHANNEL,
                message_ids=file_id
            )
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await media_forward(bot, user_id, file_id)
    except Exception as e:
        print(f"Error: {e}")
        pass

async def send_media_and_reply(bot: Client, user_id: int, file_id: int):
    sent_message = await media_forward(bot, user_id, file_id)
    if sent_message:
        warning_msg = await reply_forward(message=sent_message, file_id=file_id)
        delete_time = await db.get_auto_delete_time()
        if delete_time > 0:
            asyncio.create_task(delete_after_delay(sent_message, warning_msg, delete_time))

async def delete_after_delay(message, warning_msg, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
        if warning_msg:
            await warning_msg.delete()
    except Exception:
        pass
