#!/bin/python3
"""
Meal Prep Assistant - Main Application
Sprint 1 - Backend API
"""
from flask import Flask, jsonify, session, send_from_directory
from flask_cors import CORS
import os
from flask_sqlalchemy import SQLAlchemy

from backend.databse import db
from flask_session import Session

# Import configuration
from backend.config import Config

# Import route blueprints
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize Flask app
application = Flask(__name__)
application.config.from_object(Config)

# Enable CORS for React frontend
CORS(application,
     supports_credentials=True,

     )

# Initialize database
db.init_app(application)

from backend.routes.auth import auth_bp
from backend.routes.recipes import recipes_bp
from backend.routes.pantry import pantry_bp
from backend.routes.lists import lists_bp
from backend.routes.groceryList import grocery_bp
from backend.routes.meal_plan import meal_plan_bp
from backend.routes.user_made_recipes import user_made_recipes_bp
# Initialize recipe routes with database


# Register blueprints
application.register_blueprint(auth_bp, url_prefix='/api/auth')
application.register_blueprint(recipes_bp, url_prefix='/api/recipes')
application.register_blueprint(pantry_bp, url_prefix='/api/pantry')
application.register_blueprint(lists_bp, url_prefix='/api/lists')
application.register_blueprint(grocery_bp, url_prefix='/api/grocery')
application.register_blueprint(meal_plan_bp, url_prefix='/api/meal_plan')
application.register_blueprint(user_made_recipes_bp, url_prefix='/api/user_recipes')

application.config['SECRET_KEY'] = 'TEST SECRET KEY'


UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploaded_images")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

application.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
application.static_folder = 'uploaded_images'

#Session Config
application.config['SESSION_TYPE'] = 'filesystem'
application.config['SESSION_FILE_DIR'] = './flask_session'
application.config['SESSION_PERMANENT'] = False
application.config["SESSION_USE_SIGNER"] = True
Session(application)

# ==================== BASIC ROUTES ====================

@application.route("/")
def home():
    """Health check endpoint"""
    return jsonify({"message": "Backend is live"})

@application.route("/api/ping")
def ping():
    """Ping endpoint for testing"""
    return jsonify({"message": "pong"})

@application.route("/uploaded_images/<filename>")
def uploaded_image(filename):
    return send_from_directory(application.config["UPLOAD_FOLDER"], filename)


# ==================== RUN APP ====================

if __name__ == "__main__":
    application.run(debug=True, host="0.0.0.0")


