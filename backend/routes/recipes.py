"""
Recipe routes - Browse, search, and retrieve recipes
"""
from flask import Blueprint, jsonify, request, session
from sqlalchemy import text
from backend.databse import db
import json
import random

recipes_bp = Blueprint('recipes', __name__)

# This will be injected when blueprint is registered

# Columns in the main recipes table that admins are allowed to update
ALLOWED_RECIPE_FIELDS = [
    "Name",
    "AuthorName",
    "Description",
    "RecipeCategory",
    "Keywords",
    "CookTime",
    "PrepTime",
    "TotalTime",
    "DatePublished",
    "AggregatedRating",
    "ReviewCount",
    "RecipeServings",
    "RecipeYield",
    "RecipeIngredientQuantities",
    "RecipeIngredientParts",
    "RecipeInstructions",
    "NutritionFacts",
    "Images",
    "ingredients",
]

def init_recipes_routes(database):
    """Initialize the recipes routes with database connection"""


@recipes_bp.route('', methods=['GET'], strict_slashes=False)
def get_recipes():
    """
    Get paginated list of recipes
    
    Query params:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    
    Example: /api/recipes?page=1&per_page=20
    """
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Limit per_page to prevent excessive queries
        per_page = min(per_page, 100)
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Query recipes
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description, 
                   RecipeCategory, AggregatedRating, ReviewCount,
                   Images
            FROM recipes
            LIMIT :limit OFFSET :offset
        """)
        
        result = db.session.execute(query, {'limit': per_page, 'offset': offset})
        recipes = []
        
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7].split(',')[0].strip('c("').strip('"') if row[7] else None
            })
        
        # Get total count for pagination info
        count_query = text("SELECT COUNT(*) FROM recipes")
        total = db.session.execute(count_query).scalar()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching recipes: {str(e)}'
        }), 500



@recipes_bp.route('/<int:recipe_id>', methods=['GET'], strict_slashes=False)
def get_recipe(recipe_id):
    """
    Get a specific recipe by ID

    Example: /api/recipes/38
    """
    try:
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, Keywords, CookTime, PrepTime, TotalTime,
                   DatePublished, AggregatedRating, ReviewCount, 
                   RecipeServings, RecipeYield,
                   RecipeIngredientQuantities, RecipeIngredientParts,
                   RecipeInstructions, NutritionFacts, Images ,ingredients
            FROM recipes
            WHERE RecipeId = :recipe_id
        """)

        result = db.session.execute(query, {'recipe_id': recipe_id}).fetchone()

        if not result:
            return jsonify({
                'success': False,
                'message': 'Recipe not found'
            }), 404

        # Unpack in order of SELECT columns
        recipe = {
            'id': result[0],
            'name': result[1],
            'author': result[2],
            'description': result[3],
            'category': result[4],
            'keywords': result[5],
            'cookTime': result[6],
            'prepTime': result[7],
            'totalTime': result[8],
            'datePublished': result[9],
            'rating': float(result[10]) if result[10] else None,
            'reviewCount': result[11],
            'servings': result[12],
            'yield': result[13],
            'quantities': result[14],
            'ingredients': result[15],
            'ingredientsParts': result[19],
            'instructions': result[16],
            'nutritionFacts': result[17],  # likely a JSON string
            'images': result[18]
        }

        # Optionally parse NutritionFacts if it's JSON
        try:
            if recipe['nutritionFacts']:
                recipe['nutritionFacts'] = json.loads(recipe['nutritionFacts'])
        except Exception:
            pass  # leave as string if not JSON

        return jsonify({
            'success': True,
            'recipe': recipe
        }), 200

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching recipe: {str(e)}'
        }), 500

