# database.py
from pymongo import MongoClient
from config import Config

# MongoDB Connection
client = MongoClient(Config.MONGO_URI)
db = client['career']