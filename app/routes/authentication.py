from flask import Blueprint, jsonify, request
from ..services import database
from flask_jwt_extended import (create_access_token, create_refresh_token, set_refresh_cookies, jwt_required, unset_jwt_cookies, get_jwt_identity )
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
            a.password_hash,
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
    
    if not check_password_hash(account_database['data']['password_hash'], password):
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


@auth_bp.route('/me/profile', methods=['GET'])
@jwt_required()
def fetch_account_profile():

    # fetch account identity on token
    account_id = get_jwt_identity()

    # check if identity exists on token
    if not account_id:
        response = jsonify({"msg": "failed to fetch current account profile, identity not found"})
        unset_jwt_cookies(response)
        return response, 400

    # setup base query
    base_query = """
        select
            a.first_name,
            a.middle_name,
            a.last_name,
            a.username,
            a.email
        from accounts as a
        where a.id = %s;
    """

    # execute query
    account_profile_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_profile_fetch['success']:
        return common_database_error_response(account_profile_fetch)

    return common_success_response(
        data=account_profile_fetch['data']
    )


@auth_bp.route('/me/credentials', methods=['GET'])
@jwt_required()
def fetch_account_credentials():

    # fetch account identity on token
    account_id = get_jwt_identity()

    # check if identity exists on token
    if not account_id:
        response = jsonify({"msg": "failed to fetch current account credentials, identity not found"})
        unset_jwt_cookies(response)
        return response, 400


    # setup base query
    base_query = """
        select
            a.username,
            a.email,
            a.status,
            a.password_last_updated,
            ar.id as role_id,
            ar.name as role_name,
            ar.access_level as role_access_level
        from accounts as a
        JOIN account_roles AS ar ON a.role_id = ar.id
        where a.id = %s;
    """

    # execute query
    account_credential_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_credential_fetch['success']:
        return common_database_error_response(account_credential_fetch)

    return common_success_response(
        data=account_credential_fetch['data']
    )


@auth_bp.route('/me/settings', methods=['GET'])
@jwt_required()
def fetch_account_settings():

    # fetch account identity on token
    account_id = get_jwt_identity()

    # check if identity exists on token
    if not account_id:
        response = jsonify({"msg": "failed to fetch current account settings, identity not found"})
        unset_jwt_cookies(response)
        return response, 400


    # setup base query
    base_query = """
        select
            acs.enable_dark_mode,
            acs.notification_position,
            acs.notification_duration,
            acs.notification_sound,
            acs.updated_at
        from account_settings as acs
        where acs.account_id = %s;
    """

    # execute query
    account_setting_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_setting_fetch['success']:
        return common_database_error_response(account_setting_fetch)

    return common_success_response(
        data=account_setting_fetch['data']
    )
