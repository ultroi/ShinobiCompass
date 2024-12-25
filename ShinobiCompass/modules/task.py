import pytz
from datetime import datetime
from telegram import Update
import telegram
import asyncio
from telegram.ext import CallbackContext
from ShinobiCompass.database import db
import re
import uuid

# Assuming tasks_collection is a collection in your database
tasks_collection = db['tasks_collection']

# Timezone setup
IST = pytz.timezone('Asia/Kolkata')

async def is_admin(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator']

async def generate_task_id(chat_id: int) -> str:
    return str(uuid.uuid4().int)[:5]


async def set_task(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can create tasks.")
        return

    try:
        args = context.args
        if len(args) < 2:
            raise ValueError("Insufficient arguments")

        # Combine all arguments into a single string for easier parsing
        command_input = ' '.join(args)

        # Use regex to extract starttime-endtime, description, and reward
        match = re.match(r"(\d{1,2}:\d{2}(?:am|pm)-\d{1,2}:\d{2}(?:am|pm))\s+(.+)\s+\((.+)\)", command_input, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid format. Use: /task starttime-endtime description (reward)")

        time_range, description, reward = match.groups()

        if '-' not in time_range:
            raise ValueError("Invalid time range format. Use starttime-endtime format.")
        start_time_str, end_time_str = time_range.split('-')

        now_ist = datetime.now(IST)
        current_date = now_ist.date()

        # Parse and localize start and end times
        start_time = IST.localize(datetime.combine(
            current_date,
            datetime.strptime(start_time_str, '%I:%M%p').time()
        ))
        end_time = IST.localize(datetime.combine(
            current_date,
            datetime.strptime(end_time_str, '%I:%M%p').time()
        ))

        # Ensure times are on the current day
        if start_time.date() != now_ist.date() or end_time.date() != now_ist.date():
            await update.message.reply_text(f"Start time and end time must be on the current day. Current time: {now_ist.strftime('%I:%M %p')}")
            return

        # Ensure times are in the future
        if start_time <= now_ist or end_time <= now_ist:
            await update.message.reply_text("Start time and end time must be in the future.")
            return

        # Ensure end time is later than start time
        if end_time <= start_time:
            await update.message.reply_text("End time must be later than start time.")
            return

        chat_id = update.effective_chat.id

        # Check if there is already an active task in the database for this chat
        existing_task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$gt": now_ist}})
        if existing_task:
            await update.message.reply_text("A task is already active for today. Please wait until the current task ends before creating a new one.")
            return

        # Unpin the previous task if any
        if existing_task:
            try:
                await context.bot.unpin_chat_message(chat_id, existing_task['message_id'])
            except telegram.error.BadRequest as e:
                print(f"Error while unpinning: {e}")

        # Ensure the reward is in a valid format (either gems, tokens, or coins/glory)
        reward_match = re.match(r"(\d+)\s*(gems|tokens|coins\/glory)", reward, re.IGNORECASE)
        if not reward_match:
            raise ValueError("Invalid reward format. Use ('2 gems', '3 tokens', '100 coins/glory')")

        reward_value, reward_type = reward_match.groups()

        # Generate a unique task ID
        task_id = await generate_task_id(chat_id)

        # Save task to the database
        task = {
            "task_id": task_id,
            "chat_id": chat_id,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "reward_value": int(reward_value),
            "reward_type": reward_type.lower(),
            "created_at": now_ist,
            "verified_users": []
        }
        tasks_collection.insert_one(task)

        # Determine the task message based on start time
        if start_time > now_ist:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"<b><u>❄️📝 Today's Task ❄️</u></b>\n"
                    f"<b>Task ID:</b> <code>{task_id}</code>\n\n"
                    f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
                    f"<b>Description:</b> <i>{description}</i>\n"
                    f"<b>Reward:</b> <i>{reward_value} {reward_type.lower()}</i>\n\n"
                    f"☃️ The task will begin shortly. Prepare yourself for the icy challenge ahead! ☃️"
                ),
                parse_mode=telegram.constants.ParseMode.HTML
            )
        else:
            message = await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"<b><u>📝 Today's Task</u></b>\n\n"
                    f"<b>Task ID:</b> <i>{task_id}</i>\n"
                    f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
                    f"<b>Description:</b> <i>{description}</i>\n"
                    f"<b>Reward:</b> <i>{reward_value} {reward_type.lower()}</i>\n\n"
                    f"<b>How to Participate:</b>\n"
                    f"1️⃣ <b>/finv</b> — Submit your starting inventory.\n"
                    f"2️⃣ <b>/linv</b> — Submit your last inventory.\n"
                    f"🌨️🕒 Make sure to submit your participation before the task expires in the frosty air!"
                ),
                parse_mode=telegram.constants.ParseMode.HTML
            )

        # Update the task with the message ID and pin it
        tasks_collection.update_one({"task_id": task_id}, {"$set": {"message_id": message.message_id}})
        await context.bot.pin_chat_message(chat_id, message.message_id)

        # Schedule task to edit the message after the start time
        delay = (start_time - now_ist).total_seconds()
        asyncio.create_task(edit_task_message(context, chat_id, message.message_id, task_id, start_time_str, end_time_str, description, reward_value, reward_type.lower(), delay))

        # Schedule task to delete task data and unpin message after 12 hours
        asyncio.create_task(delete_task_data(context, task, chat_id))
    except (IndexError, ValueError) as e:
        print(f"Error: {e}")
        await update.message.reply_text(
            "Usage: /task starttime-endtime description (reward)\n"
            "Example: /task 9:40pm-10:00pm Do 100 glory (19 coins/glory)"
        )

