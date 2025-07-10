from flask import Blueprint, request, jsonify
from flask_cors import CORS, cross_origin
import re
from .database import db
from .models import Usuario

auth_bp = Blueprint("auth", __name__)
CORS(auth_bp)

@auth_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204


@auth_bp.route("/login", methods = ["POST"])
@cross_origin()
def iniciar_sesion():
    try:
        body = request.json

         # Validar que el body existe
        if not body:
            return jsonify({"ERROR": "Correo o contraseña invalidos"}), 400

        correo = body.get("correo", None)

        contrasena = body.get("contrasena", None)

        if not correo or not contrasena:
            return jsonify({"error": "Correo y contraseña son requeridos"}), 400

        usuario = Usuario.query.filter_by(correo = correo).first()

        if usuario is None:
            return jsonify({"error": "El usuario no existe"}), 404

        if usuario.verificar_contrasena(contrasena):
            return jsonify({
                "mensaje": "Login exitoso",
                "usuario": usuario.serialize()
            }), 200
        else:
            # Contraseña incorrecta
            return jsonify({"error": "Credenciales incorrectas"}), 401
    except Exception as error:
        print(f"Error en login: {str(error)}")
        # Retornar error genérico al cliente por seguridad
        return jsonify({"error": "Error interno del servidor"}), 500
