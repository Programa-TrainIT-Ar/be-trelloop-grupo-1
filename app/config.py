import os
from dotenv import load_dotenv
load_dotenv()

# Estan como ejemplo, cambiar en produccion
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/trello-clone-grupo-1")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "desarrollo-secret-key-cambiar-en-produccion")
JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))  # 1 hora por defecto
JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800"))  # 7 días por defecto

# Configuración de CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")

# Configuración de la aplicación
DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]

# Configuración de pusher
PUSHER_APP_ID = os.getenv("PUSHER_APP_ID")
PUSHER_KEY = os.getenv("PUSHER_KEY")
PUSHER_SECRET = os.getenv("PUSHER_SECRET")
PUSHER_CLUSTER = os.getenv("PUSHER_CLUSTER")