async def edit_task_message(context: CallbackContext, chat_id: int, message_id: int, task_id: int, start_time_str: str, end_time_str: str, description: str, reward_value: int, reward_type: str, delay: float):
    await asyncio.sleep(delay)
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"<b><u>❄️📝 Today's Task ❄️</u></b>\n"
            f"<b>Task ID:</b> <code>{task_id}</code>\n\n"
            f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
            f"<b>Description:</b> <i>{description}</i>\n"
            f"<b>Reward:</b> <i>{reward_value} {reward_type}</i>\n\n"
            f"<b>How to Participate:</b>\n"
            f"1️⃣ <b>/finv</b> — Submit your starting inventory.\n"
            f"2️⃣ <b>/linv</b> — Submit your last inventory.\n\n"
            f"🌨️🕒 Make sure to submit your participation before the task expires in the frosty air!"
        ),
        parse_mode=telegram.constants.ParseMode.HTML
    )

async def delete_task_data(context: CallbackContext, task: dict, chat_id: int):
    # Wait until the task end time
    now_ist = datetime.now(IST)
    delay = (task['end_time'] - now_ist).total_seconds()
    await asyncio.sleep(delay)

    # Show the leaderboard immediately after task ends
    await taskresult(chat_id, context)
    
    # Edit the task message to indicate that it has ended
    if 'message_id' in task:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=task['message_id'],
                text="❌ <b>Task Has Ended</b>\n\nThe task has ended. Check the leaderboard for results.",
                parse_mode=telegram.constants.ParseMode.HTML,
            )
        except telegram.error.BadRequest as e:
            print(f"Error while editing message: {e}")

        # Unpin the task message
        try:
            await context.bot.unpin_chat_message(chat_id, task['message_id'])
        except telegram.error.BadRequest as e:
            print(f"Error while unpinning: {e}")

    # Delete the task from the database
    tasks_collection.delete_one({"_id": task['_id']})


