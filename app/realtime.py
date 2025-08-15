from flask import Blueprint, request, jsonify
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import pusher

realtime_bp = Blueprint("realtime", __name__)
CORS(realtime_bp)

PUSHER_APP_ID = os.getenv("PUSHER_APP_ID")
PUSHER_KEY = os.getenv("PUSHER_KEY")
PUSHER_SECRET = os.getenv("PUSHER_SECRET")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER", "mt1")


_pusher_client = None


def get_pusher_client():
    global _pusher_client
    if _pusher_client is None:
        if not (PUSHER_APP_ID and PUSHER_KEY and PUSHER_SECRET):
            raise RuntimeError("Faltan credenciales de Pusher en variables de entorno")
        _pusher_client = pusher.Pusher(
            app_id=PUSHER_APP_ID,
            key=PUSHER_KEY,
            secret=PUSHER_SECRET,
            cluster=PUSHER_CLUSTER,
            ssl=True,
        )
    return _pusher_client

@realtime_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

@realtime_bp.route("/pusher/auth", methods=["POST"])
@cross_origin()  # habilita CORS en este endpoint
@jwt_required()  # requiere JWT válido (mismo esquema que /auth/me)
def pusher_auth():
    """
    Autenticación de canales privados de Pusher.
    Pusher envía: form-data con 'channel_name' y 'socket_id'
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
        return jsonify({"error": "Forbidden channel"}), 403

    try:
        client = get_pusher_client()
        auth_payload = client.authenticate(channel=channel_name, socket_id=socket_id)
        return jsonify(auth_payload), 200
    except Exception as e:
        print(f"[Pusher Auth] Error: {e}")
        return jsonify({"error": "Pusher auth failed"}), 500