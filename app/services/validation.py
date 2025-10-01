from flask import jsonify, request
from typing import Dict, Any, Optional, List, Tuple



# vlidations and checking

def check_json_payload() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple]]:
    try:
        data = request.get_json()
        if data is None:
            return None, (
                jsonify({
                    "error": "Invalid JSON payload or Content-Type not set to application/json"
                    }), 400
                )
        return data, None
    except Exception as e:
        return None, (
            jsonify({
                "error": f"JSON parsing error: {str(e)}"
                }), 400
            )


def check_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[Tuple]:
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        return (jsonify({
            "error": "Missing required fields",
            "missing_fields": missing_fields
        }), 400)
    
    return None


def check_order_parameter(order_param: str) -> str:
    """
    Validates and sanitizes order parameter to prevent SQL injection.
    
    Args:
        order_param: Order parameter from request
        
    Returns:
        Safe order string (ASC or DESC)
    """
    if order_param and order_param.lower() == "latest":
        return "DESC"
    return "ASC"



# standardized responses

def common_success_response(data: Any = None, message: str = "Success") -> Tuple:
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data

    return jsonify(response), 200


def common_error_response(message: str, status_code: int = 400, details: Dict = None) -> Tuple:
    response = {"success": False, "error": message}
    if details:
        response["details"] = details

    return jsonify(response), status_code


def common_database_error_response(db_result: Dict[str, Any]) -> Tuple:
    return common_error_response(
        message="Database failed",
        status_code=500,
        details={
            "database_error": db_result.get('msg', 'Unknown database error')
        }
    )
