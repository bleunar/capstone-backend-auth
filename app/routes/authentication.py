from flask import Blueprint, jsonify, request
from ..services import database
from flask_jwt_extended import (create_access_token, create_refresh_token, set_refresh_cookies, jwt_required, unset_jwt_cookies, get_jwt_identity, decode_token )
from werkzeug.security import check_password_hash
from ..services.system import log_account
from ..services.validation import check_json_payload, check_required_fields, common_success_response, common_error_response, common_database_error_response

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    # validate JSON payload
    data, error_response = check_json_payload()
    if error_response:
        return error_response
    
    # check required fields
    required_fields_error = check_required_fields(data, ['username', 'password'])
    if required_fields_error:
        return required_fields_error

    username = data['username']
    password = data['password']

    # ACCOUNT CHECK
    login_query = """
        select
            a.id,
            a.email,
            a.username,
            a.status,
            ar.id as role_id,
            ar.access_level
        
        from accounts as a 
        join account_roles as ar on a.role_id = ar.id
        
        where
            a.username = %s;
    """
    account_database = database.fetch_one(login_query, (username, ))

    if not account_database['success']:
        return common_database_error_response(account_database)
    
    if not account_database['data']:
        return common_error_response("Account not found", 404)
    

    # ACCOUNT STATUS CHECK
    account_status = account_database['data']['status']
    if account_status == 'suspended':
        return common_error_response("Account suspended. Contact administrator for assistance.", 403)
    elif account_status == 'deleted':
        return common_error_response("Account not found", 404)
    elif account_status != 'active':
        return common_error_response("Account not available", 403)
    
    # ACCOUNT PASSWORD CHECK
    account_password_hash = database.fetch_scalar("select a.password_hash from accounts as a where a.id = %s;", (account_database['data']['id'], ))

    if not account_password_hash['success']:
        return common_database_error_response(account_password_hash)
    
    if not check_password_hash(account_password_hash['data'], password):
        return common_error_response("Invalid credentials", 401)

    # SETUP TOKEN
    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)
    refresh_token = create_refresh_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)

    # Log successful login
    log_account.login(account_database['data']['id'])
    
    response_data = {
        "tkn_ref": refresh_token,
        "tkn_acc": access_token,
        "user_id": account_database['data']['id'],
        "access_level": account_database['data']['access_level']
    }
    
    response = jsonify(response_data)
    set_refresh_cookies(response, refresh_token)
    
    return response, 200



@auth_bp.route('/logout', methods=['POST'])
@jwt_required(refresh=True, verify_type=False)
def logout():
    account_id = get_jwt_identity()
    account_database = database.fetch_one("select a.id, a.username from accounts as a where a.id = %s;", (account_id, ))
    
    if not account_database['success']:
        response = jsonify({"success": False, "error": "Failed to process logout"})
        unset_jwt_cookies(response)
        return response, 500
    
    if not account_database['data']:
        response = jsonify({"success": False, "error": "Account not found"})
        unset_jwt_cookies(response)
        return response, 404

    # Log successful logout
    log_account.logout(account_database['data']['id'])
    
    response = jsonify({"success": True, "message": "Logged out successfully"})
    unset_jwt_cookies(response)
    
    return response, 200



@auth_bp.route('/check', methods=['POST'])
@jwt_required()
def check():
    account_id = get_jwt_identity()
    
    return common_success_response(
        data={"user_id": account_id}, 
        message="Token is valid"
    )



@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True, locations=["cookies"])
def refresh_access():

    # fetch account identity on token
    account_id = get_jwt_identity()

    # check if identity exists on token
    if not account_id:
        return jsonify({"msg": "failed to refresh, identity not found"}), 400

    # account verification 
    refresh_query = """
        SELECT
            a.id,
            a.status,
            a.role_id,
            ar.access_level
        FROM accounts AS a
        JOIN account_roles AS ar ON a.role_id = ar.id
        WHERE a.id = %s;
    """
    account_database = database.fetch_one(refresh_query, (account_id,))

    if not account_database['success']:
        return common_database_error_response(account_database)

    if not account_database['data'] or account_database['data']['status'] == "deleted":
        return common_error_response("Account not found", 404)
    
    if account_database['data']['status'] == 'suspended':
        return common_error_response("Account suspended. Contact administrator for support.", 403)
    
    if account_database['data']['status'] != 'active':
        return common_error_response("Account not available", 403)


    # setup token
    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)

    return common_success_response(
        data={"tkn_acc": access_token}, 
        message="Token refreshed successfully"
    )