from .database import db
import bcrypt

class Message(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     content = db.Column(db.String(255), nullable=False)

class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(70), unique=False, nullable=False)
    apellido = db.Column(db.String(70), unique=False, nullable=False)
    correo = db.Column(db.String(255), unique=True,nullable=False)
    contrasena_hashada = db.Column(db.String(255))

    def guarda_contrasena(self, contrasena):
        #Se guarda contraseña encriptada
        contrasena_en_bytes = contrasena.encode("utf-8")
        sal = bcrypt.gensalt()
        hashado = bcrypt.hashpw(contrasena_en_bytes, sal)
        self.contrasena_hashada = hashado.decode("utf-8")

    def verificar_contrasena(self, contrasena):
        # Se verifica si la contraseña es correcta
        if not self.contrasena_hashada:
            return False
        return bcrypt.checkpw(contrasena.encode("utf-8"), self.contrasena_hashada.encode("utf-8"))

    def serialize(self):
        # Convierte una instancia de la clase en un diccionario de Python para enviarlo como respuesta a solicitudes de la API.
        return {
            "id": self.id,
            "nombre": self.nombre,
            "apellido": self.apellido,
            "correo": self.correo
            # No incluir la contraseña. Es una brecha de seguridad.
        }
