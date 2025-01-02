import pytz
from datetime import datetime, timedelta
from telegram import Update
import telegram
import asyncio
from telegram.ext import CallbackContext
from ShinobiCompass.database import db
from ShinobiCompass.modules.verify import require_verification
from ShinobiCompass.modules.sudo import is_owner_or_sudo
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



# Helper to parse time
def parse_time(time_str):
    try:
        return datetime.strptime(time_str, "%I:%M%p").time()
    except ValueError:
        return None

# Set the task
async def set_task(update: Update, context: CallbackContext):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("This command can only be used in groups.")
        return

    user = update.effective_user
    admins = [admin.user.id for admin in await context.bot.get_chat_administrators(update.effective_chat.id)]
    if user.id not in admins:
        await update.message.reply_text("Only admins can set tasks.")
        return

    # Parse command arguments
    args = update.message.text.split(" ", 1)
    if len(args) < 2:
        await update.message.reply_text("Invalid format. Use /task starttime-endtime description (reward).")
        return

    try:
        task_info = args[1].strip()
        time_range, description_and_reward = task_info.split(" ", 1)
        start_time_str, end_time_str = time_range.split("-")
        description, reward = description_and_reward.strip().rsplit("(", 1)
        reward = reward.replace(")", "").strip()

        start_time = parse_time(start_time_str)
        end_time = parse_time(end_time_str)

        if not start_time or not end_time or not reward:
            raise ValueError

        now_ist = datetime.now(pytz.timezone("Asia/Kolkata"))

        # Convert start_time and end_time to datetime objects on the same day
        start_time = now_ist.replace(hour=start_time.hour, minute=start_time.minute, second=0, microsecond=0)
        end_time = now_ist.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)

        # Validate times
        if start_time <= now_ist:
            await update.message.reply_text("Start time must be in the future.")
            return
        if end_time <= start_time:
            await update.message.reply_text("End time must be after start time.")
            return

        chat_id = update.effective_chat.id

        # Check if there is already an active task in the database for this chat
        existing_task = task_collection().find_one({"chat_id": chat_id, "end_time": {"$gt": now_ist}})
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
            await update.message.reply_text("Invalid reward format. Use ('2 gems', '3 tokens', '100 coins/glory')")
            return

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
        task_collection().insert_one(task)

        # Determine the task message based on start time
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"<b><u>\ud83d\udcdd Today's Task</u></b>\n"
                f"<b>Task ID:</b> <code>{task_id}</code>\n\n"
                f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
                f"<b>Description:</b> <i>{description}</i>\n"
                f"<b>Reward:</b> <i>{reward_value} {reward_type.lower()}</i>\n\n"
                f"\u23f3 The task will begin shortly. Get ready!"
            ),
            parse_mode=telegram.constants.ParseMode.HTML
        )

        # Update the task with the message ID and pin it
        task_collection().update_one({"task_id": task_id}, {"$set": {"message_id": message.message_id}})
        await context.bot.pin_chat_message(chat_id, message.message_id)

        # Schedule task to edit the message after the start time
        delay = (start_time - now_ist).total_seconds()
        asyncio.create_task(task_message(context, chat_id, message.message_id, task_id, start_time_str, end_time_str, description, reward_value, reward_type.lower(), delay))

        # Schedule task to delete task data and unpin message after 12 hours
        asyncio.create_task(delete_task_data(context, task, chat_id))

    except (IndexError, ValueError) as e:
        print(f"Error: {e}")
        await update.message.reply_text(
            "Usage: /task starttime-endtime description (reward)\n"
            "Example: /task 9:40pm-10:00pm Do 100 glory (19 coins/glory)"
        )

    except Exception as e:
        print(f"Unexpected error: {e}")
        await update.message.reply_text("An unexpected error occurred. Please try again later.")



