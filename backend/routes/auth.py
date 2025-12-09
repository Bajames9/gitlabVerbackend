"""
Authentication routes - Login and Signup
"""
from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash #for password hashing
import re #for input validation (specifically email)
from backend.databse import db
from backend.models.User import User

from backend.models.List import Lists

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$" #simple email regex for validation

#Simulated DB of users (for testing only)


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Basic login endpoint for Sprint 1
    
    Expected JSON:
    {
        "username": "exampleUser@gmail.com",
        "password": "examplePassword123"
    }
    
    Returns:
    {
        "success": true/false,
        "message": "Login successful" or error message
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400

        user = User.query.filter_by(email=username).first()

        if user is None or not check_password_hash(user.password, password):
            return jsonify({
                "success": False,
                "message": "Invalid credentials"
            }), 401




        # Set a session cookie (for simplicity, using Flask's built-in session)
        session['user_id'] = user.userId
        session['username'] = user.username
        session['admin'] = user.admin

        return jsonify({
            "success": True,
            "message": "Login successful",
            "admin": user.admin
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Basic signup endpoint for Sprint 1
    
    Expected JSON:
    {
        "username": "newUser@gmail.com",
        "password": "newPassword123"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "Username and password are required"
            }), 400
        
        # Validate email format
        if not re.match(EMAIL_REGEX, username):
            return jsonify({
            "success": False,
                "message": "Invalid email format. Please use a valid email address."
            }), 400



        # Validate user input (more complex validation will be added once I've consulted with the team)
        if len(username) < 3 or len(password) < 6:
            return jsonify({
                "success": False,
                "message": "Username must be at least 3 characters long and password must be at least 6 characters long."
            }), 400

        existing_user = User.query.filter_by(email=username).first()
        if existing_user:
            return jsonify({
                "success": False,
                "message": "User already exists"
            }), 409

        hashed_password = generate_password_hash(password)

        new_user = User(
            email=username,
            username=username.split('@')[0],  # basic default username
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()


        favorites_list = Lists(
            owner_id=new_user.userId,
            title="Favorites",
            recipe_ids=[]
        )
        db.session.add(favorites_list)
        db.session.commit()

        
        return jsonify({
            "success": True,
            "message": "Signup successful"
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500
    
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint for Sprint 1 (and yes, I'm copying Eli's formatting, it's great)

    Returns:
    {
        "success": true/false,
        "message": "Logout successful" or error message
    }
    this may need to be changed in the future but it's nearly midnight and I'm not a night owl
    """
    try:
        #Clear the session cookie and server-side file
        if 'user_id' in session:
            session_id = session.get('_id')

            #clear the session data
            session.clear()

            # Delete the server-side session file
            if session_id:
                import os
                from flask import current_app

                session_dir = current_app.config.get('SESSION_FILE_DIR', './flask_session')
                session_file = os.path.join(session_dir, session_id)

                if os.path.exists(session_file):
                    os.remove(session_file)



            return jsonify({
                "success": True,
                "message": "Logout successful"
            }), 200
        else:
            return jsonify({"success": False, "message": "No user is logged in"}), 400
        
    except Exception as e:
        return jsonify({
                "success": False,
                "message": f"Server error: {str(e)}"
            }), 500
    
@auth_bp.route('/whoami', methods=['GET'])
def whoami():
        """
        Session cookie test
        """
        user = session.get('username')
        admin = session.get('admin')

        if user:
            return jsonify(success=True, user=user, admin=admin), 200
        else:
            return jsonify(success=False, message="Not logged in"), 401
        

# UPDATING ACCOUNT INFO endpoints

@auth_bp.route('/update-email', methods=['PUT'])
def update_email():
    """
    Update user's email
    
    Expected JSON:
    {
        "new_email": "newemail@example.com"
    }
    
    Returns:
    {
        "success": true/false,
        "message": "Email updated successfully" or error message
    }
    """
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        new_email = data.get('new_email')
        
        if not new_email:
            return jsonify({
                "success": False,
                "message": "New email is required"
            }), 400

        # New email validation using EMAIL_REGEX
        if not re.match(EMAIL_REGEX, new_email):
            return jsonify({
                "success": False,
                "message": "Invalid email format."
            }), 400




        
        # Check if email already exists
        existing_user = User.query.filter_by(email=new_email).first()
        if existing_user:
            return jsonify({
                "success": False,
                "message": "Email already in use"
            }), 409

        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        user.email = new_email
        db.session.commit()

        session['user_id'] = user.userId
        session['username'] = user.username


        return jsonify({
            "success": True,
            "message": "Email updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500

@auth_bp.route('/update-password', methods=['PUT'])
def update_password():
    """
    Update user's password
    
    Expected JSON:
    {
        "new_password": "newPassword123"
    }
    
    Returns:
    {
        "success": true/false,
        "message": "Password updated successfully" or error message
    }
    """
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({
                "success": False,
                "message": "New password is required"
            }), 400
        
        # Validate password length
        if len(new_password) < 6:
            return jsonify({
                "success": False,
                "message": "Password must be at least 6 characters long"
            }), 400
        
        # Get user from database
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Hash the new password
        user.password = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Password updated successfully"
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500

@auth_bp.route('/delete-account', methods=['DELETE'])
def delete_account():
    """
    Delete user's account
    
    Returns:
    {
        "success": true/false,
        "message": "Account deleted successfully" or error message
    }
    """
    try:
        # Check if user is logged in
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401
        
        # Get user from database
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        db.session.delete(user)
        db.session.commit()
        
        # Clear the session
        session_id = session.get('_id')
        session.clear()
        
        # Delete the server-side session file
        if session_id:
            import os
            session_dir = current_app.config.get('SESSION_FILE_DIR', './flask_session')
            session_file = os.path.join(session_dir, session_id)
            if os.path.exists(session_file):
                os.remove(session_file)
        
        return jsonify({
            "success": True,
            "message": "Account deleted successfully"
        }), 200
        

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500