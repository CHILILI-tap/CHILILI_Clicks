import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "chilili-clicks-secret-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///chilili.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False