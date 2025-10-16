from flask import Blueprint
from ..services import database
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_refresh_cookies,
    jwt_required,
    unset_jwt_cookies,
    get_jwt_identity
)
from werkzeug.security import check_password_hash, generate_password_hash
from ..services.system import log_account
from ..services.validation import (
    check_json_payload,
    check_required_fields,
    common_success_response,
    common_error_response,
    common_database_error_response,
)

auth_bp = Blueprint("auth", __name__)



@auth_bp.route('/login', methods=['POST'])
def login():
    data, error_response = check_json_payload()
    if error_response:
        return error_response
    
    required_fields_error = check_required_fields(data, ['username', 'password'])
    if required_fields_error:
        return required_fields_error

    username = data['username']
    password = data['password']

    login_query = """
        SELECT
            a.id,
            a.email,
            a.username,
            a.status,
            a.password_hash,
            ar.id AS role_id,
            ar.access_level
        FROM accounts AS a
        JOIN account_roles AS ar ON a.role_id = ar.id
        WHERE a.username = %s;
    """
    account_database = database.fetch_one(login_query, (username, ))

    if not account_database['success']:
        return common_database_error_response(account_database)
    
    if not account_database['data']:
        return common_error_response("Account not found", 404)

    account_status = account_database['data']['status']
    if account_status == 'suspended':
        return common_error_response("Account suspended. Contact administrator for assistance.", 403)
    elif account_status == 'deleted':
        return common_error_response("Account not found", 404)
    elif account_status != 'active':
        return common_error_response("Account not available", 403)
    
    if not check_password_hash(account_database['data']['password_hash'], password):
        return common_error_response("Invalid credentials", 401)

    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(
        identity=account_database['data']['id'],
        additional_claims=added_claims,
        expires_delta=None
    )
    refresh_token = create_refresh_token(
        identity=account_database['data']['id'],
        additional_claims=added_claims,
        expires_delta=None
    )

    log_account.login(account_database['data']['id'])

    response_data = {
        "tkn_ref": refresh_token,
        "tkn_acc": access_token,
        "user_id": account_database['data']['id'],
        "access_level": account_database['data']['access_level']
    }

    response = common_success_response(data=response_data, message="Login successful")
    set_refresh_cookies(response, refresh_token)
    return response




@auth_bp.route('/logout', methods=['POST'])
@jwt_required(refresh=True)
def logout():
    account_id = get_jwt_identity()
    account_database = database.fetch_one("SELECT a.id, a.username FROM accounts AS a WHERE a.id = %s;", (account_id, ))

    if not account_database['success']:
        response = common_error_response("Failed to process logout", 500)
        unset_jwt_cookies(response)
        return response
    
    if not account_database['data']:
        response = common_error_response("Account not found", 404)
        unset_jwt_cookies(response)
        return response

    log_account.logout(account_database['data']['id'])

    response = common_success_response(message="Logged out successfully")
    unset_jwt_cookies(response)
    return response




@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True, locations=["cookies"])
def refresh_access():
    account_id = get_jwt_identity()
    if not account_id:
        return common_error_response("Failed to refresh, identity not found", 400)

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

    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(
        identity=account_database['data']['id'],
        additional_claims=added_claims,
        expires_delta=None
    )

    return common_success_response(
        data={"tkn_acc": access_token},
        message="Token refreshed successfully"
    )




@auth_bp.route('/me/profile', methods=['GET'])
@jwt_required()
def fetch_account_profile():
    account_id = get_jwt_identity()

    base_query = """
        SELECT
            a.first_name,
            a.middle_name,
            a.last_name,
            a.username,
            a.email
        FROM accounts AS a
        WHERE a.id = %s;
    """
    account_profile_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_profile_fetch['success']:
        return common_database_error_response(account_profile_fetch)

    return common_success_response(data=account_profile_fetch['data'])




@auth_bp.route("/me/profile", methods=["PUT"])
@jwt_required()
def edit_account_profile():
    account_id = get_jwt_identity()
    data, error_response = check_json_payload()
    if error_response:
        return error_response

    required_fields_error = check_required_fields(data, ['first_name', 'last_name'])
    if required_fields_error:
        return required_fields_error

    first_name = data['first_name']
    middle_name = data.get('middle_name')
    last_name = data['last_name']

    base_query = """
        UPDATE accounts SET
            accounts.first_name = %s,
            accounts.middle_name = %s,
            accounts.last_name = %s
        WHERE accounts.id = %s;
    """
    base_params = (first_name, middle_name, last_name, account_id)

    account_profile_updated = database.execute_single(base_query, base_params)

    if not account_profile_updated['success']:
        return common_database_error_response(account_profile_updated)

    return common_success_response(message="Profile updated successfully")




