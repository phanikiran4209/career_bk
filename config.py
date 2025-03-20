import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # MongoDB Configuration (Stored in Environment Variables)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://your_username:your_password@your_cluster.mongodb.net/career")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "career")  # Database Name
    
    # JWT Secret Key (Stored in Environment Variable)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Change this in production
