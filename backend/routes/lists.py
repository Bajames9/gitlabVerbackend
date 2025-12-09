from flask import Blueprint, jsonify, request, session

from sqlalchemy import text


from backend.databse import db

from backend.models.List import Lists

lists_bp = Blueprint('lists', __name__)



@lists_bp.route("/all",methods=['GET'])
def getAllListForUser():
    """
    Return all list IDs associated with the logged-in user.

    Response:
    {
        "success": true,
        "list_ids": [1, 2, 5, 10]
    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401


    try:
        # Query all list IDs for this user
        list_ids = [r.list_id for r in Lists.query.filter_by(owner_id=user_id).all()]

        return jsonify({
            "success": True,
            "list_ids": list_ids
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500







@lists_bp.route("/add", methods=["POST"])
def create_recipe_list():
    """
    - POST: creates a new list.
    Expected JSON:
    {
        "recipe_ids": [4000],  # single int or list
        "title": "Optional title"
        "public": True

    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        data = request.get_json()
        new_ids = data.get("recipe_ids")
        title = data.get("title")

        # if not new_ids:
        #     return jsonify({"success": False, "message": "No recipe IDs provided"}), 400
        if new_ids is None:
            new_ids = []

        # Ensure new_ids is a list
        if isinstance(new_ids, int):
            new_ids = [new_ids]
        elif not isinstance(new_ids, list):
            return jsonify({"success": False, "message": "recipe_ids must be a list or single integer"}), 400

        # Create new list

        is_public = data.get("public", False)  # default False
        recipe_list = Lists(
            owner_id=user_id,
            title=title or "Untitled List",
            recipe_ids=new_ids,
            is_public=is_public
        )

        db.session.add(recipe_list)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "New recipe list created successfully",
            "list": {
                "list_id": recipe_list.list_id,
                "title": recipe_list.title,
                "recipe_ids": recipe_list.recipe_ids,
                "public": recipe_list.is_public
            }
        }), 201  # Use 201 Created for resource creation

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500




@lists_bp.route("/update/<int:list_id>", methods=["PUT"])
def update_recipe_list(list_id):
    """
    - PUT with <list_id>: updates existing list, returns error if it doesn't exist.
    Expected JSON:
    {
        "recipe_ids": [4000],  # single int or list (recipes to add/append)
        "title": "Optional new title"
    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        data = request.get_json()
        new_ids = data.get("recipe_ids")
        title_in_data = "title" in data
        title = data.get("title")

        # You can allow an update if ONLY the title is being changed, or if new_ids is provided, or if public status is being changed.
        if not new_ids and not title_in_data and "public" not in data:
            return jsonify({"success": False, "message": "No recipe IDs, title, or public status provided for update"}), 400

        # Check list existence and ownership
        recipe_list = Lists.query.filter_by(list_id=list_id, owner_id=user_id).first()
        if not recipe_list:
            return jsonify({"success": False, "message": "List ID not found"}), 404

        # Handle recipe IDs update if they were provided
        if new_ids:
            # Ensure new_ids is a list
            if isinstance(new_ids, int):
                new_ids = [new_ids]
            elif not isinstance(new_ids, list):
                return jsonify({"success": False, "message": "recipe_ids must be a list or single integer"}), 400

            # Append new IDs without wiping existing ones and ensure uniqueness
            existing_ids = recipe_list.recipe_ids or []
            updated_ids = list(set(existing_ids + new_ids))
            recipe_list.recipe_ids = updated_ids

        # Handle title update if it was provided
        if title_in_data:
            recipe_list.title = title

        if "public" in data:
            recipe_list.is_public = bool(data["public"])

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Recipe list updated successfully",
            "list": {
                "list_id": recipe_list.list_id,
                "title": recipe_list.title,
                "recipe_ids": recipe_list.recipe_ids,
                "public": recipe_list.is_public
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500


@lists_bp.route("/remove-recipes/<int:list_id>", methods=["PUT"])
def remove_recipes_from_list(list_id):
    """
    Remove one or more recipe IDs from a user's list.

    Example Request:
        PUT /api/lists/remove-recipes/5
        {
            "recipe_ids": [4000, 4002]
        }

    Response:
    {
        "success": true,
        "message": "Recipes removed successfully",
        "list": {
            "list_id": 5,
            "title": "Favorites",
            "recipe_ids": [remaining ids]
        }
    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        data = request.get_json()
        remove_ids = data.get("recipe_ids")

        if not remove_ids:
            return jsonify({
                "success": False,
                "message": "No recipe IDs provided"
            }), 400

        # Ensure remove_ids is a list
        if isinstance(remove_ids, int):
            remove_ids = [remove_ids]
        elif not isinstance(remove_ids, list):
            return jsonify({
                "success": False,
                "message": "recipe_ids must be a list or single integer"
            }), 400

        # Get the list
        recipe_list = Lists.query.filter_by(list_id=list_id, owner_id=user_id).first()
        if not recipe_list:
            return jsonify({
                "success": False,
                "message": "List not found or not owned by user"
            }), 404

        # Remove specified recipe IDs
        existing_ids = recipe_list.recipe_ids or []
        updated_ids = [rid for rid in existing_ids if rid not in remove_ids]

        recipe_list.recipe_ids = updated_ids
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Recipes removed successfully",
            "list": {
                "list_id": recipe_list.list_id,
                "title": recipe_list.title,
                "recipe_ids": recipe_list.recipe_ids
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Server error: {str(e)}"
        }), 500


