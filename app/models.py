from .database import db
import bcrypt

#Tabla pivote para declarar relación muchos a muchos entre usuarios y tableros
board_user_association = db.Table('board_user_association',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True)
)

#Tabla piovte para declarar relación muchos a muchos entre tableros y etiquetas
board_tag_association = db.Table('board_tag_association',
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


class Message(db.Model):
     id = db.Column(db.Integer, primary_key=True)
     content = db.Column(db.String(255), nullable=False)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(70), unique=False, nullable=False)
    last_name = db.Column(db.String(70), unique=False, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))

    boards = db.relationship('Board', secondary='board_user_association', back_populates='members')
    
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
    members = db.relationship('User', secondary='board_user_association', back_populates='boards')
    tags = db.relationship('Tag', secondary='board_tag_association', back_populates='boards')
    is_public = db.Column(db.Boolean, default=False) # Indica si el tablero es público o privado, por defecto será privado.


    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "image": self.image,
            "creationDate": self.creation_date.isoformat(),
            "userId": self.user_id,
            "members": [member.serialize() for member in self.members], 
            "tags": [tag.serialize() for tag in self.tags],
            "isPublic": self.is_public
        }

class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    boards = db.relationship('Board', secondary='board_tag_association', back_populates='tags')

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name
        }
