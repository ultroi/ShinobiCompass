import logging
import os
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Import custom 
from ShinobiCompass.modules.start import start, help_callback_handler, empty_update, back_to_main, help_extra, show_updates_callback, update_message
from ShinobiCompass.modules.bm import bm, handle_message
from ShinobiCompass.modules.sudo import addsudo, removesudo, sudolist
from ShinobiCompass.modules.stats import stats, handle_stats_buttons
from ShinobiCompass.modules.task import (
    set_task,
    end_task,
    clear_tasks,
    submit_inventory,
    taskresult,
    cancel_task,
)
from ShinobiCompass.modules.extra import xp_command, iseal_command
from ShinobiCompass.modules.flood import floods, set_constants

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ShinobiCompassBot")

# Load environment variables 
OWNER_ID = int(os.getenv("OWNER_ID", "5956598856"))
if not OWNER_ID:
    raise ValueError("OWNER_ID is not set")
SUDO_USERS_COLLECTION = "sudo_users"  # MongoDB collection for sudo users

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set")
client = MongoClient(MONGO_URI)

try:
    client.admin.command('ping')
    logger.info("Connected to MongoDB successfully!")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

db = client.get_database("Tgbotproject")

# Telegram bot setup
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("update", update_message))  # Update message command
application.add_handler(CommandHandler("emptyupdate", empty_update))
application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="help_bm_commands"))
application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="help_task_page_1"))
application.add_handler(CallbackQueryHandler(help_callback_handler, pattern="help_task_page_2"))
application.add_handler(CallbackQueryHandler(show_updates_callback, pattern="show_updates"))
application.add_handler(CallbackQueryHandler(back_to_main, pattern="back_to_main"))
application.add_handler(CallbackQueryHandler(help_extra, pattern="help_extra"))

# Task handlers
application.add_handler(CommandHandler("task", set_task))
application.add_handler(CommandHandler("endtask", end_task))
application.add_handler(CommandHandler("clearall", clear_tasks))
application.add_handler(CommandHandler("canceltask", cancel_task))

application.add_handler(CommandHandler("xp", xp_command))
application.add_handler(CommandHandler("iseal", iseal_command))

application.add_handler(CommandHandler("floods", floods))
application.add_handler(CommandHandler("set", set_constants))

# Inventory submission handlers
application.add_handler(CommandHandler("finv", submit_inventory, pass_args=True))
application.add_handler(CommandHandler("linv", submit_inventory, pass_args=True))
application.add_handler(CommandHandler("taskresult", taskresult))
application.add_handler(CommandHandler("bm", bm))
application.add_handler(CommandHandler("addsudo", addsudo))
application.add_handler(CommandHandler("rmsudo", removesudo))
application.add_handler(CommandHandler("sdlist", sudolist))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CallbackQueryHandler(handle_stats_buttons))
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))


# Run the bot
if __name__ == "__main__":
    application.run_polling()  # Starts the bot using long polling
