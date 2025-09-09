#!/usr/bin/env python3
"""
Script para probar que los enlaces en los emails de notificaciones funcionen correctamente.
"""

import os
import requests
import json

# Configuración
API_BASE = "http://localhost:5000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "123456"

def login_user():
    """Autentica un usuario y retorna el token JWT"""
    response = requests.post(f"{API_BASE}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    
    if response.status_code == 200:
        data = response.json()
        return data.get("access_token")
    else:
        print(f"Error en login: {response.status_code} - {response.text}")
        return None

def get_headers(token):
    """Retorna headers con autenticación"""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_user_boards(token):
    """Obtiene los tableros del usuario"""
    response = requests.get(f"{API_BASE}/board/getMyBoards", headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    return []

def get_board_cards(token, board_id):
    """Obtiene las tarjetas de un tablero"""
    response = requests.get(f"{API_BASE}/card/getCards/{board_id}", headers=get_headers(token))
    if response.status_code == 200:
        return response.json()
    return []

def test_email_notification(token, resource_kind, resource_id, title_suffix=""):
    """Envía una notificación de prueba por email"""
    response = requests.post(f"{API_BASE}/realtime/notifications/test-email",
                           headers=get_headers(token),
                           json={
                               "title": f"Prueba de Email - {resource_kind.title()} {title_suffix}",
                               "message": f"Este email contiene un enlace para abrir {resource_kind} ID: {resource_id}",
                               "resource_kind": resource_kind,
                               "resource_id": resource_id
                           })
    
    if response.status_code == 201:
        return response.json()
    else:
        print(f"Error enviando email: {response.status_code} - {response.text}")
        return None

def main():
    print("🔗 Iniciando prueba de enlaces en emails de notificaciones...")
    
    # 1. Autenticar usuario
    print("\n1️⃣ Autenticando usuario...")
    token = login_user()
    if not token:
        print("❌ No se pudo autenticar. Verifica que el usuario exista.")
        return
    print("✅ Usuario autenticado correctamente")
    
    # 2. Obtener tableros del usuario
    print("\n2️⃣ Obteniendo tableros del usuario...")
    boards = get_user_boards(token)
    if not boards:
        print("❌ No se encontraron tableros. Crea al menos un tablero para probar.")
        return
    
    print(f"📋 Encontrados {len(boards)} tableros:")
    for board in boards[:3]:  # Mostrar solo los primeros 3
        print(f"   - {board['name']} (ID: {board['id']})")
    
    # 3. Probar email con enlace a tablero
    print("\n3️⃣ Enviando email de prueba para tablero...")
    test_board = boards[0]
    board_result = test_email_notification(token, "board", str(test_board['id']), test_board['name'])
    
    if board_result:
        print(f"✅ Email enviado para tablero '{test_board['name']}'")
        print(f"   📧 Enviado a: {board_result['email_sent_to']}")
        print(f"   🔗 Debería enlazar a: {os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')}/board/{test_board['id']}")
    else:
        print("❌ Error enviando email para tablero")
    
    # 4. Obtener tarjetas del primer tablero
    print(f"\n4️⃣ Obteniendo tarjetas del tablero '{test_board['name']}'...")
    cards = get_board_cards(token, test_board['id'])
    
    if cards:
        print(f"🎯 Encontradas {len(cards)} tarjetas:")
        for card in cards[:3]:  # Mostrar solo las primeras 3
            print(f"   - {card['title']} (ID: {card['id']})")
        
        # 5. Probar email con enlace a tarjeta
        print("\n5️⃣ Enviando email de prueba para tarjeta...")
        test_card = cards[0]
        card_result = test_email_notification(token, "card", str(test_card['id']), test_card['title'])
        
        if card_result:
            print(f"✅ Email enviado para tarjeta '{test_card['title']}'")
            print(f"   📧 Enviado a: {card_result['email_sent_to']}")
            print(f"   🔗 Debería enlazar a: {os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')}/board/{test_board['id']}")
        else:
            print("❌ Error enviando email para tarjeta")
    else:
        print("⚠️ No se encontraron tarjetas en el tablero. Crea al menos una tarjeta para probar enlaces de tarjetas.")
    
    # 6. Instrucciones finales
    print("\n6️⃣ Verificación manual:")
    print("📧 Revisa tu bandeja de entrada para los emails de prueba")
    print("🔗 Haz clic en los botones 'Abrir Tablero' y 'Abrir Tarjeta'")
    print("✅ Verifica que te lleven a las páginas correctas en el frontend")
    
    print("\n📋 URLs esperadas:")
    print(f"   Tablero: {os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')}/board/{test_board['id']}")
    if cards:
        print(f"   Tarjeta: {os.getenv('FRONTEND_BASE_URL', 'http://localhost:3000')}/board/{test_board['id']} (debería mostrar la tarjeta)")
    
    print("\n✨ Prueba completada")

if __name__ == "__main__":
    main()