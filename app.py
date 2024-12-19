import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient
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
import uvicorn  # For running the FastAPI server dynamically

# Import custom modules
from ShinobiCompass.modules.start import start, handle_callback_query
from ShinobiCompass.modules.bm import bm, handle_message

# Load environment variables
load_dotenv()

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

# FastAPI setup
app = FastAPI()

# Lifespan context manager (handles startup and shutdown)
async def lifespan(app: FastAPI):
    logger.info("Application startup complete.")
    yield
    client.close()
    logger.info("MongoDB connection closed")

# Set lifespan event handler
app = FastAPI(lifespan=lifespan)

# Telegram bot setup
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("bm", bm))
application.add_handler(CallbackQueryHandler(handle_callback_query))
application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO, handle_message))

# Webhook route
@app.post("/webhook")
async def webhook(update: dict):
    try:
        telegram_update = Update.de_json(update, application.bot)
        await application.process_update(telegram_update)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Shinobi Compass Bot is Running!"}

# Run the application
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Use dynamic port from environment
    uvicorn.run(app, host="0.0.0.0", port=port)
