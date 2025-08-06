from flask import request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from .models import db, Card, State


card_bp = Blueprint("card", __name__)
CORS(card_bp)

@card_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

# CREAR TARJETAS---------------------------------------------------------------------------------------------------------------
# MOSTRAR TARJETAS (TODOS)------------------------------------------------------------------------------------------------------
# MOSTRAR TARJETAS POR ID-------------------------------------------------------------------------------------------------------
# ACTUALIZAR UNA TARJETA EXISTENTE----------------------------------------------------------------------------------------------
@card_bp.route('/card/updateCard/<int:card_id>', methods=['PUT'])
@jwt_required()
def update_card(card_id):
    card = Card.query.get(card_id)
    if not card:
        return jsonify({"error": "Tarjeta no encontrada"}), 404

    data = request.get_json()

    if 'title' in data:
        card.title = data['title']
    if 'description' in data:
        card.description = data['description']
    if 'beginDate' in data:
        card.begin_date = datetime.fromisoformat(data['beginDate'])
    if 'dueDate' in data:
        card.due_date = datetime.fromisoformat(data['dueDate'])
    if 'state' in data:
        try:
            card.state = State(data['state'])  
        except ValueError:
            return jsonify({"error": "Estado inválido"}), 400
    if 'responsableId' in data:
        card.responsable_id = data['responsableId']

    db.session.commit()
    return jsonify({"message": "Tarjeta actualizada", "card": card.serialize()}), 200


# AGREGAR UN MIEMBRO A UNA TARJETA---------------------------------------------------------------------------------------------------
@card_bp.route('/card/<int:card_id>/addCardMember/<int:user_id>', methods=['POST'])
@jwt_required()
def add_card_member(card_id, user_id):
    card = Card.query.get(card_id)
    if not card:
        return jsonify({"error": "Tarjeta no encontrada"}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if user not in card.members:
        card.members.append(user)
        db.session.commit()

    return jsonify({"message": "Miembro agregado a la tarjeta", "card": card.serialize()}), 200


# QUITAR UN MIEMBRO DE UNA TARJETA---------------------------------------------------------------------------------------------------
@card_bp.route('/card/<int:card_id>/removeCardMember/<int:user_id>', methods=['DELETE'])
@jwt_required()
def remove_card_member(card_id, user_id):
    card = Card.query.get(card_id)
    if not card:
        return jsonify({"error": "Tarjeta no encontrada"}), 404

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    if user in card.members:
        card.members.remove(user)
        db.session.commit()

    return jsonify({"message": "Miembro eliminado de la tarjeta", "card": card.serialize()}), 200


# ELIMINAR UNA TARJETA---------------------------------------------------------------------------------------------------------- 
@card_bp.route('/card/deleteCard/<int:card_id>', methods=['DELETE'])
@jwt_required()
def delete_card(card_id):
    card = Card.query.get(card_id)
    if not card:
        return jsonify({"error": "Tarjeta no encontrada"}), 404

    db.session.delete(card)
    db.session.commit()
    return jsonify({"message": "Tarjeta eliminada correctamente"}), 200
