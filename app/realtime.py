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

# =========================================================================
# ENDPOINTS PARA GESTIONAR NOTIFICACIONES
# =========================================================================

@realtime_bp.route("/notifications", methods=["GET"])
@jwt_required()
def get_notifications():
    """
    Obtiene las notificaciones del usuario autenticado.

    Permite filtrar por estado de lectura y paginar los resultados.

    Query parameters:
    - limit: Número máximo de notificaciones a retornar (default: 20)
    - offset: Número de notificaciones a saltar (para paginación, default: 0)
    - unread_only: Si es "true", solo devuelve notificaciones no leídas

    Respuesta:
    - Array de objetos de notificación con todos sus campos
    - Campo 'total_count' con el número total de notificaciones (para paginación)
    - Campo 'unread_count' con el número total de notificaciones no leídas
    """
    try:
        # Obtener el ID del usuario desde el token JWT
        user_id = get_jwt_identity()

        # Parsear parámetros de consulta
        limit = request.args.get("limit", 20, type=int)
        offset = request.args.get("offset", 0, type=int)
        unread_only = request.args.get("unread_only", "false").lower() == "true"

        # Construir la consulta base
        query = Notification.query.filter_by(user_id=user_id)

        # Aplicar filtro de no leídas si es necesario
        if unread_only:
            query = query.filter_by(read=False)

        # Obtener contadores para la respuesta
        total_count = query.count()
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()

        # Ejecutar la consulta con paginación y ordenación
        notifications = query.order_by(Notification.created_at.desc())\
            .limit(limit).offset(offset).all()

        # Construir la respuesta con los datos y metadatos
        response = {
            "notifications": [build_notification_payload(n) for n in notifications],
            "meta": {
                "total_count": total_count,
                "unread_count": unread_count,
                "limit": limit,
                "offset": offset
            }
        }

        current_app.logger.info(f"[notifications] User {user_id} fetched {len(notifications)} notifications")
        return jsonify(response), 200

    except Exception as e:
        current_app.logger.exception(f"[notifications] Error al obtener notificaciones: {e}")
        return jsonify({"error": "Error al obtener notificaciones"}), 500


