import os
import uuid
from sqlalchemy.orm import Session
from datetime import datetime
from ..models import Notification
from .pusher_client import trigger_user_notification
from .email import send_email
from flask import current_app

FRONTEND_BASE = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

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
        "createdAt": n.created_at.isoformat() + "Z" if n.created_at else None,
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
        id=str(uuid.uuid4()),
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
    # db.commit()
    # db.refresh(notif)

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
            if resource_kind == "board" and resource_id:
                cta = f'<p><a href="{FRONTEND_BASE}/board/{resource_id}">Abrir tablero</a></p>'
            elif resource_kind == "card" and resource_id:
                cta = f'<p><a href="{FRONTEND_BASE}/board/cards/{resource_id}">Abrir tarjeta</a></p>'

            html = f"""
            <div style="font-family:Arial,sans-serif">
              <h3>{title}</h3>
              <p>{message}</p>
              {cta}
              <p style="color:#888;font-size:12px">Enviado por TrainIT</p>
            </div>
            """
            current_app.logger.info(f"[notifications] Sending email to {user_email} subject={subject}")
            send_email(user_email, subject, html)
        except Exception as e:
            current_app.logger.exception(f"[notifications] Error sending email to {user_email}: {e}")

    return notif