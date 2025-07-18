import os
from dotenv import load_dotenv
load_dotenv()

# Estan como ejemplo, cambiar en produccion
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:1234@localhost:5432/trello-clone-grupo-1")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "desarrollo-secret-key-cambiar-en-produccion")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5174").split(",")

DEBUG = os.getenv("DEBUG", "True").lower() in ["true", "1", "yes"]
