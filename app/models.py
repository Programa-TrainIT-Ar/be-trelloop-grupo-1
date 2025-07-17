from .database import db
import bcrypt

board_user_association = db.Table('board_user_association',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True)
)

user_tag_association = db.Table('user_tag_association',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


class Message(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     content = db.Column(db.String(255), nullable=False)

class User(db.Model):
    __tablename__ = "users"
class User(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(70), unique=False, nullable=False)
    apellido = db.Column(db.String(70), unique=False, nullable=False)
    correo = db.Column(db.String(255), unique=True,nullable=False)
    contrasena_hashada = db.Column(db.String(255))
    boards = db.relationship('Board', secondary='board_user_association', back_populates='members')
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


class Board(db.Model):
    __tablename__ = "boards"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(70), unique=False, nullable=False)
    description = db.Column(db.String(200), unique=False, nullable=True)
    image = db.Column(db.String(500), unique=False, nullable=True)
    creation_date = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    related_members = db.relationship('User', secondary='board_user_association', back_populates='boards')
    related_tag = db.Column(db.String(50), unique=False, nullable=True)
    is_public = db.Column(db.Boolean, default=False)


    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "creation_date": self.creation_date.isoformat(),
            "user_id": self.user_id,
            "related_members": [member.serialize() for member in self.related_members], 
            "related_tags": [tag.serialize() for tag in self.tags]
            "is_public": self.is_public
        }

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    users = db.relationship('User', secondary='user_tag_association', back_populates='tags')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }
