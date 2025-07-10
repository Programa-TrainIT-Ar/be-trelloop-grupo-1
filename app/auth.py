from flask import Blueprint, request, jsonify
import re
from .database import db
from .models import Usuario

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods = ["POST"])
def iniciar_sesion():

    try:
        body = request.json
    
        correo = body.get("correo", None)
        print(correo)
        contrasena = body.get("contrasena", None)

        usuario = Usuario.query.filter_by(correo = correo).first()
        
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
    except Exception as error:
        return jsonify("Error"), 500
        



    if not correo or not contrasena:
        return jsonify({"ERROR": "Correo o contraseña invalidos"}), 400
