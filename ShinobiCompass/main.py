import logging
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.responses import JSONResponse
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

# Initialize FastAPI app
app = FastAPI()

# Main function for webhook
@app.post("/webhook")
async def webhook(update: Update):
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
    application.add_handler(CommandHandler("connections", connections))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CallbackQueryHandler(task_replacement_callback, pattern="replace_task|keep_task"))
    application.add_handler(CallbackQueryHandler(button_handler, pattern="submit_task"))
    application.add_handler(CallbackQueryHandler(handle_start, pattern="^connect:"))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

    # Process the update
    await application.process_update(update)
    return JSONResponse({"status": "ok"})
