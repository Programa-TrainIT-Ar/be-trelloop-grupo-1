from flask import Flask, request, jsonify
from flask_cors import CORS
from .config import DATABASE_URL, CORS_ORIGINS, DEBUG
from .database import db, inicializar_base_de_datos
from .models import Message
from flask_migrate import Migrate
from .auth import auth_bp
from flask_jwt_extended import JWTManager
from datetime import timedelta

app = Flask(__name__)

# Configuración de la base de datos
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["DEBUG"] = DEBUG

CORS(app, origins=CORS_ORIGINS, supports_credentials=True)
db = inicializar_base_de_datos(app)

migrate = Migrate(app, db)


app.config["JWT_SECRET_KEY"] = "super-secret"  # Change this!
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
jwt = JWTManager(app)

# Estaba repetido el blueprint, asi que lo eliminamos y dejamos este.
app.register_blueprint(auth_bp, url_prefix="/auth")


@app.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

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
     app.run(host="0.0.0.0", port=5000, debug=True)
