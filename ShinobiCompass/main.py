import logging
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from modules.task import settask, schedule, resettask, finv, linv, connect, status
from modules.start import start, handle_callback_query
from modules.bm import bm, handle_message
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    filters,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.get_database("Tgbotproject")

# Main function
def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    application = ApplicationBuilder().token(bot_token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bm", bm))
    application.add_handler(CommandHandler("settask", settask))
    application.add_handler(CommandHandler("resettask", resettask))
    application.add_handler(CommandHandler("finv", finv))
    application.add_handler(CommandHandler("linv", linv))
    application.add_handler(CommandHandler("connect", connect))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
