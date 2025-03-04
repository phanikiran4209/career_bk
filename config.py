import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = "mongodb+srv://QDiRprFe:WCU9J1dpNHhCbuTc@us-east-1.ufsuw.mongodb.net/career"
    MONGO_DB_NAME = "career"  # Add this line to specify the database name
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Change this in production