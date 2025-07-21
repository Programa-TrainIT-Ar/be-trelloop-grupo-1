from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from io import BytesIO
from .models import db, User, Board, Tag
import uuid
import boto3
import base64
from flask_cors import CORS, cross_origin
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)

# Para utilizar S3 de AWS instalar Boto3 con el siguiente comando:
# pipenv install boto3
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
    try:
        # Recibes los datos de texto desde request.form
        name = request.form.get("name")
        description = request.form.get("description", "")
        user_id = request.form.get("user_id")
        is_public = request.form.get("isPublic", "false").lower() == "true"

        # Verificar usuario
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Recibes el archivo imagen (input name="image")
        image_file = request.files.get("image")
        image_url = None

        if image_file:
            # Generar nombre único para la imagen
            filename = f"boards/{uuid.uuid4().hex}.png"

            # Convertir archivo a bytes y subir a S3
            try:
                s3.upload_fileobj(
                    image_file,
                    BUCKET_NAME,
                    filename,
                    ExtraArgs={"ContentType": image_file.content_type}
                )
                image_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"
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

        # Manejar miembros (opcional, si envías member_ids como form-data, considera recibirlos)
        member_ids = request.form.getlist("member_ids")
        for uid in member_ids:
            member = User.query.get(uid)
            if member:
                new_board.members.append(member)

        # Manejar tags (opcional, igual que member_ids)
        tag_ids = request.form.getlist("tag_ids")
        for tid in tag_ids:
            tag = Tag.query.get(tid)
            if tag:
                new_board.tags.append(tag)

        db.session.add(new_board)
        db.session.commit()
    except Exception as error:
        db.session.rollback()
        return jsonify({"error": str(error)})

    return jsonify(new_board.serialize()), 201


@board_bp.route("/getBoards", methods=["GET"])
@jwt_required()
def get_boards():
    try:
        user_id= get_jwt_identity()
    
    # Obtener todos los tableros
        boards=Board.query.all()
        return jsonify([board.serialize() for board in boards]), 200
    except Exception as error:
        return jsonify({"Error":str(error)}), 500
