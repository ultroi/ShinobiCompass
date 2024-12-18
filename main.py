import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient, errors
from fastapi import FastAPI, HTTPException
from starlette.responses import JSONResponse
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

# Importing custom modules
from ShinobiCompass.modules.start import start, handle_callback_query
from ShinobiCompass.modules.bm import bm, handle_message

# Load environment variables from .env file
try:
    load_dotenv()
except Exception as e:
    raise RuntimeError(f"Error loading environment variables: {e}")

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ShinobiCompassBot")

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the environment variables")

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("Tgbotproject")
    # Verify connection
    client.admin.command("ping")
    logger.info("Successfully connected to MongoDB")
except errors.ServerSelectionTimeoutError as e:
    logger.error(f"MongoDB connection timeout: {e}")
    raise RuntimeError("Failed to connect to MongoDB. Please check your MONGO_URI.")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    raise RuntimeError("Unexpected error connecting to MongoDB.")

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
        raise HTTPException(status_code=500, detail={"status": "error", "message": str(e)})


# Root route (optional)
@app.get("/")
async def root():
    """
    Root route for checking if the bot is running.
    """
    return {"message": "Shinobi Compass Bot is Running!"}


# Graceful shutdown
@app.on_event("shutdown")
async def shutdown():
    """
    Ensure clean disconnection from MongoDB.
    """
    try:
        client.close()
        logger.info("MongoDB connection closed")
    except Exception as e:
        logger.warning(f"Error while closing MongoDB connection: {e}")
