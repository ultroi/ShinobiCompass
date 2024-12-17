import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from fastapi import FastAPI
from starlette.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Importing your custom modules
from ShinobiCompass.modules.start import start, handle_callback_query
from ShinobiCompass.modules.bm import bm, handle_message

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
try:
    client = MongoClient(MONGO_URI)
    db = client.get_database("Tgbotproject")
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    raise e

# Initialize FastAPI app
app = FastAPI()

# Initialize the bot application globally
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in the environment variables")
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bm", bm))
application.add_handler(CallbackQueryHandler(handle_callback_query))
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

# Webhook route
@app.post("/webhook")
async def webhook(update: dict):
    """
    Webhook endpoint to process Telegram updates.
    """
    try:
        # Convert incoming dictionary to a Telegram Update object
        telegram_update = Update.de_json(update, application.bot)

        # Process the update
        await application.process_update(telegram_update)

        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


# Root route (optional)
@app.get("/")
async def root():
    return {"message": "Shinobi Compass Bot is Running!"}
