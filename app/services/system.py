from datetime import datetime
import json, os
from .log import log

def get_service_information():
    file_path = os.path.join(os.path.dirname(__file__), '..', 'service_information.json')
    with open(file_path, 'r') as f:
        data_as_dict = json.load(f)
        return data_as_dict



# account log class
from . import database

class log_account:
    def login(account_id: int) -> bool:
        database.execute_single("insert into account_logs (account_id, action) values (%s, 'LOGIN');", (account_id, ))
    
    def logout(account_id: int) -> bool:
        database.execute_single("insert into account_logs (account_id, action) values (%s, 'LOGOUT');", (account_id, ))
    
    def action(account_id: int, action: str = "ACTION", description = 'something') -> bool:
        database.execute_single("insert into account_logs (account_id, action, description) values (%s, %s, %s);", (account_id, action, description))
    

# system startup check
def system_check() -> bool:
    from .core import get_db_connection, initialize_database_with_retry

    log.inform("SYSTEM-INIT", f"\n{'\\'*25}  SYSTEM INIT  {25*'\\'}\n")
    log.inform("SYSTEM-INIT", "Starting system check...")

    # DATABASE CONNECTION
    log.inform("SYSTEM-CHECK", "Initializing database connection")
    if not initialize_database_with_retry(max_attempts=20, total_duration_minutes=5):
        log.error("SYSTEM-CHECK", "Failed to establish database connection after all retry attempts")
        return False
    
    # Verify connection works with database operations
    from .database import test_database_connection
    db_test_result = test_database_connection()
    if db_test_result["success"]:
        log.inform("SYSTEM-CHECK", "Database connection established and verified with test query")
    else:
        log.error("SYSTEM-CHECK", f"Database connection verification failed: {db_test_result.get('msg', 'Unknown error')}")
        return False

    log.inform("SYSTEM-INIT", "critical checks completed")
    log.inform("SYSTEM-INIT", f"\n{'\\'*25}  SYSTEM INIT END  {25*'\\'}\n")