@recipes_bp.route('/search', methods=['GET'], strict_slashes=False)
def search_recipes():
    """
    Search recipes by name or ingredient
    
    Query params:
    - q: Search query (searches in name, description, ingredients)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    
    Example: /api/recipes/search?q=chicken&page=1
    """
    try:
        search_query = request.args.get('q', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        per_page = min(per_page, 100)
        offset = (page - 1) * per_page
        
        # Search in name, description, and ingredients
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, AggregatedRating, ReviewCount, Images
            FROM recipes
            WHERE Name LIKE :search
               OR Description LIKE :search
               OR RecipeIngredientParts LIKE :search
            LIMIT :limit OFFSET :offset
        """)
        
        search_param = f'%{search_query}%'
        result = db.session.execute(query, {
            'search': search_param,
            'limit': per_page,
            'offset': offset
        })
        
        recipes = []
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7]
            })
        
        # Get count of search results
        count_query = text("""
            SELECT COUNT(*) FROM recipes
            WHERE Name LIKE :search
               OR Description LIKE :search
               OR RecipeIngredientParts LIKE :search
        """)
        total = db.session.execute(count_query, {'search': search_param}).scalar()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'query': search_query,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error searching recipes: {str(e)}'
        }), 500


@recipes_bp.route('/search/ingredients', methods=['GET'], strict_slashes=False)
def search_by_ingredients():
    """
    Search recipes by ingredients only
    
    Query params:
    - q: Ingredient search query (searches only in RecipeIngredientParts)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20)
    
    Example: /api/recipes/search/ingredients?q=chicken&page=1
    """
    try:
        search_query = request.args.get('q', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        per_page = min(per_page, 100)
        offset = (page - 1) * per_page
        
        # Search ONLY in ingredients
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, AggregatedRating, ReviewCount, Images
            FROM recipes
            WHERE RecipeIngredientParts LIKE :search
            LIMIT :limit OFFSET :offset
        """)
        
        search_param = f'%{search_query}%'
        result = db.session.execute(query, {
            'search': search_param,
            'limit': per_page,
            'offset': offset
        })
        
        recipes = []
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7]
            })
        
        # Get count of search results
        count_query = text("""
            SELECT COUNT(*) FROM recipes
            WHERE RecipeIngredientParts LIKE :search
        """)
        total = db.session.execute(count_query, {'search': search_param}).scalar()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'query': search_query,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error searching recipes by ingredients: {str(e)}'
        }), 500
"""
Search by recipe name added by Payton
"""
@recipes_bp.route('/search/name', methods=['GET'], strict_slashes=False)
def search_by_name():
    """
    Search recipes by recipe name ONLY
    
    Query params:
    - q: Search query (required)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    
    Example: /api/recipes/search/name?q=lasagna
    """
    try:
        search_query = request.args.get('q', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400
        
        per_page = min(per_page, 100)
        offset = (page - 1) * per_page
        
        # Search ONLY in Name
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, AggregatedRating, ReviewCount, Images
            FROM recipes
            WHERE Name LIKE :search
            LIMIT :limit OFFSET :offset
        """)
        
        search_param = f'%{search_query}%'
        result = db.session.execute(query, {
            'search': search_param,
            'limit': per_page,
            'offset': offset
        })
        
        recipes = []
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7]
            })
        
        # Get total count
        count_query = text("SELECT COUNT(*) FROM recipes WHERE Name LIKE :search")
        total = db.session.execute(count_query, {'search': search_param}).scalar()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'query': search_query,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error searching recipes by name: {str(e)}'
        }), 500

@recipes_bp.route('/category', methods=['GET'], strict_slashes=False)
def get_recipes_by_category():
    """
    Get recipes filtered by category
    
    Query params:
    - name: Category name (e.g., "Beverages", "Dessert", "Main Dish")
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    
    Example: /api/recipes/category?name=Beverages&page=1
    """
    try:
        category_name = request.args.get('name', '', type=str)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if not category_name:
            return jsonify({
                'success': False,
                'message': 'Category name is required'
            }), 400
        
        per_page = min(per_page, 100)
        offset = (page - 1) * per_page
        
        # Filter by category
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, AggregatedRating, ReviewCount, Images
            FROM recipes
            WHERE RecipeCategory LIKE :category
            LIMIT :limit OFFSET :offset
        """)
        
        category_param = f'%{category_name}%'
        result = db.session.execute(query, {
            'category': category_param,
            'limit': per_page,
            'offset': offset
        })
        
        recipes = []
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7]
            })
        
        # Get count of recipes in this category
        count_query = text("""
            SELECT COUNT(*) FROM recipes
            WHERE RecipeCategory LIKE :category
        """)
        total = db.session.execute(count_query, {'category': category_param}).scalar()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'category': category_name,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching recipes by category: {str(e)}'
        }), 500

