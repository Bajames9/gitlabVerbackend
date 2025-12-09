"""
Database configuration for the Meal Prep Assistant
"""

class Config:
    """Base configuration"""
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = (
        'mysql+pymysql://admin:MealPrep2025!@recipes.cgfac4s62gi1.us-east-1.rds.amazonaws.com:3306/recipes_db'
        #'mysql+pymysql://root:MealPrep2025!@localhost/recipes_db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask settings
    DEBUG = True
    
    # TODO: Add these for production later
    # SECRET_KEY = 'your-secret-key-here'
    # JWT_SECRET_KEY = 'your-jwt-secret-here'