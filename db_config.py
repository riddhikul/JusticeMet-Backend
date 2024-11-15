from pymongo import MongoClient

def get_db():
    client = MongoClient('mongodb+srv://mkv:mkv09@cluster0.kgq1cs6.mongodb.net/')
    return client['legal_chatbot']
