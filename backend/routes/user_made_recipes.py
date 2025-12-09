import os
import uuid

from flask import Blueprint, jsonify, request, session, current_app, send_from_directory
from sqlalchemy import text
from werkzeug.utils import secure_filename


from backend.databse import db
import json
import random

from backend.models.User import User

user_made_recipes_bp = Blueprint('user_made_recipes', __name__)


@user_made_recipes_bp.route("/get", methods=["GET"])
def get_user_recipes():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        result = db.session.execute(
            text("SELECT id, recipe_data, submitted FROM user_made_recipes WHERE userid = :uid"),
            {"uid": user_id}
        ).fetchall()

        recipes = []
        for row in result:
            recipes.append({
                "id": row[0],
                "recipe": json.loads(row[1]),
                "submitted": bool(row[2])
            })

        return jsonify({"success": True, "recipes": recipes})

    except Exception as e:
        print("Error fetching recipes:", e)
        return jsonify({"success": False, "message": str(e)}), 500



@user_made_recipes_bp.route("/add", methods=["POST"])
def add_user_recipe():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No recipe data provided"}), 400

        db.session.execute(
            text("""
                INSERT INTO user_made_recipes (userid, submitted, recipe_data)
                VALUES (:uid, :submitted, :recipe)
            """),
            {
                "uid": user_id,
                "submitted": False,
                "recipe": json.dumps(data)
            }
        )

        db.session.commit()
        return jsonify({"success": True, "message": "Recipe added successfully"})

    except Exception as e:
        print("Error adding recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500



@user_made_recipes_bp.route("/update/<int:recipe_id>", methods=["PUT"])
def update_user_recipe(recipe_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No recipe data provided"}), 400

        db.session.execute(
            text("""
                UPDATE user_made_recipes
                SET recipe_data = :recipe
                WHERE id = :rid AND userid = :uid
            """),
            {
                "recipe": json.dumps(data),
                "rid": recipe_id,
                "uid": user_id
            }
        )

        db.session.commit()

        return jsonify({"success": True, "message": "Recipe updated successfully"})

    except Exception as e:
        print("Error updating recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500


@user_made_recipes_bp.route("/delete/<int:recipe_id>", methods=["DELETE"])
def delete_user_recipe(recipe_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        db.session.execute(
            text("""
                DELETE FROM user_made_recipes
                WHERE id = :rid AND userid = :uid
            """),
            {
                "rid": recipe_id,
                "uid": user_id
            }
        )

        db.session.commit()

        return jsonify({"success": True, "message": "Recipe deleted successfully"})

    except Exception as e:
        print("Error deleting recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500


@user_made_recipes_bp.route("/submit/<int:recipe_id>", methods=["PUT"])
def submit_recipe(recipe_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        db.session.execute(
            text("""
                UPDATE user_made_recipes
                SET submitted = TRUE
                WHERE id = :rid AND userid = :uid
            """),
            {
                "rid": recipe_id,
                "uid": user_id
            }
        )

        db.session.commit()

        return jsonify({"success": True, "message": "Recipe submitted for review"})

    except Exception as e:
        print("Error submitting recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500



@user_made_recipes_bp.route("/get/all", methods=["GET"])
def get_all_user_saved_recipes():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401

        result = db.session.execute(
            text("""
                SELECT id, recipe_data, submitted
                FROM user_made_recipes
                WHERE userid = :uid
                ORDER BY id DESC
            """),
            {"uid": user_id}
        ).fetchall()

        recipes = []
        for row in result:
            recipes.append({
                "id": row[0],
                "recipe": json.loads(row[1]),
                "submitted": bool(row[2])
            })

        return jsonify({
            "success": True,
            "recipes": recipes
        })

    except Exception as e:
        print("Error fetching saved recipes:", e)
        return jsonify({
            "success": False,
            "message": f"Error fetching saved recipes: {str(e)}"
        }), 500


@user_made_recipes_bp.route("/unsubmit/<int:recipe_id>", methods=["PUT"])
def unsubmit_recipe(recipe_id):
    """Sets the submitted status of a user's recipe to FALSE.
    Admins can unsubmit any recipe.
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        # Fetch the user making the request
        user = User.query.get(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        # Admins can update any recipe
        if user.admin:
            result = db.session.execute(
                text("""
                    UPDATE user_made_recipes
                    SET submitted = FALSE
                    WHERE id = :rid
                """),
                {"rid": recipe_id}
            )
        else:
            # Normal user can only unsubmit their own
            result = db.session.execute(
                text("""
                    UPDATE user_made_recipes
                    SET submitted = FALSE
                    WHERE id = :rid AND userid = :uid
                """),
                {"rid": recipe_id, "uid": user_id}
            )

        if result.rowcount == 0:
            db.session.rollback()
            return jsonify({"success": False, "message": "Recipe not found or unauthorized"}), 404

        db.session.commit()
        return jsonify({"success": True, "message": "Submission revoked successfully"})

    except Exception as e:
        print("Error revoking submission:", e)
        return jsonify({"success": False, "message": str(e)}), 500





@user_made_recipes_bp.route("/upload_image", methods=["POST"])
def upload_recipe_image():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No file selected"}), 400

    # Generate a unique filename: UUID + original extension
    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_filename = f"{uuid.uuid4()}.{ext}"
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, unique_filename)
    file.save(file_path)

    # Return full URL for frontend
    file_url = f"/uploaded_images/{unique_filename}"
    return jsonify({"success": True, "url": file_url})


@user_made_recipes_bp.route("/get/submitted/all", methods=["GET"])
def get_all_submitted_recipes_admin():
    try:
        user_id = session.get("user_id")
        is_admin = session.get("admin")

        # ✅ Must be logged in
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401

        # ✅ Must be admin
        if not is_admin:
            return jsonify({
                "success": False,
                "message": "Admin access required"
            }), 403

        # ✅ Get ALL submitted recipes from ALL users
        result = db.session.execute(
            text("""
                SELECT id, userid, recipe_data, submitted
                FROM user_made_recipes
                WHERE submitted = TRUE
                ORDER BY id DESC
            """)
        ).fetchall()

        recipes = []
        for row in result:
            recipes.append({
                "id": row[0],
                "userId": row[1],         # ✅ which user submitted it
                "recipe": json.loads(row[2]),
                "submitted": bool(row[3])
            })

        return jsonify({
            "success": True,
            "recipes": recipes
        }), 200

    except Exception as e:
        print("Error fetching submitted recipes:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@user_made_recipes_bp.route("/admin/approve_recipe/<int:user_recipe_id>", methods=["POST"])
def approve_recipe(user_recipe_id):
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        # Check admin flag
        user = db.session.execute(
            text("SELECT admin FROM users WHERE userId=:uid"),
            {"uid": user_id}
        ).fetchone()

        if not user or not user[0]:
            return jsonify({"success": False, "message": "Admin only"}), 403

        # Get the user-submitted recipe
        row = db.session.execute(
            text("SELECT * FROM user_made_recipes WHERE id=:rid"), {"rid": user_recipe_id}
        ).fetchone()
        if not row:
            return jsonify({"success": False, "message": "Recipe not found"}), 404

        recipe_data = json.loads(row.recipe_data)

        # Insert into main recipes table
        db.session.execute(
            text("""
                INSERT INTO recipes (
                    Name, AuthorName, Description, RecipeCategory, Keywords,
                    PrepTime, CookTime, TotalTime, DatePublished,
                    AggregatedRating, ReviewCount, RecipeServings, RecipeYield,
                    RecipeIngredientQuantities, RecipeIngredientParts, RecipeInstructions,
                    NutritionFacts, Images, ingredients
                ) VALUES (
                    :Name, :AuthorName, :Description, :RecipeCategory, :Keywords,
                    :PrepTime, :CookTime, :TotalTime, :DatePublished,
                    :AggregatedRating, :ReviewCount, :RecipeServings, :RecipeYield,
                    :RecipeIngredientQuantities, :RecipeIngredientParts, :RecipeInstructions,
                    :NutritionFacts, :Images, :ingredients
                )
            """),
            {
                "Name": recipe_data.get("title", ""),
                "AuthorName": recipe_data.get("author", ""),
                "Description": recipe_data.get("description", ""),
                "RecipeCategory": recipe_data.get("category", ""),
                "Keywords": recipe_data.get("tags", ""),
                "PrepTime": recipe_data.get("prepTime", ""),
                "CookTime": recipe_data.get("cookTime", ""),
                "TotalTime": recipe_data.get("totalTime", ""),
                "DatePublished": recipe_data.get("datePublished", ""),
                "AggregatedRating": recipe_data.get("rating"),
                "ReviewCount": recipe_data.get("reviewCount"),
                "RecipeServings": recipe_data.get("servings", ""),
                "RecipeYield": recipe_data.get("yield", ""),
                "RecipeIngredientQuantities": json.dumps([i.get("amount", "") for i in recipe_data.get("ingredients", [])]),
                "RecipeIngredientParts": json.dumps([i.get("unit", "") for i in recipe_data.get("ingredients", [])]),
                "RecipeInstructions": json.dumps(recipe_data.get("instructions", [])),
                "NutritionFacts": json.dumps(recipe_data.get("nutrition", {})),
                "Images": recipe_data.get("image_url", ""),
                "ingredients": json.dumps([i.get("ingredient", "") for i in recipe_data.get("ingredients", [])]),
            }
        )

        # Delete from user_made_recipes
        db.session.execute(text("DELETE FROM user_made_recipes WHERE id=:rid"), {"rid": user_recipe_id})
        db.session.commit()

        return jsonify({"success": True, "message": "Recipe approved and moved to main recipes table"})

    except Exception as e:
        db.session.rollback()
        print("Error approving recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@user_made_recipes_bp.route("/get/<int:recipe_id>", methods=["GET"])
def get_user_recipe_by_id(recipe_id):
    """
    Fetches a single user-made recipe by its ID.
    Used for reliably loading a recipe after creation or from the 'Load' menu.
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        result = db.session.execute(
            text("SELECT id, recipe_data, submitted FROM user_made_recipes WHERE id = :rid AND userid = :uid"),
            {"rid": recipe_id, "uid": user_id}
        ).fetchone()

        if not result:
            return jsonify({"success": False, "message": "Recipe not found or unauthorized"}), 404

        recipe_data = {
            "id": result[0],
            "recipe": json.loads(result[1]),
            "submitted": bool(result[2])
        }

        return jsonify({"success": True, "recipe": recipe_data})

    except Exception as e:
        print(f"Error fetching recipe ID {recipe_id}:", e)
        return jsonify({"success": False, "message": str(e)}), 500