async def task_message(context: CallbackContext, chat_id: int, message_id: int, task_id: int, start_time_str: str, end_time_str: str, description: str, reward_value: int, reward_type: str, delay: float):
    await asyncio.sleep(delay)
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=(
            f"<b><u>📝 Today's Task</u></b>\n"
            f"<b>Task ID:</b><code>{task_id}</code>\n\n"
            f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
            f"<b>Description:</b> <i>{description}</i>\n"
            f"<b>Reward:</b> <i>{reward_value} {reward_type}</i>\n\n"
            f"<b>How to Participate:</b>\n"
            f"1️⃣ <b>/finv</b> — Submit your starting inventory.\n"
            f"2️⃣ <b>/linv</b> — Submit your last inventory.\n\n"
            f"🕒 Be sure to submit your participation before the task ends!"
        ),
        parse_mode=telegram.constants.ParseMode.HTML
    )

async def edit_task_message(
    context: CallbackContext,
    chat_id: int,
    message_id: int,
    task_id: int,
    start_time_str: str,
    end_time_str: str,
    description: str,
    reward_value: int,
    reward_type: str,
    pin=False
):
    # Prepare the message text
    task_message_text = (
        f"<b><u>🔴 Task Has Ended 🔴</u></b>\n\n"
        "Thank you for your participation 🙏\n\n"
    )

    # Edit the task message
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=message_id,
        text=task_message_text,
        parse_mode=telegram.constants.ParseMode.HTML
    )

    # Pin the task message if required
    if pin:
        try:
            await context.bot.pin_chat_message(chat_id, message_id=message_id)
        except telegram.error.BadRequest as e:
            print(f"Error while pinning the message: {e}")


async def delete_task_data(context: CallbackContext, task: dict, chat_id: int):
    now_ist = datetime.now(IST)
    task_end_time = task['end_time']
    delay = (task_end_time - now_ist).total_seconds()

    # Wait for the task duration
    if delay > 0:
        await asyncio.sleep(delay)

    # Try to generate and pin the leaderboard
    leaderboard_message_id = None
    try:
        leaderboard_message_id = await taskresult(chat_id, context)
    except Exception as e:
        print(f"Error generating leaderboard: {e}")

    # Unpin the previous task message if it exists
    if 'message_id' in task:
        try:
            await context.bot.unpin_chat_message(chat_id, task['message_id'])
        except telegram.error.BadRequest as e:
            print(f"Error while unpinning task message: {e}")

    # Update the task message to indicate it has ended
    if 'message_id' in task:
        pin_task_message = leaderboard_message_id is None  # Pin task message if no leaderboard exists
        await edit_task_message(
            context,
            chat_id=chat_id,
            message_id=task['message_id'],
            task_id=task['task_id'],
            start_time_str=task['start_time_str'],
            end_time_str=task['end_time_str'],
            description=task['description'],
            reward_value=task['reward_value'],
            reward_type=task['reward_type'],
            pin=pin_task_message
        )

    # Delete the task from the database
    tasks_collection.delete_one({"_id": task['_id']})

    # Pin the leaderboard message if it exists
    if leaderboard_message_id:
        try:
            await context.bot.pin_chat_message(chat_id, leaderboard_message_id)
        except telegram.error.BadRequest as e:
            print(f"Error while pinning leaderboard: {e}")

    

