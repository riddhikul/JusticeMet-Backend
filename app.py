from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from routes import case_routes

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Initialize MongoDB
client = MongoClient('mongodb+srv://mkv:mkv09@cluster0.kgq1cs6.mongodb.net/')
db = client['legal_chatbot']

# Register Routes
app.register_blueprint(case_routes)

if __name__ == '__main__':
    app.run(debug=True)
