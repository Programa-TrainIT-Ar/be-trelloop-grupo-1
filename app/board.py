from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from datetime import datetime
from io import BytesIO
from .models import db, User, Board, Tag
import uuid
import boto3
import base64
from sqlalchemy import or_
from .services.notifications import create_notification

board_bp = Blueprint("board", __name__)
CORS(board_bp)
# Para utilizar S3 de AWS instalar Boto3 con el siguiente comando: pipenv install boto3
# Configuración de S3
s3 = boto3.client("s3")
BUCKET_NAME = "trainit404"


#Tambien se puede instalar con
#pip install python-dotenv
# Esta función sube una imagen a S3 y devuelve la URL de la imagen
def upload_image_to_s3(base64_image, filename):
    header, encoded = base64_image.split(",", 1)
    binary_data = base64.b64decode(encoded)

    s3.upload_fileobj( 
        BytesIO(binary_data),
        BUCKET_NAME,
        filename,
        ExtraArgs={"ContentType": "image/png"}  # ajustar si recibes JPG, etc.
    )
    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"



@board_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

#CREAR TABLEROS-------------------------------------------------------------------------------------------------------
@board_bp.route("/createBoard", methods=["POST"])
@jwt_required()
def create_board():
    try:
        # Obtener ID del usuario actual desde el JWT
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Recibir datos del formulario
        name = request.form.get("name")
        description = request.form.get("description", "")
        is_public = request.form.get("isPublic", "false").lower() == "true"
        
        # Validación server-side para name
        if not name or not name.strip():
            return jsonify({"error": "Board name is required"}), 400
        
        name = name.strip()
        
        # Validación de unicidad: verificar si ya existe un tablero con el mismo nombre para este usuario
        existing_board = Board.query.filter_by(user_id=user.id, name=name).first()
        if existing_board:
            return jsonify({"error": "You already have a board with this name"}), 400

        # Recibir archivo de imagen
        image_file = request.files.get("image")
        image_url = None

        if image_file:
            try:
                # Convertir imagen a base64 para subirla con función personalizada
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                base64_image = f"data:{image_file.content_type};base64,{encoded_image}"
                filename = f"boards/{uuid.uuid4().hex}.png"
                image_url = upload_image_to_s3(base64_image, filename)
            except Exception as e:
                return jsonify({"error": "Error uploading image", "details": str(e)}), 500

        # Crear nuevo tablero
        new_board = Board(
            name=name,
            description=description,
            image=image_url,
            creation_date=datetime.utcnow(),
            user_id=user.id,
            is_public=is_public
        )

        # Agregar miembros (si se proporcionan)
        member_ids = request.form.getlist("member_ids")
        for uid in member_ids:
            member = User.query.get(uid)
            if member:
                new_board.members.append(member)

        # Agregar tags (si se proporcionan)
        tag_ids = request.form.getlist("tag_ids")
        for tid in tag_ids:
            tag = Tag.query.get(tid)
            if tag:
                new_board.tags.append(tag)

        new_board.members.append(user)  # Agregar el creador del tablero como miembro

        general_tag=Tag.query.filter_by(name="General").first()
        if not general_tag:
            general_tag = Tag(name="General")
            db.session.add(general_tag)
            db.session.flush()
            
        new_board.tags.append(general_tag)  # Agregar tag general por defecto
        # Guardar en la base de datos
        db.session.add(new_board)
        db.session.commit()

        return jsonify(new_board.serialize()), 201

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 500

#OBTENER MIS TABLEROS-------------------------------------------------------------------------------------------------------
@board_bp.route("/getMyBoards",methods=["GET"])
@jwt_required()
def get_my_boards():
    try:
        user_id=get_jwt_identity()
        user=User.query.get(user_id)
        if not user:
            return jsonify({"Error":"Usuario no encontrado"}),404
        boards=user.boards
        return jsonify([board.serialize() for board in boards]), 200
    except Exception as error:
        return jsonify({"Error":str(error)}),500

# AÑADIR MIEMBRO A UN TABLERO-------------------------------------------------------------------------------------------------------        
@board_bp.route("/addMember/<int:board_id>", methods=["POST"])
@jwt_required()
def add_member_to_board(board_id):
    try:
        # Obtengo el usuario actual (actor)
        actor_id = get_jwt_identity()
        actor = User.query.get(actor_id)
        if not actor:
            return jsonify({"Error": "Usuario no encontrado"}), 404

        # Obtengo el tablero al que se le quiere agregar un miembro
        board = Board.query.get(board_id)
        if not board:
            return jsonify({"Error": "Tablero no encontrado"}), 404

        # Obtengo el ID del miembro a agregar desde el cuerpo de la solicitud
        member_id = request.json.get("member_id")
        if not member_id:
            return jsonify({"Error": "ID no encontrado"}), 400

        member = User.query.get(member_id)
        if not member:
            return jsonify({"Error": "Miembro no encontrado"}), 404

        if member in board.members:
            return jsonify({"Error": "El miembro ya está en el tablero"}), 400

        # Agrego el miembro al tablero
        board.members.append(member)
        db.session.commit()

        # Generar event_id para idempotencia
        event_id = f"board:{board_id}:member_added:{member.id}"

        # Crear notificación (persistida, emitida por pusher y opcional email)
        try:
            create_notification(
                db.session,
                user_id=str(member.id),
                type_="BOARD_MEMBER_ADDED",
                title="Has sido agregado a un tablero",
                message=f"{actor.first_name} {actor.last_name} te agregó al tablero '{board.name}'.",
                resource_kind="board",
                resource_id=str(board.id),
                actor_id=str(actor.id),
                event_id=event_id,
                user_email=member.email,
                send_email_also=True
            )
        except Exception as notif_err:
            # No fallamos la operación principal por error en notificación; registramos y seguimos
            print(f"[Notification Error] {notif_err}")

        return jsonify({"message": "Miembro agregado exitosamente"}), 200
    except Exception as error:
        db.session.rollback()
        return jsonify({"Error": str(error)}), 500