@require_verification
async def submit_inventory(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    now_ist = datetime.now(IST)  # Timezone-aware current time
    message_text = update.message.text.strip()

    # Check if the command is properly formatted
    if not message_text.startswith('/finv') and not message_text.startswith('/linv'):
        await update.message.reply_text("Invalid Format: Use /finv(reply to inventory message) for startin g inventory or /linv for ending inventory.")
        return

    # Extract inventory type and task ID (if provided)
    parts = message_text.split()
    if len(parts) > 1:
        inventory_type = parts[0][1:]  # 'finv' or 'linv'
        task_id = parts[1]
    else:
        inventory_type = parts[0][1:]
        task_id = None

    # Handle PM (Private Message)
    if update.effective_chat.type == 'private':
        if not task_id:
            await update.message.reply_text("Please provide a task ID after the command. Example: /finv 12345")
            return

        # Find the task by task_id in PM
        task = tasks_collection.find_one({"task_id": task_id})
        if not task:
            await update.message.reply_text("Invalid task ID. \n Use /finv task_id || /linv task_id \n Task id is given in Task message in the group !!")
            return

        # Ensure the message is a reply to the inventory message
        if not update.message.reply_to_message:
            await update.message.reply_text("Please reply to the inventory message.")
            return

        inventory_message = update.message.reply_to_message.text

        # Ensure the message is forwarded from the authorized bot
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
        # Handle Group Chat
        if not update.message.reply_to_message:
            await update.message.reply_text("Please reply to the inventory message.")
            return

        inventory_message = update.message.reply_to_message.text

        # Find an active task for the current chat
        task = tasks_collection.find_one({"chat_id": chat_id, "start_time": {"$lt": now_ist}, "end_time": {"$gt": now_ist}})
        if not task:
            await update.message.reply_text("No active task to submit inventory for.")
            return

        # Safely access task start_time after checking the task
        task_start_time = task.get('start_time')
        if not task_start_time:
            await update.message.reply_text("Task does not have a valid start time.")
            return

        # Convert task start time to be aware if it's naive
        if task_start_time.tzinfo is None:
            task_start_time = IST.localize(task_start_time)

        # Compare times: now_ist should be aware, task_start_time is aware
        if now_ist < task_start_time:
            await update.message.reply_text("The event has not started yet. Please wait until the start time.")
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
            await update.message.reply_text("⚠️Starting inventory has already been submitted.⚠️")
            return
        
        # Update the task with starting inventory
        result = tasks_collection.update_one(
            {"_id": task['_id']},
            {"$set": {f"finv_{user_id}": my_glory}}
        )

        if result.modified_count == 1:
            await update.message.reply_text("Starting inventory submitted successfully.")
        else:
            await update.message.reply_text("Failed to submit starting inventory. Please try again.")
        return

    elif inventory_type == "linv":
        if f"linv_{user_id}" in task:
            await update.message.reply_text("⚠️Ending inventory has already been submitted.⚠️")
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

        if result.modified_count == 1:
            starting_inventory = task.get(f"finv_{user_id}")
            ending_inventory = my_glory
            delta = ending_inventory - starting_inventory

            # Send a message in the user's PM with the results
            await context.bot.send_message(
                user_id,
                text=(
                    f"<u>📊 Here is your inventory report:</u>\n\n"
                    f"<b>💎 Starting Inv:</b> {starting_inventory}\n"
                    f"<b>💎 Ending Inv:</b> {ending_inventory}\n"
                    f"<b>🔼 Total Grind:</b> {delta}\n\n"
                    f"<i>🙏 Thank you for participating! Please wait for the Task Result to check your reward.</i>"
                ),
                parse_mode=telegram.constants.ParseMode.HTML,
            )



            await update.message.reply_text("Ending inventory submitted successfully.")
        else:
            await update.message.reply_text("Failed to submit ending inventory. Please try again.")
        return

    else:
        await update.message.reply_text("Invalid inventory type. Use 'finv' for starting or 'linv' for ending inventory.")


async def taskresult(chat_id: int, context: CallbackContext) -> int | None:
    task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$lt": datetime.now(IST)}})
    if not task:
        await context.bot.send_message(chat_id, "No completed task to show leaderboard for.")
        return None

    leaderboard = []
    for key, value in task.items():
        if key.startswith("finv_"):
            user_id = int(key.split("_")[1])
            finv = value
            linv = task.get(f"linv_{user_id}")
            if linv is not None:
                leaderboard.append((user_id, linv - finv))

    if not leaderboard:
        await context.bot.send_message(chat_id, "No users participated in the event.")
        return None

    leaderboard.sort(key=lambda x: x[1], reverse=True)

    # Extract reward from the task
    reward_value = task.get('reward_value')
    reward_type = task.get('reward_type')
    if not reward_value or not reward_type:
        await context.bot.send_message(chat_id, "Task reward information is missing.")
        return None

    leaderboard_text = f"🏆 <b>Task Result (Reward: {reward_value} {reward_type})</b> 🏆\n\n"
    for user_id, glory_diff in leaderboard:
        user = await context.bot.get_chat_member(chat_id, user_id)
        reward_amount = int(reward_value) * glory_diff
        leaderboard_text += f"🔸 <a href='tg://user?id={user_id}'>{user.user.first_name}</a> || <code>{user_id}</code> || <code>{reward_amount}</code> {reward_type}\n\n"

    # Unpin the task message
    try:
        await context.bot.unpin_chat_message(chat_id, task['message_id'])
    except telegram.error.BadRequest as e:
        print(f"Error while unpinning: {e}")

    # Send and pin the leaderboard message
    message = await context.bot.send_message(chat_id, leaderboard_text, parse_mode=telegram.constants.ParseMode.HTML)
    await context.bot.pin_chat_message(chat_id, message.message_id)

    return message.message_id



# to clear and unpin all task 
async def clear_tasks(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can clear tasks.")
        return

    chat_id = update.effective_chat.id
    tasks_collection.delete_many({"chat_id": chat_id})
    await update.message.reply_text("All tasks have been cleared.")
    await context.bot.unpin_all_chat_messages(chat_id)


@require_verification
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

    # Notify users who have submitted their inventories
    for key in task.keys():
        if key.startswith("finv_"):
            user_id = int(key.split("_")[1])
            linv_submitted = f"linv_{user_id}" in task

            # Craft the message based on their submission status
            if linv_submitted:
                message = "The task has been canceled. You have submitted both your starting and ending inventories."
            else:
                message = "The task has been canceled. You have submitted your starting inventory, but not the final inventory."

            # Send the notification in the user's private chat
            try:
                await context.bot.send_message(user_id, message)
            except Exception as e:
                print(f"Failed to notify user {user_id}: {e}")

    await update.message.reply_text("The task has been canceled successfully, and users have been notified.")



@require_verification
async def check_current_tasks(update: Update, context: CallbackContext) -> None:
    # Check if the user is a sudo or owner
    if not await is_owner_or_sudo(update):  # Pass the Update object
        await update.message.reply_text("None")
        return

    # Fetch all active tasks from the database
    now_ist = datetime.now(IST)
    tasks = list(tasks_collection.find({"end_time": {"$gt": now_ist}}))

    # If no active tasks exist
    if not tasks:
        await update.message.reply_text("No active tasks available.")
        return

    # Prepare an interactive response message
    response = "<b>🔸 Active Tasks 🔸</b>\n\n"
    for task in tasks:
        task_id = task.get("task_id", "Unknown")
        task_message = task.get("description", "No Description")
        start_time = task.get("start_time_str", "Unknown")
        end_time = task.get("end_time_str", "Unknown")
        group_id = task.get("chat_id", "Unknown")
        group_name = (await context.bot.get_chat(group_id)).title if group_id != "Unknown" else "Unknown"

        response += (
            f"┏━━━━━━━━━━━━━━━━\n"
            f"┣ <b>Task ID:</b> {task_id}\n"
            f"┣ <b>Task Message:</b> {task_message}\n"
            f"┣ <b>Start Time:</b> {start_time}\n"
            f"┣ <b>End Time:</b> {end_time}\n"
            f"┣ <b>Group Name:</b> {group_name}\n"
            f"┣ <b>Group ID:</b> <code>{group_id}</code>\n"
            f"━━━━━━━━━━━━━━━━\n\n"
        )

    # Send the interactive task list
    await update.message.reply_text(
        response,
        parse_mode=telegram.constants.ParseMode.HTML,
        disable_web_page_preview=True
    )






