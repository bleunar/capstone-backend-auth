from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from .log import log
from mysql.connector import Error, MySQLConnection
from mysql.connector.cursor import MySQLCursor

# alias types
ApiResponse = Dict[str, Any]
Params = Tuple[Any, ...]


# error formatting
def _format_db_error(err: Exception) -> str:
    try:
        errno = getattr(err, "errno", "n/a")
        sqlstate = getattr(err, "sqlstate", "n/a")
        return f"{errno} | {sqlstate} | {str(err)}"
    except Exception:
        return str(err)
    

def _format_db_message(err: Exception) -> str:
    try:
        errno = getattr(err, "errno", None)
        msg = str(err).lower()

        # Duplicate entry (MySQL error 1062)
        if errno == 1062 or "duplicate entry" in msg:
            return "Item already exists."

        # Foreign key constraint fails (MySQL error 1452)
        if errno == 1452 or "foreign key constraint" in msg:
            return "Invalid reference — related item not found."

        # Cannot delete/update because of foreign key (MySQL error 1451)
        if errno == 1451:
            return "Cannot delete item — it is still in use."

        # Data too long (MySQL error 1406)
        if errno == 1406 or "data too long" in msg:
            return "Input value is too long."

        # Default: generic short message
        return f"Database error: {msg}"
    except Exception:
        return "An unexpected database error occurred."



def _get_connection_pool():
    from .core import connection_pool
    return connection_pool


def is_database_available() -> bool:
    try:
        current_pool = _get_connection_pool()
        if not current_pool:
            return False
        
        # test with a simple connection
        conn = current_pool.get_connection()
        if conn:
            conn.close()
            return True
        return False
    except Exception as e:
        log.error("database-availability", f"Database availability check failed: {str(e)}")
        return False


def _db_executionist(executionLogic, isWrite: bool = False) -> ApiResponse:
    current_pool = _get_connection_pool()
    
    if not current_pool:
        from .core import initialize_database_with_retry
        log.warn("db-executionist", "Connection pool not available, attempting to initialize with retry...")
        
        if not initialize_database_with_retry():
            msg = "Database connection failed after retry attempts"
            log.error("db-executionist", msg)
            return {"success": False, "msg": msg, "errno": None, "sqlstate": None}
        
        # Get the newly created pool
        current_pool = _get_connection_pool()
        if not current_pool:
            msg = "Failed to establish database connection pool"
            log.error("db-executionist", msg)
            return {"success": False, "msg": msg, "errno": None, "sqlstate": None}
        else:
            log.inform("db-executionist", "Connection pool successfully established after retry")

    conn: Optional[MySQLConnection] = None

    try:
        conn = current_pool.get_connection()

        # for execute queries
        if isWrite and getattr(conn, "autocommit", None) is True:
            conn.autocommit = False

        # execute current setup
        with conn.cursor(dictionary=True, buffered=True) as cursor:
            result_data = executionLogic(cursor)

        # commit the executed queries
        if isWrite:
            conn.commit()
            log.inform("db-executionist", "Transaction committed successfully")

        # return paldo
        return {"success": True, "data": result_data}

    except Error as err:
        # check if it's a connection-related error and try to recover
        errno = getattr(err, "errno", None)
        if errno in [2003, 2006, 2013]:  # common connection error codes
            log.warn("db-executionist", f"Connection error detected (errno: {errno}), attempting recovery...")
            
            # atttempt to recreate connection pool
            from .core import create_connection_pool
            if create_connection_pool():
                log.inform("db-executionist", "Connection pool recreated, retrying operation...")
                # retry the operation once with new pool
                try:
                    new_pool = _get_connection_pool()
                    if new_pool:
                        conn = new_pool.get_connection()
                        
                        if isWrite and getattr(conn, "autocommit", None) is True:
                            conn.autocommit = False
                        
                        with conn.cursor(dictionary=True, buffered=True) as cursor:
                            result_data = executionLogic(cursor)
                        
                        if isWrite:
                            conn.commit()
                            log.inform("db-executionist", "Transaction committed successfully after retry")
                        
                        return {"success": True, "data": result_data}
                        
                except Error as retry_err:
                    log.error("db-executionist", f"Retry failed: {_format_db_error(retry_err)}")
                    err = retry_err  # use the retry error for final response
        
        # rollback if something went wrong
        if isWrite and conn:
            try:
                conn.rollback()
                log.inform("db-executionist-rollback", "Transaction rolled back due to error")
            except Exception as rollback_err:
                log.warn("db-executionist-rollback", _format_db_error(rollback_err))

        # formats the error trace
        formatted_err = _format_db_error(err)

        # log the error on system
        log.error("db-executionist", formatted_err)

        return {
            "success": False,
            "msg": _format_db_message(err),
            "errno": getattr(err, "errno", None),
            "sqlstate": getattr(err, "sqlstate", None),
        }

    finally:
        # close connection after performing the opration
        if conn and getattr(conn, "is_connected", lambda: False)():
            try:
                conn.close()
            except Exception:
                log.warn("db-executionist", "failed to close connection")
                pass


