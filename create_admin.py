from app import app
from database import db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    existing_admin = User.query.filter_by(email="admin@chilili.com").first()

    if existing_admin:
        print("Admin account already exists.")
    else:
        admin = User(
            full_name="CHILILI Admin",
            email="admin@chilili.com",
            phone="08000000000",
            password=generate_password_hash("admin123"),
            wallet_balance=0.0,
            role="admin"
        )

        db.session.add(admin)
        db.session.commit()

        print("Admin account created successfully.")