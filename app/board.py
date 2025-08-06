from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from datetime import datetime
from io import BytesIO
from .models import db, User, Board, Tag
import uuid
import boto3
import base64

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

@board_bp.route("/getBoards", methods=["GET"])
@jwt_required()
def get_boards():
    try:
        # Obtener el usuario actual
        user_id= get_jwt_identity()
        user = User.query.get(user_id)

        # Validar si el usuario existe
        if not user:
            return jsonify({"error": "User not found"}), 404
        # Obtener todos los tableros
        boards=Board.query.all()
        return jsonify([board.serialize() for board in boards]), 200

    except Exception as error:
        return jsonify({"Error":str(error)}), 500

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

@board_bp.route("/addMember/<int:board_id>", methods=["POST"])
@jwt_required()
def add_member_to_board(board_id):
    try:
        #Obtengo el usuario actual
        user_id=get_jwt_identity()
        user=User.query.get(user_id)
        if not user:
            return jsonify({"Error":"Usuario no encontrado"}),404

        # Obtengo el tablero al que se le quiere agregar un miembro
        board=Board.query.get(board_id)
        if not board:
            return jsonify({"Error":"Tablero no encontrado"}),404

        # Obtengo el ID del miembro a agregar desde el cuerpo de la solicitud
        member_id=request.json.get("member_id")
        if not member_id:
            return jsonify({"Error":"ID no encontrado"}),400

        member=User.query.get(member_id)
        if not member:
            return jsonify({"Error":"Miembro no encontrado"}),404

        if member in board.members:
            return jsonify({"Error":"El miembro ya está en el tablero"}),400


        # Agrego el miembro al tablero
        board.members.append(member)
        db.session.commit()
        return jsonify({"message": "Miembro agregado exitosamente"}), 200
    except Exception as error:
        db.session.rollback()
        return jsonify({"Error":str(error)}),500


@board_bp.route("/getBoard/<int:board_id>", methods=["GET"])
@jwt_required()
def get_board_by_id(board_id):
    try:
        user_id=get_jwt_identity()
        user= User.query.get(user_id)
        if not user:
            return jsonify({"Error":"Usuario no encontrado"}),404
        board=Board.query.get(board_id)
        if not board:
            return jsonify({"Error":"Tablero no encontrado"}),404
        if user not in board.members and not board.is_public:
            return jsonify({"Error": "No tienes acceso a este tablero"}), 403
        
        return jsonify(board.serialize()), 200
    except Exception as error:
        return jsonify({"Error":str(error)}),500

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
    
#ACTUALIZAR UN TABLERO EXISTENTE

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
        
        board.name = name
        board.description = description
        board.is_public = is_public

        db.session.commit()
        db.session.commit()
        return jsonify({"message": "Tablero actualizado exitosamente"}), 200
    except Exception as error:
        db.session.rollback()
        return jsonify({"error":str(error)}),500

# ELIMINAR UN TABLERO
#----------------------------------------------------------------------------------------------
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
        if board.user_id != current_user_id:
            return jsonify({"error": "No tienes permiso para eliminar este tablero"}), 403

        # Nota: Sería ideal eliminar la imagen asociada de S3 aquí para no dejar archivos huérfanos.

        # 3. Eliminar el tablero de la base de datos
        db.session.delete(board)
        db.session.commit()

        return jsonify({"message": "Tablero eliminado exitosamente"}), 200

    except Exception as error:
        db.session.rollback()
        return jsonify({"error": "Ocurrió un error al eliminar el tablero", "details": str(error)}), 500
