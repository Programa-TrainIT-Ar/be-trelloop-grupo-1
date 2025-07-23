from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from io import BytesIO
from .models import db, User, Board, Tag
import uuid
import boto3
import base64

board_bp = Blueprint("board", __name__)

# Para utilizar S3 de AWS instalar Boto3 con el siguiente comando: pipenv install boto3
# Configuración de S3
s3 = boto3.client("s3")
BUCKET_NAME = "trainit404"


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



#CREAR TABLEROS-------------------------------------------------------------------------------------------------------
@board_bp.route("/createBoard", methods=["POST"])
@jwt_required()
def create_board():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    name = request.form.get("name")
    description = request.form.get("description", "")
    is_public = request.form.get("isPublic", "false").lower() == "true"

    image_file = request.files.get("image")
    image_url = None

    if image_file:
        try:
            # Convertir archivo a base64 para reutilizar la función
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            base64_image = f"data:{image_file.content_type};base64,{encoded_image}"
            filename = f"boards/{uuid.uuid4().hex}.png"
            image_url = upload_image_to_s3(base64_image, filename)
        except Exception as e:
            return jsonify({"error": "Error uploading image", "details": str(e)}), 500

    new_board = Board(
        name=name,
        description=description,
        image=image_url,
        creation_date=datetime.utcnow(),
        user_id=user.id,
        is_public=is_public
    )

    member_ids = request.form.getlist("member_ids")
    for uid in member_ids:
        member = User.query.get(uid)
        if member:
            new_board.members.append(member)

    tag_ids = request.form.getlist("tag_ids")
    for tid in tag_ids:
        tag = Tag.query.get(tid)
        if tag:
            new_board.tags.append(tag)

    db.session.add(new_board)
    db.session.commit()

    return jsonify(new_board.serialize()), 201


# eliminar tableros---------------------------------------------------------------------------------
@board_bp.route("/deleteBoard/<int:board_id>", methods=["DELETE"])
@jwt_required()
def delete_board(board_id):
    current_user_id = get_jwt_identity()
    board = Board.query.get(board_id)

    if not board:
        return jsonify({"error": "Board not found"}), 404

    # Solo el creador del board puede eliminarlo
    if board.user_id != current_user_id:
        return jsonify({"error": "Unauthorized: You can't delete this board"}), 403

    try:
        db.session.delete(board)
        db.session.commit()
        return jsonify({"message": f"Board '{board.name}' deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Error deleting board", "details": str(e)}), 500