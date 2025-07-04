from flask import Blueprint, request, jsonify
import re
from .database import db
from .models import Usuario, verificar_contrasena

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods = ["POST", "GET"])
def iniciar_sesion():
    body = request.json
    correo = body.get("correo", None)
    contrasena = body.get("contrasena", None)

    usuario = User.query.filter_by(correo = coreo).first()
    if usuario is None:
        return jsonify("El usuario no existe"), 404
    else:
        try:
            if usuario.verificar_contrasena(contrasena):
                return jsonify({"usuario": usuario.serialize()}), 200
            else:
                return jsonify("Credenciales incorrectas"), 404
        except Exception as error:
            return jsonify("Error"), 500

    pass
    if not correo or not contrasena:
        return jsonify({"ERROR": "Correo o contraseña invalidos"}), 400
