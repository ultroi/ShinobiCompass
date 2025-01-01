from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from ShinobiCompass.database import db  # Assuming db is already initialized to work with MongoDB
from ShinobiCompass.modules.sudo import is_owner_or_sudo

# Command to show stats: Total users and total groups with buttons
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the user is the owner or a sudo user
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("<b>⚠ You must be the owner or a sudo user to use this command.</b>", parse_mode="HTML")
        return

    # Get total counts for users and groups
    user_count = db.users.count_documents({})

    # Prepare the message with total users and groups
    message_text = f"<b>Total Users: {user_count}</b>\n<b>Total Groups: {group_count}</b>"

    # Create inline keyboard with buttons
    keyboard = [
        [InlineKeyboardButton("Users", callback_data="users")],
        [InlineKeyboardButton("Groups", callback_data="groups")]
    ]
    # Add an exit button if the command is triggered in a group chat
    if update.message.chat.type != 'private':
        keyboard.append([InlineKeyboardButton("Exit", callback_data="exit")])

    # Send the message with the keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message_text, parse_mode="HTML", reply_markup=reply_markup)

# Function to handle users and groups button presses
async def handle_stats_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the button press

    if query.data == "users":
        # Fetch all users from the database
        users_cursor = db.users.find()

        # Prepare user list
        user_list = "<b>List of Users:</b>\n"
        for user in users_cursor:  # Use regular `for` loop
            user_id = user['user_id']
            try:
                # Fetch user details using their user_id
                user_info = await context.bot.get_chat(user_id)  # Fetch user details from Telegram
                user_name = user_info.first_name  # Get the user's first name
                user_list += f"<b>{user_name}</b> - <a href='tg://user?id={user_id}'>@{user_name}</a> ({user_id})\n"
            except Exception as e:
                # Handle error if user details cannot be fetched
                user_list += f"<b>User ID:</b> {user_id} (Could not fetch details - {str(e)})\n"

        # Send the list of users
        await query.edit_message_text(user_list, parse_mode="HTML")

    elif query.data == "groups":
        # Fetch all groups from the database
        groups_cursor = db.groups.find()

        # Prepare group list
        group_list = "<b>List of Groups:</b>\n"
        for group in groups_cursor:  # Use regular `for` loop
            group_id = group['group_id']
            group_name = group.get('group_name', 'Unknown Group')  # Default to 'Unknown Group' if name is missing
            try:
                # Fetch group details using their group_id
                group_info = await context.bot.get_chat(group_id)  # Fetch group details from Telegram
                group_list += f"<b>{group_name}</b> - <a href='tg://chat?id={group_id}'>@{group_name}</a> ({group_id})\n"
            except Exception as e:
                # Handle error if group details cannot be fetched
                group_list += f"<b>Group ID:</b> {group_id} (Could not fetch details - {str(e)})\n"

        # Send the list of groups
        await query.edit_message_text(group_list, parse_mode="HTML")

    elif query.data == "exit":
        # Handle exit button: Edit message with exit text
        await query.edit_message_text("<b>Exited the stats interaction.</b>", parse_mode="HTML")

    elif query.data == "back":
        # Handle back button: Go back to the main stats view
        await stats(update, context)

