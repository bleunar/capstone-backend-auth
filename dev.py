from app.app import jarvis_deploy_website
from app.config import config

if __name__ == "__main__":
    jarvis_deploy_website().run(debug=True, port=config.BACKEND_PORT)