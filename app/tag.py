from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from .models import db, User, Tag 

tag_bp = Blueprint("tag", __name__)

# CREAR ETIQUETAS----------------------------------------------------------------------------------------
@tag_bp.route("/createTag", methods=["POST"])
@jwt_required()
def create_tag():
    # Obtener el ID del usuario desde el token
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Obtener datos del cuerpo de la solicitud
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "El nombre de la etiqueta es requerido"}), 400

    tag_name = data["name"].strip()

    # Verificar si la etiqueta ya existe (opcional)
    existing_tag = Tag.query.filter_by(name=tag_name).first()
    if existing_tag:
        return jsonify({"error": "La etiqueta ya existe"}), 409

    # Crear la nueva etiqueta
    new_tag = Tag(name=tag_name)
    db.session.add(new_tag)
    db.session.commit()

    return jsonify({
        "mensaje": "Etiqueta creada exitosamente",
        "tag": new_tag.serialize()
    }), 201
