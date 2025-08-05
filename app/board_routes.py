from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Board, User, Tag
from app.database import db
from sqlalchemy.orm import joinedload


board_bp = Blueprint('board', __name__)

@board_bp.route('/boards/<int:board_id>', methods=['GET'])
@jwt_required()
def get_board(board_id):
    
    try:
        print(f"🔍 Usuario solicitando tablero {board_id}")
        
        # Obtener ID del usuario autenticado
        current_user_id = get_jwt_identity()
        
        # Buscar tablero con relaciones cargadas (optimización)
        board = Board.query.options(
            joinedload(Board.members),
            joinedload(Board.tags)
        ).filter_by(id=board_id).first()
        
        if not board:
            print(f"❌ Tablero {board_id} no encontrado")
            return jsonify({
                "success": False,
                "error": "Tablero no encontrado"
            }), 404
        
        
        if not board.is_public and board.user_id != current_user_id:
            # Verificar si es miembro del tablero
            member_ids = [member.id for member in board.members]
            if current_user_id not in member_ids:
                print(f"❌ Usuario {current_user_id} sin permisos para ver tablero {board_id}")
                return jsonify({
                    "success": False,
                    "error": "No tienes permisos para ver este tablero"
                }), 403
        
        print(f"✅ Tablero {board.name} enviado al usuario {current_user_id}")
        
        return jsonify({
            "success": True,
            "board": board.serialize()
        }), 200
        
    except Exception as e:
        print(f"💥 Error al obtener tablero: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500


@board_bp.route('/boards/<int:board_id>', methods=['PUT'])
@jwt_required()
def update_board(board_id):
 
    try:
        print(f"🔄 Actualizando tablero {board_id}")
        
        # Obtener ID del usuario autenticado
        current_user_id = get_jwt_identity()
        
        # Buscar el tablero
        board = Board.query.filter_by(id=board_id).first()
        
        if not board:
            print(f"❌ Tablero {board_id} no encontrado")
            return jsonify({
                "success": False,
                "error": "Tablero no encontrado"
            }), 404
        
        if board.user_id != current_user_id:
            print(f"❌ Usuario {current_user_id} sin permisos para editar tablero {board_id}")
            return jsonify({
                "success": False,
                "error": "Solo el creador del tablero puede editarlo"
            }), 403
        
        # Obtener datos del request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No se enviaron datos para actualizar"
            }), 400
        
        print(f"📝 Datos recibidos: {list(data.keys())}")
        
        errors = []
        
        if 'name' in data:
            if not data['name'] or not data['name'].strip():
                errors.append("El nombre del tablero es obligatorio")
            elif len(data['name'].strip()) > 70:
                errors.append("El nombre no puede tener más de 70 caracteres")
        
        if 'description' in data and data['description']:
            if len(data['description']) > 200:
                errors.append("La descripción no puede tener más de 200 caracteres")
        
        if errors:
            return jsonify({
                "success": False,
                "error": "Datos inválidos",
                "details": errors
            }), 400
        
        changes_made = []
        
        if 'name' in data and data['name'].strip():
            old_name = board.name
            board.name = data['name'].strip()
            changes_made.append(f"Nombre: '{old_name}' → '{board.name}'")
        
        if 'description' in data:
            board.description = data['description'] if data['description'] else None
            changes_made.append("Descripción actualizada")
        
        if 'image' in data:
            board.image = data['image'] if data['image'] else None
            changes_made.append("Imagen actualizada")
        
        if 'isPublic' in data:
            board.is_public = data['isPublic']
            visibility = "público" if board.is_public else "privado"
            changes_made.append(f"Visibilidad: {visibility}")
        
        # ACTUALIZAR MIEMBROS (FORMA CORRECTA)
        if 'members' in data:
            print(f"👥 Actualizando miembros...")
            
            # Validar que los IDs de usuarios existan
            member_ids = data['members'] if data['members'] else []
            
            if member_ids:
                # Verificar que todos los usuarios existen
                existing_users = User.query.filter(User.id.in_(member_ids)).all()
                existing_ids = {user.id for user in existing_users}
                invalid_ids = [uid for uid in member_ids if uid not in existing_ids]
                
                if invalid_ids:
                    return jsonify({
                        "success": False,
                        "error": f"Usuarios no encontrados: {invalid_ids}"
                    }), 400
            
            # FORMA CORRECTA de actualizar relación many-to-many
            board.members.clear()  # Limpiar relaciones existentes
            
            if member_ids:
                users_to_add = User.query.filter(User.id.in_(member_ids)).all()
                for user in users_to_add:
                    board.members.append(user)
                    print(f"➕ Miembro agregado: {user.first_name} {user.last_name}")
            
            changes_made.append(f"Miembros actualizados ({len(member_ids)} miembros)")
        
        # ACTUALIZAR ETIQUETAS (FORMA MEJORADA)
        if 'tags' in data:
            print(f"🏷️ Actualizando etiquetas...")
            
            tag_names = data['tags'] if data['tags'] else []
            
            # FORMA CORRECTA de actualizar relación many-to-many
            board.tags.clear()  # Limpiar relaciones existentes
            
            if tag_names:
                for tag_name in tag_names:
                    tag_name = tag_name.strip()
                    if not tag_name:
                        continue
                    
                    # Buscar etiqueta existente
                    tag = Tag.query.filter_by(name=tag_name).first()
                    
                    # Si no existe, crear nueva etiqueta
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                        print(f"🆕 Nueva etiqueta creada: {tag_name}")
                    
                    board.tags.append(tag)
                    print(f"➕ Etiqueta agregada: {tag_name}")
            
            changes_made.append(f"Etiquetas actualizadas ({len(tag_names)} etiquetas)")
        
        # GUARDAR CAMBIOS CON MANEJO DE ERRORES
        db.session.commit()
        print(f"💾 Cambios guardados: {'; '.join(changes_made)}")
        
        # Recargar tablero con relaciones actualizadas
        updated_board = Board.query.options(
            joinedload(Board.members),
            joinedload(Board.tags)
        ).filter_by(id=board_id).first()
        
        return jsonify({
            "success": True,
            "message": "Tablero actualizado correctamente",
            "board": updated_board.serialize(),
            "changes": changes_made
        }), 200
        
    except Exception as e:
        # ROLLBACK en caso de error
        db.session.rollback()
        print(f"💥 Error al actualizar tablero: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500

@board_bp.route('/boards/<int:board_id>/members', methods=['GET'])
@jwt_required()
def get_board_members(board_id):
   
    try:
        board = Board.query.options(joinedload(Board.members)).get(board_id)
        
        if not board:
            return jsonify({
                "success": False,
                "error": "Tablero no encontrado"
            }), 404
        
        return jsonify({
            "success": True,
            "members": [member.serialize() for member in board.members],
            "count": len(board.members)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Error interno del servidor"
        }), 500

@board_bp.route('/users/search', methods=['GET'])
@jwt_required()
def search_users():
    """
    Busca usuarios para agregar como miembros
    """
    try:
        query = request.args.get('q', '').strip()
        
        if len(query) < 2:
            return jsonify({
                "success": True,
                "users": [],
                "message": "Ingresa al menos 2 caracteres"
            }), 200
        
        users = User.query.filter(
            db.or_(
                User.first_name.ilike(f'%{query}%'),
                User.last_name.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(10).all()
        
        return jsonify({
            "success": True,
            "users": [user.serialize() for user in users],
            "count": len(users)
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Error al buscar usuarios"
        }), 500