from telegram import Update
from telegram.ext import CallbackContext, ContextTypes
from ShinobiCompass.database import db  # Adjusted database import
from ShinobiCompass.modules.sudo import is_owner_or_sudo
from functools import wraps
import logging
import re
from datetime import datetime, timedelta


logger = logging.getLogger(__name__)

CHANNEL_ID = -1002254557222  # Your channel ID for notifications

# Function to get sudo users collection
async def get_sudo_users_collection():
    if db is not None:
        return db["sudo_users"]
    else:
        logger.error("Database connection is not initialized.")
        return None

# Function to get users collection
async def get_users_collection():
    if db is not None:
        return db["users"]
    else:
        logger.error("Database connection is not initialized.")
        return None

# Function to check if the user is verified
# Function to check if the user is verified
async def is_verified(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    logger.info(f"Checking verification for user ID: {user_id}")

    # Get the users collection directly from db
    users_collection = await get_users_collection()
    if users_collection is None:
        logger.error("Unable to access 'users' collection.")
        return False

    # Check if the user exists and if verified
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data.get("verified", False):
        logger.info(f"User ID: {user_id} is verified.")
        return True

    logger.info(f"User ID: {user_id} is not verified.")
    return False


# This decorator checks if the user is verified. If not, it asks the user to verify.
def require_verification(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        # Check if the user is verified (using asyncio to run async DB operation)
        is_verified_user = await is_verified(update, context)

        # If the user is not verified, inform them they are not authorized to use the command
        if not is_verified_user:
            await update.message.reply_text(
                "⚠️ You are not authorized to use this command. Please verify your clan by replying to your inventory with /verify."
            )
            return

        # If the user is verified, proceed to the original function
        return await func(update, context, *args, **kwargs)

    return wrapper


# Function to verify the user
async def verify_user(update: Update, context: CallbackContext) -> None:
    """Verify user based on inventory message."""

    # Check if the user is already verified
    user = db.users.find_one({"id": update.effective_user.id})
    if user and user.get("verified", False):
        await update.message.reply_text(" You are already verified!✅")
        return
    
    # Check if the message is coming from a private message
    if update.message.chat.type != 'private':
        await update.message.reply_text(
            "⚠️ Verification only in a private message (PM) to me. I cannot verify users in group chats."
        )
        return

    # Check if the database connection is initialized
    if db is None:
        await update.message.reply_text("⚠️ Database connection is not initialized.")
        return

    # Check if the message is a reply to an inventory message
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to your inventory message.")
        return

    inventory_message = update.message.reply_to_message.text

    # Check if the forwarded message is from the required ID
    if update.message.reply_to_message.forward_from and update.message.reply_to_message.forward_from.id != 5416991774:
        await update.message.reply_text("⚠️ The forwarded inventory message must come from user ID 5416991774.")
        return

    # Check if the inventory message was sent within the last minute
        message_time = update.message.reply_to_message.date
        current_time = datetime.now()
        time_diff = current_time - message_time

        if time_diff > timedelta(minutes=1):
            await update.message.reply_text("⚠️ The inventory message is older than 1 minute. Please resend your inventory message.")
            return

    try:
        # Extract user ID from inventory message
        id_match = re.search(r"┣ 🆔 ID[:：]?\s*(\d+)", inventory_message)
        if not id_match or int(id_match.group(1)) != update.effective_user.id:
            await update.message.reply_text("⚠️ The inventory message user ID does not match your Telegram ID.")
            return

        # Extract other required fields
        name_match = re.search(r"┣ 👤 Name[:：]?\s*(.+)", inventory_message)
        level_match = re.search(r"┣ 🎚️ Level[:：]?\s*(\d+)", inventory_message)
        clan_match = re.search(r"🏯 Clan[:：]?\s*(.+)", inventory_message)

        # Check if all necessary fields are extracted
        if not name_match or not level_match or not clan_match:
            missing_fields = []
            if not name_match:
                missing_fields.append("Name")
            if not level_match:
                missing_fields.append("Level")
            if not clan_match:
                missing_fields.append("Clan")
            await update.message.reply_text(
                f"⚠️ Could not extract the following fields from the inventory message: {', '.join(missing_fields)}."
            )
            return

        # Extract values from regex matches
        name = name_match.group(1).strip()
        level = int(level_match.group(1))
        clan = clan_match.group(1).strip()

        # Get the current time
        current_time = datetime.now()

        # Check clan authorization
        clan_auth = db.clans.find_one({"name": clan, "authorized": True})
        is_owner = await is_owner_or_sudo(update)

        # Update the user's data in the database (ensure this is async if using Motor)
        db.users.update_one(
            {"id": update.effective_user.id},
            {
                "$set": {
                    "name": name,
                    "clan": clan,
                    "level": level,
                    "verified": is_owner or clan_auth is not None,
                    "joined_at": current_time.strftime('%Y-%m-%d %H:%M:%S')
                }
            },
            upsert=True,
        )

        # Retrieve user data from the database
        user = db.users.find_one({"id": update.effective_user.id})

        # Generate a well-formatted message
        user_link = f"tg://user?id={update.effective_user.id}"
        message = (
            f"<b>🌟 New User 🌟</b>\n\n"
            f"<b>👤 Name:</b> {user['name']}\n"
            f"<b>🆔 ID:</b> <code>{user['id']}</code>\n"
            f"<b>🏯 Clan:</b> {user['clan']}\n"
            f"<b>🔗 Link:</b> <a href='{user_link}'>User Profile</a>\n"
            f"<b>📅 Joined At:</b> {user['joined_at']}\n"
            f"✅ <b>Verified:</b> {'Yes' if user['verified'] else 'No'}"
        )

        # Send the message to the specified channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode="HTML"
        )

        # Notify the user about their verification status
        if is_owner or clan_auth is not None:
            await update.message.reply_text(
                f"✅ {name} (ID: {update.effective_user.id}) has been verified as part of the {clan} clan!"
            )
        else:
            await update.message.reply_text(
                f"⚠️ {name} (ID: {update.effective_user.id}) is not authorized to use this bot. Clan '{clan}' is not authorized."
            )

    except Exception as e:
        await update.message.reply_text(f"⚠️ An error occurred while verifying the user: {str(e)}")

# Function to authorize a user or clan
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Authorize a clan or verify a specific user."""
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("⚠️ Only owners or sudo users can perform this action.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a clan name or user ID.")
        return

    input_value = context.args[0]

    if input_value.isdigit():
        user_id = int(input_value)
        user = db.users.find_one({"id": user_id})
        if not user:
            await update.message.reply_text(f"⚠️ No user found with ID {user_id}.")
            return

        db.users.update_one({"id": user_id}, {"$set": {"verified": True}})
        await update.message.reply_text(f"✅ User [{user['name']}](tg://user?id={user_id}) (ID: {user_id}) has been verified.", parse_mode="Markdown")
    else:
        clan_name = input_value
        db.clans.update_one({"name": clan_name}, {"$set": {"authorized": True}}, upsert=True)
        await update.message.reply_text(f"✅ Clan '{clan_name}' has been authorized.")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display information about a user."""
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("⚠️ Only owners or sudo users can view user info.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a user ID.")
        return

    try:
        user_id = int(context.args[0])  # Convert argument to integer for user ID
        user = db.users.find_one({"id": user_id})  # Ensure this is async
        if not user:
            await update.message.reply_text(f"⚠️ No user found with ID {user_id}.")
            return

        # Build the user info message with HTML formatting
        user_info = (
            f"👤 <b>Name:</b> {user['name']}\n"
            f"🆔 <b>ID:</b> <code>{user['id']}</code>\n"
            f"🏯 <b>Clan:</b> {user['clan']}\n"
            f"🎚️ <b>Level:</b> {user['level']}\n"
            f"✅ <b>Verified:</b> {'Yes' if user['verified'] else 'No'}"
        )

        # Send the formatted user info back to the chat
        await update.message.reply_text(user_info, parse_mode="HTML")

    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID provided. Please ensure the ID is a number.")

