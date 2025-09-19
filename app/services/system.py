from datetime import datetime
import json
from app.services.log import log

def get_service_information():
    with open('service_information.json', 'r') as f:
        data_as_dict = json.load(f)
        return data_as_dict



# account log class
import services.database as database

class log_account:
    def login(account_id: int) -> bool:
        database.execute_single("insert into account_logs (account_id, action) values (%s, 'LOGIN');", (account_id, ))
    
    def logout(account_id: int) -> bool:
        database.execute_single("insert into account_logs (account_id, action) values (%s, 'LOGOUT');", (account_id, ))
    
    def action(account_id: int, action: str = "ACTION", description = 'something') -> bool:
        database.execute_single("insert into account_logs (account_id, action, description) values (%s, %s, %s);", (account_id, action, description))
    

# system startup check
def system_check() -> bool:
    from services.core import get_db_connection, get_mail_server

    log.inform("SYSTEM-INIT", f"\n{'\\'*25}  SYSTEM INIT  {25*'\\'}\n")
    log.inform("SYSTEM-INIT", "Starting system check...")

    # DATABASE CONNECTION
    if get_db_connection():
        log.inform("SYSTEM-INIT", "Database connection established")
    else:
        log.error("SYSTEM-INIT", "Failed to connect to database")
        return False


    # MAIL SERVER
    if get_mail_server():
        log.inform("SYSTEM-INIT", "Mail server connection established")
    else:
        log.error("SYSTEM-INIT", "Failed to connect to mail server")
        return False

    log.inform("SYSTEM-INIT", "critical checks completed")
    log.inform("SYSTEM-INIT", f"\n{'\\'*25}  SYSTEM INIT END  {25*'\\'}\n")
