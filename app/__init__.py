# app/__init__.py
from flask import Flask
from .database import db 

def create_app():
    app = Flask(__name__)


    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:4567@localhost:5432/trelloclonegrupo1"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)

    return app