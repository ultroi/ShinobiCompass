from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ShinobiCompass.database import db  # Assuming db is already initialized to work with MongoDB

OWNER_ID = 5956598856  
SUDO_USERS_COLLECTION = "sudo_users"  # MongoDB collection for sudo users

# Helper function to check if the user is the owner
async def is_owner(update: Update) -> bool:
    return update.message.from_user.id == OWNER_ID  # Owner ID from variable

async def is_owner_or_sudo(update: Update) -> bool:
    user_id = update.message.from_user.id
    owner_id = 5956598856  # Define owner ID

    # Fetch sudo users as an async cursor
    sudo_users_cursor = db.sudo_users.find()

    # Loop through the cursor asynchronously
    async for sudo_user in sudo_users_cursor:
        if sudo_user['user_id'] == user_id or user_id == owner_id:
            return True

    return False

# Command to add a sudo user
async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await is_owner(update):
        await update.message.reply_text("<b>⚠ You must be the owner to use this command.</b>", parse_mode="HTML")
        return

    try:
        user_id = int(context.args[0])  # Get user ID from command argument
        user_info = await context.bot.get_chat(user_id)  # Get user details from Telegram
        user_name = user_info.first_name

        # Add user to the sudo users collection
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


# Assuming this is in your `sudolist` function where you fetch the sudo users from the database
async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user is authorized
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("<b>⚠ You must be the owner or a sudo user to use this command.</b>", parse_mode="HTML")
        return

    sudo_users_cursor = db.sudo_users.find()

    # Convert the Cursor to a list asynchronously
    sudo_users_list = await sudo_users_cursor.to_list(None)

    if not sudo_users_list:
        await update.message.reply_text("<b>⚠ No sudo users found.</b>", parse_mode="HTML")
        return

    sudo_users_message = "<b>List of Sudo Users:</b>\n"
    for user in sudo_users_list:  # Now using a regular for loop
        user_id = user['user_id']
        try:
            user_info = await context.bot.get_chat(user_id)  # Get user details from Telegram
            user_name = user_info.first_name
            sudo_users_message += f"<b>{user_name}</b> - <a href='tg://user?id={user_id}'>User Link</a> ({user_id})\n"
        except Exception:
            sudo_users_message += f"<b>User ID:</b> {user_id} (Could not fetch details)\n"

    await update.message.reply_text(sudo_users_message, parse_mode="HTML")
