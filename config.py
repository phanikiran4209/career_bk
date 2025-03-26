import os
from dotenv import load_dotenv
from datetime import timedelta  # Import timedelta for cleaner time definition

# Load environment variables from .env file
load_dotenv()

class Config:
    DEEPSEEK_API_KEY = "sk_iTKUcyR1a6wno7ZIKrIu_i6Sn51WFHVhdWpGTMduC4k"
    # MongoDB Configuration (Stored in Environment Variables)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://your_username:your_password@your_cluster.mongodb.net/career")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "career")  # Database Name
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")  # Change this in production
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)  # Set token expiration to 24 hours
    
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")