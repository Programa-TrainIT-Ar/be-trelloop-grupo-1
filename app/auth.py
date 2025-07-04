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

@auth_bp.route("/register", methods=["POST"])
def registrar_usuario():
    
    # 1. Obtener datos del request
    data = request.get_json()

    nombre = data.get("nombre")
    apellido = data.get("apellido")
    correo = data.get("correo")
    contrasena = data.get("contrasena")

    # 2. Validar campos vacíos
    if not nombre or not apellido or not correo or not contrasena:
        return jsonify({"ERROR": "Todos los campos son obligatorios"}), 400

    # 3. Validar formato de correo
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, correo):
        return jsonify({"ERROR": "Correo inválido"}), 400

    # 4. Verificar si el correo ya está registrado
    usuario_existente = Usuario.query.filter_by(correo=correo).first()
    if usuario_existente:
        return jsonify({"ERROR": "El correo ya está registrado"}), 400

    # 5. Crear usuario
    nuevo_usuario = Usuario(
        nombre=nombre,
        apellido=apellido,
        correo=correo
    )
    nuevo_usuario.guarda_contasena(contrasena)

    # 6. Guardar en la base de datos
    db.session.add(nuevo_usuario)
    db.session.commit()

    # 7. Devolver respuesta
    return jsonify({
        "mensaje": "Usuario registrado exitosamente",
        "usuario": nuevo_usuario.serialize()
    }), 201
