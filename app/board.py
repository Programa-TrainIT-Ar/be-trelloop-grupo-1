from flask import Blueprint, request, jsonify
from datetime import datetime
from io import BytesIO
from .models import db, User, Board, Tag
import uuid
import boto3
import base64

# Para utilizar S3 de AWS instalar Boto3 con el siguiente comando:
# pipenv install boto3
# Configuración de S3
s3 = boto3.client("s3")
BUCKET_NAME = "trainit404"

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


board_bp = Blueprint('board', __name__)

#CREAR TABLEROS-------------------------------------------------------------------------------------------------------
@app.route("/createBoard", methods=["POST"])
def create_board():
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

    return jsonify(new_board.serialize()), 201