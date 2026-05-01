from backend.mongo_database import db

def get_db():
    yield db