async def submit_inventory(update: Update, context: CallbackContext, inventory_type: str) -> None:
    context = context  # To avoid unused variable warning
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    now_ist = datetime.now(IST)
    message_text = update.message.text

    # Check if the command is used in a private message
    if update.effective_chat.type == 'private':
        # Ensure the message is a reply to the inventory message
        if not update.message.reply_to_message:
            await update.message.reply_text("Please reply to the inventory message.")
            return

        inventory_message = update.message.reply_to_message.text

        # Extract the unique task ID from the command
        match = re.match(r"/(finv|linv) (\S+)", message_text)
        if not match:
            await update.message.reply_text("Invalid command format. Use /finv unique_id or /linv unique_id.")
            return

        inventory_type, task_id = match.groups()

        # Find the task by unique ID
        task = tasks_collection.find_one({"task_id": task_id})
        if not task:
            await update.message.reply_text("Invalid task ID.")
            return

        # Ensure the user is part of the group chat
        try:
            member = await context.bot.get_chat_member(task['chat_id'], user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                await update.message.reply_text("You must be a member of the group chat to submit inventory.")
                return
        except telegram.error.BadRequest:
            await update.message.reply_text("You must be a member of the group chat to submit inventory.")
            return

        # Verify the message is forwarded from the authorized bot (by sender ID)
        if hasattr(update.message.reply_to_message, 'forward_from') and update.message.reply_to_message.forward_from.id != 5416991774:
            await update.message.reply_text("The inventory message must be forwarded from the authorized bot.")
            return

        # Extract user ID and My Glory
        id_match = re.search(r"ID:\s*(\d+)", inventory_message)
        if not id_match or int(id_match.group(1)) != user_id:
            await update.message.reply_text("The inventory message user ID does not match your Telegram ID.")
            return

        glory_match = re.search(r"My Glory:\s*(\d+)", inventory_message)
        if not glory_match:
            await update.message.reply_text("Invalid inventory message format. Ensure it contains 'My Glory:' followed by a number.")
            return
        my_glory = int(glory_match.group(1))

    else:
        # Ensure the message is a reply to the inventory message
        if not update.message.reply_to_message:
            await update.message.reply_text("Please reply to the inventory message.")
            return

        inventory_message = update.message.reply_to_message.text

        # Find an active task for the current chat
        task = tasks_collection.find_one({"chat_id": chat_id, "start_time": {"$lt": now_ist}, "end_time": {"$gt": now_ist}})
        if not task:
            await update.message.reply_text("No active task to submit inventory for.")
            return
        
        # Verify the message is from the authorized bot (by sender ID)
        if update.message.reply_to_message.from_user.id != 5416991774:
            await update.message.reply_text("The inventory message must be from the authorized bot.")
            return
        
        # Extract user ID and My Glory
        id_match = re.search(r"ID:\s*(\d+)", inventory_message)
        if not id_match or int(id_match.group(1)) != user_id:
            await update.message.reply_text("The inventory message user ID does not match your Telegram ID.")
            return

        # Check if the inventory message is recent (within 1 minute)
        if (now_ist - update.message.reply_to_message.date).total_seconds() > 60:
            await update.message.reply_text("The inventory message must be recent (within 1 minute).")
            return

        glory_match = re.search(r"My Glory:\s*(\d+)", inventory_message)
        if not glory_match:
            await update.message.reply_text("Invalid inventory message format. Ensure it contains 'My Glory:' followed by a number.")
            return
        my_glory = int(glory_match.group(1))

    # Submit starting or ending inventory
    if inventory_type == "finv":
        if f"finv_{user_id}" in task:
            await update.message.reply_text("Starting inventory has already been submitted.")
            return
        
        # Update the task with starting inventory
        result = tasks_collection.update_one(
            {"_id": task['_id']},
            {"$set": {f"finv_{user_id}": my_glory}}
        )
        
        # Check if the update was successful
        if result.modified_count == 1:
            await update.message.reply_text("Starting inventory submitted successfully.")
        else:
            await update.message.reply_text("Failed to submit starting inventory. Please try again.")
        return

    elif inventory_type == "linv":
        if f"linv_{user_id}" in task:
            await update.message.reply_text("Ending inventory has already been submitted.")
            return

        # Ensure starting inventory is submitted first
        if f"finv_{user_id}" not in task:
            await update.message.reply_text("You must submit the starting inventory first.")
            return
        
        # Update the task with ending inventory
        result = tasks_collection.update_one(
            {"_id": task['_id']},
            {"$set": {f"linv_{user_id}": my_glory}}
        )

        # Check if the update was successful
        if result.modified_count == 1:
            await update.message.reply_text("Ending inventory submitted successfully.")
        else:
            await update.message.reply_text("Failed to submit ending inventory. Please try again.")
        return

    else:
        await update.message.reply_text("Invalid inventory type. Use 'finv' for starting or 'linv' for ending inventory.")

# Show the leaderboard for the task
async def taskresult(chat_id: int, context: CallbackContext) -> None:
    task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$lt": datetime.now(IST)}})
    if not task:
        await context.bot.send_message(chat_id, "No completed task to show leaderboard for.")
        return

    leaderboard = []
    for key, value in task.items():
        if key.startswith("finv_"):
            user_id = int(key.split("_")[1])
            finv = value
            linv = task.get(f"linv_{user_id}")
            if linv is not None:
                leaderboard.append((user_id, linv - finv))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    # Extract reward from the task message
    reward_text = f"{task['reward_value']} {task['reward_type']}"
    if not reward_text:
        await context.bot.send_message(chat_id, "Task reward information is missing.")
        return
    
    # Extract the numerical value from the reward (e.g., '100 coins')
    reward_match = re.match(r"(\d+)\s*(gems|tokens|coins\/glory)", reward_text, re.IGNORECASE)
    if not reward_match:
        await context.bot.send_message(chat_id, "Invalid reward format.")
        return
    
    reward_value, reward_type = reward_match.groups()
    leaderboard_text = f"🏆 <b>Task Result ({reward_type})</b> 🏆\n\n"
    for user_id, glory_diff in leaderboard:
        user = await context.bot.get_chat_member(chat_id, user_id)
        reward_amount = int(reward_value) * glory_diff
        leaderboard_text += f"🔸 <a href='tg://user?id={user_id}'>{user.user.first_name}</a> <code>{user_id}</code> {reward_amount} {reward_type}\n\n"

    # Unpin the task message
    try:
        await context.bot.unpin_chat_message(chat_id, task['message_id'])
    except telegram.error.BadRequest as e:
        print(f"Error while unpinning: {e}")

    # Send and pin the leaderboard message
    message = await context.bot.send_message(chat_id, leaderboard_text, parse_mode=telegram.constants.ParseMode.HTML)
    await context.bot.pin_chat_message(chat_id, message.message_id)

async def clear_tasks(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can clear tasks.")
        return

    chat_id = update.effective_chat.id
    tasks_collection.delete_many({"chat_id": chat_id})
    await update.message.reply_text("All tasks have been cleared.")
    await context.bot.unpin_all_chat_messages(chat_id)


async def end_task(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can end tasks.")
        return

    chat_id = update.effective_chat.id
    task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$gt": datetime.now(IST)}})
    if not task:
        await update.message.reply_text("No active task to end.")
        return

    # Show leaderboard
    leaderboard = []
    for key, value in task.items():
        if key.startswith("finv_"):
            user_id = int(key.split("_")[1])
            finv = value
            linv = task.get(f"linv_{user_id}")
            if linv is not None:
                leaderboard.append((user_id, linv - finv))

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    reward_type = task['reward'].split()[-1]
    leaderboard_text = f"🏆 <b>Task Leaderboard ({reward_type})</b> 🏆\n\n"
    for user_id, glory_diff in leaderboard:
        user = await context.bot.get_chat_member(chat_id, user_id)
        reward_amount = int(task['reward'].split()[0]) * glory_diff
        leaderboard_text += f"👤 {user.user.first_name} (ID: {user_id}) - {reward_amount} {reward_type}\n"

    # Tag admins
    admins = await context.bot.get_chat_administrators(chat_id)
    admin_mentions = ' '.join([f"@{admin.user.username}" for admin in admins if admin.user.username])
    leaderboard_text += f"\n\nAdmins: {admin_mentions}"

    # Edit the task message to indicate that it has ended and show the leaderboard
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=task['message_id'],
        text=leaderboard_text,
        parse_mode=telegram.constants.ParseMode.HTML,
    )

async def cancel_task(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can cancel tasks.")
        return

    chat_id = update.effective_chat.id
    now_ist = datetime.now(IST)
    task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$gt": now_ist}})
    if not task:
        await update.message.reply_text("No active task to cancel.")
        return

    # Edit the task message to indicate that it has been canceled
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=task['message_id'],
        text="❌ <b>Task Has Been Canceled</b>\n\nThe task has been canceled by an admin.",
        parse_mode=telegram.constants.ParseMode.HTML,
    )

    # Delete the task from the database
    tasks_collection.delete_one({"_id": task['_id']})

    # Unpin the task message
    try:
        await context.bot.unpin_chat_message(chat_id, task['message_id'])
    except telegram.error.BadRequest as e:
        print(f"Error while unpinning: {e}")

    await update.message.reply_text("The task has been canceled successfully.")
    
