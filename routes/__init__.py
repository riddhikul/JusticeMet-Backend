from flask import Blueprint, request, jsonify
from db_config import get_db
from models import case_schema

case_routes = Blueprint('case_routes', __name__)
db = get_db()
cases_collection = db['cases']

@case_routes.route('/cases', methods=['POST'])
def add_case():
    data = request.json
    case = case_schema()
    
    # Populate the schema with request data
    case.update({
        "title": data.get("title"),
        "plaintiff": data.get("plaintiff"),
        "defendant": data.get("defendant"),
        "case_type": data.get("case_type"),
        "date_filed": data.get("date_filed"),
        "case_description": data.get("case_description"),
        "verdict": data.get("verdict"),
        "articles_violated": data.get("articles_violated", []),
        "points_of_violation": data.get("points_of_violation", [])
    })
    
    # Insert into MongoDB
    cases_collection.insert_one(case)
    return jsonify({"message": "Case added successfully", "case_id": str(case["_id"])}), 201

@case_routes.route('/cases/search', methods=['GET'])
def search_case():
    title = request.args.get('title', None)
    
    if not title:
        return jsonify({"error": "Title query parameter is required"}), 400

    # Use regex for case-insensitive, partial matching
    cases = list(cases_collection.find({"title": {"$regex": f"^{title}.*", "$options": "i"}}))

    if not cases:
        return jsonify({"message": "No cases found"}), 404

    # Convert ObjectId to string and return results
    for case in cases:
        case['_id'] = str(case['_id'])
    
    return jsonify(cases), 200

