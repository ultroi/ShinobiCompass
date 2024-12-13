import certifi
from pymongo import MongoClient, errors
import os
import time
import logging
from dotenv import load_dotenv
import atexit

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set or is incorrect. Please check your .env file.")

# Ensure MONGO_URI contains the correct credentials
if not (":" in MONGO_URI and "@" in MONGO_URI):
    raise ValueError("MONGO_URI does not contain the required username and password.")


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Setup
mongo_client = None

def setup_mongo(retries: int = 3, delay: int = 5):
    global mongo_client
    attempt = 0
    
    while attempt < retries:
        try:
            logger.debug(f"Connecting to MongoDB using URI: {MONGO_URI}")
            # Use certifi for CA certificates
            mongo_client = MongoClient(MONGO_URI, tls=True, tlsCAFile=certifi.where(), 
                                       serverSelectionTimeoutMS=30000,  # 30 seconds
                                       connectTimeoutMS=10000,  # 10 seconds
                                       socketTimeoutMS=20000)  # 20 seconds
            mongo_client.get_database("Tgbotproject")  # Check if connection is valid
            mongo_client.admin.command("ping")  # Ensure connection is active
            logger.info("MongoDB connected successfully.")
            return mongo_client
        except errors.ConnectionFailure as e:
            attempt += 1
            logger.error(f"MongoDB connection attempt {attempt} failed. Error: {e}")
            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.critical("Failed to connect to MongoDB after multiple attempts.", exc_info=True)
                raise e
        except Exception as e:
            logger.critical(f"Unexpected error while connecting to MongoDB: {e}", exc_info=True)
            raise e

def close_mongo_connection():
    """Close MongoDB connection Gracefully."""
    global mongo_client
    if mongo_client:
        try:
            mongo_client.close()
            logger.info("MongoDB connection closed.")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")

# Set up cleanup when the bot shuts down
atexit.register(close_mongo_connection)

# Initialize MongoDB client and database
try:
    mongo_client = setup_mongo()
    db = mongo_client.get_database("Tgbotproject")
except Exception as e:
    logger.critical("Failed to initialize MongoDB client.", exc_info=True)
    raise e
