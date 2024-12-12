from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI")

# Initialize MongoDB client and database
client = MongoClient(MONGO_URI)
db = client.get_database("Tgbotproject")
