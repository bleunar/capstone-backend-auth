from flask import Blueprint, jsonify, request
import services.database as database
from flask_jwt_extended import (create_access_token, create_refresh_token, set_refresh_cookies, jwt_required, unset_jwt_cookies, get_jwt_identity, decode_token )
from werkzeug.security import check_password_hash
from services.system import log_account

auth_bp = Blueprint("auth", __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        result = jsonify({
            "msg": "Missing username or password"
        })
        return result, 400

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
        result = jsonify({
            "msg": "failed to login, " + account_database['msg']
        })
        return result, 400
    
    if account_database['success'] and not account_database['data']:
        result = jsonify({
            "msg": "account not found"
        })
        return result, 400
    

    # ACCOUNT STATUS CHECK
    if not account_database['data']['status'] == 'active':
        result = jsonify({
            "msg": "account not found"
        })
        return result, 400
    
    if account_database['data']['status'] == 'suspended':
        result = jsonify({
            "msg": "account suspended. contact administrator for assistance."
        })
        return result, 400
    
    # ACCOUNT PASSWORD CHECK
    account_password_hash = database.fetch_scalar("select a.password_hash from accounts as a where a.id = %s;", (account_database['data']['id'], ))

    if not check_password_hash(account_password_hash['data'], password):
        result = jsonify({
            "msg": "password incorrect"
        })
        return result, 400

    # SETUP TOKEN
    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)
    refresh_token = create_refresh_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)

    response = jsonify({
        "tkn_ref": refresh_token,
        "tkn_acc": access_token,
    })

    set_refresh_cookies(response, refresh_token)
    log_account.login(account_database['data']['id'])

    return response, 200



@auth_bp.route('/logout', methods=['POST'])
@jwt_required(refresh=True, verify_type=False)
def logout():
    account_id = get_jwt_identity()
    account_database = database.fetch_one("select a.id, a.username from accounts as a where a.id = %s;", (account_id, ))
    
    if not account_database['success']:
        response = jsonify({
            "msg": "Failed to clear logout"
        })

        unset_jwt_cookies(response)
        return response, 400
    
    if account_database['success'] and not account_database['data']:
        response = jsonify({
            "msg": "Failed to search account on logout"
        })

        unset_jwt_cookies(response)
        return response, 400

    response = jsonify({
        "msg": "Logged out successfuly"
    })
    unset_jwt_cookies(response)
    log_account.logout(account_database['data']['id'])

    return response, 200



@auth_bp.route('/check', methods=['POST'])
@jwt_required()
def check():
    account_id = get_jwt_identity()

    response = jsonify({
        "msg": "hello, " + account_id
    })
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
        return jsonify({"msg": "failed to refresh session"}), 400

    if account_database['success'] and (not account_database['data'] or account_database['data']['status'] == "deleted"):
        return jsonify({"msg": "account not found"}), 404
    
    if account_database['data']['status'] == 'suspended':
        return jsonify({"msg": "Account suspended. Contact administrator for support."}), 400


    # setup token
    added_claims = {
        "rol": account_database["data"]['role_id'],
        "acc": account_database["data"]['access_level']
    }

    access_token = create_access_token(identity=account_database['data']['id'], additional_claims=added_claims, expires_delta=None)

    return jsonify(tkn_acc=access_token), 200