@recipes_bp.route('/admin/update/<int:recipe_id>', methods=['PUT'])
def admin_update_recipe(recipe_id):
    """
    Admin-only: update an existing recipe in the main `recipes` table.

    Expects JSON with any subset of these keys (matching DB columns):
    Name, AuthorName, Description, RecipeCategory, Keywords,
    CookTime, PrepTime, TotalTime, DatePublished,
    AggregatedRating, ReviewCount, RecipeServings, RecipeYield,
    RecipeIngredientQuantities, RecipeIngredientParts,
    RecipeInstructions, NutritionFacts, Images, ingredients
    """
    try:
        user_id = session.get("user_id")
        is_admin = session.get("admin")

        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        if not is_admin:
            return jsonify({"success": False, "message": "Admin only"}), 403

        data = request.get_json() or {}
        if not data:
            return jsonify({"success": False, "message": "No fields provided to update"}), 400

        # Only keep allowed columns
        updates = {k: v for k, v in data.items() if k in ALLOWED_RECIPE_FIELDS}
        if not updates:
            return jsonify({"success": False, "message": "No valid fields to update"}), 400

        # Build dynamic SET clause
        set_clauses = []
        params = {"rid": recipe_id}
        for idx, (col, val) in enumerate(updates.items()):
            param_name = f"v{idx}"
            set_clauses.append(f"{col} = :{param_name}")
            params[param_name] = val

        sql = f"""
            UPDATE recipes
            SET {', '.join(set_clauses)}
            WHERE RecipeId = :rid
        """

        result = db.session.execute(text(sql), params)

        if result.rowcount == 0:
            db.session.rollback()
            return jsonify({"success": False, "message": "Recipe not found"}), 404

        db.session.commit()
        return jsonify({"success": True, "message": "Recipe updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("Error updating recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@recipes_bp.route('/admin/delete/<int:recipe_id>', methods=['DELETE'])
def admin_delete_recipe(recipe_id):
    """
    Admin-only: delete a recipe from the main `recipes` table.
    """
    try:
        user_id = session.get("user_id")
        is_admin = session.get("admin")

        if not user_id:
            return jsonify({"success": False, "message": "Not logged in"}), 401

        if not is_admin:
            return jsonify({"success": False, "message": "Admin only"}), 403

        result = db.session.execute(
            text("DELETE FROM recipes WHERE RecipeId = :rid"),
            {"rid": recipe_id}
        )

        if result.rowcount == 0:
            db.session.rollback()
            return jsonify({"success": False, "message": "Recipe not found"}), 404

        db.session.commit()
        return jsonify({"success": True, "message": "Recipe deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        print("Error deleting recipe:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@recipes_bp.route('/random', methods=['GET'], strict_slashes=False)
def get_random_recipes():
    """
    Get random recipes for homepage display
    
    Query params:
    - count: Number of random recipes (default: 10, max: 50)
    
    Example: /api/recipes/random?count=10
    """
    try:
        count = request.args.get('count', 10, type=int)
        count = min(count, 50)  # Limit to 50
        
        query = text("""
            SELECT RecipeId, Name, AuthorName, Description,
                   RecipeCategory, AggregatedRating, ReviewCount, Images
            FROM recipes
            ORDER BY RAND()
            LIMIT :count
        """)
        
        result = db.session.execute(query, {'count': count})
        recipes = []
        
        for row in result:
            recipes.append({
                'id': row[0],
                'name': row[1],
                'author': row[2],
                'description': row[3],
                'category': row[4],
                'rating': float(row[5]) if row[5] else None,
                'reviewCount': row[6],
                'image': row[7]
            })
        
        return jsonify({
            'success': True,
            'recipes': recipes
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching random recipes: {str(e)}'
        }), 500


@recipes_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """
    Get recipe recommendations based on user's pantry items
    Matches pantry ingredients to recipe ingredientsParts field
    Returns top 12 recipes sorted by match count with randomization
    
    Example: /api/recipes/recommendations
    Requires login to access user's pantry
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401
    
    try:
        # Get user's pantry items
        pantry_query = text("SELECT items FROM pantry WHERE user_id = :user_id")
        pantry_result = db.session.execute(pantry_query, {"user_id": user_id}).fetchone()
        
        if not pantry_result or not pantry_result[0]:
            # No pantry items - return random recipes
            random_query = text("""
                SELECT RecipeId, Name, Images, AggregatedRating, RecipeCategory
                FROM recipes
                WHERE Images IS NOT NULL AND Images != ''
                ORDER BY RAND()
                LIMIT 12
            """)
            random_recipes = db.session.execute(random_query).fetchall()
            
            recipes_list = [{
                "id": r[0],
                "name": r[1],
                "images": r[2],
                "rating": r[3],
                "category": r[4],
                "matchCount": 0
            } for r in random_recipes]
            
            return jsonify({
                "success": True,
                "recipes": recipes_list,
                "message": "No pantry items found, showing random recipes"
            }), 200
        
        # Parse pantry items (stored as JSON array)
        pantry_items = json.loads(pantry_result[0])
        pantry_ingredients = [item["name"].lower().strip() for item in pantry_items]
        
        if not pantry_ingredients:
            # Empty pantry - return random recipes
            random_query = text("""
                SELECT RecipeId, Name, Images, AggregatedRating, RecipeCategory
                FROM recipes
                WHERE Images IS NOT NULL AND Images != ''
                ORDER BY RAND()
                LIMIT 12
            """)
            random_recipes = db.session.execute(random_query).fetchall()
            
            recipes_list = [{
                "id": r[0],
                "name": r[1],
                "images": r[2],
                "rating": r[3],
                "category": r[4],
                "matchCount": 0
            } for r in random_recipes]
            
            return jsonify({
                "success": True,
                "recipes": recipes_list,
                "message": "Empty pantry, showing random recipes"
            }), 200
        
        # Get all recipes with ingredients field
        recipes_query = text("""
            SELECT RecipeId, Name, Images, AggregatedRating, RecipeCategory, ingredients
            FROM recipes
            WHERE ingredients IS NOT NULL 
            AND ingredients != ''
            AND Images IS NOT NULL 
            AND Images != ''
        """)
        all_recipes = db.session.execute(recipes_query).fetchall()
        
        # Score each recipe based on matching ingredients
        scored_recipes = []
        for recipe in all_recipes:
            recipe_id, name, images, rating, category, ingredients_parts = recipe
            
            if not ingredients_parts:
                continue
            
            # Parse recipe ingredients (comma-separated string)
            recipe_ingredients = [ing.lower().strip() for ing in ingredients_parts.split(',')]
            
            # Count matches
            match_count = 0
            for pantry_item in pantry_ingredients:
                for recipe_ingredient in recipe_ingredients:
                    # Check if pantry item is in recipe ingredient
                    # e.g., "chicken" matches "chicken breast"
                    if pantry_item in recipe_ingredient or recipe_ingredient in pantry_item:
                        match_count += 1
                        break  # Count each pantry item only once per recipe
            
            if match_count > 0:
                scored_recipes.append({
                    "id": recipe_id,
                    "name": name,
                    "images": images,
                    "rating": rating,
                    "category": category,
                    "matchCount": match_count
                })
        
        # Sort by match count (descending)
        scored_recipes.sort(key=lambda x: x["matchCount"], reverse=True)
        
        # Add some randomization while maintaining priority
        # Take top 30 matches, shuffle them, then take top 12
        # This gives variety while still prioritizing good matches
        if len(scored_recipes) > 30:
            top_matches = scored_recipes[:30]
            random.shuffle(top_matches)
            final_recipes = top_matches[:12]
        elif len(scored_recipes) > 12:
            # Shuffle all and take 12
            random.shuffle(scored_recipes)
            final_recipes = scored_recipes[:12]
        else:
            # Fewer than 12 matches - add random recipes to fill
            final_recipes = scored_recipes
            needed = 12 - len(final_recipes)
            if needed > 0:
                random_query = text("""
                    SELECT RecipeId, Name, Images, AggregatedRating, RecipeCategory
                    FROM recipes
                    WHERE Images IS NOT NULL AND Images != ''
                    ORDER BY RAND()
                    LIMIT :limit
                """)
                random_recipes = db.session.execute(random_query, {"limit": needed}).fetchall()
                
                for r in random_recipes:
                    final_recipes.append({
                        "id": r[0],
                        "name": r[1],
                        "images": r[2],
                        "rating": r[3],
                        "category": r[4],
                        "matchCount": 0
                    })
        
        return jsonify({
            "success": True,
            "recipes": final_recipes,
            "pantryItems": pantry_ingredients
        }), 200
        
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
    
@recipes_bp.route('/<int:recipe_id>/missing-ingredients', methods=['GET'])
def get_missing_ingredients(recipe_id):
    """
    Compare recipe ingredients with user's pantry to find missing items
    
    Returns:
    {
        "success": true,
        "missing_ingredients": ["chicken breast", "tomatoes"],
        "pantry_items": ["onion", "garlic"],
        "recipe_ingredients": ["chicken breast", "onion", "garlic", "tomatoes"]
    }
    """
    user_id = session.get("user_id")
    
    # Allow non-logged-in users - just return all ingredients as missing
    if not user_id:
        try:
            # Get recipe ingredients
            recipe_query = text("""
                SELECT RecipeIngredientParts 
                FROM recipes 
                WHERE RecipeId = :recipe_id
            """)
            recipe_result = db.session.execute(recipe_query, {"recipe_id": recipe_id}).fetchone()
            
            if not recipe_result or not recipe_result[0]:
                return jsonify({
                    "success": False,
                    "message": "Recipe not found or has no ingredients"
                }), 404
            
            # Parse recipe ingredients
            recipe_ingredients = [ing.strip() for ing in recipe_result[0].split(',')]
            
            return jsonify({
                "success": True,
                "missing_ingredients": recipe_ingredients,
                "pantry_items": [],
                "recipe_ingredients": recipe_ingredients,
                "message": "Login to track pantry items"
            }), 200
            
        except Exception as e:
            return jsonify({
                "success": False,
                "message": f"Error: {str(e)}"
            }), 500
    
    # Logged in user - compare with pantry
    try:
        # Get user's pantry items
        pantry_query = text("SELECT items FROM pantry WHERE user_id = :user_id")
        pantry_result = db.session.execute(pantry_query, {"user_id": user_id}).fetchone()
        
        pantry_items = []
        if pantry_result and pantry_result[0]:
            pantry_data = json.loads(pantry_result[0])
            pantry_items = [item["name"].lower().strip() for item in pantry_data]
        
        # Get recipe ingredients
        recipe_query = text("""
            SELECT RecipeIngredientParts 
            FROM recipes 
            WHERE RecipeId = :recipe_id
        """)
        recipe_result = db.session.execute(recipe_query, {"recipe_id": recipe_id}).fetchone()
        
        if not recipe_result or not recipe_result[0]:
            return jsonify({
                "success": False,
                "message": "Recipe not found or has no ingredients"
            }), 404
        
        # Parse recipe ingredients (comma-separated string)
        recipe_ingredients = [ing.strip() for ing in recipe_result[0].split(',')]
        
        # Find missing ingredients
        missing = []
        for recipe_ing in recipe_ingredients:
            recipe_ing_lower = recipe_ing.lower()
            
            # Check if any pantry item matches this recipe ingredient
            found = False
            for pantry_item in pantry_items:
                # Check for partial matches (e.g., "chicken" matches "chicken breast")
                if pantry_item in recipe_ing_lower or recipe_ing_lower in pantry_item:
                    found = True
                    break
            
            if not found:
                missing.append(recipe_ing)
        
        return jsonify({
            "success": True,
            "missing_ingredients": missing,
            "pantry_items": [item for item in recipe_ingredients if item not in missing],
            "recipe_ingredients": recipe_ingredients
        }), 200
        
    except Exception as e:
        print(f"Error checking missing ingredients: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500