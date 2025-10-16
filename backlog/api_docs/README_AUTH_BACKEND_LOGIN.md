NEUSI Task Manager – API de Autenticación (Backend)

**Desarrollado por:** Jorge Cardona  
**Framework:** Django 5.2  
**Puerto local:** 8076  
**Base URL (entorno local):** `http://localhost:8076`

> 🔁 En producción / ngrok reemplazar base por:
> `https://devops-neusi.ngrok.io`  
> Mantener el mismo path `/api/auth/`

-----------------------------------------------------------

##  Endpoints de Autenticación

### 1 Obtener CSRF Token
**Método:** `GET`  
**URL:** `/api/auth/csrf/`  
**Respuesta 200:**
```json
{ "detail": "CSRF cookie set", "csrfToken": "<valor opcional>" }
Efecto:
Crea una cookie csrftoken en el navegador, necesaria antes de cualquier POST, PUT, PATCH o DELETE.

Notas:

Debe llamarse antes de cualquier envío de datos.

Django rota este token tras cada login → refrescar después de autenticarse.

----------------------------------------------------------------------------------------------
2 Iniciar sesión (Login)
Método: POST
URL: /api/auth/login/

Headers requeridos:
Content-Type: application/json
X-CSRFToken: <valor de la cookie csrftoken>

Body:

{ "username": "jorge", "password": "Jorge2025." }
Respuesta exitosa 200:


{
  "id": 1,
  "username": "jorge",
  "rol": "Scrum Master / PO",
  "is_authenticated": true,
  "must_change_password": false
}
Respuesta 400 (error):

{ "error": "Usuario o contraseña incorrectos" }
Efecto:
Genera una cookie sessionid (sesión activa) y actualiza csrftoken.

----------------------------------------------------------------------------------------------
3 Usuario actual (Ver sesión)
Método: GET
URL: /api/auth/me/

Respuesta 200 (autenticado):

{
  "id": 1,
  "username": "jorge",
  "rol": "Scrum Master / PO",
  "is_authenticated": true
}
Sin sesión:
Retorna 302 Redirect a la página de login (HTML).
→ En frontend, detectar si la respuesta no es JSON para asumir “no autenticado”.

----------------------------------------------------------------------------------------------
4 Cerrar sesión (Logout)
Método: POST
URL: /api/auth/logout/

Headers:

X-CSRFToken: <valor actual de csrftoken>

Respuesta 200:

{ "detail": "Sesión cerrada" }
Efecto:
Elimina la cookie sessionid → el usuario queda deslogueado.

----------------------------------------------------------------------------------------------
Reglas generales para Frontend (Next.js)
Usar siempre credentials: "include" para que el navegador envíe cookies.
Incluir X-CSRFToken en todos los métodos que modifiquen datos (POST, PUT, PATCH, DELETE).
Refrescar /api/auth/csrf/ después del login.
Si /api/auth/me/ devuelve HTML o 403 → sesión expirada.

----------------------------------------------------------------------------------------------
Ejemplo de flujo en Next.js:

const BASE = process.env.NEXT_PUBLIC_API_BASE;

await fetch(`${BASE}/api/auth/csrf/`, { credentials: 'include' });

await fetch(`${BASE}/api/auth/login/`, {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': document.cookie
      .split('; ')
      .find(r => r.startsWith('csrftoken='))?.split('=')[1] || ''
  },
  body: JSON.stringify({ username: 'jorge', password: 'Jorge2025.' })
});

----------------------------------------------------------------------------------------------
Variables de entorno (Frontend)
Archivo .env.local:

ini
Copiar código
NEXT_PUBLIC_API_BASE=http://localhost:8076
Uso:


fetch(`${process.env.NEXT_PUBLIC_API_BASE}/api/auth/me/`)

----------------------------------------------------------------------------------------------
 Pruebas rápidas (Postman / CURL)
GET /api/auth/csrf/
POST /api/auth/login/
GET /api/auth/me/
POST /api/auth/logout/
--------------------------------------------------------------------------------------------
Estado actual
Módulo	                  Estado	                    Próximo paso
Auth (Login/Logout)	 Terminado y probado	    Ya esta Completado el font Next.js funcional

--------------------------------------------------------------------------------------------
Autor:
Jorge Luis Cardona Gregory
Backend Developer – Octubre 2025