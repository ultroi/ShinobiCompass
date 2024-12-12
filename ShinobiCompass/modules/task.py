# Task Managment 
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    CallbackContext,
    filters,
)

# Command to set the task time and reward rule
async def settask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if not update.message.chat.type == "private":
        await update.message.reply_text("❗ This command can only be used in private chat by admins.")
        return

    if db.tasks.find_one({"active_task": True}):
        await update.message.reply_text(
            "❗ An active task already exists.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Replace Task", callback_data="replace_task")],
                [InlineKeyboardButton("Keep Current Task", callback_data="keep_task")]
            ])
        )
        return

    try:
        start_time = context.args[0]
        end_time = context.args[1]
        reward_rule = ' '.join(context.args[2:])

        start_datetime = datetime.strptime(start_time, '%I:%M%p')
        end_datetime = datetime.strptime(end_time, '%I:%M%p')

        if end_datetime <= start_datetime:
            await update.message.reply_text("❗ End time must be after start time.")
            return

        db.tasks.insert_one({
            'active_task': True,
            'start_time': start_time,
            'end_time': end_time,
            'reward_rule': reward_rule,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime
        })
        await update.message.reply_text(f"🎯 Task Set! Start: {start_time} - End: {end_time} with reward: {reward_rule}.")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Please use the correct format: /settask [start_time] [end_time] [reward_rule].")

# Command to reset the task
async def resettask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message.chat.type == "private":
        await update.message.reply_text("❗ This command can only be used in private chat by admins.")
        return

    db.tasks.delete_many({})
    db.inventory.delete_many({})
    await update.message.reply_text("🔄 Task Reset! All data cleared.")

# Command to submit the first inventory value
async def finv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if not db.tasks.find_one({"active_task": True}):
        await update.message.reply_text("❗ No active task available.")
        return

    if update.message.forward_from and update.message.forward_from.username == "Naruto_X_Boruto_Bot":
        try:
            forwarded_text = update.message.text
            if "My Glory:" in forwarded_text:
                glory_value = int(forwarded_text.split("My Glory:")[1].split()[0])
                db.inventory.update_one(
                    {'user_id': user_id},
                    {'$set': {'first_inventory': glory_value, 'finv_time': update.message.date}},
                    upsert=True
                )
                await update.message.reply_text(f"🗂️ First Inventory Recorded: {glory_value}.")
            else:
                await update.message.reply_text("❗ Unable to find 'My Glory' in the forwarded message.")
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("❗ An error occurred while processing the inventory.")
    else:
        await update.message.reply_text("❗ Forward a message only from @Naruto_X_Boruto_Bot.")

# Command to submit the last inventory value
async def linv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if not db.tasks.find_one({"active_task": True}):
        await update.message.reply_text("❗ No active task available.")
        return

    if update.message.forward_from and update.message.forward_from.username == "Naruto_X_Boruto_Bot":
        try:
            forwarded_text = update.message.text
            if "My Glory:" in forwarded_text:
                glory_value = int(forwarded_text.split("My Glory:")[1].split()[0])
                finv_time = db.inventory.find_one({'user_id': user_id}).get('finv_time')
                if not finv_time or update.message.date <= finv_time:
                    await update.message.reply_text("❗ The last inventory must be after the first inventory.")
                    return

                task = db.tasks.find_one({"active_task": True})
                if update.message.date >= task['end_datetime']:
                    await update.message.reply_text("❗ The last inventory must be before the task end time.")
                    return

                db.inventory.update_one(
                    {'user_id': user_id},
                    {'$set': {'last_inventory': glory_value}},
                    upsert=True
                )
                await update.message.reply_text(f"🗂️ Last Inventory Recorded: {glory_value}.")
            else:
                await update.message.reply_text("❗ Unable to find 'My Glory' in the forwarded message.")
        except Exception as e:
            logging.error(e)
            await update.message.reply_text("❗ An error occurred while processing the inventory.")
    else:
        await update.message.reply_text("❗ Forward a message only from @Naruto_X_Boruto_Bot.")

# Command to connect the bot with a user
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat.type != "group":
        await update.message.reply_text("❗ This command can only be used in a group.")
        return

    db.connected_users.update_one(
        {'user_id': update.message.from_user.id},
        {'$set': {'connected': True}},
        upsert=True
    )
    await update.message.reply_text("✅ You are now connected to the bot.")

# Command to check the user status
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    inventory = db.inventory.find_one({'user_id': user_id})
    if inventory:
        first_inventory = inventory.get('first_inventory', 'Not submitted')
        last_inventory = inventory.get('last_inventory', 'Not submitted')
        await update.message.reply_text(f"🏆 Your Status:\nFirst Inventory: {first_inventory}\nLast Inventory: {last_inventory}")
    else:
        await update.message.reply_text("❗ You haven't submitted any inventory yet.")

# Command to schedule a message in the group
async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        group_id = context.args[0]
        schedule_time = context.args[1]
        message = ' '.join(context.args[2:])

        schedule_datetime = datetime.strptime(schedule_time, '%Y-%m-%d %I:%M%p')

        if schedule_datetime <= datetime.now():
            await update.message.reply_text("❗ Scheduled time must be in the future.")
            return

        db.scheduled_messages.insert_one({
            'group_id': group_id,
            'time': schedule_datetime,
            'message': message
        })
        await update.message.reply_text(f"📅 Scheduled Message: {message} for Group ID: {group_id} at {schedule_time}.")
    except (IndexError, ValueError):
        await update.message.reply_text("❗ Please use the correct format: /schedule [group_id] [time] [message].")