#OBTENER UN TABLERO POR ID-------------------------------------------------------------------------------------------------------
@board_bp.route("/getBoard/<int:board_id>", methods=["GET"])
@jwt_required()
def get_board_by_id(board_id):
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return jsonify({"Error": "Usuario no encontrado"}), 404
        
        board = Board.query.get(board_id)
        if not board:
            return jsonify({"Error": "Tablero no encontrado"}), 404
        
        # Control de acceso: verificar si el usuario puede ver este tablero
        is_member = any(member.id == user.id for member in board.members)
        
        if not board.is_public and not is_member:
            return jsonify({"Error": "No tienes acceso a este tablero"}), 403
        
        return jsonify(board.serialize()), 200
    except Exception as error:
        return jsonify({"Error": str(error)}), 500

#AÑADIR TABLERO A FAVORITOS-------------------------------------------------------------------------------------------------------
@board_bp.route("/favoriteBoard/<int:board_id>",methods=["POST"])
@jwt_required()
def favorite_board(board_id):
   try:
       user_id=get_jwt_identity()
       user=User.query.get(user_id)
       if not user:
           return jsonify({"Warning":"Usuario no encontrado"}),404
       board=Board.query.get(board_id)
       if not board:
           return jsonify({"Warning":"Tablero no encontrado"}),404
       if board in user.favorites:
           return jsonify({"Warning":"El tablero ya está en favoritos"}),400
       user.favorites.append(board)
       db.session.commit()
       
       return jsonify({"message":"Tablero agregado a favoritos"}),200
   except Exception as error:
       db.session.rollback()
       return jsonify({"Warning":str(error)}),500

#OBTENER TABLEROS FAVORITOS-------------------------------------------------------------------------------------------------------
@board_bp.route("/getFavoriteBoards",methods=["GET"])
@jwt_required()
def get_favorite_boards():
    try:
        user_id=get_jwt_identity()
        user=User.query.get(user_id)
        if not user:
            return jsonify({"Warning":"Usuario no encontrado"}),404
        favorite_boards=user.favorites
        return jsonify([board.serialize() for board in favorite_boards]),200
    except Exception as error:
           return jsonify({"Warning":str(error)}),500

#ELIMINAR TABLERO DE FAVORITOS-------------------------------------------------------------------------------------------------------
@board_bp.route("/removeFavoriteBoard/<int:board_id>",methods=["DELETE"])
@jwt_required() 
def remove_favorite_board(board_id):
    try:
        user_id=get_jwt_identity()
        user=User.query.get(user_id)
        if not user:
            return jsonify({"Warning":"Usuario no encontrado"}),404
        board=Board.query.get(board_id)
        if not board:
            return jsonify({"Warning":"Tablero no encontrado"}),404
        if board not in user.favorites:
            return jsonify({"Warning":"El tablero no está en favoritos"}),400
        user.favorites.remove(board)
        db.session.commit()
        return jsonify({"message":"Tablero eliminado de favoritos"}),200
    except Exception as error:
        db.session.rollback()
        return jsonify({"Warning":str(error)}),500
    
