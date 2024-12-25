from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict
import asyncio

# Track user activity
user_last_command_time = {}
user_warn_count = defaultdict(int)  # {user_id: warn_count}
user_blocked = {}  # {user_id: unban_time}

# Settings
COOLDOWN = timedelta(seconds=3)  # Wait time between commands
SPAM_THRESHOLD = 5  # Max commands in 10 seconds
SPAM_TIME_FRAME = timedelta(seconds=10)
WARN_LIMIT = 3  # Number of warnings before escalating
PAUSE_DURATIONS = [1800, 3600, 86400]  # 30 min, 1 hour, 1 day in seconds

# Flood control wrapper
def flood_control(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if not user:
            return await func(update, context, *args, **kwargs)  # Ignore non-user messages
        
        user_id = user.id
        now = datetime.now()

        # Check if user is blocked
        if user_id in user_blocked:
            unban_time = user_blocked[user_id]
            if now < unban_time:
                remaining_time = (unban_time - now).seconds
                await update.message.reply_text(
                    f"⛔ You're temporarily paused for spamming. Try again in {remaining_time // 60} minutes."
                )
                return
            else:
                del user_blocked[user_id]  # Unblock user after cooldown

        # Enforce cooldown between commands
        if user_id in user_last_command_time:
            last_command_time = user_last_command_time[user_id]
            if now - last_command_time < COOLDOWN:
                await update.message.reply_text(
                    f"⚠️ Please wait {COOLDOWN.seconds} seconds between commands."
                )
                return

        # Track user activity within the spam time frame
        user_activity = [
            timestamp for timestamp in user_last_command_time.get(user_id, [])
            if now - timestamp <= SPAM_TIME_FRAME
        ]
        user_activity.append(now)
        user_last_command_time[user_id] = user_activity

        # Check for spam
        if len(user_activity) > SPAM_THRESHOLD:
            user_warn_count[user_id] += 1
            warn_count = user_warn_count[user_id]

            if warn_count <= WARN_LIMIT:
                await update.message.reply_text(
                    f"⚠️ Warning {warn_count}/{WARN_LIMIT}: Stop spamming, or your activity will be paused."
                )
            else:
                # Temporarily pause the user
                pause_duration = PAUSE_DURATIONS[min(warn_count - WARN_LIMIT - 1, len(PAUSE_DURATIONS) - 1)]
                user_blocked[user_id] = now + timedelta(seconds=pause_duration)
                if warn_count - WARN_LIMIT < len(PAUSE_DURATIONS):
                    await update.message.reply_text(
                        f"🚨 You are temporarily paused for {pause_duration // 60} minutes due to excessive spamming."
                    )
                else:
                    await update.message.reply_text(
                        "❌ You have been permanently banned for repeated spamming."
                    )
                    # Optional: Add permanent ban logic here (e.g., remove from database)

                return

        # Update last command time and proceed with the original handler
        user_last_command_time[user_id] = now
        return await func(update, context, *args, **kwargs)

    return wrapper

