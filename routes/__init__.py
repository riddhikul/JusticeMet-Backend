from bson import ObjectId
from flask import Blueprint, json, request, jsonify
from db_config import get_db
from models import case_schema
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import os
from ddos_limiter import limiter
import requests

# Load environment variables
def generate_key():
    # Check if the key already exists in memory
    if not hasattr(generate_key, "key"):
        # Generate a new encryption key
        generate_key.key = Fernet.generate_key()
        print("Encryption key generated.")
    return generate_key.key

# Initialize the key for encryption/decryption (this is called once when the app starts)
ENCRYPTION_KEY = generate_key()
print("ENC:", ENCRYPTION_KEY)
cipher_suite = Fernet(ENCRYPTION_KEY)

# Initialize MongoDB collections
case_routes = Blueprint('case_routes', __name__)
db = get_db()
cases_collection = db['cases']
users_collection = db['users']  # New collection for storing user data

# Signup API
@case_routes.route('/signup', methods=['POST'])
@limiter.limit("5 per minute")  # Apply rate limit
def signup_user():
    data = request.json
    
    # Validate input fields
    required_fields = ['name', 'email', 'profession']
    for field in required_fields:
        if field not in data or not data[field].strip():
            return jsonify({"error": f"'{field}' is required"}), 400

    # Check if the email is already registered
    existing_user = users_collection.find_one({"email": data['email']})
    if existing_user:
        return jsonify({"error": "Email is already registered"}), 409

    # Save user details (initialize 'case_ids' as an empty array)
    user = {
        "name": data['name'],
        "email": data['email'],
        "profession": data['profession'],
        "case_ids": []  # Initialize as an empty array
    }
    
    # Insert into MongoDB
    users_collection.insert_one(user)

    # Return success response
    return jsonify({"message": "User registered successfully"}), 201

# Add Case API
@case_routes.route('/cases', methods=['POST'])
@limiter.limit("5 per minute")  # Apply rate limit
def add_case():
    data = request.json

    # Extract inputs from the request body
    title = data.get("title")
    plaintiff = data.get("plaintiff")
    defendant = data.get("defendant")
    case_type = data.get("case_type")
    date_filed = data.get("date_filed")
    case_description = data.get("case_description")

    user_email = data.get("email")  # User email to associate the case

    # Validate input
    if not all([title, plaintiff, defendant, case_type, date_filed, case_description, user_email]):
        return jsonify({"error": "All fields, including email, are required"}), 400

    # Encrypt sensitive fields
    encrypted_plaintiff = cipher_suite.encrypt(plaintiff.encode())
    encrypted_defendant = cipher_suite.encrypt(defendant.encode())
    encrypted_case_description = cipher_suite.encrypt(case_description.encode())

    # Initial case schema
    case = {
        "title": title,
        "plaintiff": encrypted_plaintiff,
        "defendant": encrypted_defendant,
        "case_type": case_type,
        "date_filed": date_filed,
        "case_description": encrypted_case_description,
        "verdict": None,  # To be updated after bot response
        "articles_violated": [],
        "points_of_violation": [],
        "comment": None  # Additional bot response field
    }

    # Insert the case into the 'cases' collection
    result = cases_collection.insert_one(case)
    case_id = str(result.inserted_id)

    # Call the bot API
    bot_api_url = "https://justice-ai-b2lc.onrender.com/process_query/"  # Replace with the actual bot API URL
    bot_payload = {
        "case_details": case_description,
        "case_id": case_id,
        "case_title": title
    }
    try:
        bot_response = requests.post(bot_api_url, json=bot_payload)
        bot_response.raise_for_status()  # Raise an exception for HTTP errors
        bot_raw_data = bot_response.json()

        # Extract the JSON string from the 'response' field
        bot_response_string = bot_raw_data.get("response", "").strip("```json\n").strip("\n```")

        # Parse the extracted JSON string into a Python dictionary
        bot_data = json.loads(bot_response_string)
        print(bot_data)
        # Extract bot response fields
        verdict = bot_data.get("guilty_or_not")
        articles_violated = bot_data.get("articles_violated", [])
        points_of_violation = bot_data.get("points_of_violation", [])
        comment = bot_data.get("comment")
        # print(verdict)
        # print(articles_violated)
        # print(points_of_violation)
        # print(comment)
        verdict = "not guilty" if verdict == "no" else "guilty"
        # Update the case document with bot response
        cases_collection.update_one(
            {"_id": result.inserted_id},
            {
                "$set": {
                    "verdict": verdict,
                    "articles_violated": articles_violated,
                    "points_of_violation": points_of_violation,
                    "comment": comment
                }
            }
        )
        user_update_result = users_collection.update_one(
            {"email": user_email},
            {"$push": {"case_ids": case_id}}
        )

        if user_update_result.matched_count == 0:
            # If the user doesn't exist, rollback the case insertion
            cases_collection.delete_one({"_id": result.inserted_id})
            return jsonify({"error": "User not found. Case not associated with any user"}), 404

        # Success response
        return jsonify({
            "message": "Case added successfully",
            "case_id": case_id,
            "verdict": verdict,
            "articles_violated": articles_violated,
            "points_of_violation": points_of_violation,
            "comment": comment
        }), 201

    except requests.exceptions.RequestException as e:
        # Rollback case insertion if the bot API fails
        cases_collection.delete_one({"_id": result.inserted_id})
        return jsonify({"error": "Failed to process case with bot API", "details": str(e)}), 500

