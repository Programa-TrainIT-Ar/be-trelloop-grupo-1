from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from .models import db, User, Tag

tag_bp = Blueprint("tag", __name__)

#Buscar etiqueta por nombre 
@tag_bp.route("/by-name/<string:name>", methods=["GET"])
@jwt_required()
def get_tag_by_name(name):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    tag = Tag.query.filter(func.lower(Tag.name) == name.strip().lower()).first()

    if not tag:
        return jsonify({"success": False, "message": "Etiqueta no encontrada"}), 404

    return jsonify({"success": True, "tag": tag.serialize()}), 200


#Crear etiqueta
@tag_bp.route("", methods=["POST"])
@jwt_required()
def create_tag():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "El nombre de la etiqueta es requerido"}), 400

    tag_name = data["name"].strip()


    existing_tag = Tag.query.filter(func.lower(Tag.name) == tag_name.lower()).first()
    if existing_tag:
        return jsonify({"success": True, "tag": existing_tag.serialize()}), 200


    new_tag = Tag(name=tag_name)
    db.session.add(new_tag)
    db.session.commit()

    return jsonify({"success": True, "tag": new_tag.serialize()}), 201
