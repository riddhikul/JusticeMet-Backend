from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")

def get_db():
    # Connect to the MongoDB database
    client = MongoClient(MONGO_URI)
    db = client['legal_chatbot']  # Replace 'legal_chatbot' with your database name if needed
    return db
