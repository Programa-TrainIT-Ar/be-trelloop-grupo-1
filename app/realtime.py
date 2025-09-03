from flask import Blueprint, request, jsonify, current_app
from flask_cors import CORS, cross_origin
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import desc
from .models import db, Notification
from .services.notifications import build_notification_payload, create_notification
from .services.pusher_client import get_pusher_client
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
        current_app.logger.exception(f"Error: {e}")
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
        with db.session.begin():
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

        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        return jsonify({"updated_count": updated_count, "unread_count": unread_count}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error: {e}")
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
            with db.session.begin():
                notification.read = True

        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()
        return jsonify({
            "notification": build_notification_payload(notification),
            "unread_count": unread_count
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error: {e}")
        return jsonify({"error": "Error al marcar notificación"}), 500

@realtime_bp.route("/notifications/test-push", methods=["POST"])
@jwt_required()
def test_push_notification():
    try:
        user_id = get_jwt_identity()
        data = request.json or {}

        with db.session.begin():
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
        current_app.logger.exception(f"Error: {e}")
        return jsonify({"error": "Error al enviar notificación"}), 500
