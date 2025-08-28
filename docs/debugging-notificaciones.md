# Debugging del Sistema de Notificaciones

## Resumen de Cambios Realizados

### Frontend

1. **LayoutProviders.tsx**
   - Corregido para obtener el userId del store de Zustand en lugar de localStorage
   - Ahora usa `useAuthStore` para obtener el usuario autenticado
   - Convierte el user.id a string para compatibilidad

2. **pusherClient.ts**
   - Actualizado para obtener el token JWT del store de Zustand (auth-storage)
   - Mejorado el manejo de errores y logs de debugging
   - Agregado verificación de canal existente antes de suscribirse

3. **NotificationContext.tsx**
   - Agregado más logs de debugging
   - Mejorado el manejo de errores
   - Prevención de notificaciones duplicadas

### Backend

1. **main.py**
   - Agregado endpoint `/pusher/auth` en la raíz de la aplicación
   - Configurado con JWT authentication
   - Logs mejorados para debugging

2. **realtime.py y card.py**
   - Eliminados endpoints duplicados de `/pusher/auth`

## Checklist de Verificación

### Variables de Entorno

#### Frontend (.env.local o .env)
```
NEXT_PUBLIC_PUSHER_KEY=tu_pusher_key
NEXT_PUBLIC_PUSHER_CLUSTER=tu_pusher_cluster
NEXT_PUBLIC_PUSHER_AUTH_ENDPOINT=http://localhost:5000/pusher/auth
NEXT_PUBLIC_API=http://localhost:5000
```

#### Backend (.env)
```
PUSHER_APP_ID=tu_app_id
PUSHER_KEY=tu_pusher_key
PUSHER_SECRET=tu_pusher_secret
PUSHER_CLUSTER=tu_pusher_cluster
```

### Logs para Revisar en la Consola del Navegador

1. **Autenticación y Usuario**
   - `[LayoutProviders] User ID updated: {id}` - Verifica que el userId esté disponible
   - `[pusher] Connected successfully` - Conexión exitosa con Pusher

2. **Suscripción a Canal**
   - `[pusher] Attempting to subscribe to channel: private-user-{id}`
   - `[pusher] subscription succeeded to private-user-{id}`
   - `[NotificationProvider] Successfully connected to notification channel`

3. **Recepción de Notificaciones**
   - `[pusher] received notification event` - Evento recibido desde Pusher
   - `[NotificationProvider] Received notification:` - Notificación procesada

### Logs para Revisar en el Backend

1. **Autenticación de Pusher**
   - `[pusher_auth] User {id} trying to auth channel {channel}`
   - `[pusher_auth] Authenticated user {id} for channel {channel}`

2. **Envío de Notificaciones**
   - `[notifications] Emitting pusher for user={id}`
   - `[pusher] Triggering event 'notification' on private-user-{id}`

## Página de Prueba

Visita `http://localhost:3000/test-notifications` para:

1. Ver el estado de autenticación
2. Verificar la configuración de Pusher
3. Enviar notificaciones de prueba locales
4. Ver todas las notificaciones recibidas

## Prueba End-to-End

### 1. Verificar Autenticación
```bash
# En el frontend, abrir consola y ejecutar:
localStorage.getItem('auth-storage')
```

### 2. Probar Endpoint de Notificación
```bash
# Obtener token JWT del auth-storage
TOKEN="tu_token_jwt"

# Enviar notificación de prueba
curl -X POST http://localhost:5000/test-notif \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"userid": "1", "title": "Test", "message": "Prueba desde curl"}'
```

### 3. Agregar Miembro a Tablero (genera notificación real)
```bash
# Agregar miembro a tablero
curl -X POST http://localhost:5000/board/{board_id}/members \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"userId": "2"}'
```

## Problemas Comunes y Soluciones

### 1. No se conecta a Pusher
- Verificar las credenciales de Pusher en las variables de entorno
- Verificar que el token JWT esté presente
- Revisar CORS en el backend

### 2. No se autentican los canales privados
- Verificar que el endpoint `/pusher/auth` responda correctamente
- Verificar que el token JWT se envíe en el header Authorization
- Verificar que el userId coincida con el canal solicitado

### 3. Se reciben notificaciones pero no se muestran
- Verificar que el NotificationProvider esté envolviendo la aplicación
- Verificar que el componente NotificationBell esté usando el hook correctamente
- Revisar la estructura de la notificación recibida

### 4. Notificaciones duplicadas
- Verificar que no haya múltiples suscripciones al mismo canal
- Verificar que el event_id esté configurado correctamente en el backend

## Comandos Útiles

### Frontend
```bash
# Ver todos los logs de Pusher en consola
Pusher.logToConsole = true

# Verificar estado del store
const authState = JSON.parse(localStorage.getItem('auth-storage'))
console.log(authState)
```

### Backend
```bash
# Ver logs del servidor Flask
tail -f app.log

# Verificar conexión con Pusher
python -c "from app.services.pusher_client import get_pusher_client; print(get_pusher_client())"
```
