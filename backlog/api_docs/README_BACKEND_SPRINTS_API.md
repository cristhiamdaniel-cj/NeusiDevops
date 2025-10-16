#  NEUSI Task Manager – API de Sprints (Backend)

**Módulo:** Gestión de Sprints  
**Framework:** Django 5.2  
**Ruta base:** `/api/backlog/sprints/`  
**Versión:** Octubre 2025  
**Desarrollado por:** Jorge Cardona


--------------------------------------------------------------------------------------

##  Descripción general
Los **sprints** definen los ciclos de trabajo del backlog.  
Cada tarea (`/tareas/`) debe pertenecer a un sprint activo.

--------------------------------------------------------------------------------------

Endpoints principales

1 Crear sprint
**POST** `/api/backlog/sprints/`
```json
{
  "nombre": "Sprint 1",
  "inicio": "2025-10-10",
  "fin": "2025-10-24"
}

Respuesta (201):
{ "id": 1, "nombre": "Sprint 1", "inicio": "2025-10-10", "fin": "2025-10-24" }
--------------------------------------------------------------------------------------
2 Listar sprints

GET /api/backlog/sprints/

Respuesta:

[
  { "id": 1, "nombre": "Sprint 1", "inicio": "2025-10-10", "fin": "2025-10-24" }
]

--------------------------------------------------------------------------------------

3 Consultar sprint por ID

GET /api/backlog/sprints/{id}/

Respuesta:

{
  "id": 1,
  "nombre": "Sprint 1",
  "inicio": "2025-10-10",
  "fin": "2025-10-24"
}

--------------------------------------------------------------------------------------

4 Actualizar sprint

PATCH o PUT /api/backlog/sprints/{id}/

{
  "nombre": "Sprint 1 – Actualizado",
  "inicio": "2025-10-11",
  "fin": "2025-10-25"
}

--------------------------------------------------------------------------------------

5 Eliminar sprint

DELETE /api/backlog/sprints/{id}/

Respuesta:
204 No Content

--------------------------------------------------------------------------------------

Reglas para el Frontend (Next.js)

Cada tarea debe asociarse a un sprint existente (sprint_id).
Los sprints se listan para dropdowns o select de planificación.

--------------------------------------------------------------------------------------

Headers estándar:
Content-Type: application/json
X-CSRFToken: <valor cookie csrftoken>

--------------------------------------------------------------------------------------

Estado del módulo
Funcionalidad              	Estado	Observaciones
Crear Sprint	               ✅	Probado curl
Listar Sprints                 ✅	Probado curl
Editar Sprint	               ✅	Probado curl
Eliminar Sprint	               ✅	Probado curl
Relación con Tareas	           ✅	Integrada

--------------------------------------------------------------------------------------

Autor: Jorge Cardona – Backend Developer
Octubre 2025