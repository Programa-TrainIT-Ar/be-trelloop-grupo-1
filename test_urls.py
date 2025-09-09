#!/usr/bin/env python3
"""
Script para probar diferentes variaciones de URLs y encontrar la correcta
"""

import requests
import json

API_BASE = "http://localhost:5000"
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "123456"

def login_user():
    response = requests.post(f"{API_BASE}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    })
    
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def test_url_generation(token, resource_kind, resource_id):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    response = requests.post(f"{API_BASE}/realtime/notifications/test-url",
                           headers=headers,
                           json={
                               "resource_kind": resource_kind,
                               "resource_id": resource_id
                           })
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def main():
    print("🔗 Probando generación de URLs...")
    
    token = login_user()
    if not token:
        print("❌ No se pudo autenticar")
        return
    
    print("✅ Usuario autenticado")
    
    # Probar diferentes combinaciones
    test_cases = [
        ("board", "1"),
        ("card", "1"),
        ("board", "2"),
        ("card", "2")
    ]
    
    for resource_kind, resource_id in test_cases:
        print(f"\n🧪 Probando {resource_kind} ID {resource_id}:")
        result = test_url_generation(token, resource_kind, resource_id)
        
        if result:
            print(f"   📋 Tipo: {result['resource_kind']}")
            print(f"   🆔 ID: {result['resource_id']}")
            print(f"   🔗 URL generada: {result['generated_url']}")
            print(f"   🏠 Frontend base: {result['frontend_base']}")
        else:
            print("   ❌ Error generando URL")

if __name__ == "__main__":
    main()