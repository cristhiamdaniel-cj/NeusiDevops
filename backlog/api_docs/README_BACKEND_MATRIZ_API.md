# NEUSI Task Manager – API de Matriz Eisenhower

**Módulo:** Matriz de Prioridades (UI/NUI/UNI/NUNI)  
**Framework:** Django 5.2  
**Ruta base:** `/api/backlog/matriz/`  
**Versión:** Octubre 2025  
**Desarrollado por:** Jorge Cardona

--------------------------------------------------------------------------------------
## Descripción general
La **matriz Eisenhower** clasifica las tareas según su urgencia e importancia:

| Categoría | Significado |
|------------|-------------|
| **UI** | Urgente e Importante |
| **NUI** | No urgente pero importante |
| **UNI** | Urgente pero no importante |
| **NUNI** | Ni urgente ni importante |

--------------------------------------------------------------------------------------
## Endpoint principal

### 1 Obtener matriz completa
**GET** `/api/backlog/matriz/`

**Respuesta 200:**
```json
{
  "ui": [
    { "id": 1, "titulo": "Configurar DRF", "estado": "NUEVO" }
  ],
  "nui": [
    { "id": 2, "titulo": "Doc API para Next", "estado": "COMPLETADO" }
  ],
  "uni": [
    { "id": 3, "titulo": "Ajustar estilos", "estado": "EN_PROGRESO" }
  ],
  "nuni": [
    { "id": 4, "titulo": "Iconos definitivos", "estado": "NUEVO" }
  ]
}
--------------------------------------------------------------------------------------
Reglas para el Frontend
Cada grupo (ui, nui, uni, nuni) corresponde a una columna o cuadrante visual.
Puede usarse para construir drag & drop o dashboard de tareas.
Si una tarea cambia de cuadrante, usar:
PATCH /api/backlog/tareas/{id}/categoria/
--------------------------------------------------------------------------------------
Estado del módulo
Funcionalidad		Observaciones
Generación de matriz		OK
Integración con tareas		OK
--------------------------------------------------------------------------------------
Autor: Jorge Cardona – Backend Developer
Octubre 2025