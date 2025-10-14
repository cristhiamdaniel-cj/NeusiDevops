#  NEUSI Task Manager – Backlog API (Índice general)

**Framework:** Django 5.2  
**Versión:** Octubre 2025  
**Desarrollado por:** Jorge Cardona  

--------------------------------------------------------------------------------------

##  Estructura del Backlog
| Módulo | Archivo de documentación | Descripción |
|---------|--------------------------|--------------|
|  Autenticación | `README_AUTH_BACKEND_LOGIN.md` | Inicio, CSRF, login/logout |(esta ya esta listo)
|  Épicas | `README_BACKEND_EPICAS_API.md` | CRUD de grandes objetivos |
|  Sprints | `README_BACKEND_SPRINTS_API.md` | Ciclos de trabajo |
|  Tareas | `README_BACKEND_TAREAS_API.md` | CRUD + estado + categoría |
|  Matriz | `README_BACKEND_MATRIZ_API.md` | Visualización priorizada |

--------------------------------------------------------------------------------------

##  Base URLs
| Entorno | URL Base |
|----------|-----------|
| Local | `http://localhost:8076/api/backlog/` |
| Producción (ngrok) | `https://devops-neusi.ngrok.io/api/backlog/` |


Estructura Urls de Backend
router = DefaultRouter()
router.register(r'integrantes', IntegranteViewSet, basename='integrante')
router.register(r'epicas', EpicaViewSet, basename='epica')
router.register(r'sprints', SprintViewSet, basename='sprint')
router.register(r'tareas', TareaViewSet, basename='tarea')

urlpatterns = [
    path('', include(router.urls)),
    path('matriz/', matriz_eisenhower, name='matriz-eisenhower'),
]


--------------------------------------------------------------------------------------

## Headers comunes
```http
Content-Type: application/json
X-CSRFToken: <csrftoken cookie>
Siempre con:

fetch(url, { credentials: 'include' })
--------------------------------------------------------------------------------------
Flujo recomendado (Frontend)
1️⃣ GET /api/auth/csrf/ → obtener token.
2️⃣ POST /api/auth/login/ → autenticar usuario.
3️⃣ GET /api/backlog/epicas/ → listar épicas.
4️⃣ GET /api/backlog/sprints/ → listar sprints.
5️⃣ GET /api/backlog/matriz/ → renderizar tablero.
6️⃣ PATCH /api/backlog/tareas/{id}/categoria/ → mover tarea.
7️⃣ PATCH /api/backlog/tareas/{id}/estado/ → actualizar estado.