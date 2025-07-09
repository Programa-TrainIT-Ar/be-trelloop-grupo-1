from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from .models import db, Usuario

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()


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
def register():
    try:
        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        # Validaciones básicas
        if not name or not email or not password:
            return jsonify({"error": "Todos los campos (name, email, password) son obligatorios."}), 400

        if "@" not in email or "." not in email:
            return jsonify({"error": "Formato de correo inválido."}), 400

        if len(password) < 6:
            return jsonify({"error": "La contraseña debe tener al menos 6 caracteres."}), 400

        # Verificar si usuario ya existe
        existing_user = Usuario.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "El correo ya está registrado. Intenta con otro correo."}), 409

        # Encriptar contraseña
        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

        # Crear nuevo usuario
        new_user = Usuario(
            name=name,
            email=email,
            password=hashed_password,
            is_active=True
        )

        # Guardar en la base de datos
        db.session.add(new_user)
        db.session.commit()

        # Respuesta exitosa
        return jsonify({"message": "Registro exitoso", "user_id": new_user.id}), 201

    except Exception as e:
        db.session.rollback()
        print("Error en el registro:", e)
        return jsonify({"error": str(e)}), 500

