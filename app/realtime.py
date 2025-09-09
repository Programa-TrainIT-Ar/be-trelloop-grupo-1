from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from .models import db, Notification
from .services.notifications import build_notification_payload, create_notification
from .services.pusher_client import get_pusher_client
from sqlalchemy import func
import os

realtime_bp = Blueprint("realtime", __name__)
CORS(realtime_bp)

@realtime_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

@realtime_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    try:
        user_id = get_jwt_identity()
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        unread_only = request.args.get("unread_only", "false").lower() == "true"

        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(read=False)

        total_count = query.count()
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset).all()

        current_app.logger.info(f"[notifications] User {user_id} requested notifications - Total: {total_count}, Unread: {unread_count}")
        
        response = {
            "notifications": [build_notification_payload(n) for n in notifications],
            "meta": {
                "total_count": total_count,
                "unread_count": unread_count,
                "limit": limit,
                "offset": offset
            }
        }
        return jsonify(response), 200
    except Exception as e:
        current_app.logger.exception(f"Error getting notifications: {e}")
        return jsonify({"error": "Error al obtener notificaciones"}), 500

@realtime_bp.route("/notifications/mark-read", methods=["POST"])
@jwt_required()
def mark_notifications_read():
    try:
        user_id = get_jwt_identity()
        data = request.json or {}
        notification_ids = data.get("ids", [])
        mark_all = data.get("all", False)

        if not notification_ids and not mark_all:
            return jsonify({"error": "Debe proporcionar 'ids' o 'all=true'"}), 400

        updated_count = 0
        if mark_all:
            result = Notification.query.filter_by(user_id=user_id, read=False).update({"read": True}, synchronize_session=False)
            updated_count = result
        else:
            result = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.id.in_(notification_ids),
                Notification.read == False
            ).update({"read": True}, synchronize_session=False)
            updated_count = result
        
        db.session.commit()
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        
        current_app.logger.info(f"[notifications] Marked {updated_count} notifications as read for user {user_id}")
        return jsonify({"updated_count": updated_count, "unread_count": unread_count}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error marking notifications as read: {e}")
        return jsonify({"error": "Error al marcar notificaciones"}), 500

@realtime_bp.route("/notifications/mark-one-read/<notification_id>", methods=["POST"])
@jwt_required()
def mark_one_notification_read(notification_id):
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        
        if not notification:
            return jsonify({"error": "Notificación no encontrada"}), 404

        if not notification.read:
            notification.read = True
            db.session.commit()
            current_app.logger.info(f"[notifications] Marked notification {notification_id} as read for user {user_id}")

        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        return jsonify({
            "notification": build_notification_payload(notification),
            "unread_count": unread_count
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error marking notification as read: {e}")
        return jsonify({"error": "Error al marcar notificación"}), 500

@realtime_bp.route("/notifications/debug/<notification_id>", methods=["GET"])
@jwt_required()
def debug_notification(notification_id):
    """Endpoint para verificar el estado actual de una notificación específica"""
    try:
        user_id = get_jwt_identity()
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        
        if not notification:
            return jsonify({"error": "Notificación no encontrada"}), 404

        return jsonify({
            "notification": build_notification_payload(notification),
            "raw_data": {
                "id": notification.id,
                "user_id": notification.user_id,
                "read": notification.read,
                "created_at": notification.created_at.isoformat() if notification.created_at else None
            }
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Error debugging notification: {e}")
        return jsonify({"error": "Error al obtener información de debug"}), 500

@realtime_bp.route("/notifications/cleanup-test", methods=["DELETE"])
@jwt_required()
def cleanup_test_notifications():
    """Elimina todas las notificaciones de tipo TEST para el usuario actual"""
    try:
        user_id = get_jwt_identity()
        
        # Eliminar notificaciones de prueba
        deleted_count = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.type.in_(["TEST", "TEST_PERSISTENCE"])
        ).delete(synchronize_session=False)
        
        db.session.commit()
        
        current_app.logger.info(f"[notifications] Cleaned up {deleted_count} test notifications for user {user_id}")
        return jsonify({"deleted_count": deleted_count}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error cleaning up test notifications: {e}")
        return jsonify({"error": "Error al limpiar notificaciones de prueba"}), 500

@realtime_bp.route("/notifications/test-push", methods=["POST"])
@jwt_required()
def test_push_notification():
    try:
        user_id = get_jwt_identity()
        data = request.json or {}

        notification = create_notification(
            db.session,
            user_id=str(user_id),
            type_=data.get("type", "TEST"),
            title=data.get("title", "Notificación de prueba"),
            message=data.get("message", "Esta es una notificación de prueba."),
            resource_kind=data.get("resource_kind"),
            resource_id=data.get("resource_id"),
            actor_id=str(user_id),
            send_email_also=False
        )

        return jsonify({"notification_id": notification.id}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error creating test notification: {e}")
        return jsonify({"error": "Error al enviar notificación"}), 500

@realtime_bp.route("/notifications/stats", methods=["GET"])
@jwt_required()
def get_notification_stats():
    """Obtiene estadísticas detalladas de las notificaciones del usuario"""
    try:
        user_id = get_jwt_identity()
        
        total_count = Notification.query.filter_by(user_id=user_id).count()
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        read_count = Notification.query.filter_by(user_id=user_id, read=True).count()
        
        # Contar por tipo
        type_counts = db.session.query(
            Notification.type, 
            func.count(Notification.id).label('count')
        ).filter_by(user_id=user_id).group_by(Notification.type).all()
        
        return jsonify({
            "total_count": total_count,
            "unread_count": unread_count,
            "read_count": read_count,
            "by_type": {type_name: count for type_name, count in type_counts}
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Error getting notification stats: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

@realtime_bp.route("/notifications/test-url", methods=["POST"])
@jwt_required()
def test_url_generation():
    """Endpoint para probar la generación de URLs sin enviar email"""
    try:
        data = request.json or {}
        resource_kind = data.get("resource_kind")
        resource_id = data.get("resource_id")
        frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
        
        # Generar múltiples variaciones de URL para probar
        url_variations = []
        
        if resource_kind == "board":
            url_variations = [
                f"{frontend_base}/board/{resource_id}",
                f"{frontend_base}/boards/{resource_id}",
                f"{frontend_base}/dashboard/board/{resource_id}",
                f"{frontend_base}/workspace/board/{resource_id}",
                f"{frontend_base}/project/{resource_id}",
            ]
        elif resource_kind == "card":
            # Obtener board_id de la tarjeta
            from ..models import Card
            card = db.session.query(Card).filter(Card.id == resource_id).first()
            if card and card.board_id:
                url_variations = [
                    f"{frontend_base}/board/{card.board_id}?cardId={resource_id}",
                    f"{frontend_base}/board/{card.board_id}?card={resource_id}",
                    f"{frontend_base}/board/{card.board_id}/card/{resource_id}",
                    f"{frontend_base}/boards/{card.board_id}?cardId={resource_id}",
                    f"{frontend_base}/card/{resource_id}",
                ]
        
        from .services.notifications import get_resource_url
        current_generated = get_resource_url(resource_kind, resource_id, db.session)
        
        return jsonify({
            "resource_kind": resource_kind,
            "resource_id": resource_id,
            "current_generated_url": current_generated,
            "url_variations": url_variations,
            "frontend_base": frontend_base,
            "recommendation": "Prueba estas URLs en tu navegador para ver cuál funciona"
        }), 200
    except Exception as e:
        current_app.logger.exception(f"Error testing URL generation: {e}")
        return jsonify({"error": "Error al probar generación de URL"}), 500

@realtime_bp.route("/notifications/test-email", methods=["POST"])
@jwt_required()
def test_email_notification():
    """Endpoint para probar el envío de emails con URLs correctas"""
    try:
        user_id = get_jwt_identity()
        data = request.json or {}
        
        # Obtener datos del usuario
        from ..models import User
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404
        
        # Probar generación de URL primero
        from .services.notifications import get_resource_url
        test_url = get_resource_url(data.get("resource_kind"), data.get("resource_id"), db.session)
        
        # Crear notificación de prueba con email
        notification = create_notification(
            db.session,
            user_id=str(user_id),
            type_="EMAIL_TEST",
            title=data.get("title", "Prueba de Email con Enlaces"),
            message=data.get("message", "Esta es una prueba para verificar que los enlaces funcionan correctamente."),
            resource_kind=data.get("resource_kind"),  # "board" o "card"
            resource_id=data.get("resource_id"),
            actor_id=str(user_id),
            user_email=user.email,
            send_email_also=True
        )
        
        return jsonify({
            "message": "Email de prueba enviado",
            "notification_id": notification.id,
            "email_sent_to": user.email,
            "resource_kind": data.get("resource_kind"),
            "resource_id": data.get("resource_id"),
            "generated_url": test_url
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error sending test email: {e}")
        return jsonify({"error": "Error al enviar email de prueba"}), 500
