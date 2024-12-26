from telegram import Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from functools import wraps
from ShinobiCompass.database import db
from datetime import datetime

# MongoDB collection to store user information
users_collection = db["users"]  # Collection to store user info
group_info_collection = db["groups"]  # Collection to store group info
CHANNEL_ID = -1002254557222  # Channel ID where you want to send the info

def save_info(func):
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        user_link = f"t.me/{username}" if username else "No username"
        current_time = datetime.utcnow()

        # Check if user info already exists in the database to prevent duplicates
        user_data = users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            # New user: save basic info to the database
            user_data = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "user_link": user_link,
                "joined_at": current_time,
                "has_started": False  # Track if user has started bot via PM
            }
            users_collection.insert_one(user_data)

            # Send user info to the channel with an embedded user link
            await context.bot.send_message(
                chat_id=CHANNEL_ID,
                text = f"""
                        <b>New User Info:</b>
                        <b>🆔 ID:</b> <code>{user_id}</code>
                        <b>👤 Name:</b> {first_name} @{username if username else 'No Username'}
                        <b>🔗 Link:</b> <a href="{user_link}">User Profile</a>
                        <b>📅 Joined At:</b> {current_time.strftime('%Y-%m-%d %H:%M:%S')}
                        """
            )

        # Check if the user has started the bot via PM
        if not user_data["has_started"]:
            # If the message is from a group (not private), ask the user to start the bot via PM
            if update.message.chat.type != 'private':  # The message is not from PM
                button = InlineKeyboardButton("Start Bot", url="t.me/ShinobiCompassBot")
                keyboard = InlineKeyboardMarkup([[button]])

                await update.message.reply_text(
                    "Please start the bot via PM for future updates. Click below to start:",
                    reply_markup=keyboard
                )
                return  # Stop further command execution until the user starts the bot via PM

            # User has directly started the bot in PM, update the has_started flag
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"has_started": True}}
            )

        # Proceed to the original function (command or message)
        await func(update, context)
        
    return wrapper
    

# Group Info Capture
def log_group_info(update: Update, context: CallbackContext):
    if update.message.chat.type in [Update.Chat.GROUP, Update.Chat.SUPERGROUP]:
        group_id = update.message.chat.id
        group_name = update.message.chat.title

        # Check if the group already exists in the database
        if not group_info_collection.find_one({"group_id": group_id}):
            # Save group info to database if it's not already stored
            group_data = {
                "group_id": group_id,
                "group_name": group_name,
                "joined_at": datetime.utcnow()
            }
            group_info_collection.insert_one(group_data)

            # Send group info to the channel
            context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"New Group Added:\nGroup Name: {group_name}\nGroup ID: {group_id}\n"
            )
        else:
            # Optional: Log that the bot is rejoined into an existing group
            context.bot.send_message(
                chat_id=CHANNEL_ID,
                text=f"Bot rejoined existing group:\nGroup Name: {group_name}\nGroup ID: {group_id}\n"
            )

# User removed from group info capture
def user_removed_from_group(update: Update, context: CallbackContext):
    if update.message.left_chat_member:
        user_id = update.message.left_chat_member.id
        username = update.message.left_chat_member.username
        first_name = update.message.left_chat_member.first_name
        user_link = f"t.me/{username}" if username else "No username"
        current_time = datetime.utcnow()

        # Send the removed user's info to the channel
        context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"User Removed:\nID: {user_id}\nName: {first_name} {username}\nLink: {user_link}\nRemoved At: {current_time}\n"
        )
