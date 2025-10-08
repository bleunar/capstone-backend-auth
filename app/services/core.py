import mysql.connector
from ..config import config
import json
import smtplib
import time
from flask_jwt_extended import JWTManager
from flask import Flask
from .log import log

# instance of flask and jwt
app = Flask(__name__)
jwt = JWTManager(app)


# instance fetch
def get_flask_app():
    return app

def get_jwt_manager():
    return jwt


# global connection pool variable
connection_pool = None

# creates new connection pool
def create_connection_pool():
    global connection_pool
    
    try:
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="conn-pool-auth",
            pool_size=int(config.MYSQL_POOL_SIZE),
            host=config.MYSQL_HOST,
            port=int(config.MYSQL_PORT),
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DB,
            use_pure=True
        )
        log.inform("DATABASE", "Connection pool created successfully")
        return True
        
    except mysql.connector.Error as err:
        log.error("DATABASE", f"Error creating connection pool: {err}")
        connection_pool = None
        return False

# initialize database connection w/ retry mechanism.
def initialize_database_with_retry(max_attempts=10, total_duration_minutes=3):
    
    global connection_pool
    
    if connection_pool is not None:
        log.inform("DATABASE", "Connection pool already exists")
        return True
    
    # calculate delay between attempts (in seconds)
    total_duration_seconds = total_duration_minutes * 60
    delay_between_attempts = total_duration_seconds / max_attempts
    
    log.inform("DATABASE-RETRY", f"Starting database connection with retry mechanism")
    log.inform("DATABASE-RETRY", f"Max attempts: {max_attempts}, Total duration: {total_duration_minutes} minutes")
    log.inform("DATABASE-RETRY", f"Delay between attempts: {delay_between_attempts:.1f} seconds")
    
    for attempt in range(1, max_attempts + 1):
        log.inform("DATABASE-RETRY", f"Connection attempt {attempt}/{max_attempts}")
        
        if create_connection_pool():
            log.inform("DATABASE-RETRY", f"Database connection established successfully on attempt {attempt}")
            return True
        
        if attempt < max_attempts:
            log.inform("DATABASE-RETRY", f"Attempt {attempt} failed. Waiting {delay_between_attempts:.1f} seconds before next attempt...")
            time.sleep(delay_between_attempts)
        else:
            log.error("DATABASE-RETRY", f"All {max_attempts} connection attempts failed")
    
    log.error("DATABASE-RETRY", "Failed to establish database connection after all retry attempts")
    return False

# attempt to initialize connection pool on module load (for backward compatibility)
try:
    create_connection_pool()
except Exception as e:
    log.error("DATABASE", f"Initial connection pool creation failed: {e}")
    connection_pool = None

# get database connection from pool w/ automatic retry if pool is null.
def get_db_connection():
    global connection_pool
    
    # if connection pool is null, try to initialize it with retry
    if connection_pool is None:
        log.warn("DATABASE", "Connection pool is not available. Attempting to initialize with retry...")
        if not initialize_database_with_retry():
            log.error("DATABASE", "Failed to initialize connection pool after retry attempts")
            return None
        
    try:
        conn = connection_pool.get_connection()
        return conn
        
    except mysql.connector.Error as err:
        log.error("DATABASE", f"Error getting connection from pool: {err}")

        log.warn("DATABASE", "Attempting to recreate connection pool...")
        if create_connection_pool():
            try:
                conn = connection_pool.get_connection()
                return conn
            except mysql.connector.Error as retry_err:
                log.error("DATABASE", f"Error getting connection after pool recreation: {retry_err}")
        return None


def reset_connection_pool():
    """Reset the connection pool (useful for manual reconnection)."""
    global connection_pool
    
    if connection_pool:
        try:
            log.inform("DATABASE", "Closing existing connection pool...")
            connection_pool = None
            log.inform("DATABASE", "Connection pool reset successfully")
        except Exception as e:
            log.error("DATABASE", f"Error resetting connection pool: {e}")
    
    connection_pool = None

# check if db is connected
def is_database_connected():
    try:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True
        return False
    except Exception as e:
        log.error("DATABASE", f"Database connection test failed: {e}")
        return False


# forces a database reconnection by resetting pool and reinitializing
def force_reconnect_database():
    log.inform("DATABASE", "Forcing database reconnection...")
    reset_connection_pool()
    return initialize_database_with_retry()


# fetching mail server
def get_mail_server():
    try:
        server = smtplib.SMTP(config.MAIL_SERVER_ADDRESS, int(config.MAIL_SERVER_PORT))
        server.starttls()
        server.login(config.MAIL_ADDRESS, config.MAIL_PASSKEY)
        return server
    except smtplib.SMTPException as e:
        log.error("MAIL_SRV-ERR", f"SMTP error: {str(e)}")
        return None
    except Exception as e:
        log.error("MAIL_SRV-ERR", f"Failed to connect with mail server: {str(e)}")
        return None