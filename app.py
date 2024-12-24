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

# Import custom modules
from ShinobiCompass.modules.start import start, handle_callback_query
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

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ShinobiCompassBot")

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

# Task handlers
application.add_handler(CommandHandler("task", set_task))
application.add_handler(CommandHandler("endtask", end_task))
application.add_handler(CommandHandler("clearall", clear_tasks))
application.add_handler(CommandHandler("canceltask", cancel_task))

# Inventory submission handlers
application.add_handler(CommandHandler("finv", lambda update, context: submit_inventory(update, context, "finv")))
application.add_handler(CommandHandler("linv", lambda update, context: submit_inventory(update, context, "linv")))
application.add_handler(CommandHandler("taskresult", taskresult))
application.add_handler(CommandHandler("bm", bm))
application.add_handler(CommandHandler("addsudo", addsudo))
application.add_handler(CommandHandler("rmsudo", removesudo))
application.add_handler(CommandHandler("sdlist", sudolist))
application.add_handler(CommandHandler("stats", stats))
application.add_handler(CallbackQueryHandler(handle_stats_buttons))
application.add_handler(CallbackQueryHandler(handle_callback_query))
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))


# Run the bot
if __name__ == "__main__":
    application.run_polling()  # Starts the bot using long polling
