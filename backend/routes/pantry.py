from flask import Blueprint, jsonify, request, session

from sqlalchemy import text


from backend.databse import db

# Create a new blueprint for pantry routes
pantry_bp = Blueprint('pantry', __name__)



@pantry_bp.route("/items", methods=['GET'])
def getPantryItems():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401

        # Fetch pantry items from DB
        result = db.session.execute(
            text("SELECT items FROM pantry WHERE user_id = :uid"),
            {"uid": user_id}
        ).fetchone()

        items = []
        if result and result[0]:
            import json
            items = json.loads(result[0])

        return jsonify({
            "success": True,
            "items": items
        })

    except Exception as e:
        print(f"Error fetching pantry items: {e}")
        return jsonify({
            "success": False,
            "message": f"Error fetching pantry items: {str(e)}"
        }), 500


@pantry_bp.route("/items", methods=['POST'], strict_slashes=False)
def postPantryItems():
    """
    Add, update, or remove pantry items for a user.

    If an item in the request has amount = 0, it will be removed.
    """
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401

        data = request.get_json()
        print(f"Received JSON: {data}")  # Debugging
        if not data or "items" not in data:
            return jsonify({
                "success": False,
                "message": "No items provided"
            }), 400

        new_items = data["items"]

        existing = db.session.execute(
            text("SELECT items FROM pantry WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        print(f"Existing items: {existing}")  # Debugging
        import json

        if existing:
            # Load current items
            current_items = existing[0] or []
            if isinstance(current_items, str):
                current_items = json.loads(current_items)

            # Convert list to dict for merging/removing (keyed by name)
            item_map = {i["name"]: {"amount": i["amount"], "units": i.get("units", "")} for i in current_items}

            for item in new_items:
                name = item["name"]
                amount = item["amount"]
                units = item.get("units", "")  # default to empty string if not provided
                if amount == 0:
                    # Remove if exists
                    item_map.pop(name, None)
                else:
                    # Add or update
                    item_map[name] = {"amount": amount, "units": units}

            # Convert back to list format
            merged_items = [{"name": k, "amount": v["amount"], "units": v["units"]} for k, v in item_map.items()]

            # Update the DB
            db.session.execute(
                text("UPDATE pantry SET items = :items WHERE user_id = :uid"),
                {"items": json.dumps(merged_items), "uid": user_id},
            )

        else:
            # Filter out zero-amount items
            filtered_new_items = [i for i in new_items if i["amount"] != 0]
            if filtered_new_items:
                # Ensure each has units (default empty string)
                for i in filtered_new_items:
                    if "units" not in i:
                        i["units"] = ""
                db.session.execute(
                    text("INSERT INTO pantry (user_id, items) VALUES (:uid, :items)"),
                    {"uid": user_id, "items": json.dumps(filtered_new_items)},
                )
            else:
                return jsonify({
                    "success": True,
                    "message": "No nonzero items to add"
                })

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Pantry updated successfully",
        })

    except Exception as e:
        print(f"Error updating pantry: {e}")
        return jsonify({
            "success": False,
            "message": f"Error updating pantry: {str(e)}"
        }), 500


@pantry_bp.route('/search/ingredients', methods=['GET'], strict_slashes=False)
def search_by_ingredients():
    """
    Search recipes by ingredients.

    Query params:
    - q: Search query (required)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)

    Example: /api/recipes/search/ingredients?q=flour
    """
    try:
        search_query = request.args.get('q', '', type=str).strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        if not search_query:
            return jsonify({
                'success': False,
                'message': 'Search query is required'
            }), 400

        per_page = min(per_page, 100)
        offset = (page - 1) * per_page

        # This query searches for the search term in ingredients (comma-separated or space-separated)
        # and ensures only unique matches (using DISTINCT)
        query = text("""
                     SELECT DISTINCT ingredients
                     FROM recipes
                     WHERE ingredients LIKE :search
                         LIMIT :limit OFFSET :offset
                     """)

        search_param = f'%{search_query}%'
        result = db.session.execute(query, {
            'search': search_param,
            'limit': per_page,
            'offset': offset
        })

        matches = set()
        for row in result:
            # Split ingredients by comma and check each ingredient
            for ingredient in row[0].split(','):
                ingredient = ingredient.strip()
                if search_query.lower() in ingredient.lower():
                    matches.add(ingredient)

        matches = list(matches)

        # Get total count of unique matches
        count_query = text("""
                           SELECT COUNT(DISTINCT ingredient) FROM (
                                                                      SELECT TRIM(SUBSTRING_INDEX(SUBSTRING_INDEX(ingredients, ',', n.n), ',', -1)) as ingredient
                                                                      FROM recipes
                                                                               CROSS JOIN (SELECT 1 as n UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
                                                                                           UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8
                                                                                           UNION SELECT 9 UNION SELECT 10) n
                                                                      WHERE ingredients LIKE :search
                                                                  ) sub
                           """)
        total = db.session.execute(count_query, {'search': search_param}).scalar()

        return jsonify({
            'success': True,
            'matches': matches,
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