@auth_bp.route('/me/credential', methods=['GET'])
@jwt_required()
def fetch_account_credential():
    account_id = get_jwt_identity()

    base_query = """
        SELECT
            a.username,
            a.email,
            a.status,
            a.password_last_updated,
            ar.id AS role_id,
            ar.name AS role_name,
            ar.access_level AS role_access_level
        FROM accounts AS a
        JOIN account_roles AS ar ON a.role_id = ar.id
        WHERE a.id = %s;
    """
    account_credential_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_credential_fetch['success']:
        return common_database_error_response(account_credential_fetch)

    return common_success_response(data=account_credential_fetch['data'])




@auth_bp.route("/me/credential/password", methods=["PUT"])
@jwt_required()
def edit_account_credential_password():
    account_id = get_jwt_identity()
    data, error_response = check_json_payload()
    if error_response:
        return error_response

    required_fields_error = check_required_fields(data, ['old_password', 'new_password', 'new_password_confirm'])
    if required_fields_error:
        return required_fields_error

    old_password = data['old_password']
    new_password = data['new_password']
    new_password_confirm = data['new_password_confirm']

    password_reset_query = """
        SELECT a.password_hash
        FROM accounts AS a 
        WHERE a.id = %s;
    """
    account_password_reset_data = database.fetch_one(password_reset_query, (account_id, ))

    if not account_password_reset_data['success']:
        return common_database_error_response(account_password_reset_data)

    if not check_password_hash(account_password_reset_data['data']['password_hash'], old_password):
        return common_error_response("Old password is incorrect", 400)

    if new_password != new_password_confirm:
        return common_error_response("Password confirmation does not match", 400)

    password_reset_query = """
        UPDATE accounts SET
            accounts.password_hash = %s,
            accounts.password_last_updated = CURRENT_TIMESTAMP
        WHERE accounts.id = %s;
    """
    base_params = (generate_password_hash(new_password), account_id)
    password_reset_result = database.execute_single(password_reset_query, base_params)

    if not password_reset_result['success']:
        return common_database_error_response(password_reset_result)

    return common_success_response(message="Successfully updated your password")




@auth_bp.route('/me/settings', methods=['GET'])
@jwt_required()
def fetch_account_settings():
    account_id = get_jwt_identity()

    if not is_initialized(account_id):
        return common_error_response("Failed to fetch settings, not properly initialized", 400)

    base_query = """
        SELECT
            acs.enable_dark_mode,
            acs.notification_position,
            acs.notification_duration,
            acs.notification_sound,
            acs.updated_at
        FROM account_settings AS acs
        WHERE acs.account_id = %s;
    """
    account_setting_fetch = database.fetch_one(base_query, (account_id, ))

    if not account_setting_fetch['success']:
        return common_database_error_response(account_setting_fetch)

    return common_success_response(data=account_setting_fetch['data'])




@auth_bp.route("/me/settings", methods=["PUT"])
@jwt_required()
def edit_account_settings():
    account_id = get_jwt_identity()
    data, error_response = check_json_payload()
    if error_response:
        return error_response

    required_fields_error = check_required_fields(
        data,
        ['enable_dark_mode', 'notification_position', 'notification_duration', 'notification_sound']
    )
    if required_fields_error:
        return required_fields_error

    if not is_initialized(account_id):
        return common_error_response("Failed to edit settings, not properly initialized", 400)

    base_query = """
        UPDATE account_settings SET
            account_settings.enable_dark_mode = %s,
            account_settings.notification_position = %s,
            account_settings.notification_duration = %s,
            account_settings.notification_sound = %s
        WHERE account_settings.account_id = %s;
    """
    base_params = (
        data['enable_dark_mode'],
        data['notification_position'],
        data['notification_duration'],
        data['notification_sound'],
        account_id
    )

    account_settings_updated = database.execute_single(base_query, base_params)
    if not account_settings_updated['success']:
        return common_database_error_response(account_settings_updated)

    return common_success_response(message="Account settings updated successfully")




def is_initialized(account_id: str):
    record_checked = database.fetch_scalar(
        """
            SELECT account_settings.account_id
            FROM account_settings
            WHERE account_settings.account_id = %s
        """,
        (account_id, )
    )

    if record_checked['success'] and record_checked['data']:
        return True
    else:
        base_query = """
            INSERT INTO account_settings (
                account_settings.account_id,
                account_settings.enable_dark_mode,
                account_settings.notification_position,
                account_settings.notification_duration,
                account_settings.notification_sound
            )
            VALUES (%s, 1, 'top-0 start-50 translate-middle-x', '4', 'full');
        """
        insert_status = database.execute_single(base_query, (account_id, ))
        return insert_status['success']