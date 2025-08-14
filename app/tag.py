from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from .models import db, User, Tag

tag_bp = Blueprint("tag", __name__)

def _require_user():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return None, (jsonify({"error": "Usuario no encontrado"}), 404)
    return user, None

# =========================
# OBTENER TODAS LAS ETIQUETAS
# =========================
@tag_bp.route("", methods=["GET"])
@tag_bp.route("/getTags", methods=["GET"])
@jwt_required()
def get_all_tags():
    user, err = _require_user()
    if err: return err
    try:
        tags = Tag.query.order_by(Tag.name.asc()).all()
        return jsonify({
            "success": True,
            "total": len(tags),
            "items": [{"id": t.id, "name": t.name} for t in tags]
        }), 200
    except Exception as error:
        return jsonify({"error": str(error)}), 500

# =========================
# BUSCAR ETIQUETA POR NOMBRE 
# =========================
@tag_bp.route("/by-name/<string:name>", methods=["GET"])
@jwt_required()
def get_tag_by_name(name):
    user, err = _require_user()
    if err: return err

    norm = name.strip()
    tag = Tag.query.filter(func.lower(Tag.name) == norm.lower()).first()

    if not tag:
        return jsonify({"success": False, "message": "Etiqueta no encontrada"}), 404

    return jsonify({"success": True, "tag": tag.serialize()}), 200

# =========================
# CREAR ETIQUETA 
# =========================
@tag_bp.route("", methods=["POST"])
@jwt_required()
def create_tag():
    user, err = _require_user()
    if err: return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "El nombre de la etiqueta es requerido"}), 400

    tag_name = " ".join(data["name"].strip().split()) 

    existing_tag = Tag.query.filter(func.lower(Tag.name) == tag_name.lower()).first()
    if existing_tag:
        return jsonify({"success": True, "tag": existing_tag.serialize(), "created": False}), 200

    new_tag = Tag(name=tag_name)
    try:
        db.session.add(new_tag)
        db.session.commit()
        return jsonify({"success": True, "tag": new_tag.serialize(), "created": True}), 201
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 500

# =========================
# ACTUALIZAR ETIQUETA 
# =========================
@tag_bp.route("/<int:tag_id>", methods=["PUT"])
@jwt_required()
def update_tag(tag_id):
    user, err = _require_user()
    if err: return err

    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "El nombre de la etiqueta es requerido"}), 400

    tag_name = " ".join(data["name"].strip().split())
    
    tag = Tag.query.get(tag_id)
    if not tag:
        return jsonify({"error": "Etiqueta no encontrada"}), 404

    # Verificar si ya existe otra etiqueta con ese nombre
    existing_tag = Tag.query.filter(
        func.lower(Tag.name) == tag_name.lower(),
        Tag.id != tag_id
    ).first()
    
    if existing_tag:
        return jsonify({"error": "Ya existe una etiqueta con ese nombre"}), 400

    try:
        tag.name = tag_name
        db.session.commit()
        return jsonify({"success": True, "tag": tag.serialize()}), 200
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 500
