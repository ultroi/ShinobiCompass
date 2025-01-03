from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ShinobiCompass.database import db  # Assuming db is already initialized to work with MongoDB
import os

OWNER_ID = 5956598856
SUDO_USERS_COLLECTION = "sudo_users"

# Helper function to check if the user is the owner
async def is_owner(update: Update) -> bool:
    """Check if the user initiating the update is the owner."""
    if update.effective_user:  # Use `effective_user` for broader compatibility
        return update.effective_user.id == OWNER_ID
    return False

# Helper function to check if the user is the owner or a sudo user.
async def is_owner(update: Update) -> bool:
    """Check if the user initiating the update is the owner."""
    if update.effective_user:  # Use `effective_user` for broader compatibility
        return update.effective_user.id == OWNER_ID
    return False

# Helper function to check if the user is the owner or a sudo user
async def is_owner_or_sudo(update: Update) -> bool:
    """Check if the user is the owner or a sudo user."""
    if not update.effective_user:  # Ensure `effective_user` exists
        return False

    user_id = update.effective_user.id

    # Check if the user is the owner
    if user_id == OWNER_ID:
        return True

    # Check if the user is a sudo user by querying MongoDB
    sudo_user = db[SUDO_USERS_COLLECTION].find_one({"user_id": user_id})
    return bool(sudo_user)


# Command to add a sudo user
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_owner(update):
        await update.message.reply_text("<b>⚠ You must be the owner to use this command.</b>", parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])  # Get user ID from command argument
        user_info = await context.bot.get_chat(user_id)  # Get user details from Telegram
        user_name = user_info.first_name

        # Add user to the sudo users collection in MongoDB
        db[SUDO_USERS_COLLECTION].update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "first_name": user_name}},
            upsert=True  # If the user doesn't exist, it will be created
        )

        await update.message.reply_text(f"<b>{user_name} (ID: {user_id})</b> has been added to the sudo users list.", parse_mode="HTML")
    except (IndexError, ValueError):
        await update.message.reply_text("<b>⚠ Please provide a valid user ID.</b>", parse_mode="HTML")

# Command to remove a sudo user
async def removesudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_owner(update):
        await update.message.reply_text("<b>⚠ You must be the owner to use this command.</b>", parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])  # Get user ID from command argument

        # Remove user from the sudo users collection
        db[SUDO_USERS_COLLECTION].delete_one({"user_id": user_id})

        await update.message.reply_text(f"<b>User with ID: {user_id}</b> has been removed from the sudo users list.", parse_mode="HTML")
    except (IndexError, ValueError):
        await update.message.reply_text("<b>⚠ Please provide a valid user ID.</b>", parse_mode="HTML")


# Command to list all sudo users
# Command to list all sudo users
async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the user is authorized (owner or sudo user)
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("<b>⚠ You must be the owner or a sudo user to use this command.</b>", parse_mode="HTML")
        return

    # Fetch all sudo users from the collection
    sudo_users_cursor = db[SUDO_USERS_COLLECTION].find()

    # Prepare the message to list sudo users
    sudo_users_message = "<b>List of Sudo Users:</b>\n"

    # Loop through the cursor synchronously
    for user in sudo_users_cursor:
        user_id = user['user_id']
        try:
            user_info = await context.bot.get_chat(user_id)  # Get user details from Telegram
            user_name = user_info.first_name
            sudo_users_message += f"<b>{user_name}</b> - <a href='tg://user?id={user_id}'>User Link</a> ({user_id})\n"
        except Exception as e:
            sudo_users_message += f"<b>User ID:</b> {user_id} (Could not fetch details - {str(e)})\n"

    # Handle the case when no sudo users are found
    if sudo_users_message == "<b>List of Sudo Users:</b>\n":
        sudo_users_message = "<b>⚠ No sudo users found.</b>"

    await update.message.reply_text(sudo_users_message, parse_mode="HTML")
