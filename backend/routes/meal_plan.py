"""
Meal Plan routes - Add, delete, get
"""
from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from backend.databse import db 
from datetime import datetime

from flask_cors import cross_origin

meal_plan_bp = Blueprint('meal_plan', __name__)

@meal_plan_bp.route('/add', methods=['POST'], strict_slashes=False)
def add_meal_plan():
    """
    Add a recipe to the user's meal plan for a specific date and meal type
    
    JSON Body:
    {
        "mealDate": "2025-12-10",
        "mealType": "dinner",
        "recipeId": 42
    }
    
    Returns:
    - 201: Success
    - 400: Invalid input
    - 401: Not logged in
    - 404: Recipe not found
    - 409: Duplicate meal slot
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Invalid JSON"}), 400

    meal_date = data.get('mealDate')
    meal_type = data.get('mealType')
    recipe_id = data.get('recipeId')

    # Validate required fields
    if not all([meal_date, meal_type, recipe_id]):
        return jsonify({
            "success": False,
            "message": "Missing required fields: mealDate, mealType, recipeId"
        }), 400

    # Validate mealType
    valid_types = {'breakfast', 'lunch', 'dinner'}
    if meal_type not in valid_types:
        return jsonify({"success": False, "message": "Invalid mealType"}), 400

    # Validate date format (YYYY-MM-DD)
    try:
        datetime.strptime(meal_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Validate recipe ID is a number
    try:
        recipe_id = int(recipe_id)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid recipeId. Must be a positive number"
        }), 400

    # Validate recipe ID is positive
    if recipe_id <= 0:
        return jsonify({
            "success": False,
            "message": "Invalid recipeId. Must be a positive number"
        }), 400

    # Check if recipe exists
    recipe_check = db.session.execute(
        text("SELECT 1 FROM recipes WHERE RecipeId = :recipe_id"),
        {"recipe_id": recipe_id}
    ).fetchone()

    if not recipe_check:
        return jsonify({"success": False, "message": "Recipe not found"}), 404

    # Insert into meal_plans (UNIQUE constraint will block duplicates)
    try:
        result = db.session.execute(
            text("""
                INSERT INTO meal_plans (userId, mealDate, mealType, RecipeId)
                VALUES (:user_id, :meal_date, :meal_type, :recipe_id)
            """),
            {
                "user_id": user_id,
                "meal_date": meal_date,
                "meal_type": meal_type,
                "recipe_id": recipe_id
            }
        )
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Meal added to plan",
        }), 201

    except Exception as e:
        db.session.rollback()
        # Check if it's a duplicate (from UNIQUE constraint)
        if "Duplicate entry" in str(e) or "UNIQUE constraint" in str(e):
            return jsonify({
                "success": False,
                "message": "A meal is already scheduled for this user, date, and meal type"
            }), 409
        else:
            # Log for debugging
            print(f"Database error: {str(e)}")
            return jsonify({
                "success": False,
                "message": "Failed to save meal plan"
            }), 500


@meal_plan_bp.route('/get', methods=['GET'], strict_slashes=False)
def get_meal_plan():
    """
    Retrieve the user's meal plan

    Optional Query Params:
    - mealDate: Date in YYYY-MM-DD format (if omitted, returns all meal plans for the user)
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    meal_date = request.args.get('mealDate')

    # ✅ Validate date if provided
    if meal_date:
        try:
            datetime.strptime(meal_date, '%Y-%m-%d')
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400

    # ✅ UPDATED QUERY — added r.Images
    base_query = """
        SELECT 
            mp.mealDate,
            mp.mealType,
            r.RecipeId,
            r.Name,
            r.Description,
            r.CookTime,
            r.Images
        FROM meal_plans mp
        JOIN recipes r ON mp.RecipeId = r.RecipeId
        WHERE mp.userId = :user_id
    """

    params = {"user_id": user_id}

    if meal_date:
        base_query += " AND mp.mealDate = :meal_date"
        params["meal_date"] = meal_date

    base_query += " ORDER BY mp.mealDate, FIELD(mp.mealType, 'breakfast', 'lunch', 'dinner')"

    try:
        result = db.session.execute(text(base_query), params)
        rows = result.fetchall()

        # ✅ UPDATED JSON OUTPUT — includes imageUrl
        meal_plan = [
            {
                "mealDate": row.mealDate,
                "mealType": row.mealType,
                "recipeId": row.RecipeId,
                "recipeName": row.Name,
                "description": row.Description,
                "cookTime": row.CookTime,
                "imageUrl": row.Images  # ✅ ADDED
            }
            for row in rows
        ]

        return jsonify({
            "success": True,
            "mealPlan": meal_plan
        }), 200

    except Exception as e:
        print(f"Database error during fetch: {str(e)}")
        return jsonify({
            "success": False,
            "message": "Failed to retrieve meal plan"
        }), 500


@meal_plan_bp.route('/delete', methods=['DELETE'], strict_slashes=False)
@cross_origin(supports_credentials=True)
def remove_meal_plan():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Authentication required"}), 401

    data = request.get_json()
    meal_date = data.get("mealDate")
    meal_type = data.get("mealType")

    if not meal_date or not meal_type:
        return jsonify({
            "success": False,
            "message": "Missing required query parameters: mealDate and mealType"
        }), 400

    # Validate mealType
    valid_types = {'breakfast', 'lunch', 'dinner'}
    if meal_type not in valid_types:
        return jsonify({"success": False, "message": "Invalid mealType"}), 400

    # Validate date format
    try:
        datetime.strptime(meal_date, '%Y-%m-%d')
    except ValueError:
        return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Delete the meal plan entry
    result = db.session.execute(
        text("""
            DELETE FROM meal_plans
            WHERE userId = :user_id
              AND mealDate = :meal_date
              AND mealType = :meal_type
        """),
        {
            "user_id": user_id,
            "meal_date": meal_date,
            "meal_type": meal_type
        }
    )

    db.session.commit()

    if result.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "No meal found for the specified date and meal type"
        }), 404

    return jsonify({
        "success": True,
        "message": "Meal removed from plan"
    }), 200

