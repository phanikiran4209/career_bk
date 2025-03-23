from pymongo import MongoClient
from pymongo.read_preferences import ReadPreference
from config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Connection
try:
    client = MongoClient(
        Config.MONGO_URI,
        connectTimeoutMS=30000,        # 30 seconds timeout for establishing connection
        socketTimeoutMS=30000,         # 30 seconds timeout for socket operations
        serverSelectionTimeoutMS=30000, # 30 seconds timeout for server selection
        retryWrites=True,              # Retry writes on network errors
        w="majority",                  # Ensure writes are acknowledged by majority
        tls=True,                      # Explicitly enable TLS
        tlsAllowInvalidCertificates=False  # Enforce valid certificates
    )
    # Test the connection by pinging the server
    client.admin.command("ping")
    db = client['career']
    logger.info("Successfully connected to MongoDB Atlas")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Additional debugging info
    logger.error(f"Mongo URI: {Config.MONGO_URI}")
    raise

# Optional: Print topology for debugging
logger.info(f"Topology: {client.topology_description}")