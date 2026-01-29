from app.app import app
from app.extensions import db

with app.app_context():
    db.create_all()
    print("Database recreated successfully.")
