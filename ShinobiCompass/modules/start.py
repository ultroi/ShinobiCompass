from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from ShinobiCompass.database import db
from ShinobiCompass.modules.sudo import is_owner_or_sudo

# Command for sudo users/owners to update the message
async def update_message(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if not await is_owner_or_sudo(update):  # Check if the user is authorized
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if context.args:  # Check if arguments are provided
        new_message = " ".join(context.args)
    elif update.message.reply_to_message:  # Check if the command is used as a reply
        new_message = update.message.reply_to_message.text
    else:
        await update.message.reply_text("⚠️ Please provide an update message or reply to a message.")
        return

    if new_message:
        db.update_one({"_id": "update_message"}, {"$set": {"message": new_message}}, upsert=True)
        await update.message.reply_text(f"✅ Update message set to:\n\n<b>{new_message}</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ The replied message is empty.")

# Command to clear the update message
async def empty_update(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if not await is_owner_or_sudo(update):  # Check if the user is authorized
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    db.update_one({"_id": "update_message"}, {"$set": {"message": None}}, upsert=True)
    await update.message.reply_text("✅ Update message cleared.")


UPDATE_MESSAGE = None

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    global UPDATE_MESSAGE
    user = update.effective_user
    update_text = UPDATE_MESSAGE or "No Updates Available"
    
    buttons = [
        [InlineKeyboardButton("📖 Help", callback_data="help_bm_commands")],
        [InlineKeyboardButton("📣 Updates", callback_data="show_updates")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    welcome_message = (
    f"❄️<b>Welcome, {user.first_name}!</b>❄️\n\n"
    "⛄ <b>Your Assistant Bot for Naruto Game Bot is here to keep you warm this winter!</b>\n"
    "Let me help you analyze black market deals, manage tasks, and much more as the cold breeze rolls in!\n\n"
    "🌨️ <b>Winter Features:</b>\n"
    "🔥 Black Market Analysis\n"
    "🧣 Task Management\n"
    "🧤 Inventory Tracking\n\n"
    "☃️ <b>Current Updates:</b>\n"
    f"{update_text}\n\n"
    "❄️🎄Wishing you warmth, joy, and plenty of rewards this winter! 🎄❄️"
)
    await update.message.reply_text(welcome_message, parse_mode="HTML", reply_markup=reply_markup)

# Callback Query Handlers

async def help_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "help_bm_commands":
        buttons = [[InlineKeyboardButton("Task Commands", callback_data="help_task_page_1")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
            "❄️<b>Black Market Analysis</b>❄️\n\n"
            "🛠️ <b>Commands:</b>\n"
            "1️⃣ <b>/bm</b> - Analyze a black market message by replying to it.\n"
            "2️⃣ Automatic detection of messages in group chats.\n\n"
            "🌨️ <b>Features:</b>\n"
            "- Analyze black market messages in real-time.\n"
            "- Identify profitable deals using pre-set pricing logic.\n"
            "- Generate detailed analysis reports directly in the chat.\n\n"
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

    elif query.data == "help_task_page_1":
        buttons = [
            [InlineKeyboardButton("Inv Submission", callback_data="help_task_page_2")],
            [InlineKeyboardButton("Black Market", callback_data="help_bm_commands")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
    "❄️<b>Task Management</b>❄️\n\n"
    "🛠️ <b>Admin Commands (Only for Group):</b>\n\n"
    "• <b>/task starttime-endtime <i>task description</i> (reward)</b>\n"
    "  Create a new task for today with a specific name and reward format: <code>'coins', 'tokens', 'gems', or 'glory'</code>.\n\n"
    "• <b>Ensure Reward must be in bracket</b> e.g: (2 gems/glory)\n"
    "• <b>Ensure that the task command must be sent at least 1 minute before the task time</b>\n\n"
    "• <b>/endtask</b> Used to end the current active task for the day.\n"
    "• <b>/canceltask</b> Cancels the current active task before it ends.\n\n"
    "📅 <b>Details:</b>\n"
    "• Tasks expire at <b>midnight IST</b> Valid Time : 12:00am - 11:59pm.\n"
    "• Use meaningful task names to easily track the task.\n"
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

    elif query.data == "help_task_page_2":
        buttons = [
            [InlineKeyboardButton("Admin Task", callback_data="help_task_page_1")],
            [InlineKeyboardButton(" Back", callback_data="help_bm_commands")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
    "❄️<b>Task Management</b>❄️\n\n"
    "🛠️ <b>Inventory Submission:</b>\n\n"
    
    "<b>In Group Chat:</b>\n"
    "• <b>/finv</b>: To submit your starting inventory, reply to the latest inventory message and use the command.\n"
    "• <b>/linv</b>: To submit your last inventory, reply to the latest inventory message and use the command.\n\n"
    
    "<b>In Private Chat:</b>\n"
    "• <b>/finv <code>task_id</code></b>: To submit your starting inventory, copy the <b>task_id</b> from the task message and forward your starting inventory message from the Naruto bot. Then, use <code>/finv task_id</code>.\n"
    "• <b>/linv <code>task_id</code></b>: To submit your ending inventory, copy the <b>task_id</b> from the task message and forward your ending inventory message. Then, use <code>/linv task_id</code>.\n\n"
    
    "📊 <b>Reward Calculation:</b>\n"
    "• Formula: <code>(Ending Inventory - Starting Inventory) × Reward Value</code>\n\n"
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

# Updates Callback
async def show_updates_callback(update: Update, context: CallbackContext) -> None:
    global UPDATE_MESSAGE
    query = update.callback_query
    await query.answer()
    update_text = UPDATE_MESSAGE or "❄️ No Updates Available. Stay cozy and check back later!"
    await query.edit_message_text(f"📣 <b>Updates:</b>\n\n{update_text}", parse_mode="HTML")
