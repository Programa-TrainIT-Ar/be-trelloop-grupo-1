from .database import db
from datetime import datetime
import bcrypt
from sqlalchemy.dialects.postgresql import UUID
import uuid

# import enum------------------(pendiente borrar si ya no se usa)

#Tabla pivote para declarar relación muchos a muchos entre usuarios y tableros
board_user_association = db.Table('board_user_association',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True), 
)

#Tabla piovte para declarar relación muchos a muchos entre tableros y etiquetas
board_tag_association = db.Table('board_tag_association',
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

#Tabla pivote para declarar relación muchos a muchos entre tarjetas y usuarios'
card_user_association = db.Table('card_user_association',
    db.Column('card_id', db.Integer, db.ForeignKey('cards.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

#Tabla pivote para declaracion de muchos a muchos entre favoritos y usuarios
favorite_boards = db.Table('favorite_boards',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('board_id', db.Integer, db.ForeignKey('boards.id'), primary_key=True)
)

# Agregar esta tabla card y etiquetas para la relación muchos a muchos entre tarjetas y etiquetas:
card_tag_association = db.Table('card_tag_association',
    db.Column('card_id', db.Integer, db.ForeignKey('cards.id'), primary_key=True),
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
    # profile_image = db.Column(db.String(500), nullable=True)  # Campo para almacenar la URL de la imagen

    boards = db.relationship('Board', secondary='board_user_association', back_populates='members')
    favorites = db.relationship('Board', secondary='favorite_boards', backref='favorited_by')

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
            "email": self.email,
            # "profileImage": self.profile_image  # Incluir la URL de la imagen en la serialización
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

    cards = db.relationship("Card", backref="board", cascade="all, delete-orphan")
   


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

#------------------(pendiente borrar si ya no se usa)
# class State(enum.Enum):
#     TODO = "To Do"
#     IN_PROGRESS = "In Progress"
#     DONE = "Done"

class Card(db.Model):
    __tablename__="cards"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    responsable_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    creation_date = db.Column(db.DateTime, nullable=False)
    begin_date = db.Column(db.DateTime, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    state = db.Column(db.String(255), nullable=False, default='To Do') 
    board_id = db.Column(db.Integer, db.ForeignKey("boards.id"), nullable=False)
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = db.Column(db.String(20), nullable=True)

    tags = db.relationship('Tag', secondary='card_tag_association', backref='cards')
    members = db.relationship('User', secondary='card_user_association', backref='cards')
    list = db.relationship("List", backref="cards")
    
    def serialize(self):
        list_name = self.list.name if self.list else None
        state = list_name or self.state

        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "responsableId": self.responsable_id,
            "creationDate": self.creation_date.isoformat(),
            "beginDate": self.begin_date.isoformat() if self.begin_date else None,
            "dueDate": self.due_date.isoformat() if self.due_date else None,
            "state": self.state,
            "boardId": self.board_id,
            "listId": self.list_id,
            "listName": list_name,
            "tags":[tag.name for tag in self.tags],
            "members": [member.serialize() for member in self.members]
        }
    
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Tipo y contenido
    type = db.Column(db.String(50), nullable=False)        
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)

    # Recurso relacionado (opcional)
    resource_kind = db.Column(db.String(20), nullable=True)  
    resource_id = db.Column(db.Integer, nullable=True)

    # Actor que originó el evento (opcional)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Estado y tiempo
    read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    # Idempotencia (opcional pero útil)
    event_id = db.Column(db.String(100), unique=True, nullable=True)

    # Índices para consultas típicas
    __table_args__ = (
        db.Index("idx_notifications_user_read_created", "user_id", "read", "created_at"),
    )

    def serialize(self):
        return {
            "id": str(self.id),  
            "userId": self.user_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "resource": (
                {"kind": self.resource_kind, "id": self.resource_id}
                if self.resource_kind and self.resource_id is not None else None
            ),
            "actorId": self.actor_id,
            "read": self.read,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "eventId": self.event_id,
        }

class Subtask(db.Model):
    __tablename__ = "subtasks"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    limit_date = db.Column(db.DateTime, nullable=True)

    # Relación con usuario responsable
    responsible_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    responsible = db.relationship("User", backref="subtasks")
    # Relación con la tarjeta (cada subtask pertenece a una card)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    # Estado activa/inactiva
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "description": self.description,
            "limitDate": self.limit_date.isoformat() if self.limit_date else None,
            "responsible": self.responsible.serialize() if self.responsible else None,
            "cardId": self.card_id,
            "isActive": self.is_active,
        }
    

class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    parent_id = db.Column(db.Integer, db.ForeignKey("comments.id"), nullable=True, index=True)

    content   = db.Column(db.Text, nullable=False)
    is_edited = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=True)

 
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        db.Index("idx_comments_card_created", "card_id", "created_at"),
    )
    user = db.relationship("User", foreign_keys=[user_id])
    def serialize(self, *, include_deleted_content: bool = False):
        is_deleted = self.deleted_at is not None
        u = self.user  

        return {
            "id": self.id,
            "cardId": self.card_id,
            "userId": self.user_id,                      
            "user": u.serialize() if u else None,          
            "parentId": self.parent_id,
            "content": (self.content if (not is_deleted or include_deleted_content) else None),
            "placeholder": ("Comentario eliminado" if is_deleted else None),
            "isEdited": self.is_edited,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
            "deleted": is_deleted,
            "deletedAt": self.deleted_at.isoformat() if self.deleted_at else None,
            "deletedBy": self.deleted_by,
        }


class List(db.Model):
    __tablename__ = "lists"

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey("boards.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())

    board = db.relationship("Board", backref=db.backref("lists", cascade="all, delete-orphan"))

    __table_args__ = (
        db.Index("uq_lists_board_lower_name", "board_id", db.text("LOWER(name)"), unique=True),
    )

    def serialize(self):
        return {
            "id": self.id,
            "boardId": self.board_id,
            "name": self.name,
            "position": self.position,
            "createdBy": self.created_by,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
