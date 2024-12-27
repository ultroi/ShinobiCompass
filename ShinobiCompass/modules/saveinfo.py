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
