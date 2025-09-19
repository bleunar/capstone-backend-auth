from flask import jsonify
import datetime
from config import config
from flask_cors import CORS
from services.system import get_service_information
from services.core import get_flask_app
from services.system import system_check

app = get_flask_app()
app.config["SECRET_KEY"] = config.FLASK_SECRET_KEY
app.config["JWT_SECRET_KEY"] = config.JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = datetime.timedelta(seconds=config.JWT_REFRESH_TOKEN_EXPIRES)
app.config["JWT_TOKEN_LOCATION"] = ["headers","cookies"]
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_COOKIE_SAMESITE"] = "None"
app.config["JWT_COOKIE_HTTPONLY"] = True
app.config["JWT_COOKIE_CSRF_PROTECT"] = True
app.url_map.strict_slashes = False

# ENDPOINTS FROM BLUEPRINTS
from routes.authentication import auth_bp
app.register_blueprint(auth_bp, url_prefix="/auth")

# status endppint 
@app.route("/", methods=["GET"])
def status():
    data = {
        "msg": "authen services is up",
        "date": datetime.datetime.today(),
        "info": get_service_information()
    }
    return jsonify(data)

# setup CORS for all endpoint
CORS(app, origins=config.WEB_CLIENT_HOSTS, supports_credentials=True)

# main method
if __name__ == "__main__":
    system_check()
    app.run(debug=config.FLASK_ENVIRONMENT == "development", host=config.BACKEND_ADDRESS, port=config.BACKEND_PORT)