#ACTUALIZAR UN TABLERO EXISTENTE----------------------------------------------------------------------------------------------
@board_bp.route("/updateBoard/<int:board_id>", methods=["PUT"])
@jwt_required()
def update_board(board_id):
    try:
        current_user_id=get_jwt_identity()
        user=User.query.get(current_user_id)
        if not user:
            return jsonify({"Warning":"Usuario no encontrado"}),404
        board=Board.query.get(board_id)
        if not board:
            return jsonify({"Warning":"Tablero no encontrado"}),404
        if board.user_id != user.id:
            return jsonify({"Warning":"No tienes permiso para actualizar este tablero"}),403
        
        print(f"DEBUG: board.user_id = {board.user_id} (tipo: {type(board.user_id)})")
        print(f"DEBUG: user.id = {user.id} (tipo: {type(user.id)})")
        print(f"DEBUG: Comparación board.user_id != user.id: {board.user_id != user.id}")
        
        if board.user_id != user.id:
            print(f"DEBUG: ACCESO DENEGADO - Los IDs no coinciden")
            return jsonify({"Warning": "No tienes permiso para actualizar este tablero"}), 403



          # Recibir datos del formulario
        name = request.form.get("name")
        description = request.form.get("description", "")
        is_public = request.form.get("isPublic", "false").lower() == "true"

        # Recibir archivo de imagen
        image_file = request.files.get("image")
        image_url = None

        if image_file:
            try:
                # Convertir imagen a base64 para subirla con función personalizada
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
                base64_image = f"data:{image_file.content_type};base64,{encoded_image}"
                filename = f"boards/{uuid.uuid4().hex}.png"
                image_url = upload_image_to_s3(base64_image, filename)
            except Exception as e:
                return jsonify({"error": "Error uploading image", "details": str(e)}), 500
        
         # PROCESAR ETIQUETAS 
        tag_names = request.form.getlist("tags")  # Obtener lista de etiquetas
        
        # Limpiar etiquetas existentes del tablero
        board.tags.clear()
        
        # Agregar nuevas etiquetas
        for tag_name in tag_names:
            if tag_name.strip():
                # Buscar si la etiqueta ya existe
                tag = Tag.query.filter_by(name=tag_name.strip()).first()
                if not tag:
                    # Crear nueva etiqueta si no existe
                    tag = Tag(name=tag_name.strip())
                    db.session.add(tag)
                board.tags.append(tag)

        board.name = name
        board.description = description
        board.is_public = is_public

        db.session.commit()
        db.session.commit()
        return jsonify({"message": "Tablero actualizado exitosamente"}), 200
    except Exception as error:
        db.session.rollback()
        return jsonify({"error":str(error)}),500

# ELIMINAR UN TABLERO----------------------------------------------------------------------------------------------
@board_bp.route("/deleteBoard/<int:board_id>", methods=["DELETE"])
@jwt_required()
def delete_board(board_id):
    """
    Elimina un tablero. Solo el creador del tablero puede eliminarlo.
    """
    try:
        current_user_id = get_jwt_identity()
        board = Board.query.get(board_id)

        # 1. Verificar si el tablero existe
        if not board:
            return jsonify({"error": "Tablero no encontrado"}), 404

        # 2. Verificar si el usuario actual es el propietario del tablero
        if board.user_id != int(current_user_id):
            return jsonify({"error": "No tienes permiso para eliminar este tablero"}), 403

        # Nota: Sería ideal eliminar la imagen asociada de S3 aquí para no dejar archivos huérfanos.

        # 3. Eliminar el tablero de la base de datos
        db.session.delete(board)
        db.session.commit()

        return jsonify({"message": "Tablero eliminado exitosamente"}), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": "Ocurrió un error al eliminar el tablero", "details": str(error)}), 500

# BÚSQUEDA DE USUARIOS PARA AGREGAR COMO MIEMBROS---------------------------------------------------------------------------------------
@board_bp.route("/users/search", methods=["GET"])
@jwt_required()
def search_users():
    try:
        # Obtener parámetro de búsqueda
        query = request.args.get("q", "").strip()

        if not query or len(query) < 2:
            return jsonify({
                "success": True,
                "users": [],
                "message": "Ingrese al menos 2 caracteres para buscar"
            }), 200

        # Buscar por nombre, apellido o email
        users = User.query.filter(
            db.or_(
                User.first_name.ilike(f"%{query}%"),
                User.last_name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%")
            )
        ).limit(10).all()

        # Serializar resultados
        users_serialized = [{
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        } for user in users]

        return jsonify({
            "success": True,
            "users": users_serialized,
            "count": len(users_serialized)
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Error al buscar usuarios",
            "details": str(e)
        }), 500


# ELIMINAR MIEMBRO DE UN TABLERO-------------------------------------------------------------------------------------------------------
@board_bp.route("/removeMember", methods=["DELETE"])
@jwt_required()
def remove_member_from_board():
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        data = request.get_json()
        board_id = data.get("boardId")
        user_id = data.get("userId")

        if not board_id or not user_id:
            return jsonify({"error": "boardId y userId son requeridos"}), 400

        board = Board.query.get(board_id)
        if not board:
            return jsonify({"error": "Tablero no encontrado"}), 404
        
        print(f"DEBUG: board.user_id = {board.user_id} (tipo: {type(board.user_id)})")
        print(f"DEBUG: Comparación: {board.user_id} != {int(current_user_id)} = {board.user_id != int(current_user_id)}")


        # Verificar que el usuario actual sea el propietario del tablero
        if board.user_id != int(current_user_id):
            return jsonify({"error": "No tienes permiso para eliminar miembros de este tablero"}), 403

        user_to_remove = User.query.get(user_id)
        if not user_to_remove:
            return jsonify({"error": "Usuario a eliminar no encontrado"}), 404

        if user_to_remove not in board.members:
            return jsonify({"error": "El usuario no es miembro de este tablero"}), 400

        # No permitir que el propietario se elimine a sí mismo
        if int(user_id) == int(current_user_id):
            return jsonify({"error": "El propietario del tablero no puede eliminarse a sí mismo"}), 400

        board.members.remove(user_to_remove)
        db.session.commit()

        return jsonify({"message": "Miembro eliminado correctamente"}), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 500