@lists_bp.route("/remove/<int:list_id>", methods=["DELETE"])
def delete_recipe_list(list_id):
    """
    Delete a recipe list by ID (only if it belongs to the logged-in user).

    Example Request:
        DELETE /api/lists/lists/5

    Returns:
    {
        "success": true,
        "message": "List deleted successfully"
    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        # Check list ownership
        recipe_list = Lists.query.filter_by(list_id=list_id, owner_id=user_id).first()
        if not recipe_list:
            return jsonify({"success": False, "message": "List not found or not owned by user"}), 404

        db.session.delete(recipe_list)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"List {list_id} deleted successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500





@lists_bp.route("/get/<int:list_id>", methods=["GET"])
def get_recipe_list(list_id):
    """
    Retrieve a specific recipe list and its recipes for the logged-in user.

    Example Request:
        GET /api/lists/12

    Response:
    {
        "success": true,
        "list": {
            "list_id": 12,
            "title": "Dinner Ideas",
            "recipe_ids": [49, 50, 76]
        }
    }
    """
    user_id = session.get("user_id")


    try:
        # Query list by ID and ownership
        recipe_list = Lists.query.filter_by(list_id=list_id).first()

        if not recipe_list:
            return jsonify({
                "success": False,
                "message": "List not found or not owned by user"
            }), 404

        if not recipe_list.is_public and (user_id is None or recipe_list.owner_id != user_id):
            return jsonify({
                "success": False,
                "message": "List not found or not accessible"
            }), 403

        return jsonify({
            "success": True,
            "list": {
                "list_id": recipe_list.list_id,
                "title": recipe_list.title,
                "recipe_ids": recipe_list.recipe_ids,
                "public": recipe_list.is_public
            }

        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@lists_bp.route("/generate-favorites", methods=["POST"])
def generate_favorites_list():
    """
    Generate a dedicated 'Favorites' list for the logged-in user.
    Automatically called on signup, but can be called manually.

    Returns:
    {
        "success": true,
        "message": "Favorites list created successfully",
        "list": {
            "list_id": 1,
            "title": "Favorites",
            "recipe_ids": []
        }
    }
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not logged in"}), 401

    try:
        # Check if user already has a favorites list
        existing_fav = Lists.query.filter_by(owner_id=user_id, title="Favorites").first()
        if existing_fav:
            return jsonify({
                "success": True,
                "message": "Favorites list already exists",
                "list": {
                    "list_id": existing_fav.list_id,
                    "title": existing_fav.title,
                    "recipe_ids": existing_fav.recipe_ids
                }
            }), 200

        # Otherwise, create a new one
        favorites_list = Lists(
            owner_id=user_id,
            title="Favorites",
            recipe_ids=[]
        )
        db.session.add(favorites_list)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Favorites list created successfully",
            "list": {
                "list_id": favorites_list.list_id,
                "title": favorites_list.title,
                "recipe_ids": favorites_list.recipe_ids
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500



@lists_bp.route("/favorites", methods=['GET'])
def get_favorites_list():
    """
    Return the Favorites list for the logged-in user.

    Response:
    {
        "success": true/false,
        "message": "...",
        "list": { ... }  # Only included if found
    }
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401

        favorites_list = Lists.query.filter_by(owner_id=user_id, title="Favorites").first()

        if not favorites_list:
            return jsonify({
                "success": False,
                "message": "Favorites list not found"
            }), 404

        return jsonify({
            "success": True,
            "list": {
                "id": favorites_list.list_id,
                "title": favorites_list.title,
                "recipe_ids": favorites_list.recipe_ids,
                "public": favorites_list.is_public
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@lists_bp.route('/search-public', methods=['GET'], strict_slashes=False)
def search_public_lists():
    """
    Search public recipe lists by title

    Query params:
    - q: Search query (required)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)

    Example: /api/lists/search-public?q=dinner
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

        # Search only in public lists by title
        query = text("""
            SELECT list_id, title, recipe_ids, is_public
            FROM RecipeLists
            WHERE is_public = 1 AND title LIKE :search
            LIMIT :limit OFFSET :offset
        """)

        search_param = f'%{search_query}%'
        result = db.session.execute(query, {
            'search': search_param,
            'limit': per_page,
            'offset': offset
        })

        lists = []
        for row in result:
            lists.append({
                'list_id': row[0],
                'title': row[1],
                'recipe_ids': row[2],
                'public': bool(row[3])
            })

        # Get total count of matching public lists
        count_query = text("""
            SELECT COUNT(*) FROM RecipeLists
            WHERE is_public = 1 AND title LIKE :search
        """)
        total = db.session.execute(count_query, {'search': search_param}).scalar()

        return jsonify({
            'success': True,
            'lists': lists,
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
            'message': str(e)
        }), 500

