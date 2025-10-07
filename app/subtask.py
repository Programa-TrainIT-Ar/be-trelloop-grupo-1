from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from .models import db, Subtask, User, Card
from datetime import datetime

subtask_bp = Blueprint("subtask", __name__)
CORS(subtask_bp)

# CREAR UNA SUBTAREA---------------------------------------------------------------------------------------------
@subtask_bp.route("/createSubtask", methods=["POST"])
@jwt_required()
def create_subtask():
    try:
        data = request.get_json()

        description = data.get("description")
        limit_date = data.get("limitDate")
        responsible_id = data.get("responsibleId")
        card_id = data.get("cardId")

        if not description or not card_id:
            return jsonify({"error": "description y cardId son obligatorios"}), 400

        subtask = Subtask(
            description=description,
            limit_date=datetime.fromisoformat(limit_date) if limit_date else None,
            responsible_id=responsible_id,
            card_id=card_id,
        )

        db.session.add(subtask)
        db.session.commit()

        return jsonify(subtask.serialize()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# MOSTRAR TODAS LAS SUBTAREAS-----------------------------------------------------------------------------------
@subtask_bp.route("/cards/<int:card_id>/subtasks", methods=["GET"])
@jwt_required()
def get_subtasks(card_id):
    # Filtrar solo subtareas activas de la tarjeta indicada
    subtasks = Subtask.query.filter_by(card_id=card_id, is_active=True).all()
    return jsonify([s.serialize() for s in subtasks]), 200


# MOSTRAR UNA SUBTAREA POR ID----------------------------------------------------------------------------------
@subtask_bp.route("/getSubtask/<int:id>", methods=["GET"])
@jwt_required()
def get_subtask(id):
    subtask = Subtask.query.get(id)
    if not subtask or not subtask.is_active:
        return jsonify({"error": "Subtask no encontrada"}), 404
    return jsonify(subtask.serialize()), 200


# MODIFICAR UNA SUBTAREA----------------------------------------------------------------------------------------
@subtask_bp.route("/updateSubtask/<int:id>", methods=["PUT"])
@jwt_required()
def update_subtask(id):
    try:
        subtask = Subtask.query.get(id)
        if not subtask or not subtask.is_active:
            return jsonify({"error": "Subtask no encontrada"}), 404

        data = request.get_json()
        subtask.description = data.get("description", subtask.description)
        subtask.limit_date = datetime.fromisoformat(data["limitDate"]) if data.get("limitDate") else subtask.limit_date
        subtask.responsible_id = data.get("responsibleId", subtask.responsible_id)
        subtask.card_id = data.get("cardId", subtask.card_id)

        db.session.commit()
        return jsonify(subtask.serialize()), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


# ELIMINAR UNA SUBTAREA CON SOFT DELETE (SÓLO INACTIVA)-------------------------------------------------------------------------------
@subtask_bp.route("/inactivateSubtask/<int:id>", methods=["PATCH"])
@jwt_required()
def delete_subtask(id):
    try:
        subtask = Subtask.query.get(id)
        if not subtask or not subtask.is_active:
            return jsonify({"error": "Subtarea no encontrada o ya eliminada"}), 404

        subtask.is_active = False
        db.session.commit()
        return jsonify({"message": "Subtarea eliminada con éxito"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
