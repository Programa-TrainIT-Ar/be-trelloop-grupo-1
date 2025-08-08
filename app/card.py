from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from datetime import datetime
from .models import db, Board, Card, State


card_bp = Blueprint("card", __name__)
CORS(card_bp)

@card_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

# CREAR TARJETAS-------------------------------------------------------------------------------------------------------
@card_bp.route('/createCard', methods=['POST'])
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

# MOSTRAR TARJETAS DE UN TABLERO (TODOS)-------------------------------------------------------------------------------------------------------
@card_bp.route("/getCards/<int:board_id>", methods=["GET"])
@jwt_required()
def get_all_cards(board_id):
    try:
        all_cards = Card.query.filter_by(board_id = board_id)
        if not all_cards:
            return jsonify({"Error": "Tablero no encontrado"}), 404
        return jsonify([card.serialize() for card in all_cards]), 200
    except Exception as error:
        return jsonify({"error": "Se ha producido un error al obtener las tarjetas", "details": str(error)}), 500

# MOSTRAR TARJETAS POR ID-------------------------------------------------------------------------------------------------------
@card_bp.route("/getCard/<int:card_id>", methods=["GET"])
@jwt_required()
def get_card(card_id):
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify({"Error": "Tarjeta no encontrada"}), 404
        return jsonify(card.serialize()), 200
    except Exception as error:
        return jsonify({"error": "Se ha producido un error al obtener la tarjeta", "details": str(error)}), 500

# ACTUALIZAR UNA TARJETA EXISTENTE----------------------------------------------------------------------------------------------
@card_bp.route("/updateCard/<int:card_id>", methods=["PUT"])
@jwt_required()
def update_card(card_id):
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify({"error": "Tarjeta no encontrada"}), 404

        data = request.get_json()

        card.title = data.get("title", card.title)
        card.description = data.get("description", card.description)
        card.responsable_id = data.get("responsableId", card.responsable_id)
        card.begin_date = datetime.fromisoformat(data["beginDate"]) if data.get("beginDate") else card.begin_date
        card.due_date = datetime.fromisoformat(data["dueDate"]) if data.get("dueDate") else card.due_date
        card.state = data.get("state", card.state)

        db.session.commit()
        return jsonify({"message": "Tarjeta actualizada correctamente", "card": card.serialize()}), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": "Error al actualizar la tarjeta", "details": str(error)}), 500

# ELIMINAR UNA TARJETA---------------------------------------------------------------------------------------------------------------
@card_bp.route("/deleteCard/<int:card_id>", methods=["DELETE"])
@jwt_required()
def delete_card(card_id):
    try:
        card = Card.query.get(card_id)
        if not card:
            return jsonify({"error": "Tarjeta no encontrada"}), 404

        db.session.delete(card)
        db.session.commit()
        return jsonify({"message": "Tarjeta eliminada correctamente"}), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": "Error al eliminar la tarjeta", "details": str(error)}), 500


# ELIMINAR UNA TARJETA----------------------------------------------------------------------------------------------
# AGREGAR MIEMBROS A UNA TARJETA-------------------------------------------------------------------------------------------------------
@card_bp.route('/addMembers/<int:card_id>', methods=['POST'])
@jwt_required()
def add_memember(card_id):
    try:
        current_user_id=get_jwt_identity()
        user=User.query.get(current_user_id)
        if not user:
            return jsonify({"Warning":"Usuario no encontrado"}),404
        
        data=request.get_json()
        user_id=data.get("userId")
        print(request.data)
        print(request.get_json())

        if not user_id:
            return jsonify({"Warning":"Datos incompletos"}),400
        
        card = Card.query.get(card_id)
        if not card:
            return jsonify({"Warning":"Tarjeta no encontrada"}),404
        
        user_to_add = User.query.get(user_id)
        if not user_to_add:
            return jsonify({"Warning":"Usuario no encontrado"}),404
        if user_to_add in card.members:
            return jsonify({"Warning":"El usuario ya es miembro de la tarjeta"}),400
        
        card.members.append(user_to_add)
        db.session.commit()
        return jsonify({"Message":"Miembro agregado correctamente"}),200   
      
    except Exception as error:
        db.session.rollback()
        return jsonify({"Warning":str(error)}),500
 
# ELIMINAR MIEMBROS DE UNA TARJETA-------------------------------------------------------------------------------------------------------
# OBTENER MIEMBROS DE UNA TARJETA------------------------------------------------------------------------------------------------------- 
@card_bp.route("getMembers/<int:card_id>", methods=['GET'])
@jwt_required()
def get_members(card_id):
    try:
        card=Card.query.get(card_id)
        if not card:
            return jsonify({"Warning":"Tarjeta no encontrada"}),404
        members=[member.serialize() for member in card.members]
        return jsonify(members),200
    except Exception as error:
        return jsonify({"Warning":str(error)}),500