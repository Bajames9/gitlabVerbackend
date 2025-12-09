from flask import Blueprint, jsonify, request, session

from sqlalchemy import text
from backend.databse import db

# Create a new blueprint for Grocery routes
grocery_bp = Blueprint('grocery', __name__)

@grocery_bp.route("/items", methods=['GET'])
def getGroceryItems():
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({
                "success": False,
                "message": "Not logged in"
            }), 401


        result = db.session.execute(
            text("SELECT items FROM groceryList WHERE user_id = :uid"),
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
        print(f"Error fetching grocery items: {e}")
        return jsonify({
            "success": False,
            "message": f"Error fetching grocery items: {str(e)}"
        }), 500


@grocery_bp.route("/items", methods=['POST'], strict_slashes=False)
def postGroceryItems():
    """
    Add, update, or remove grocery items for a user.

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

        for item in new_items:
            name = item.get("name", "").strip()
            amount = item.get("amount", 0)

            # Validate amount
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "message": f"Invalid amount for item '{name}'"
                }), 400

            if amount < 0:
                return jsonify({
                    "success": False,
                    "message": f"Invalid amount for item '{name}'"
                }), 400

            # Only validate name if item is being added/updated
            if amount != 0:
                if not name:
                    return jsonify({
                        "success": False,
                        "message": "Invalid item name"
                    }), 400
                if len(name) > 100:
                    return jsonify({
                        "success": False,
                        "message": "Invalid item name"
                    }), 400

            # Update the item with cleaned values
            item["name"] = name
            item["amount"] = amount

        existing = db.session.execute(
            text("SELECT items FROM groceryList WHERE user_id = :uid"),
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
                text("UPDATE groceryList SET items = :items WHERE user_id = :uid"),
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
                    text("INSERT INTO groceryList (user_id, items) VALUES (:uid, :items)"),
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
            "message": "grocery list updated successfully",
        })

    except Exception as e:
        print(f"Error updating grocery list: {e}")
        return jsonify({
            "success": False,
            "message": f"Error updating grocery list: {str(e)}"
        }), 500



