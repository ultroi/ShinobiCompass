from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from ShinobiCompass.database import db
from ShinobiCompass.modules.sudo import is_owner_or_sudo
from ShinobiCompass.modules.saveinfo import save_info

# Reference to the new collection
collection = db.message_collector  

# Command for sudo users/owners to update the message
async def update_message(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    if context.args:
        new_message = " ".join(context.args)
    elif update.message.reply_to_message:
        new_message = update.message.reply_to_message.text
    else:
        await update.message.reply_text("⚠️ Please provide an update message or reply to a message.")
        return

    if new_message:
        # Update the document in the new collection
        collection.update_one({"_id": "update_message"}, {"$set": {"message": new_message}}, upsert=True)
        await update.message.reply_text(f"✅ Update message set to:\n\n<b>{new_message}</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("⚠️ The replied message is empty.")

# Command for sudo users/owners to clear the message
async def empty_update(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    if not await is_owner_or_sudo(update):
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Clear the update message
    collection.update_one({"_id": "update_message"}, {"$set": {"message": None}}, upsert=True)
    await update.message.reply_text("✅ Update message cleared.")

# Start command with updated message status
@save_info
async def start(update: Update, context: CallbackContext) -> None:
    # Check if update.message exists (in case of callback queries)
    if not update.message:
        return  # If there's no message object, exit the function early

    # Fetch the update message from the database
    update_message = collection.find_one({"_id": "update_message"})
    update_text = update_message["message"] if update_message and update_message["message"] else "❄️ No Updates Available. Stay cozy and check back later!"
    
    user = update.effective_user

    # Checking the update status
    if update_text == "❄️ No Updates Available. Stay cozy and check back later!":
        update_status = "🔴 Stay tuned for next update or upcoming updates"
    else:
        update_status = "🟠 Check Out"

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
        f"{update_status}\n\n"
        "❄️🎄Wishing you warmth, joy, and plenty of rewards this winter! 🎄❄️"
    )

    # Send the welcome message if update.message exists
    await update.message.reply_text(welcome_message, parse_mode="HTML", reply_markup=reply_markup)

# Updated help callback handler
async def help_callback_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data == "help_bm_commands":
        buttons = [
            [InlineKeyboardButton("Task Commands", callback_data="help_task_page_1")],
            [InlineKeyboardButton("Extra", callback_data="help_extra")],
        ]
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
            [InlineKeyboardButton("Back", callback_data="help_bm_commands")],
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

    elif query.data == "help_extra":
        buttons = [
            [InlineKeyboardButton("Back", callback_data="help_bm_commands")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        extra_help_text = (
            "👾<b>     Extra  </b>\n\n"
            "🔸 <b>/iseal</b> - Check info about sealing techniques.\n"
            "🔸 <b>/xp</b> - View how much exploration is left and the next level-up reward.\n"
        )
        await query.edit_message_text(extra_help_text, parse_mode="HTML", reply_markup=reply_markup)

# Updates Callback
async def show_updates_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    # Fetch the update message from the database
    update_message = collection.find_one({"_id": "update_message"})
    update_text = update_message["message"] if update_message and update_message["message"] else "❄️ No Updates Available. Stay cozy and check back later!"
    
    await query.edit_message_text(f"📣 <b>Updates:</b>\n\n{update_text}", parse_mode="HTML")

# Back to Main Menu Command
async def back_to_main(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()  # Always acknowledge the callback query
    
    user = update.effective_user
    await start(update, context)  # Show main menu again with the updated buttons
    
async def help_extra(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    buttons = [
        [InlineKeyboardButton("Back", callback_data="help_bm_commands")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    extra_help_text = (
        "🔸 <b>/iseal</b> - Check info about sealing techniques.\n"
        "🔸 <b>/xp</b> - View how much exploration is left and the next level-up reward.\n"
    )
    await query.edit_message_text(extra_help_text, parse_mode="HTML", reply_markup=reply_markup)
