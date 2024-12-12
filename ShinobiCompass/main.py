import logging
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
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# MongoDB setup
client = MongoClient("mongodb+srv://Akshayofficial:islandbot1904@tgbotproject.uwaxq.mongodb.net/Tgbotproject?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE")
db = client.Tgbotproject

# Main function
def main() -> None:
    bot_token = "7866673972:AAFSczpid7J-1vAANUfFgKkq0pxaz-Rc9oA"
    application = ApplicationBuilder().token(bot_token).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("bm", bm))
    application.add_handler(CommandHanlder("settask", settask))
    application.add_handler(CommandHanlder("resettask", resettask))
    application.add_handler(CommandHanlder("finv", fnv))
    application.add_handler(CommandHandler("linv", linv))
    application.add_handler(CommandHanlder("connect", connect))
    application.add_Handler(CommandHandler("status", status))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
