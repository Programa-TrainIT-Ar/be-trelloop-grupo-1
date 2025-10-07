# app/__init__.py
from flask import Flask
from flask_migrate import Migrate
from .database import db 

migrate = Migrate()

def create_app():
    app = Flask(__name__)


    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:1804@localhost:5432/trello-clone-grupo-1"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)

    migrate.init_app(app, db)

    return app