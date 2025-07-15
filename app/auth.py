from flask import Blueprint, request, jsonify
from flask_cors import CORS, cross_origin
import re
from .database import db
from .models import Usuario
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required

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
            access_token=create_access_token(identity=usuario.id)
            return jsonify({
                "mensaje": "Login exitoso",
                "usuario": usuario.serialize(),
                "access_token": access_token
            }), 200
        else:
            return jsonify({"error":"Contraseña incorrecta"}),401
    except Exception as error:
        print(f"Error en login: {str(error)}")
        # Retornar error genérico al cliente por seguridad
        return jsonify({"error": "Error interno del servidor"}), 500

@auth_bp.route("/register", methods=["POST"])
@cross_origin()
def registrar_usuario():
    try:
        body = request.json

        # Validar que el body existe
        if not body:
            return jsonify({"error": "Datos incompletos"}), 400

        nombre = body.get("nombre",None)
        apellido = body.get("apellido",None)
        correo = body.get("correo",None)
        contrasena = body.get("contrasena",None)

        # Validaciones básicas
        if not nombre or not apellido or not correo or not contrasena:
            return jsonify({"error": "Todos los campos son requeridos"}), 400

        # Validar formato del correo
        patron_correo = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(patron_correo, correo):
            return jsonify({"error": "Correo inválido"}), 400

        # Verificar si ya existe el usuario
        usuario_existente = Usuario.query.filter_by(correo=correo).first()
        if usuario_existente:
            return jsonify({"error": "El correo ya está registrado"}), 409

        # Crear el nuevo usuario
        nuevo_usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            correo=correo
        )
        nuevo_usuario.set_contrasena(contrasena)

        db.session.add(nuevo_usuario)
        db.session.commit()

        return jsonify({
            "mensaje": "Usuario registrado exitosamente",
            "usuario": nuevo_usuario.serialize()
        }), 201

    except Exception as e:
        print(f"Error en el registro: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