@realtime_bp.route("/notifications/mark-read", methods=["POST"])
@jwt_required()
def mark_notifications_read():
    """
    Marca notificaciones como leídas para el usuario autenticado.

    Permite marcar notificaciones específicas o todas las notificaciones del usuario.

    Cuerpo de la solicitud (JSON):
    - ids: Array de IDs de notificaciones a marcar como leídas (opcional)
    - all: Boolean que indica si se deben marcar todas las notificaciones (opcional)

    Si no se proporciona 'ids' ni 'all=true', se devuelve un error 400.

    Respuesta:
    - Mensaje de éxito con la cantidad de notificaciones actualizadas
    - Nuevo contador de notificaciones no leídas
    """
    try:
        # Obtener el ID del usuario desde el token JWT
        user_id = get_jwt_identity()

        # Obtener datos del cuerpo de la solicitud
        data = request.json or {}
        notification_ids = data.get("ids", [])
        mark_all = data.get("all", False)

        # Validar que se proporcione al menos una opción válida
        if not notification_ids and not mark_all:
            return jsonify({
                "error": "Debe proporcionar 'ids' o 'all=true' para marcar notificaciones como leídas"
            }), 400

        # Inicializar contador de actualizaciones
        updated_count = 0

        # Ejecutar la actualización en una transacción
        with db.session.begin():
            if mark_all:
                # Marcar todas las notificaciones no leídas del usuario
                result = Notification.query.filter_by(
                    user_id=user_id,
                    read=False
                ).update({"read": True}, synchronize_session=False)
                updated_count = result
                current_app.logger.info(f"[notifications] User {user_id} marked all ({updated_count}) notifications as read")
            else:
                # Marcar solo las notificaciones específicas del usuario
                result = Notification.query.filter(
                    Notification.user_id == user_id,
                    Notification.id.in_(notification_ids),
                    Notification.read
                ).update({"read": True}, synchronize_session=False)
                updated_count = result
                current_app.logger.info(f"[notifications] User {user_id} marked {updated_count} specific notifications as read")

        # Obtener el nuevo conteo de notificaciones no leídas
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()

        return jsonify({
            "message": f"Se marcaron {updated_count} notificaciones como leídas",
            "updated_count": updated_count,
            "unread_count": unread_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[notifications] Error al marcar notificaciones como leídas: {e}")
        return jsonify({"error": "Error al marcar notificaciones como leídas"}), 500


@realtime_bp.route("/notifications/mark-one-read/<notification_id>", methods=["POST"])
@jwt_required()
def mark_one_notification_read(notification_id):
    """
    Marca una notificación específica como leída.

    Este endpoint es útil para cuando el usuario hace clic en una notificación
    individual desde la interfaz de usuario.

    Parámetros de ruta:
    - notification_id: ID de la notificación a marcar como leída

    Respuesta:
    - Confirmación de la operación
    - Nuevo contador de notificaciones no leídas
    """
    try:
        # Obtener el ID del usuario desde el token JWT
        user_id = get_jwt_identity()

        # Buscar la notificación y verificar que pertenezca al usuario
        notification = Notification.query.filter_by(
            id=notification_id,
            user_id=user_id
        ).first()

        # Verificar si la notificación existe
        if not notification:
            return jsonify({"error": "Notificación no encontrada o no autorizada"}), 404

        # Marcar como leída solo si no lo está ya
        if not notification.read:
            with db.session.begin():
                notification.read = True
            current_app.logger.info(f"[notifications] User {user_id} marked notification {notification_id} as read")

        # Obtener el nuevo conteo de notificaciones no leídas
        unread_count = Notification.query.filter_by(user_id=user_id, read=False).count()

        return jsonify({
            "message": "Notificación marcada como leída",
            "notification": build_notification_payload(notification),
            "unread_count": unread_count
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[notifications] Error al marcar notificación como leída: {e}")
        return jsonify({"error": "Error al marcar notificación como leída"}), 500


@realtime_bp.route("/notifications/test-push", methods=["POST"])
@jwt_required()
def test_push_notification():
    """
    Endpoint de prueba para enviar una notificación push al propio usuario.

    Útil para probar el sistema de notificaciones en tiempo real sin necesidad
    de realizar acciones que generen notificaciones reales.

    Cuerpo de la solicitud (JSON):
    - title: Título de la notificación (opcional)
    - message: Mensaje de la notificación (opcional)
    - type: Tipo de notificación (opcional)

    Respuesta:
    - Confirmación de que la notificación fue enviada
    - ID de la notificación creada
    """
    try:
        # Obtener el ID del usuario desde el token JWT
        user_id = get_jwt_identity()

        # Obtener datos del cuerpo de la solicitud
        data = request.json or {}

        # Importar servicio de notificaciones
        from .services.notifications import create_notification

        # Crear y enviar la notificación
        with db.session.begin():
            notification = create_notification(
                db.session,
                user_id=str(user_id),
                type_=data.get("type", "TEST"),
                title=data.get("title", "Notificación de prueba"),
                message=data.get("message", "Esta es una notificación de prueba enviada manualmente."),
                resource_kind=data.get("resource_kind"),
                resource_id=data.get("resource_id"),
                actor_id=str(user_id),  # El actor es el mismo usuario
                send_email_also=False    # No enviar email para pruebas
            )

        current_app.logger.info(f"[notifications] Test notification sent to user {user_id}")

        return jsonify({
            "message": "Notificación de prueba enviada exitosamente",
            "notification_id": notification.id
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"[notifications] Error al enviar notificación de prueba: {e}")
        return jsonify({"error": "Error al enviar notificación de prueba"}), 500
