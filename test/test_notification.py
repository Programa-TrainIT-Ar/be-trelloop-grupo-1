import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import User, Notification  # Ajusta según tu proyecto
from app.services.notifications import create_notification
from datetime import datetime

# Configuración de la base de datos (igual que tu proyecto)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:4567@localhost:5432/trelloclonegrupo1")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def main():
    session = SessionLocal()

    # 1️⃣ Crear usuario de prueba si no existe
    test_email = "test_user@example.com"
    user = session.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(
            first_name="Test",
            last_name="User",
            email=test_email,
            password_hash="123456"  # solo para test
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    # 2️⃣ Crear la notificación
    notif = create_notification(
        db=session,
        user_id=str(user.id),
        actor_id=str(user.id),
        type_="CARD_ASSIGNED",
        title="Nueva tarjeta",
        message="Te asignaron una tarjeta en el tablero de prueba",
    )

    print("Notificación creada:", notif.id, notif.title, notif.user_id)

    # 3️⃣ (Opcional) limpiar después del test
    # session.delete(notif)
    # session.delete(user)
    # session.commit()

if __name__ == "__main__":
    main()