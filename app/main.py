from flask import Flask, request, jsonify, url_for
from flask_cors import CORS
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from .config import DATABASE_URL, CORS_ORIGINS, DEBUG, JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, JWT_REFRESH_TOKEN_EXPIRES
from .database import db, initialize_database
from .models import Message, User, Board, Tag, Card
from .auth import auth_bp
from .board import board_bp
from .tag import tag_bp
from .card import card_bp
from .realtime import realtime_bp
from .services.notifications import create_notification
from .services.pusher_client import get_pusher_client
from datetime import timedelta
import os

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

# Blueprint para relacionar archico principal con el manejo de autenticación y tableros
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(board_bp, url_prefix="/board")
app.register_blueprint(tag_bp, url_prefix="/tag")
app.register_blueprint(card_bp, url_prefix="/card")
app.register_blueprint(realtime_bp, url_prefix="/realtime")

# Pusher Auth endpoint

@app.route("/pusher/auth", methods=["POST"])
@jwt_required()
def pusher_auth():
    """
    Endpoint de autenticación para canales privados de Pusher.
    Debe estar en la raíz para coincidir con la configuración del frontend.
    """
    # Usuario autenticado por JWT
    user_id = str(get_jwt_identity())

    # Leer datos ya sea desde form-data o JSON
    channel_name = request.form.get("channel_name") or (request.json or {}).get("channel_name")
    socket_id = request.form.get("socket_id") or (request.json or {}).get("socket_id")

    if not channel_name or not socket_id:
        return jsonify({"error": "channel_name y socket_id son requeridos"}), 400

    # Solo permitir el canal privado del propio usuario
    expected_channel = f"private-user-{user_id}"
    if channel_name != expected_channel:
        app.logger.warning(f"[pusher_auth] User {user_id} tried to auth for channel {channel_name}")
        return jsonify({"error": "Forbidden channel"}), 403

    try:
        client = get_pusher_client()
        auth_payload = client.authenticate(channel=channel_name, socket_id=socket_id)
        app.logger.info(f"[pusher_auth] Authenticated user {user_id} for channel {channel_name}")
        return jsonify(auth_payload), 200
    except Exception as e:
        app.logger.error(f"[pusher_auth] Error: {e}")
        return jsonify({"error": "Pusher auth failed"}), 500


@app.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

#PRUEBA PUSHER----------------------------------------------------------------------------------------------------------

@app.route("/test-notif", methods=["POST"])
def test_notification():
    data = request.json
    with db.session.begin():  # abre un contexto de sesión
        notif = create_notification(
            db.session,  # <-- PASA la sesión, no db directamente
            user_id=data.get("userid", 1),
            type_="test",
            title=data.get("title", "Notificación de prueba"),
            message=data.get("message", "Esto es un test"),
            send_email_also=False
        )
    return {"status": "ok", "notif_id": notif.id}

#---------------------------------------------------------------------------------------------------------------------------------

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
    app.run(host="0.0.0.0", port=5000, debug=True)
