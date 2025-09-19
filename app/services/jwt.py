from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask import jsonify, request
from functools import wraps
from config import config

ACCESS_LEVELS = config.access_levels

# required access level to use the endpoint
def require_access(access_level_codename: str, exact: bool = False):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            user_access = claims.get("acc", None)

            if user_access is None:
                return jsonify({"msg": "Invalid token: missing access claims"}), 401

            if exact and user_access != ACCESS_LEVELS[(access_level_codename)]:
                return jsonify({"msg": "Access denied: incorrect access level"}), 403

            if not exact and user_access < ACCESS_LEVELS[(access_level_codename)]:
                return jsonify({"msg": "Access denied: insufficient access level"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator
