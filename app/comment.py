from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from .models import db, User, Card, Board, Comment
from sqlalchemy.orm import joinedload
from .services.notifications import create_notification


comment_bp = Blueprint("comment", __name__)
CORS(comment_bp)

def _get_board_from_card(card: Card):
    board_id = getattr(card, "board_id", None)
    return Board.query.get(board_id) if board_id else None

def _can_manage_comment(user_id: int, comment: Comment) -> bool:
    """Autor del comentario o dueño del board."""
    if comment.user_id == user_id:
        return True
    card = Card.query.get(comment.card_id)
    board = _get_board_from_card(card) if card else None
    return bool(board and board.user_id == user_id)

def _user_can_view_card(user_id: int, card: Card) -> bool:
    """Miembro del board o publico."""
    board = _get_board_from_card(card)
    if not board:
        return False
    if board.is_public:
        return True
    return any(m.id == user_id for m in board.members)

#Crear comentario
@comment_bp.route("/create", methods=["POST"])
@jwt_required()
def create_comment():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        card_id   = data.get("cardId")
        content   = (data.get("content") or "").strip()
        parent_id = data.get("parentId")

        if not card_id or not content:
            return jsonify({"error": "cardId y content son requeridos"}), 400

        card = Card.query.get(card_id)
        if not card:
            return jsonify({"error": "Tarjeta no encontrada"}), 404

        if not _user_can_view_card(user_id, card):
            return jsonify({"error": "No tienes acceso a esta tarjeta"}), 403

        parent = None
        if parent_id:
            parent = Comment.query.get(parent_id)
            if not parent or parent.card_id != card.id:
                return jsonify({"error": "parentId inválido"}), 400

        c = Comment(
            card_id=card.id,
            user_id=user_id,
            parent_id=parent_id,
            content=content
        )
        db.session.add(c)
        db.session.commit()

        #Notificaciones 
        try:
            preview = (content[:50] + "…") if len(content) > 50 else content
            actor = c.user
            actor_name = f"{actor.first_name} {actor.last_name}".strip() if actor else "Alguien"

            if not parent_id:
                recipient_ids = {m.id for m in card.members if m.id != user_id}
                for rid in recipient_ids:
                    event_id = f"card:{card.id}:comment:{c.id}:to:{rid}"
                    create_notification(
                        db.session,
                        user_id=str(rid),
                        type_="COMMENT_NEW",
                        title="Nuevo comentario en una tarjeta",
                        message=f"{actor_name} comentó en '{card.title}': {preview}",
                        resource_kind="card",
                        resource_id=str(card.id),
                        actor_id=str(user_id),
                        event_id=event_id,
                        user_email=None,
                        send_email_also=False,
                    )
            else:
                if parent and parent.user_id != user_id:
                    event_id = f"card:{card.id}:comment:{parent.id}:reply:{c.id}:to:{parent.user_id}"
                    create_notification(
                        db.session,
                        user_id=str(parent.user_id),
                        type_="COMMENT_REPLY",
                        title="Nueva respuesta a tu comentario",
                        message=f"{actor_name} respondió: {preview}",
                        resource_kind="card",
                        resource_id=str(card.id),
                        actor_id=str(user_id),
                        event_id=event_id,
                        user_email=None,
                        send_email_also=False,
                    )
        except Exception as notif_err:
            current_app.logger.exception(f"[comments] notify failed (non-blocking): {notif_err}")

        return jsonify(c.serialize()), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[comments] create failed: {e}")
        return jsonify({"error": "Error creando comentario"}), 500


# Listar comentarios
@comment_bp.route("/list", methods=["GET"])
@jwt_required()
def list_comments():
    try:
        user_id = get_jwt_identity()
        uid = int(user_id) if isinstance(user_id, str) and str(user_id).isdigit() else user_id

        card_id = request.args.get("cardId", type=int)
        include_deleted = request.args.get("include_deleted", "false").lower() == "true"
        limit  = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)

        if not card_id:
            return jsonify({"error": "cardId es requerido"}), 400

        card = Card.query.get(card_id)
        if not card:
            return jsonify({"error": "Tarjeta no encontrada"}), 404

        if not _user_can_view_card(uid, card):
            return jsonify({"error": "No tienes acceso a esta tarjeta"}), 403

        q = (Comment.query
             .options(joinedload(Comment.user))   
             .filter(Comment.card_id == card_id))

        if not include_deleted:
            q = q.filter(Comment.deleted_at.is_(None))

        q = q.order_by(Comment.created_at.asc())

        total = q.count()
        rows = q.limit(limit).offset(offset).all()

        payload = [c.serialize(include_deleted_content=include_deleted) for c in rows]

        return jsonify({
            "items": payload,
            "meta": {"total": total, "limit": limit, "offset": offset}
        }), 200

    except Exception as e:
        current_app.logger.exception(f"[comments] list failed: {e}")
        return jsonify({"error": "Error listando comentarios"}), 500

#Editar comentario 
@comment_bp.route("/update/<int:comment_id>", methods=["PUT"])
@jwt_required()
def update_comment(comment_id: int):
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json() or {}
        content = (data.get("content") or "").strip()

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comentario no encontrado"}), 404

        if comment.deleted_at:
            return jsonify({"error": "No se puede editar un comentario eliminado"}), 400

        if comment.user_id != user_id:
            return jsonify({"error": "No puedes editar este comentario"}), 403

        if not content:
            return jsonify({"error": "content requerido"}), 400

        comment.content = content
        comment.is_edited = True
        comment.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(comment.serialize()), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[comments] update failed: {e}")
        return jsonify({"error": "Error actualizando comentario"}), 500

# soft delete
@comment_bp.route("/delete/<int:comment_id>", methods=["DELETE"])
@jwt_required()
def soft_delete_comment(comment_id: int):
    try:
        user_id = int(get_jwt_identity())
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comentario no encontrado"}), 404

        if not _can_manage_comment(user_id, comment):
            return jsonify({"error": "No puedes eliminar este comentario"}), 403

        if not comment.deleted_at:
            comment.deleted_at = datetime.utcnow()
            comment.deleted_by = user_id
            db.session.commit()

        return jsonify({"message": "Comentario eliminado"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[comments] delete failed: {e}")
        return jsonify({"error": "Error eliminando comentario"}), 500

# Restaurar un comentario eliminado
@comment_bp.route("/restore/<int:comment_id>", methods=["POST"])
@jwt_required()
def restore_comment(comment_id: int):
    try:
        user_id = (get_jwt_identity())
        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comentario no encontrado"}), 404

       
        if not _can_manage_comment(user_id, comment):
            return jsonify({"error": "No puedes restaurar este comentario"}), 403

        if comment.deleted_at:
            comment.deleted_at = None
            comment.deleted_by = None
            db.session.commit()

        return jsonify({"message": "Comentario restaurado"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[comments] restore failed: {e}")
        return jsonify({"error": "Error restaurando comentario"}), 500
