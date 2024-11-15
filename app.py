from flask import Flask
from flask_cors import CORS
from routes import case_routes

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# Register Routes
app.register_blueprint(case_routes)

if __name__ == '__main__':
    app.run(debug=True)
