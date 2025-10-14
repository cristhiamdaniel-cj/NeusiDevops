#  NEUSI Task Manager – API de Épicas (Backend)

**Módulo:** Gestión de Épicas  
**Framework:** Django 5.2  
**Ruta base:** `/api/backlog/epicas/`  
**Versión:** Octubre 2025  
**Desarrollado por:** Jorge Cardona

--------------------------------------------------------------------------------------

##  Descripción general
Las **épicas** son los objetivos principales del backlog.  
Cada sprint y tarea se relaciona con una épica.

--------------------------------------------------------------------------------------

##  Endpoints principales

### 1 Crear épica
**POST** `/api/backlog/epicas/`
```json
{
  "nombre": "Épica - Backlog NEUSI",
  "descripcion": "Pruebas Matriz",
  "prioridad": 2
}
--------------------------------------------------------------------------------------
2 Listar épicas
GET /api/backlog/epicas/
--------------------------------------------------------------------------------------
3 Actualizar (PATCH)
PATCH /api/backlog/epicas/{id}/


{ "nombre": "Épica - Revisión Final" }
--------------------------------------------------------------------------------------
4 Asignar responsable
PATCH /api/backlog/epicas/{id}/

{ "owner_id": 1 }
--------------------------------------------------------------------------------------
5 Reemplazar (PUT)
PUT /api/backlog/epicas/{id}/

{
  "nombre": "Épica - Revisión Final",
  "descripcion": "Edición completa desde PUT",
  "prioridad": 3,
  "activa": true,
  "owner_id": 1
}
--------------------------------------------------------------------------------------
6 Eliminar
DELETE /api/backlog/epicas/{id}/
--------------------------------------------------------------------------------------
Reglas para el Frontend
Campo clave: owner_id debe provenir de /api/backlog/integrantes/.
Puede representarse como tarjetas tipo “Epic Cards” en la UI.
Requiere cabeceras estándar de autenticación CSRF.
--------------------------------------------------------------------------------------
Estado del módulo
Funcionalidad	Estado	
Crear	       	OK Backend
Editar / PATCH	OK Backend
Asignar owner	OK Backend
Eliminar	    OK Backend
--------------------------------------------------------------------------------------
Autor: Jorge Cardona – Backend Developer
Octubre 2025


