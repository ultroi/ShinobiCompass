from datetime import datetime, timedelta
from functools import wraps
from ShinobiCompass.database import db

# Constants
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
        if user_data["block_end_time"]:
            block_end_time = user_data["block_end_time"]
            if current_time < block_end_time:
                remaining_time = int((block_end_time - current_time).total_seconds())
                await update.message.reply_text(
                    f"🚫 You are temporarily paused. Try again after {remaining_time} seconds."
                )
                return
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

        # Enforce cooldown
        if recent_activity and (current_time - recent_activity[-1]).total_seconds() < COOLDOWN:
            await update.message.reply_text(
                f"⏳ Please wait {COOLDOWN} seconds between commands."
            )
            return

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
                return

        # Execute the command
        await func(update, context)

    return wrapper
