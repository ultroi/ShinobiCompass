import pytz
from datetime import datetime
from telegram import Update
import telegram
import asyncio
from telegram.ext import CallbackContext
from database import db

# Assuming tasks_collection is a collection in your database
tasks_collection = db['tasks_collection']
BOT_ID = "5416991774"

# Timezone setup
IST = pytz.timezone('Asia/Kolkata')

async def is_admin(update: Update, context: CallbackContext) -> bool:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ['administrator', 'creator']

async def set_task(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can create tasks.")
        return

    try:
        args = context.args
        if len(args) < 3:
            raise ValueError("Insufficient arguments")

        # Parse command arguments
        time_range, description, reward = args[0], ' '.join(args[1:-1]), args[-1]
        start_time_str, end_time_str = time_range.split('-')
        now_ist = datetime.now(IST)

        # Add the current date to the parsed times
        current_date = now_ist.date()
        start_time = IST.localize(datetime.combine(
            current_date,
            datetime.strptime(start_time_str, '%I:%M%p').time()
        ))
        end_time = IST.localize(datetime.combine(
            current_date,
            datetime.strptime(end_time_str, '%I:%M%p').time()
        ))

        # Debugging logs
        print(f"now_ist: {now_ist}, start_time: {start_time}, end_time: {end_time}")

        # Ensure times are on the current day
        if start_time.date() != now_ist.date() or end_time.date() != now_ist.date():
            await update.message.reply_text("Start time and end time must be on the current day.")
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

        # Unpin the previous task if any
        existing_task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$gt": now_ist}})
        if existing_task:
            try:
                await context.bot.unpin_chat_message(chat_id, existing_task['message_id'])
            except telegram.error.BadRequest as e:
                print(f"Error while unpinning: {e}")

        # Proceed to save the task
        existing_task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$gt": now_ist}})
        if existing_task:
            await update.message.reply_text("There is already an ongoing task in this group.")
            return

        # Save task to the database
        task = {
            "chat_id": chat_id,
            "start_time": start_time,
            "end_time": end_time,
            "description": description,
            "reward": reward,
            "created_at": now_ist,
            "verified_users": []
        }
        result = tasks_collection.insert_one(task)
        task_id = result.inserted_id

        # Send task details and pin the message
        if start_time > now_ist:
            if start_time > now_ist:
                message = await update.message.reply_html(
                    f"📝 <b>Today’s Task!</b>\n\n"
                    f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
                    f"<b>Description:</b> <i>{description}</i>\n"
                    f"<b>Reward:</b> <i>{reward}</i>\n\n"
                    f"Your Task will begin soon."
                )
            else:
                message = await update.message.reply_html(
                    f"📝 <b>Today’s Task!</b>\n\n"
                    f"<b>Task Time:</b> <i>{start_time_str} - {end_time_str}</i>\n\n"
                    f"<b>Description:</b> <i>{description}</i>\n"
                    f"<b>Reward:</b> <i>{reward}</i>\n\n"
                    f"To submit your participation, use /finv to submit the starting inventory and /linv to submit the last inventory."
                )
        tasks_collection.update_one({"_id": task_id}, {"$set": {"message_id": message.message_id}})
        await context.bot.pin_chat_message(chat_id, message.message_id)

    except (IndexError, ValueError) as e:
        print(f"Error: {e}")
        await update.message.reply_text(
            "Usage: /task starttime-endtime description reward\n"
            "Example: /task 9:40pm-10:00pm Do 100 glory (19)"
        )

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

    leaderboard_text = "🏆 <b>Task Leaderboard</b> 🏆\n\n"
    for user_id, glory_diff in leaderboard:
        user = await context.bot.get_chat_member(chat_id, user_id)
        leaderboard_text += f"👤 {user.user.first_name} (ID: {user_id}) - {glory_diff} Glory\n"

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

    # Schedule task to delete task data and unpin message after 12 hours
    async def delete_task_data():
        await asyncio.sleep(12 * 60 * 60)  # 12 hours
        tasks_collection.delete_one({"_id": task['_id']})
        try:
            await context.bot.unpin_chat_message(chat_id, task['message_id'])
        except telegram.error.BadRequest as e:
            print(f"Error while unpinning: {e}")

    asyncio.create_task(delete_task_data())

async def clear_tasks(update: Update, context: CallbackContext) -> None:
    if not await is_admin(update, context):
        await update.message.reply_text("Only admins can clear tasks.")
        return

    chat_id = update.effective_chat.id
    tasks_collection.delete_many({"chat_id": chat_id})
    await update.message.reply_text("All tasks have been cleared.")
    await context.bot.unpin_all_chat_messages(chat_id)

async def submit_inventory(update: Update, context: CallbackContext, inventory_type: str) -> None:
    context = context  # To avoid unused variable warning
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to the inventory message.")
        return

    inventory_message = update.message.reply_to_message.text
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    now_ist = datetime.now(IST)

    # Find an active task for the current chat
    task = tasks_collection.find_one({"chat_id": chat_id, "start_time": {"$lt": now_ist}, "end_time": {"$gt": now_ist}})
    if not task:
        # Check if there is a pinned task that hasn't started yet
        upcoming_task = tasks_collection.find_one({"chat_id": chat_id, "start_time": {"$gt": now_ist}})
        if upcoming_task:
            upcoming_start_time = IST.localize(upcoming_task['start_time'])
            time_remaining = str(upcoming_start_time - now_ist).split(".")[0]
            await update.message.reply_text(f"No active task. The next task starts in {time_remaining}.")
            return
        else:
            await update.message.reply_text("No active task to submit inventory for.")
        return

    # Check if the inventory message is recent (within 1 minute)
    if (now_ist - update.message.reply_to_message.date).total_seconds() > 60:
        await update.message.reply_text("The inventory message must be recent (within 1 minute).")
        return

    # Verify the message is from the authorized bot (by sender ID)
    if update.message.reply_to_message.from_user.id != 5416991774:
        await update.message.reply_text("The inventory message must be from the authorized bot.")
        return

    # Extract user ID and My Glory
    import re
    id_match = re.search(r"ID:\s*(\d+)", inventory_message)
    if not id_match or int(id_match.group(1)) != user_id:
        await update.message.reply_text("The inventory message user ID does not match your Telegram ID.")
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
        tasks_collection.update_one(
            {"_id": task['_id']},
            {"$set": {f"finv_{user_id}": my_glory}}
        )
        await update.message.reply_text("Starting inventory submitted successfully.")
    elif inventory_type == "linv":
        if f"linv_{user_id}" in task:
            await update.message.reply_text("Ending inventory has already been submitted.")
            return
        if f"finv_{user_id}" not in task:
            await update.message.reply_text("You must submit the starting inventory first.")
            return
        tasks_collection.update_one(
            {"_id": task['_id']},
            {"$set": {f"linv_{user_id}": my_glory}}
        )
        await update.message.reply_text("Ending inventory submitted successfully.")
    else:
        await update.message.reply_text("Invalid inventory type. Use 'finv' for starting or 'linv' for ending inventory.")

async def show_leaderboard(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    task = tasks_collection.find_one({"chat_id": chat_id, "end_time": {"$lt": datetime.now(IST)}})
    if not task:
        await update.message.reply_text("No completed task to show leaderboard for.")
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

    leaderboard_text = "🏆 <b>Task Leaderboard</b> 🏆\n\n"
    for user_id, glory_diff in leaderboard:
        user = await context.bot.get_chat_member(chat_id, user_id)
        leaderboard_text += f"👤 {user.user.first_name} (ID: {user_id}) - {glory_diff} Glory\n"

    # Unpin the task message
    try:
        await context.bot.unpin_chat_message(chat_id, task['message_id'])
    except telegram.error.BadRequest as e:
        print(f"Error while unpinning: {e}")

    # Send and pin the leaderboard message
    message = await update.message.reply_html(leaderboard_text)
    await context.bot.pin_chat_message(chat_id, message.message_id)

async def convert_to_leaderboard(task_id, end_time, now_ist, chat_id, context):
    # Wait until the task ends
    await asyncio.sleep((end_time - now_ist).total_seconds())
    task = tasks_collection.find_one({"_id": task_id})
    if task:
        leaderboard = []
        for key, value in task.items():
            if key.startswith("finv_"):
                user_id = int(key.split("_")[1])
                finv = value
                linv = task.get(f"linv_{user_id}")
                if linv is not None:
                    leaderboard.append((user_id, linv - finv))

        leaderboard.sort(key=lambda x: x[1], reverse=True)

        leaderboard_text = "🏆 <b>Task Leaderboard</b> 🏆\n\n"
        for user_id, glory_diff in leaderboard:
            user = await context.bot.get_chat_member(chat_id, user_id)
            leaderboard_text += f"👤 {user.user.first_name} (ID: {user_id}) - {glory_diff} Glory\n"

        # Tag admins
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_mentions = ' '.join([f"@{admin.user.username}" for admin in admins if admin.user.username])
        leaderboard_text += f"\n\nAdmins: {admin_mentions}"

        # Edit the task message to indicate that it has ended and show the leaderboard
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=task['message_id'],
            text=leaderboard_text,
            parse_mode=telegram.constants.ParseMode.HTML
        )

        # Pin the leaderboard message
        await context.bot.pin_chat_message(chat_id, task['message_id'])

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
