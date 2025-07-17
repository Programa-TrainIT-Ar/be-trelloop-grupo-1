from .database import db
import bcrypt

class Message(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     content = db.Column(db.String(255), nullable=False)

class User(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(70), unique=False, nullable=False)
    last_name = db.Column(db.String(70), unique=False, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))

    def set_password(self, password):
        # Guarda la contraseña encriptada
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        self.password_hash = hashed.decode("utf-8")

    def verify_password(self, password):
        # Verifica si la contraseña es correcta
        if not self.password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))

    def serialize(self):
        # Convierte una instancia de la clase en un diccionario de Python para respuestas de API
        return {
            "id": self.id,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email
            # No incluir la contraseña - brecha de seguridad
        }
