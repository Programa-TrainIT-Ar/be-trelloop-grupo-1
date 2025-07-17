from flask import Blueprint, request, jsonify
from flask_cors import CORS, cross_origin
import re
from .database import db
from .models import User
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

auth_bp = Blueprint("auth", __name__)
CORS(auth_bp)

@auth_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204


@auth_bp.route("/login", methods = ["POST"])
@cross_origin()
def login():
    try:
        body = request.json

         # Valida que el body existe
        if not body:
            return jsonify({"ERROR": "Correo o contraseña invalidos"}), 400

        email = body.get("email", None)

        password = body.get("password", None)

        if not email or not password:
            return jsonify({"error": "Correo y contraseña son requeridos"}), 400

        user = User.query.filter_by(email=email).first()

        if user is None:
            return jsonify({"error": "El usuario no existe"}), 404

        if user.verify_password(password):
            # Genera el token de acceso con Flask-JWT-Extended
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            return jsonify({
                "mensaje": "Login exitoso",
                "usuario": user.serialize(),
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer"
            }), 200
        else:
            # Contraseña incorrecta
            return jsonify({"error": "Credenciales incorrectas"}), 401
    except Exception as error:
        print(f"Error in login: {str(error)}")
        # Retorna un error genérico al cliente por seguridad
        return jsonify({"error": "Error interno del servidor"}), 500

@auth_bp.route("/refresh", methods=["POST"])
@cross_origin()
@jwt_required(refresh=True)
def refresh_token():
    """
    Renueva el token de acceso usando un token de refresco válido.
    """
    try:
        # Obtiene el ID del usuario del token de refresco
        user_id = get_jwt_identity()

        # Encuentra al usuario
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Genera un nuevo token de acceso
        new_access_token = create_access_token(identity=user_id)

        return jsonify({
            "access_token": new_access_token,
            "token_type": "Bearer"
        }), 200

    except Exception as e:
        print(f"Error refreshing token: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@auth_bp.route("/register", methods=["POST"])
@cross_origin()
def register_user():
    try:
        body = request.json

        # Valida que el body existe
        if not body:
            return jsonify({"error": "Datos incompletos"}), 400

        first_name = body.get("firstName")
        last_name = body.get("lastName")
        email = body.get("email")
        password = body.get("password")

        # Validaciones básicas
        if not first_name or not last_name or not email or not password:
            return jsonify({"error": "Todos los campos son requeridos"}), 400

        # Valida el formato del correo
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, email):
            return jsonify({"error": "Correo inválido"}), 400

        # Verifica si el usuario ya existe
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "El correo ya está registrado"}), 409

        # Crea el nuevo usuario
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Genera tokens para el usuario recién registrado con Flask-JWT-Extended
        access_token = create_access_token(identity=new_user.id)
        refresh_token = create_refresh_token(identity=new_user.id)

        return jsonify({
            "mensaje": "Usuario registrado exitosamente",
            "usuario": new_user.serialize(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer"
        }), 201

    except Exception as e:
        print(f"Error in registration: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500

@auth_bp.route("/me", methods=["GET"])
@cross_origin()
@jwt_required()
def get_user_profile():
    """
    Obtiene el perfil del usuario autenticado.
    Esta ruta está protegida por el decorador jwt_required.
    """
    try:
        # Obtiene el ID del usuario desde el token
        user_id = get_jwt_identity()

        # Busca el usuario en la base de datos
        user = User.query.get(int(user_id))
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        return jsonify({
            "usuario": user.serialize()
        }), 200
    except Exception as e:
        print(f"Error al obtener el perfil de usuario: {str(e)}")
        return jsonify({"error": "Error interno del servidor"}), 500
