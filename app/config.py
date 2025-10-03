import os
from dotenv import load_dotenv
from .services import access
load_dotenv()

# default key if missing
default_key = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def strippers(data: str):
    if data:
        return [url.strip() for url in data.split(',')]
    return ["http://localhost:5173"]


class Config:
    BACKEND_ADDRESS = os.environ.get("BACKEND_ADDRESS", "localhost")
    BACKEND_PORT = os.environ.get("BACKEND_PORT", "5000")
    FLASK_ENVIRONMENT = os.environ.get("FLASK_ENVIRONMENT", "development")

    # flask server
    FLASK_SECRET_KEY = os.environ.get("SECRET_NI_FLASK", default_key)
    JWT_SECRET_KEY = os.environ.get("SECRET_NI_JWT", default_key)
    
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("TOKEN_ACCESS_DURATION", "15")) * 60 # 15 minute defult
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("TOKEN_REFRESH_DURATION", "1440")) * 60  # 24 hours default

    # mail server credentials
    MAIL_SERVER_ADDRESS = os.environ.get("MAIL_SERVER_ADDRESS", "smpt.changeme.com")
    MAIL_SERVER_PORT = os.environ.get("MAIL_SERVER_PORT", "123")
    MAIL_ADDRESS = os.environ.get("MAIL_ADDRESS", "changeme@example.com")
    MAIL_PASSKEY =  os.environ.get("MAIL_PASSKEY", "XXX XXXX XXX")

    # database
    MYSQL_POOL_SIZE = os.environ.get("MYSQL_POOL_SIZE", 10)
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")
    MYSQL_DB = os.environ.get("MYSQL_DATABASE", "databased")
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")

    # web client
    WEB_CLIENT_HOSTS = strippers(os.environ.get("WEB_CLIENT_HOSTS"))

    access_levels = access.access_level_lookup()

config = Config()