# fetches all the record
def fetch_all(query: str, parameters: Optional[Params] = None) -> ApiResponse:
    def logic(cursor: MySQLCursor):
        cursor.execute(query, parameters or ())
        return cursor.fetchall()
    return _db_executionist(logic)


# fetches the first record
def fetch_one(query: str, parameters: Optional[Params] = None) -> ApiResponse:
    def logic(cursor: MySQLCursor):
        cursor.execute(query, parameters or ())
        return cursor.fetchone()
    return _db_executionist(logic)


# runs one query
def execute_single(query: str, params: Optional[Params] = None) -> ApiResponse:
    def logic(cursor: MySQLCursor):
        cursor.execute(query, params or ())
        return {
            "rowcount": cursor.rowcount,
            "lastrowid": cursor.lastrowid
        }
    return _db_executionist(logic, isWrite=True)


# runs multiple queries
def execute_many(query: str, params_list: Sequence[Params]) -> ApiResponse:
    def logic(cursor: MySQLCursor):
        cursor.executemany(query, params_list)
        return {
            "rowcount": cursor.rowcount,
            "lastrowid": cursor.lastrowid
        }
    return _db_executionist(logic, isWrite=True)


# runs multiple queries via transaction
def execute_transaction(queries: Sequence[Tuple[str, Params]]) -> ApiResponse:
    def logic(cursor: MySQLCursor):
        total_rowcount = 0
        last_id = None
        for query, params in queries:
            cursor.execute(query, params or ())
            total_rowcount += cursor.rowcount
            if cursor.lastrowid:
                last_id = cursor.lastrowid
        return {
            "rowcount": total_rowcount,
            "lastrowid": last_id,
            "queries": len(queries)
        }
    return _db_executionist(logic, isWrite=True)


# returns the data on the first column of the first record
def fetch_scalar(query: str, params: Optional[Params] = None) -> ApiResponse:
    result = fetch_one(query, params)
    if not result["success"]:
        return result

    row = result["data"]
    if row:
        scalar_value = next(iter(row.values()), None)
        return {"success": True, "data": scalar_value}
    
    return {"success": True, "data": None}


# test database connection
def test_database_connection() -> ApiResponse:
    try:
        result = fetch_one("SELECT 1 as test_value")
        if result["success"] and result["data"] and result["data"].get("test_value") == 1:
            log.inform("database-test", "Database connection test successful")
            return {"success": True, "msg": "Database connection working properly"}
        else:
            log.error("database-test", "Database connection test failed - invalid response")
            return {"success": False, "msg": "Database connection test failed"}
    except Exception as e:
        log.error("database-test", f"Database connection test error: {str(e)}")
        return {"success": False, "msg": f"Database connection test error: {str(e)}"}
