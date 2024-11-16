from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv

# Generate the encryption key
key = Fernet.generate_key()

# Store it securely in the .env file
with open(".env", "a") as f:
    f.write(f"\nENCRYPTION_KEY={key.decode()}")
    
print("Key generated and stored in .env file.")