# Search Case API
@case_routes.route('/cases/search', methods=['GET'])
@limiter.limit("10 per minute")  # Apply rate limit
def search_case():
    title = request.args.get('title', None)
    
    if not title:
        return jsonify({"error": "Title query parameter is required"}), 400

    # Use regex for case-insensitive, partial matching
    cases = list(cases_collection.find({"title": {"$regex": f"^{title}.*", "$options": "i"}}))

    if not cases:
        return jsonify({"message": "No cases found"}), 404

    # Decrypt sensitive fields before returning
    for case in cases:
        case['_id'] = str(case['_id'])
        case['plaintiff'] = cipher_suite.decrypt(case['plaintiff']).decode()
        case['defendant'] = cipher_suite.decrypt(case['defendant']).decode()
        case['case_description'] = cipher_suite.decrypt(case['case_description']).decode()
    
    return jsonify(cases), 200

@case_routes.route('/user/<email>/cases', methods=['GET'])
@limiter.limit("5 per minute")  # Apply rate limit
def get_user_cases(email):
    # Find the user by email
    user = users_collection.find_one({"email": email})
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Get the list of case IDs from the user's document
    case_ids = user.get("case_ids", [])
    if not case_ids:
        return jsonify({"message": "No cases found for this user"}), 200

    # Fetch all cases from the 'cases' collection where '_id' is in the case_ids list
    cases = list(cases_collection.find({"_id": {"$in": [ObjectId(case_id) for case_id in case_ids]}}))

    # Convert MongoDB ObjectId to string for JSON serialization
    for case in cases:
        case['_id'] = str(case['_id'])
        case['plaintiff'] = cipher_suite.decrypt(case['plaintiff']).decode()
        case['defendant'] = cipher_suite.decrypt(case['defendant']).decode()
        case['case_description'] = cipher_suite.decrypt(case['case_description']).decode()
        # Add verdict to the response (already present in the case document)

    return jsonify(cases), 200

@case_routes.route('/cases/<case_id>/chat', methods=['POST'])
@limiter.limit("10 per minute")  # Apply rate limit
def chat_on_case(case_id):
    """
    Enables conversation based on the current case in context.
    """
    data = request.json

    # Validate input
    user_query = data.get("user_query")
    if not user_query:
        return jsonify({"error": "User query is required"}), 400

    # Call the chatbot API with the user's query and case_id
    bot_api_url = "https://justice-ai-b2lc.onrender.com/chat_query/"
    bot_payload = {
        "user_query": user_query,
        "case_id": case_id
    }
    try:
        bot_response = requests.post(bot_api_url, json=bot_payload)
        bot_response.raise_for_status()  # Raise exception for HTTP errors
        bot_data = bot_response.json()

        # Extract chatbot's response
        chat_response = bot_data.get("response", "No response from chatbot.")
        
        # Return the chatbot's response
        return jsonify({
            "case_id": case_id,
            "user_query": user_query,
            "chatbot_response": chat_response
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to connect to chatbot API", "details": str(e)}), 500
