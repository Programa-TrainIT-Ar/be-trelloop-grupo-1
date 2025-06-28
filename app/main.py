from flask import Flask, request, jsonify
from flask_cors import CORS
from .config import DATABASE_URL, CORS_ORIGINS
from .database import db
from .models import Message

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
CORS(app, origins=CORS_ORIGINS)
db.init_app(app)

@app.route("/message", methods=["POST"])
def post_message():
     data = request.json
     msg = Message(content=data["content"])
     db.session.add(msg)
     db.session.commit()
     return jsonify({"id": msg.id, "content": msg.content}), 201

@app.route("/message", methods=["GET"])
def get_messages():
     msgs = Message.query.all()
     return jsonify([{"id": m.id, "content": m.content} for m in msgs])

if __name__ == "__main__":
     with app.app_context():
          db.create_all()
     app.run(host="0.0.0.0", port=5000)
