from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from ShinobiCompass.database import db

# Command for sudo users/owners to update the message
async def update_message(update: Update, context: CallbackContext, OWNER_SUDO: list) -> None:
    user = update.effective_user
    if user.id in OWNER_SUDO:
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
    else:
        await update.message.reply_text("❌ You are not authorized to use this command.")

# Command to clear the update message
async def empty_update(update: Update, context: CallbackContext, OWNER_SUDO: list) -> None:
    user = update.effective_user
    if user.id in OWNER_SUDO:
        db.update_one({"_id": "update_message"}, {"$set": {"message": None}}, upsert=True)
        await update.message.reply_text("✅ Update message cleared.")
    else:
        await update.message.reply_text("❌ You are not authorized to use this command.")

# Start command
async def start(update: Update, context: CallbackContext) -> None:
    global UPDATE_MESSAGE
    user = update.effective_user
    # Use a default message if UPDATE_MESSAGE is None
    update_text = UPDATE_MESSAGE or "No Updates Available"
    
    buttons = [
        [InlineKeyboardButton("📖 Help", callback_data="help_bm_commands")],
        [InlineKeyboardButton("📣 Updates", callback_data="show_updates")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    welcome_message = (
        f"👋 <b>Welcome, {user.first_name}!</b>\n\n"
        "🤖 <b>This is your assistant bot for Naruto Game Bot!</b>\n"
        "I can help you analyze black market deals, manage tasks, and much more!\n\n"
        "⚡ <b>Features:</b>\n"
        "➡️ Black Market Analysis\n"
        "➡️ Task Management\n"
        "➡️ Inventory Tracking\n\n"
        "🔧 Use the <b>Help</b> button below to learn more about the available commands and features.\n\n"
        "📣 <b>Current Updates:</b>\n"
        f"{update_text}"
    )
    await update.message.reply_text(welcome_message, parse_mode="HTML", reply_markup=reply_markup)


# Callback query handler for help menu
async def help_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "help_bm_commands":
        # Black Market Analysis Commands
        buttons = [
            [InlineKeyboardButton("➡️ Task Commands", callback_data="help_task_page_1")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
            "📖 <b>Help: Black Market Analysis</b>\n\n"
            "🛠 <b>Commands:</b>\n"
            "1️⃣ <b>/bm</b> - Analyze a black market message by replying to it.\n"
            "2️⃣ Automatic detection of messages in group chats.\n\n"
            "⚙️ <b>Features:</b>\n"
            "- Analyze black market messages in real-time.\n"
            "- Identify profitable deals using pre-set pricing logic.\n"
            "- Generate detailed analysis reports directly in the chat.\n\n"
            "Use the <b>➡️ Task Commands</b> button to explore Task Management features."
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

    elif query.data == "help_task_page_1":
        # Task Management Commands (Page 1)
        buttons = [
            [InlineKeyboardButton("➡️ Page 2", callback_data="help_task_page_2")],
            [InlineKeyboardButton("⬅️ BM Commands", callback_data="help_bm_commands")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
            "📖 <b>Help: Task Management (Page 1)</b>\n\n"
            "🛠 <b>Admin Commands:</b>\n"
            "1️⃣ <b>/task starttime-endtime <i>task description</i> (reward)</b>\n"
            "   - Starts a new task for the current day with a unique name.\n"
            "   - Ensure the reward format: <code>'coins', 'tokens', 'gems', or 'glory'</code>.\n"
            "   - Valid only for tasks initiated on the same day.\n\n"
            "2️⃣ <b>/end_task</b>\n"
            "   - Ends the currently active task for the day.\n"
            "   - Tasks not ended manually will expire automatically at midnight IST.\n\n"
            "📌 <b>Details:</b>\n"
            "- Tasks are tied to the <b>current day</b> and expire at <b>midnight IST</b>.\n"
            "- Use meaningful task names to identify their purpose.\n\n"
            "Use <b>➡️ Page 2</b> to learn about inventory submission and reward calculations."
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

    elif query.data == "help_task_page_2":
        # Task Management Commands (Page 2)
        buttons = [
            [InlineKeyboardButton("⬅️ Page 1", callback_data="help_task_page_1")],
            [InlineKeyboardButton("⬅️ BM Commands", callback_data="help_bm_commands")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        help_text = (
            "📖 <b>Help: Task Management (Page 2)</b>\n\n"
            "🛠 <b>Inventory Submission:</b>\n"
            "3️⃣ <b>/finv task_id</b>\n"
            "   - Submit your <b>starting inventory</b>.\n"
            "   - Forward the inventory message from the Naruto bot in PM, then reply to the forwarded message.\n\n"
            "4️⃣ <b>/linv task_id</b>\n"
            "   - Submit your <b>ending inventory</b>.\n"
            "   - Follow the same process as above. Can be done in PM or group chats.\n\n"
            "🕒 <b>Time Validation:</b>\n"
            "- Tasks are valid for the <b>current day</b> only (12:00am to 11:59pm).\n"
            "- Both starting and ending inventories must be submitted within the same day/task time.\n\n"
            "📊 <b>Reward Calculation:</b>\n"
            "- Formula: <code>Reward = (linv - finv) * reward value</code>\n"
            "- Example:\n"
            "   <code>/task 9:00am-10:00pm Boost clan glory (2 gems/glory)</code>\n"
            "   Reward Value: 2 | Starting Inventory: 1000 glory (finv) | Ending Inventory: 1500 glory (linv)\n"
            "   <b>Reward: (1500 - 1000) * 2 = 1000</b>\n\n"
            "Use <b>⬅️ Page 1</b> for general task commands."
        )
        await query.edit_message_text(help_text, parse_mode="HTML", reply_markup=reply_markup)

# Callback query handler for Updates button
async def show_updates_callback(update: Update, context: CallbackContext) -> None:
    global UPDATE_MESSAGE
    query = update.callback_query
    await query.answer()
    update_text = UPDATE_MESSAGE if UPDATE_MESSAGE else "No Updates Available"
    await query.edit_message_text(f"📣 <b>Updates:</b>\n\n{update_text}", parse_mode="HTML")


