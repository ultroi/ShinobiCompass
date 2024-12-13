import logging
from datetime import datetime
from ShinobiCompass.modules.start import check_bot_rights
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
import telegram
from telegram.ext import ContextTypes, CallbackQueryHandler
from ShinobiCompass.database import db

# Helper function to check if a user is an admin
async def is_admin(update: Update) -> bool:
    if update.message.chat.type == "private":
        return True  # Allow private chat commands for now
    chat_admins = await update.message.chat.get_administrators()
    user_id = update.message.from_user.id
    return any(admin.user.id == user_id for admin in chat_admins)

# Command to set the task time and reward rule
async def settask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Check if the user is an admin
    if not await is_admin(update):
        await update.message.reply_text("\u2757 You must be an admin to use this command.")
        return

    if db.tasks.find_one({"active_task": True}):
        await update.message.reply_text(
            "\u2757 An active task already exists.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Replace Task", callback_data="replace_task")],
                [InlineKeyboardButton("Keep Current Task", callback_data="keep_task")]
            ])
        )
        return

    try:
        start_time, end_time = context.args[0], context.args[1]
        reward_rule = ' '.join(context.args[2:])

        start_datetime = datetime.strptime(start_time, '%I:%M%p')
        end_datetime = datetime.strptime(end_time, '%I:%M%p')

        current_time = datetime.now()
        if end_datetime <= start_datetime or start_datetime <= current_time:
            await update.message.reply_text("\u2757 Start time must be after the current time, and end time must be after the start time.")
            return

        group_id = context.args[3]  # Assuming group_id is passed as the fourth argument
        task_message = (
            f"\U0001F3AF <b>Today\'s Task</b>\n"
            f"<b>Time:</b> {start_time} - {end_time}\n"
            f"<b>Description:</b> {reward_rule}\n\n"
            f"<i>Submit your task by clicking the button below and forwarding your inventory in PM.</i>"
        )

        # Add a "Submit Task" button
        task_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("Submit Task", callback_data="submit_task")]
        ])

        sent_message = await context.bot.send_message(
            chat_id=group_id,
            text=task_message,
            reply_markup=task_buttons,
            parse_mode=telegram.constants.ParseMode.HTML
        )

        db.tasks.insert_one({
            'active_task': True,
            'start_time': start_time,
            'end_time': end_time,
            'reward_rule': reward_rule,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
            'pinned_message_id': sent_message.message_id,
            'group_id': group_id
        })

        try:
            await context.bot.pin_chat_message(chat_id=group_id, message_id=sent_message.message_id)
        except telegram.error.BadRequest as e:
            await update.message.reply_text(f"\u2757 Failed to pin task message in group {group_id}: {e}")

        await update.message.reply_text(f"\U0001F3AF Task Set! Start: {start_time} - End: {end_time} with reward: {reward_rule}.")
    except (IndexError, ValueError):
        await update.message.reply_text("\u2757 Invalid input. Please use the correct format: /settask [start_time] [end_time] [reward_rule] [group_id].")

# Function to handle task completion
async def check_and_complete_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    current_time = datetime.now()
    active_task = db.tasks.find_one({"active_task": True})

    if active_task and current_time >= active_task['end_datetime']:
        group_id = active_task['group_id']
        pinned_message_id = active_task.get('pinned_message_id')

        # Unpin the task message
        if pinned_message_id:
            try:
                await context.bot.unpin_chat_message(chat_id=group_id, message_id=pinned_message_id)
            except telegram.error.BadRequest as e:
                logging.error(f"Failed to unpin task message in group {group_id}: {e}")

        # Notify admins with collected data
        collected_data = "\n".join(["Sample data: finv/linv collected here"])  # Replace with actual data retrieval logic
        chat_admins = await context.bot.get_chat_administrators(chat_id=group_id)
        for admin in chat_admins:
            try:
                await context.bot.send_message(chat_id=admin.user.id, text=f"\U0001F4DD Task completed. Collected data:\n{collected_data}")
            except Exception as e:
                logging.error(f"Failed to send collected data to admin {admin.user.id}: {e}")

        # Mark task as completed
        db.tasks.update_one({"_id": active_task["_id"]}, {"$set": {"active_task": False}})

# Callback handler for task replacement options
async def task_replacement_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "replace_task":
        active_task = db.tasks.find_one({"active_task": True})
        if active_task:
            group_id = active_task['group_id']
            pinned_message_id = active_task.get('pinned_message_id')

            # Unpin the current task message
            if pinned_message_id:
                try:
                    await context.bot.unpin_chat_message(chat_id=group_id, message_id=pinned_message_id)
                except telegram.error.BadRequest as e:
                    logging.error(f"Failed to unpin task message in group {group_id}: {e}")

        db.tasks.delete_many({})
        await query.edit_message_text("\U0001F501 Previous task replaced. You can now set a new task.")
    elif query.data == "keep_task":
        await query.edit_message_text("\U0001F4DD Keeping the current task.")

# Handle task submissions
async def handle_task_submission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    active_task = db.tasks.find_one({"active_task": True})

    if not active_task:
        await query.answer("No active task to submit.", show_alert=True)
        return

    await query.answer()
    await context.bot.send_message(
        chat_id=user_id,
        text="\U0001F4E6 Please forward your inventory here to complete the task."
    )

# Add callback handler for "Submit Task" button
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query.data == "submit_task":
        await handle_task_submission(update, context)

# Dummy command for finv
async def finv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")

# Dummy command for linv
async def linv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")

# Dummy command for status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")

# Dummy command for schedule
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")

async def resettask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("This is command is under-construction 🚧.")
    
