from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from ShinobiCompass.database import db  # Assuming db is already initialized to work with MongoDB

OWNER_ID = 5956598856  
SUDO_USERS_COLLECTION = "sudo_users"  # MongoDB collection for sudo users

# Helper function to check if the user is the owner
async def is_owner(update: Update) -> bool:
    return update.message.from_user.id == OWNER_ID  # Owner ID from variable

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

# Command to list all sudo users with their first name and user ID using HTML
async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the user is the owner
    if not await is_owner(update):
        await update.message.reply_text("<b>⚠ You must be the owner to use this command.</b>", parse_mode="HTML")
        return
    
    # Fetch all sudo users from the database (using the collection variable)
    sudo_users_cursor = db.sudo_users.find()
    
    if sudo_users.count_documents({}) == 0:
        await update.message.reply_text("<b>⚠ There are no sudo users.</b>", parse_mode="HTML")
        return

    # Prepare the user list with tagged user names
    user_list = "<b>List of Sudo Users:</b>\n"
    async for user in sudo_users:
        user_id = user['user_id']
        try:
            # Fetch user details using their user_id
            user_info = await context.bot.get_chat(user_id)  # Fetch user details from Telegram
            user_name = user_info.first_name  # Get the user's first name
            user_list += f"<b>{user_name}</b> - <a href='tg://user?id={user_id}'>@{user_name}</a> ({user_id})\n"
        except Exception as e:
            # If there is an issue fetching the user's details, display user ID with error
            user_list += f"<b>User ID:</b> {user_id} (Could not fetch details)\n"

    # Send the list of sudo users with embedded links
    await update.message.reply_text(user_list, parse_mode="HTML")
