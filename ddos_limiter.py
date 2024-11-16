# extensions.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Define the Limiter globally
limiter = Limiter(key_func=get_remote_address)
