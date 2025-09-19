import os
from dotenv import load_dotenv
import services.access
load_dotenv()

# default key if missing
default_key = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

class Config:
    BACKEND_ADDRESS = os.environ.get("BACKEND_ADDRESS")
    BACKEND_PORT = os.environ.get("BACKEND_PORT")
    FLASK_ENVIRONMENT = os.environ.get("FLASK_ENVIRONMENT")

    # flask server
    FLASK_SECRET_KEY = os.environ.get("SECRET_NI_FLASK")

    JWT_SECRET_KEY = os.environ.get("SECRET_NI_JWT")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get("TOKEN_ACCESS_DURATION")) * 60
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get("TOKEN_REFRESH_DURATION")) * 60

    # mail server credentials
    MAIL_ADDRESS = os.environ.get("MAIL_ADDRESS")
    MAIL_PASSKEY =  os.environ.get("MAIL_PASSKEY")

    # database
    MYSQL_HOST = os.environ.get("MYSQL_HOST")
    MYSQL_PORT = os.environ.get("MYSQL_PORT")
    MYSQL_DB = os.environ.get("MYSQL_DATABASE")
    MYSQL_USER = os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")

    # web client
    WEB_CLIENT_HOSTS = [url.strip() for url in os.environ.get("WEB_CLIENT_HOSTS").split(',')]

    access_levels = services.access.access_level_lookup()

config = Config()