from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext, ContextTypes
from ShinobiCompass.database import db  # Adjusted database import
from ShinobiCompass.modules.sudo import is_owner_or_sudo
from functools import wraps
import logging
import pytz
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
        # If the user is verified, check if their clan is authorized
        clan = user_data.get("clan")
        if clan is None:
            logger.info(f"User ID: {user_id} is verified, but has no clan specified.")
            return False  # If no clan is specified, return False

        # If clan is specified, check if it's authorized
        clan_auth = db.clans.find_one({"name": clan, "authorized": True})
        if clan_auth:
            logger.info(f"User ID: {user_id} is verified and part of an authorized clan.")
            return True
        else:
            # Provide specific feedback that the clan is not authorized
            logger.info(f"User ID: {user_id} is verified but their clan '{clan}' is not authorized.")
            return "You are not authorized!!"
    logger.info(f"User ID: {user_id} is not verified.")
    return False

# This decorator checks if the user is verified. If not, it asks the user to verify.
def require_verification(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        # Check if the user is verified (using asyncio to run async DB operation)
        is_verified_user = await is_verified(update, context)

        # If the user is not verified, inform them they are not authorized to use the command
        if is_verified_user == False:
            await update.message.reply_text(
                "⚠️ You are not authorized to use this command. Please verify your clan by replying to your inventory with /verify."
            )
            return

        # If the user is verified but the clan is not authorized, inform the user
        elif isinstance(is_verified_user, str) and is_verified_user == "You are not authorized!!":
            await update.message.reply_text(
                "⚠️ You are not authorized!!"
            )
            return

        # If the user is verified and the clan is authorized, proceed to the original function
        return await func(update, context, *args, **kwargs)

    return wrapper



# Default list of clans (initially unauthorized)
DEFAULT_CLANS = ["Uzumaki", "Namikaze", "Uchiha", "Otsutsuki"]

# Function to verify the user
async def verify_user(update: Update, context: CallbackContext) -> None:
    """Verify user based on inventory message."""
    # Initialize user ID early
    user_id = update.effective_user.id
    timezone = pytz.timezone('Asia/Kolkata')
    
    try:
        # Check if the message is private
        if update.message.chat.type != 'private':
            await update.message.reply_text(
                "⚠️ Verification only in a private message (PM) to me. I cannot verify users in group chats."
            )
            return

        # Check if the database is connected
        if db is None:
            await update.message.reply_text("⚠️ Database connection is not initialized.")
            return

        # Check for a reply to the inventory message
        if not update.message.reply_to_message:
            await update.message.reply_text("⚠️ Please reply to your inventory message.")
            return

        inventory_message = update.message.reply_to_message.text

        # Check the forwarded message source
        if update.message.reply_to_message.forward_from and update.message.reply_to_message.forward_from.id != 5416991774:
            await update.message.reply_text("⚠️ The forwarded inventory message must come from user ID 5416991774.")
            return

        # Time validation
        original_message_time = update.message.reply_to_message.date.replace(tzinfo=timezone)
        current_time = datetime.now(timezone)
        time_diff_seconds = (current_time - original_message_time).total_seconds()
        if time_diff_seconds > 60:
            await update.message.reply_text("⚠️ The inventory message must be recent (within 1 minute).")
            return

        # Extract user ID from the inventory message
        id_match = re.search(r"┣ 🆔 ID[:：]?\s*(\d+)", inventory_message)
        if not id_match or int(id_match.group(1)) != user_id:
            await update.message.reply_text("⚠️ The inventory message user ID does not match your Telegram ID.")
            return

        # Extract user details
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

        # Handle the case when clan is None (No clan specified)
        if not clan or clan.lower() == "none":
            clan = None

        # Check if the clan is authorized
        clan_auth = db.clans.find_one({"name": clan, "authorized": True}) if clan else None

        # Update the user's data in the database (ensure this is async if using Motor)
        db.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "name": name,
                    "clan": clan,
                    "level": level,
                    "verified": clan_auth is not None,
                    "joined_at": current_time.strftime('%Y-%m-%d %H:%M:%S')
                }
            },
            upsert=True,
        )

        # Notify the user about their verification status
        if clan_auth is not None:
            await update.message.reply_text(
                f"✅ {name} (ID: {user_id}) has been verified as part of the {clan} clan!"
            )
        else:
            await update.message.reply_text(
                f"⚠️ {name} (ID: {user_id}) is not authorized to use this bot. Clan '{clan}' is not authorized."
            )

        # Send the player's data to the channel
        user = {
            'name': name,
            'id': user_id,
            'clan': clan,
            'level': level,
            'verified': clan_auth is not None
        }

        channel_message = (
            f"🌟 New User 🌟\n"
            f"👤 <b>Name:</b> {user['name']}\n"
            f"🆔 <b>ID:</b> <code>{user['id']}</code>\n"
            f"🏯 <b>Clan:</b> {user['clan'] or 'None'}\n"
            f"🎚️ <b>Level:</b> {user['level']}\n"
            f"🔗 <b>Link:</b> <a href='tg://user?id={user['id']}'>User Profile</a>\n"
            f"📅 <b>Joined At:</b> {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"✅ <b>Verified:</b> {'Yes' if user['verified'] else 'No'}"
        )

        # Send the message to the channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,  # Replace with your actual channel ID
            text=channel_message,
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        logger.error(f"Verification error for user ID {user_id}: {str(e)}")
        await update.message.reply_text(f"⚠️ An error occurred while verifying the user: {str(e)}")




# Function to authorize a clan
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Authorize a clan."""
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("⚠️ Only owners or sudo users can perform this action.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a clan name to authorize.")
        return

    input_value = context.args[0].strip()

    # Check if the clan is in the default list
    if input_value in DEFAULT_CLANS:
        await update.message.reply_text(f"✅ Clan '{input_value}' is already authorized by default.")
        return

    db.clans.update_one({"name": input_value}, {"$set": {"authorized": True}}, upsert=True)
    await update.message.reply_text(f"✅ Clan '{input_value}' has been authorized.")


# Function to unauthorize a clan
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unauthorize a clan."""
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("⚠️ Only owners or sudo users can perform this action.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Please provide a clan name to unauthorize.")
        return

    input_value = context.args[0].strip()

    # Check if the clan is in the default list
    if input_value in DEFAULT_CLANS:
        await update.message.reply_text(f"⚠️ Clan '{input_value}' cannot be unauthenticated because it's a default authorized clan.")
        return

    db.clans.update_one({"name": input_value}, {"$set": {"authorized": False}})
    await update.message.reply_text(f"✅ Clan '{input_value}' has been unauthorized.")


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

