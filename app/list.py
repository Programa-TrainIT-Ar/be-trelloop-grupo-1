from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_
from .models import db, Board, List, Card, User

list_bp = Blueprint("list", __name__)

def _user_is_member(user_id: int, board: Board) -> bool:
    if not board:
        return False
    if board.user_id == user_id:
        return True
    return any(m.id == user_id for m in board.members)

def _can_view_board(user_id: int, board: Board) -> bool:
    return board.is_public or _user_is_member(user_id, board)

@list_bp.route("/by-board/<int:board_id>", methods=["GET"])
@jwt_required()
def get_lists_by_board(board_id):
    try:
        user_id = int(get_jwt_identity())
        board = Board.query.get(board_id)
        if not board:
            return jsonify({"error": "Tablero no encontrado"}), 404
        if not _can_view_board(user_id, board):
            return jsonify({"error": "Sin acceso al tablero"}), 403

        rows = (List.query
                .filter_by(board_id=board_id)
                .order_by(List.position.asc(), List.id.asc())
                .all())

        payload = [{
            "id": r.id,
            "boardId": r.board_id,
            "name": r.name,
            "position": r.position,
            "createdBy": r.created_by,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        } for r in rows]

        return jsonify({"items": payload}), 200
    except Exception as e:
        current_app.logger.exception(f"[lists] by-board failed: {e}")
        return jsonify({"error": "Error listando listas"}), 500

@list_bp.route("/create", methods=["POST"])
@jwt_required()
def create_list():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        board_id = data.get("boardId")
        name = (data.get("name") or "").strip()

        if not board_id or not name:
            return jsonify({"error": "boardId y name son requeridos"}), 400

        board = Board.query.get(board_id)
        if not board:
            return jsonify({"error": "Tablero no encontrado"}), 404
        if not _user_is_member(user_id, board):
            return jsonify({"error": "Debes ser miembro del tablero"}), 403

        # Único por tablero (case-insensitive)
        exists = (List.query
                  .filter(List.board_id == board_id,
                          db.func.lower(List.name) == name.lower())
                  .first())
        if exists:
            return jsonify({"error": "Ya existe una lista con ese nombre"}), 409

        max_pos = (db.session.query(db.func.max(List.position))
                   .filter(List.board_id == board_id)
                   .scalar()) or 0

        row = List(
            board_id=board_id,
            name=name,
            position=max_pos + 1,
            created_by=user_id
        )
        db.session.add(row)
        db.session.commit()

        return jsonify({
            "id": row.id,
            "boardId": row.board_id,
            "name": row.name,
            "position": row.position
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[lists] create failed: {e}")
        return jsonify({"error": "Error al crear lista"}), 500

# (Opcional) eliminar lista con reglas de negocio
@list_bp.route("/<int:list_id>", methods=["DELETE"])
@jwt_required()
def delete_list(list_id):
    try:
        user_id = int(get_jwt_identity())
        row = List.query.get(list_id)
        if not row:
            return jsonify({"error": "Lista no encontrada"}), 404

        board = Board.query.get(row.board_id)
        if not _user_is_member(user_id, board):
            return jsonify({"error": "Debes ser miembro del tablero"}), 403

        has_cards = db.session.query(Card.id).filter(Card.list_id == list_id).first() is not None

        # Si tiene tarjetas: solo el dueño del tablero puede eliminarla
        if has_cards and board.user_id != user_id:
            return jsonify({"error": "Solo el creador del tablero puede eliminar listas con tarjetas"}), 403

        db.session.delete(row)
        db.session.commit()
        return jsonify({"ok": True}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[lists] delete failed: {e}")
        return jsonify({"error": "Error eliminando lista"}), 500
