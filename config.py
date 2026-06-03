import os

from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN")
USERS_FILE = "users.json"
ADMIN_ID_RAW = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW else None
DISCORD_API_VERSION = "v9"
