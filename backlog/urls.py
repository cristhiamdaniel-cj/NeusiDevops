# backlog/urls.py - Rutas del módulo backlog (NEUSI Task Manager)
from django.urls import path
from . import views

urlpatterns = [
    # 🔑 Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("change-password/", views.change_password, name="change_password"),

    # 🏠 Página principal
    path("", views.home, name="home"),

    # 📋 Backlog (lista y matriz)
    path("lista/", views.backlog_lista, name="backlog_lista"),
    path("matriz/", views.backlog_matriz, name="backlog_matriz"),

    # ✅ Tareas
    path("nueva/", views.nueva_tarea, name="nueva_tarea"),  # Crear tarea
    path("tarea/<int:tarea_id>/", views.detalle_tarea, name="detalle_tarea"),  # Detalle
    path("tarea/<int:tarea_id>/editar/", views.editar_tarea, name="editar_tarea"),  # Editar
    path("tarea/<int:tarea_id>/cerrar/", views.cerrar_tarea, name="cerrar_tarea"),  # Cerrar

    # 📎 Evidencias
    path("tarea/<int:tarea_id>/evidencia/", views.agregar_evidencia, name="agregar_evidencia"),  # Agregar
    path(
        "tarea/<int:tarea_id>/evidencia/<int:evidencia_id>/editar/",
        views.editar_evidencia,
        name="editar_evidencia"
    ),  # Editar
    path(
        "tarea/<int:tarea_id>/evidencia/<int:evidencia_id>/eliminar/",
        views.eliminar_evidencia,
        name="eliminar_evidencia"
    ),  # Eliminar

    # 📌 Checklist (por integrante)
    path("checklist/<int:integrante_id>/", views.checklist_view, name="checklist"),

    # 📅 Daily
    path("daily/", views.daily_personal, name="daily_personal"),  # Acceso directo al daily personal
    path("daily/<int:integrante_id>/", views.daily_view, name="daily_view"),  # Daily de un integrante
    path("daily/resumen/", views.daily_resumen, name="daily_resumen"),  # Resumen de dailies
    path("daily/eliminar/<int:daily_id>/", views.eliminar_daily, name="eliminar_daily"),  # Eliminar daily (solo admin)

    # 📅 Sprints
    path("sprints/", views.sprint_list, name="sprint_list"),
    path("sprints/nuevo/", views.sprint_create, name="sprint_create"),
    path("sprints/<int:sprint_id>/editar/", views.sprint_edit, name="sprint_edit"),
    path("sprints/<int:sprint_id>/eliminar/", views.sprint_delete, name="sprint_delete"),

    path("daily/nuevo/", views.daily_create_admin, name="daily_create_admin"),

    path("tarea/<int:tarea_id>/cerrar/", views.cerrar_tarea, name="cerrar_tarea"),  # Cerrar
    path("tarea/<int:tarea_id>/eliminar/", views.eliminar_tarea, name="eliminar_tarea"),  # Eliminar

    # 📊 Kanban Board
    path("kanban/", views.kanban_board, name="kanban_board"),
    path("tarea/<int:tarea_id>/cambiar-estado/", views.cambiar_estado_tarea, name="cambiar_estado_tarea"),
]
