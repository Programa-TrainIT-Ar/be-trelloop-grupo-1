import os
import uuid
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import Notification
from .pusher_client import trigger_user_notification
from .email import send_email
from flask import current_app

FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

def get_resource_url(resource_kind: str, resource_id: str, db: Session) -> str | None:
    """Genera la URL correcta para el recurso en el frontend"""
    if not resource_kind or not resource_id:
        return None
        
    try:
        if resource_kind == "board":
            return f"{FRONTEND_BASE}/dashboard/board/{resource_id}"
        elif resource_kind == "card":
            from ..models import Card
            card = db.query(Card).filter(Card.id == resource_id).first()
            if card and card.board_id:
                return f"{FRONTEND_BASE}/dashboard/board/{card.board_id}?cardId={resource_id}"
        return None
    except Exception as e:
        current_app.logger.error(f"Error generating resource URL: {e}")
        return None

def build_notification_payload(n: Notification) -> dict:
    return {
        "id": n.id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "resource": {
            "kind": n.resource_kind,
            "id": n.resource_id,
        } if n.resource_kind and n.resource_id else None,
        "actorId": n.actor_id,
        "read": n.read,
        "createdAt": n.
        created_at.isoformat() + "Z" if n.created_at else None,
    }

def create_notification(
    db: Session,
    *,
    user_id: str,
    type_: str,
    title: str,
    message: str,
    resource_kind: str | None = None,
    resource_id: str | None = None,
    actor_id: str | None = None,
    event_id: str | None = None,
    user_email: str | None = None,
    send_email_also: bool = True,
) -> Notification:
     # Idempotencia
    if event_id:
        existing = db.query(Notification).filter(Notification.event_id == event_id).first()
        if existing:
            payload = build_notification_payload(existing)
            current_app.logger.info(f"[notifications] idempotent: re-emitting to pusher user={user_id} payload={payload}")
            trigger_user_notification(user_id, payload)
            return existing

    notif = Notification(
      
        user_id=int(user_id) if user_id is not None and str(user_id).isdigit() else user_id,
        type=type_,
        title=title,
        message=message,
        resource_kind=resource_kind,
        resource_id=int(resource_id) if resource_id and str(resource_id).isdigit() else resource_id,
        actor_id=int(actor_id) if actor_id and str(actor_id).isdigit() else actor_id,
        read=False,
        created_at=datetime.utcnow(),
        event_id=event_id,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    payload = build_notification_payload(notif)

    # Emitir en tiempo real
    try:
        current_app.logger.info(f"[notifications] Emitting pusher for user={user_id} payload={payload}")
        trigger_user_notification(user_id, payload)
    except Exception as e:
        current_app.logger.exception(f"[notifications] Pusher trigger failed for user={user_id}: {e}")

    # Email (opcional) — capturar errores para no romper el flujo
    if send_email_also and user_email:
        try:
            subject = title
            cta = ""
            
            # Generar URL y botón de acción
            resource_url = get_resource_url(resource_kind, resource_id, db)
            if resource_url:
                button_text = "Abrir Tablero" if resource_kind == "board" else "Abrir Tarjeta"
                button_color = "#007bff" if resource_kind == "board" else "#28a745"
              
                cta = f'''
                <div style="margin: 20px 0; text-align: center;">
                    <a href="{resource_url}" 
                       style="background-color: {button_color}; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;
                              font-weight: bold; font-size: 14px;">{button_text}</a>
                </div>
                '''

            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title}</title>
            </head>
            <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="border-left: 4px solid #007bff; padding-left: 20px; margin-bottom: 20px;">
                            <h2 style="color: #333; margin: 0 0 10px 0; font-size: 24px;">{title}</h2>
                        </div>
                        <p style="color: #555; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">{message}</p>
                        {cta}
                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0 20px 0;">
                        <div style="text-align: center;">
                            <p style="color: #888; font-size: 12px; margin: 0;">Enviado por TrainIT</p>
                            <p style="color: #aaa; font-size: 11px; margin: 5px 0 0 0;">Sistema de Gestión de Proyectos</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            current_app.logger.info(f"[notifications] Sending email to {user_email} subject={subject} resource_url={resource_url}")
            send_email(user_email, subject, html)
        except Exception as e:
            current_app.logger.exception(f"[notifications] Error sending email to {user_email}: {e}")

    return notif