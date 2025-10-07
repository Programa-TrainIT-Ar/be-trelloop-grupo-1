# app/services/pusher_client.py
import os
import pusher
from flask import current_app

_pusher = None

def get_pusher_client():
    global _pusher
    if _pusher is None:
        current_app.logger.info("[pusher] Initializing pusher client")
        _pusher = pusher.Pusher(
            app_id=os.getenv("PUSHER_APP_ID"),
            key=os.getenv("PUSHER_KEY"),
            secret=os.getenv("PUSHER_SECRET"),
            cluster=os.getenv("PUSHER_CLUSTER"),
            ssl=True,
        )
    return _pusher

def trigger_user_notification(user_id: str, payload: dict, private: bool = True):
    channel = f"private-user-{user_id}" if private else f"user-{user_id}"
    try:
        client = get_pusher_client()
        current_app.logger.info(f"[pusher] Triggering event 'notification' on {channel} payload={payload}")
        client.trigger(channel, "notification", payload)
    except Exception as e:
        current_app.logger.exception(f"[pusher] Failed to trigger on {channel}: {e}")
