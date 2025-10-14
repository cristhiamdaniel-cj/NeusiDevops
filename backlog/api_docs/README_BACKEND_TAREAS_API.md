#  NEUSI Task Manager – API de Tareas (Backend)

**Módulo:** Gestión de Tareas  
**Framework:** Django 5.2  
**Ruta base:** `/api/backlog/tareas/`  
**Versión:** Octubre 2025  
**Desarrollado por:** Jorge Cardona
--------------------------------------------------------------------------------------

##  Descripción general
Las **tareas** son los elementos base del backlog.  
Cada tarea pertenece a una **épica**, un **sprint** y puede cambiar de estado o categoría según avance el proyecto.

--------------------------------------------------------------------------------------

##  Endpoints principales

### 1 Crear tarea
**POST** `/api/backlog/tareas/`
```json
{
  "titulo": "Configurar DRF",
  "descripcion": "Serializers y ViewSets",
  "categoria": "UI",
  "estado": "NUEVO",
  "asignado_a_id": 1,
  "sprint_id": 1,
  "epica_id": 1
}
Respuesta (201):

{
  "id": 1,
  "titulo": "Configurar DRF",
  "estado": "NUEVO",
  "categoria": "UI",
  "sprint": { "id": 1, "nombre": "Sprint 1" },
  "epica": { "id": 1, "nombre": "Épica - Backlog NEUSI" }
}
--------------------------------------------------------------------------------------
2 Listar tareas
GET /api/backlog/tareas/

Respuesta:


[
  {
    "id": 1,
    "titulo": "Configurar DRF",
    "categoria": "NUI",
    "estado": "NUEVO"
  }
]
--------------------------------------------------------------------------------------

3 Filtrar tareas
Por sprint:
GET /api/backlog/tareas/?sprint=1

Por estado:
GET /api/backlog/tareas/?estado=EN_PROGRESO
--------------------------------------------------------------------------------------

4 Cambiar categoría (mover en matriz)
PATCH /api/backlog/tareas/{id}/categoria/
{ "categoria": "NUI" }
Respuesta (200):


{ "ok": true, "categoria": "NUI" }
--------------------------------------------------------------------------------------

5 Cambiar estado (kanban)
PATCH /api/backlog/tareas/{id}/estado/


{ "estado": "COMPLETADO" }
Respuesta (200):


{ "ok": true, "estado": "COMPLETADO" }
--------------------------------------------------------------------------------------
6 Eliminar tarea
DELETE /api/backlog/tareas/{id}/

Respuesta:
204 No Content
--------------------------------------------------------------------------------------

Reglas para el Frontend
Campos clave: titulo, descripcion, categoria, estado.
Las tareas se agrupan por categoría en la matriz y por estado en el tablero kanban.
Usar credentials: 'include' y X-CSRFToken en todos los métodos que modifiquen datos.

--------------------------------------------------------------------------------------

Estado del módulo
Funcionalidad	Estado	
Crear	        	OK
Listar		        OK
Cambiar categoría	OK
Cambiar estado		OK
Eliminar		    OK

--------------------------------------------------------------------------------------

Autor: Jorge Cardona – Backend Developer
Octubre 2025