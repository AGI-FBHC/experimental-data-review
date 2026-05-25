from flask import Flask
from flask_cors import CORS
from .api import review_bp, file_bp, chat_bp


def create_app():
    app = Flask(__name__)
    CORS(app, origins="*")

    # 注册蓝图
    app.register_blueprint(review_bp, url_prefix="/api/review")
    app.register_blueprint(file_bp, url_prefix="/api/file")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")

    return app
