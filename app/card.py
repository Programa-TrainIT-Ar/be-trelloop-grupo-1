from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from datetime import datetime
from .models import db, User, Board, Tag, Card
import uuid


card_bp = Blueprint("card", __name__)
CORS(card_bp)

@card_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

# CREAR TARJETAS-------------------------------------------------------------------------------------------------------
@card_bp.route('/cards', methods=['POST'])
@jwt_required()
def create_card():
    try:
        user_id = get_jwt_identity()  # Usuario autenticado
        data = request.get_json()

        title = data.get('title')
        description = data.get('description')
        board_id = data.get('boardId')
        responsable_id = data.get('responsableId')
        begin_date = data.get('beginDate')
        due_date = data.get('dueDate')
        state = data.get('state', 'To Do')

        # Validaciones mínimas
        if not title or not board_id:
            return jsonify({"error": "El título y el ID del tablero son obligatorios"}), 400

        board = Board.query.get(board_id)
        if not board:
            return jsonify({"error": "El tablero no existe"}), 404

        # Crear tarjeta
        new_card = Card(
            title=title,
            description=description,
            responsable_id=responsable_id,
            creation_date=datetime.utcnow(),
            begin_date=datetime.fromisoformat(begin_date) if begin_date else None,
            due_date=datetime.fromisoformat(due_date) if due_date else None,
            state=state,
            board_id=board_id
        )

        db.session.add(new_card)
        db.session.commit()

        return jsonify({"message": "Tarjeta creada correctamente", "card": new_card.serialize()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# MOSTRAR TARJETAS (TODOS)-------------------------------------------------------------------------------------------------------
# MOSTRAR TARJETAS POR ID-------------------------------------------------------------------------------------------------------
# ACTUALIZAR UNA TARJETA EXISTENTE----------------------------------------------------------------------------------------------
# ELIMINAR UNA TARJETA----------------------------------------------------------------------------------------------
# AGREGAR MIEMBROS A UNA TARJETA-------------------------------------------------------------------------------------------------------
# ELIMINAR MIEMBROS DE UNA TARJETA-------------------------------------------------------------------------------------------------------
# OBTENER MIEMBROS DE UNA TARJETA------------------------------------------------------------------------------------------------------- 