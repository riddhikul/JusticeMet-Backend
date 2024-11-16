from flask import Flask
from flask_cors import CORS
from routes import case_routes
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from ddos_limiter import limiter

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable Cross-Origin Resource Sharing

# limiter = Limiter(app, key_func=get_remote_address)
# Register Routes
app.register_blueprint(case_routes)
# limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

if __name__ == '__main__':
    app.run(debug=True)
