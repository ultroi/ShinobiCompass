from datetime import datetime, timedelta
from functools import wraps
from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from ShinobiCompass.database import db
from ShinobiCompass.modules.sudo import is_owner_or_sudo

# Constants (Initial Values)
COOLDOWN = 3  # Minimum time between commands (in seconds)
SPAM_THRESHOLD = 5  # Maximum allowed commands in SPAM_TIME_FRAME
SPAM_TIME_FRAME = 10  # Time frame to detect spamming (in seconds)
WARN_LIMIT = 3  # Maximum warnings before escalating penalties
PAUSE_DURATIONS = [30 * 60, 60 * 60, 24 * 60 * 60]  # Penalty durations: 30 mins, 1 hr, 1 day

# MongoDB collections
users_collection = db["users"]  # Collection to store user activity

def flood_control(func):
    @wraps(func)
    async def wrapper(update, context):
        user_id = update.effective_user.id
        current_time = datetime.utcnow()

        # Fetch or initialize user data
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data:
            user_data = {
                "user_id": user_id,
                "activity": [],
                "warnings": 0,
                "block_end_time": None
            }
            users_collection.insert_one(user_data)

        # Check if the user is blocked
        if user_data["end_time"]:
            block_end_time = user_data["end_time"]
            if current_time < block_end_time:
                remaining_time = int((block_end_time - current_time).total_seconds())
                await update.message.reply_text(
                    f"🚫 You are temporarily paused. Try again after {remaining_time} seconds."
                )
                return  # Ignore the command during the block time
            else:
                # Unblock user after block period expires
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"block_end_time": None, "warnings": 0}}
                )

        # Filter activity timestamps within the SPAM_TIME_FRAME
        recent_activity = [
            timestamp for timestamp in user_data["activity"]
            if timestamp >= current_time - timedelta(seconds=SPAM_TIME_FRAME)
        ]

          # Block further commands within the cooldown period

        # Update activity log
        recent_activity.append(current_time)
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"activity": recent_activity}}
        )

        # Check for spamming
        if len(recent_activity) >= SPAM_THRESHOLD:
            warnings = user_data["warnings"] + 1
            if warnings <= WARN_LIMIT:
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"warnings": warnings}}
                )
                await update.message.reply_text(
                    f"⚠️ Warning {warnings}/{WARN_LIMIT}: Stop spamming!"
                )
            else:
                # Temporarily block the user with increasing durations
                penalty_index = warnings - WARN_LIMIT - 1
                pause_duration = PAUSE_DURATIONS[min(penalty_index, len(PAUSE_DURATIONS) - 1)]
                block_end_time = current_time + timedelta(seconds=pause_duration)

                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"block_end_time": block_end_time}}
                )

                await update.message.reply_text(
                    f"🚫 You are temporarily blocked for {pause_duration // 60} minutes."
                )
                return  # Block further commands until the pause is over

        # Execute the command after the cooldown and spamming checks
        await func(update, context)

    return wrapper

# /floods command to show the current flood control settings
async def floods(update: Update, context: CallbackContext):
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("🚫 You do not have permission to view the flood settings.")
        return

    flood_settings = (
        f"🛑 **Current Flood Control Settings** 🛑\n\n"
        f"⏳ COOLDOWN: {COOLDOWN} seconds\n"
        f"⚠️ SPAM_THRESHOLD: {SPAM_THRESHOLD} commands\n"
        f"⏱️ SPAM_TIME_FRAME: {SPAM_TIME_FRAME} seconds\n"
        f"🚫 WARN_LIMIT: {WARN_LIMIT} warnings\n"
        f"⏳ PAUSE_DURATIONS: {', '.join([str(duration // 60) + ' mins' for duration in PAUSE_DURATIONS])}"
    )

    await update.message.reply_text(flood_settings)

# /set command to modify constants
async def set_constants(update: Update, context: CallbackContext):
    if not is_owner_or_sudo(update.effective_user.id):
        await update.message.reply_text("🚫 You do not have permission to modify the constants.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /set <constant_name> <value>")
        return

    constant_name = context.args[0].lower()
    try:
        if constant_name == "cooldown":
            global COOLDOWN
            COOLDOWN = int(context.args[1])
            await update.message.reply_text(f"✅ COOLDOWN time has been updated to {COOLDOWN} seconds.")

        elif constant_name == "spam_threshold":
            global SPAM_THRESHOLD
            SPAM_THRESHOLD = int(context.args[1])
            await update.message.reply_text(f"✅ SPAM_THRESHOLD has been updated to {SPAM_THRESHOLD}.")

        elif constant_name == "spam_time_frame":
            global SPAM_TIME_FRAME
            SPAM_TIME_FRAME = int(context.args[1])
            await update.message.reply_text(f"✅ SPAM_TIME_FRAME has been updated to {SPAM_TIME_FRAME} seconds.")

        elif constant_name == "warn_limit":
            global WARN_LIMIT
            WARN_LIMIT = int(context.args[1])
            await update.message.reply_text(f"✅ WARN_LIMIT has been updated to {WARN_LIMIT}.")

        elif constant_name == "pause_durations":
            durations = [int(x) for x in context.args[1:]]
            global PAUSE_DURATIONS
            PAUSE_DURATIONS = durations
            await update.message.reply_text(f"✅ PAUSE_DURATIONS has been updated to {PAUSE_DURATIONS} seconds.")
        
        else:
            await update.message.reply_text("⚠️ Invalid constant name. Valid names: cooldown, spam_threshold, spam_time_frame, warn_limit, pause_durations.")
    except ValueError:
        await update.message.reply_text("⚠️ Please provide a valid value for the constant.")

