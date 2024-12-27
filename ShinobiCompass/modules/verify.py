from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from database import db  # Adjusted database import
from modules.sudo import is_owner_or_sudo
import logging
import re
from functools import wraps

logger = logging.getLogger(__name__)

CHANNEL_ID = -1002254557222  # Your channel ID for notifications

async def get_sudo_users_collection():
    if db:
        return db["sudo_users"]
    else:
        logger.error("Database connection is not initialized.")
        return None

async def is_verified(update: Update) -> bool:
    """Check if the user is verified in the database."""
    user_id = update.effective_user.id
    logger.info(f"Checking verification for user ID: {user_id}")

    if not db or "users" not in db.list_collection_names():
        logger.error("Database or 'users' collection is not initialized.")
        raise RuntimeError("Database connection or 'users' collection is not initialized.")
    
    try:
        user = await db.users.find_one({"id": user_id})
        logger.debug(f"Query result for user ID {user_id}: {user}")
        return user and user.get("verified", False)
    except Exception as e:
        logger.error(f"Error querying 'users' collection: {e}")
        raise

def require_verification(func):
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not await is_verified(update):
            await update.message.reply_text("⚠️ You need to verify your inventory first.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

async def verify_user(update: Update, context: CallbackContext) -> None:
    """Verify user based on inventory message."""
    if not db:
        await update.message.reply_text("⚠️ Database connection is not initialized.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Please reply to your inventory message.")
        return

    inventory_message = update.message.reply_to_message.text

    if update.message.reply_to_message.forward_from and update.message.reply_to_message.forward_from.id != 5416991774:
        await update.message.reply_text("⚠️ The forwarded inventory message must come from user ID 5416991774.")
        return

    id_match = re.search(r"ID[:：]?\s*(\d+)", inventory_message)
    if not id_match or int(id_match.group(1)) != update.effective_user.id:
        await update.message.reply_text("⚠️ The inventory message user ID does not match your Telegram ID.")
        return

    name_match = re.search(r"Name[:：]?\s*([\w\s\W]+)", inventory_message)
    level_match = re.search(r"Level[:：]?\s*(\d+)", inventory_message)
    clan_match = re.search(r"Clan[:：]?\s*([\w\s\W]+)", inventory_message)

    if not name_match or not level_match or not clan_match:
        missing_fields = []
        if not name_match:
            missing_fields.append("Name")
        if not level_match:
            missing_fields.append("Level")
        if not clan_match:
            missing_fields.append("Clan")
        await update.message.reply_text(f"⚠️ Could not extract the following fields from the inventory message: {', '.join(missing_fields)}.")
        return

    name = name_match.group(1).strip()
    level = int(level_match.group(1))
    clan = clan_match.group(1).strip()

    clan_auth = await db.clans.find_one({"name": clan, "authorized": True})
    is_owner = await is_owner_or_sudo(update)

    await db.users.update_one(
        {"id": update.effective_user.id},
        {
            "$set": {
                "name": name,
                "clan": clan,
                "level": level,
                "verified": is_owner or clan_auth is not None,
            }
        },
        upsert=True,
    )

    user = await db.users.find_one({"id": update.effective_user.id})

    message = (
        f"👤 <b>Name:</b> {user['name']}\n"
        f"🆔 <b>ID:</b> {user['id']}\n"
        f"🏯 <b>Clan:</b> {user['clan']}\n"
        f"🎚️ <b>Level:</b> {user['level']}\n"
        f"✅ <b>Verified:</b> {'Yes' if user['verified'] else 'No'}"
    )

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        parse_mode="HTML"
    )

    if is_owner or clan_auth is not None:
        await update.message.reply_text(f"✅ {name} (ID: {update.effective_user.id}) has been verified as part of the {clan} clan!")
    else:
        await update.message.reply_text(f"⚠️ {name} (ID: {update.effective_user.id}) is not authorized to use this bot. Clan '{clan}' is not authorized.")

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
        user = await db.users.find_one({"id": user_id})
        if not user:
            await update.message.reply_text(f"⚠️ No user found with ID {user_id}.")
            return

        await db.users.update_one({"id": user_id}, {"$set": {"verified": True}})
        await update.message.reply_text(f"✅ User [{user['name']}](tg://user?id={user_id}) (ID: {user_id}) has been verified.", parse_mode="Markdown")
    else:
        clan_name = input_value
        await db.clans.update_one({"name": clan_name}, {"$set": {"authorized": True}}, upsert=True)
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
        user_id = int(context.args[0])
        user = await db.users.find_one({"id": user_id})
        if not user:
            await update.message.reply_text("⚠️ No user found with the given ID.")
            return

        user_info = (
            f"👤 <b>Name:</b> {user['name']}\n"
            f"🆔 <b>ID:</b> {user['id']}\n"
            f"🏯 <b>Clan:</b> {user['clan']}\n"
            f"🎚️ <b>Level:</b> {user['level']}\n"
            f"✅ <b>Verified:</b> {'Yes' if user['verified'] else 'No'}"
        )
        await update.message.reply_text(user_info, parse_mode="HTML")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid user ID.")
