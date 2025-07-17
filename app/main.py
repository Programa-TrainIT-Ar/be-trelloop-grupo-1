from flask import Flask, request, jsonify
from flask_cors import CORS
from .config import DATABASE_URL, CORS_ORIGINS, DEBUG, JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES
from .database import db, initialize_database
from .models import Message, User
from flask_migrate import Migrate
from .auth import auth_bp
from flask_jwt_extended import JWTManager
from datetime import timedelta

app = Flask(__name__)

# Configuración de la base de datos
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["DEBUG"] = DEBUG

CORS(app, origins=CORS_ORIGINS, supports_credentials=True)
initialize_database(app)

migrate = Migrate(app, db)


# Configuración de JWT
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=JWT_ACCESS_TOKEN_EXPIRES)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(seconds=JWT_REFRESH_TOKEN_EXPIRES)
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
jwt = JWTManager(app)

# Callback para cargar el usuario desde el token JWT
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """
    Función que carga el usuario a partir del token JWT.
    Se ejecuta automáticamente cuando se usa @jwt_required()
    """
    identity = jwt_data["sub"]
    return User.query.filter_by(id=identity).one_or_none()

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
