import mysql.connector
from config import config
import json
import smtplib
from flask_jwt_extended import JWTManager
from flask import Flask
from services.log import log

# instance of flask and jwt
app = Flask(__name__)
jwt = JWTManager(app)


# instance fetch
def get_flask_app():
    return app

def get_jwt_manager():
    return jwt


try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="conn-pool-auth",
        pool_size=10,
        host=config.MYSQL_HOST,
        user=config.MYSQL_USER,
        password=config.MYSQL_PASSWORD,
        database=config.MYSQL_DB,
        use_pure=True
    )
    log.inform("DATABASE", "Connection pool created successfully")

except mysql.connector.Error as err:
    log.error("DATABASE", f"Error creating connection pool: {err}")
    connection_pool = None


def get_db_connection():
    if connection_pool is None:
        log.error("DATABASE", "Connection pool is not available.")
        return None
        
    try:
        conn = connection_pool.get_connection()
        return conn
        
    except mysql.connector.Error as err:
        log.error("DATABASE", f"Error getting connection from pool: {err}")
        return None


# fetching access levels
def get_access_levels():
    with open('access_levels.json', 'r') as f:
        data_as_dict = json.load(f)
        return list(data_as_dict.values())


# fetching mail server
def get_mail_server():
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(config.MAIL_ADDRESS, config.MAIL_PASSKEY)
        return server
    except:
        return None