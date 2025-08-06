from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_cors import CORS, cross_origin
from datetime import datetime
from .models import db, User, Board, Tag, Card
import uuid


card_bp = Blueprint("card", __name__)
CORS(card_bp)

@board_bp.before_request
def handle_options_request():
    if request.method == 'OPTIONS':
        return '', 204

# CREAR TARJETAS-------------------------------------------------------------------------------------------------------
# MOSTRAR TARJETAS (TODOS)-------------------------------------------------------------------------------------------------------
# MOSTRAR TARJETAS POR ID-------------------------------------------------------------------------------------------------------
# ACTUALIZAR UNA TARJETA EXISTENTE----------------------------------------------------------------------------------------------
# ELIMINAR UNA TARJETA----------------------------------------------------------------------------------------------
# AGREGAR MIEMBROS A UNA TARJETA-------------------------------------------------------------------------------------------------------
# ELIMINAR MIEMBROS DE UNA TARJETA-------------------------------------------------------------------------------------------------------
# OBTENER MIEMBROS DE UNA TARJETA------------------------------------------------------------------------------------------------------- 