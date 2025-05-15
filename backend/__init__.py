from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__,
                template_folder='../frontend/templates',
                static_folder='../frontend/static')

    # Load environment variables
    load_dotenv()

    # Retrieve database credentials from .env file
    db_username = os.getenv('DB_USERNAME')
    db_password = os.getenv('DB_PASSWORD')
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT')
    db_name = os.getenv('DB_NAME')

    # Ensure DB_PORT is an integer
    try:
        db_port = int(db_port)
    except ValueError:
        raise ValueError("Invalid DB_PORT value. Ensure it is a valid integer.")

    # SQLAlchemy database URI
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"mysql+pymysql://{db_username}:{db_password}@{db_host}:{db_port}/{db_name}"
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    # Initialize Flask extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User Loader function
    from backend.models import User  # Updated import path

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = 'auth.login'  # Update this to use auth blueprint

    # Register routes using the new blueprint structure
    from backend.routes import init_routes
    init_routes(app)

    return app
