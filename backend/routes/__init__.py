from flask import Blueprint
from .auth import auth_bp
from .editor import editor_bp
from .main import main_bp

def init_routes(app):
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(editor_bp, url_prefix='/editor')