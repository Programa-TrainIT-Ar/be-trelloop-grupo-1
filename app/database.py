from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

# Instancia global del ORM de SQLAlchemy para usar con Flask
db = SQLAlchemy()  # Previamente: bd

def get_engine():
    """
    Crea y retorna un motor de SQLAlchemy utilizando la URL de conexión a la base de datos.
    Ideal para tareas fuera del contexto de Flask (scripts, mantenimiento, etc).
    """
    from .config import DATABASE_URL
    return create_engine(
        DATABASE_URL,
        pool_size=5,                   # Tamaño del pool de conexiones
        max_overflow=10,               # Máximo de conexiones adicionales
        pool_timeout=30,               # Tiempo máximo de espera para obtener conexión
        pool_recycle=1800,             # Recicla conexiones cada 30 minutos
        connect_args={
            'connect_timeout': 10,     # Tiempo límite de conexión
            'application_name': 'trelloop-app'  # Nombre de la app para identificar en PG
        }
    )

def get_session():
    """
    Crea y retorna una sesión de SQLAlchemy (Scoped Session).
    Se usa para scripts y tareas que requieren acceso directo a la BD.
    """
    engine = get_engine()
    session_factory = sessionmaker(bind=engine)
    return scoped_session(session_factory)

def initialize_database(app):
    """
    Configura e inicializa SQLAlchemy con la aplicación Flask.
    Debe llamarse al iniciar la app.
    """
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ECHO"] = app.config.get("DEBUG", False)

    # Configuración del pool para PostgreSQL
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 1800,
    }

    db.init_app(app)
    return db

def verify_connection():
    """
    Verifica si se puede establecer una conexión con la base de datos.
    Devuelve True si la conexión fue exitosa, False si hubo error.
    """
    try:
        engine = get_engine()
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as error:
        print(f"❌ Error de conexión a PostgreSQL: {str(error)}")
        return False
