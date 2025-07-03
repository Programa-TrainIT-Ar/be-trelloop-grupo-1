from flask import Blueprint, request, jsonify
import re
from .database import db
from .models import Usuario

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods = ["POST", "GET"])
def iniciar_sesion():
    """
    Aqui va el codigo de Ale, no pude hacer mas que eso porque
    tu vas a validar los correos
    """

    if not correo or not contrasena:
        return jsonify({"ERROR": "Correo o contraseña invalidos"}), 400
