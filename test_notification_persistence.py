#!/usr/bin/env python3
"""
Script para probar la persistencia de las notificaciones marcadas como leídas.
Este script ayuda a verificar que las notificaciones se marquen correctamente en la base de datos.
"""

import os
import sys
import requests
import json
from datetime import datetime

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

def create_test_notification(token):
    """Crea una notificación de prueba"""
    response = requests.post(f"{API_BASE}/realtime/notifications/test-push", 
                           headers=get_headers(token),
                           json={
                               "title": "Prueba de persistencia",
                               "message": "Esta notificación debe mantenerse como leída después de marcarla",
                               "type": "TEST_PERSISTENCE"
                           })
    
    if response.status_code == 201:
        data = response.json()
        return data.get("notification_id")
    else:
        print(f"Error creando notificación: {response.status_code} - {response.text}")
        return None

def get_notifications(token):
    """Obtiene todas las notificaciones del usuario"""
    response = requests.get(f"{API_BASE}/realtime/notifications", 
                          headers=get_headers(token))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error obteniendo notificaciones: {response.status_code} - {response.text}")
        return None

def mark_notification_read(token, notification_id):
    """Marca una notificación específica como leída"""
    response = requests.post(f"{API_BASE}/realtime/notifications/mark-one-read/{notification_id}", 
                           headers=get_headers(token))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error marcando notificación como leída: {response.status_code} - {response.text}")
        return None

def debug_notification(token, notification_id):
    """Obtiene información de debug de una notificación"""
    response = requests.get(f"{API_BASE}/realtime/notifications/debug/{notification_id}", 
                          headers=get_headers(token))
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error obteniendo debug: {response.status_code} - {response.text}")
        return None

def main():
    print("🔍 Iniciando prueba de persistencia de notificaciones...")
    
    # 1. Autenticar usuario
    print("\n1️⃣ Autenticando usuario...")
    token = login_user()
    if not token:
        print("❌ No se pudo autenticar. Verifica que el usuario exista.")
        return
    print("✅ Usuario autenticado correctamente")
    
    # 2. Crear notificación de prueba
    print("\n2️⃣ Creando notificación de prueba...")
    notification_id = create_test_notification(token)
    if not notification_id:
        print("❌ No se pudo crear la notificación")
        return
    print(f"✅ Notificación creada: {notification_id}")
    
    # 3. Verificar que la notificación existe y está como no leída
    print("\n3️⃣ Verificando estado inicial...")
    notifications_data = get_notifications(token)
    if notifications_data:
        unread_count = notifications_data["meta"]["unread_count"]
        print(f"📊 Notificaciones no leídas: {unread_count}")
        
        # Buscar nuestra notificación
        test_notif = None
        for notif in notifications_data["notifications"]:
            if notif["id"] == notification_id:
                test_notif = notif
                break
        
        if test_notif:
            print(f"📋 Notificación encontrada - Leída: {test_notif['read']}")
        else:
            print("❌ No se encontró la notificación creada")
            return
    
    # 4. Marcar como leída
    print("\n4️⃣ Marcando notificación como leída...")
    mark_result = mark_notification_read(token, notification_id)
    if mark_result:
        print(f"✅ Notificación marcada como leída. Nuevas no leídas: {mark_result['unread_count']}")
    else:
        print("❌ Error marcando como leída")
        return
    
    # 5. Verificar que se marcó correctamente
    print("\n5️⃣ Verificando que se marcó correctamente...")
    debug_info = debug_notification(token, notification_id)
    if debug_info:
        is_read = debug_info["raw_data"]["read"]
        print(f"🔍 Estado en base de datos - Leída: {is_read}")
        
        if is_read:
            print("✅ La notificación está correctamente marcada como leída en la base de datos")
        else:
            print("❌ ERROR: La notificación NO está marcada como leída en la base de datos")
    
    # 6. Verificar nuevamente con GET general
    print("\n6️⃣ Verificación final con GET general...")
    final_notifications = get_notifications(token)
    if final_notifications:
        final_unread = final_notifications["meta"]["unread_count"]
        print(f"📊 Notificaciones no leídas finales: {final_unread}")
        
        # Buscar nuestra notificación nuevamente
        final_test_notif = None
        for notif in final_notifications["notifications"]:
            if notif["id"] == notification_id:
                final_test_notif = notif
                break
        
        if final_test_notif:
            print(f"📋 Estado final de la notificación - Leída: {final_test_notif['read']}")
            
            if final_test_notif['read']:
                print("🎉 ¡ÉXITO! La notificación se mantiene como leída")
            else:
                print("💥 PROBLEMA: La notificación volvió a aparecer como no leída")
        else:
            print("❓ La notificación ya no aparece en la lista (posible filtro)")
    
    print("\n✨ Prueba completada")

if __name__ == "__main__":
    main()