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
    path("tarea/<int:tarea_id>/eliminar/", views.eliminar_tarea, name="eliminar_tarea"),  # Eliminar
    path("tarea/<int:tarea_id>/cambiar-categoria/", views.cambiar_categoria_tarea, name="cambiar_categoria_tarea"),

    # 🧱 Bloques y Subtareas
    path("bloque/<int:bloque_id>/editar/", views.bloque_edit, name="bloque_edit"),
    path("bloque/<int:bloque_id>/subtareas/nueva/", views.subtarea_create, name="subtarea_create"),
    path("subtareas/<int:subtarea_id>/editar/", views.subtarea_edit, name="subtarea_edit"),
    path("subtareas/<int:subtarea_id>/eliminar/", views.subtarea_delete, name="subtarea_delete"),

    # ⚙️ Estado de Subtarea (nuevo)
    path(
        "subtareas/<int:subtarea_id>/estado/",
        views.subtarea_cambiar_estado,
        name="subtarea_cambiar_estado",
    ),

    # 📎 Evidencias de Tarea
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

    # 📎 Evidencias por Subtarea (nuevo)
    path(
        "subtareas/<int:subtarea_id>/evidencias/nueva/",
        views.agregar_evidencia_subtarea,
        name="agregar_evidencia_subtarea",
    ),
    path(
        "subtareas/<int:subtarea_id>/evidencias/<int:evid_id>/editar/",
        views.editar_evidencia_subtarea,
        name="editar_evidencia_subtarea",
    ),
    path(
        "subtareas/<int:subtarea_id>/evidencias/<int:evid_id>/eliminar/",
        views.eliminar_evidencia_subtarea,
        name="eliminar_evidencia_subtarea",
    ),

    # 📌 Checklist (por integrante)
    path("checklist/<int:integrante_id>/", views.checklist_view, name="checklist"),

    # 📅 Daily
    path("daily/", views.daily_personal, name="daily_personal"),  # Acceso directo al daily personal
    path("daily/<int:integrante_id>/", views.daily_view, name="daily_view"),  # Daily de un integrante
    path("daily/resumen/", views.daily_resumen, name="daily_resumen"),  # Resumen de dailies
    path("daily/eliminar/<int:daily_id>/", views.eliminar_daily, name="eliminar_daily"),  # Eliminar daily (solo admin)
    path("daily/nuevo/", views.daily_create_admin, name="daily_create_admin"),

    # 📅 Sprints
    path("sprints/", views.sprint_list, name="sprint_list"),
    path("sprints/nuevo/", views.sprint_create, name="sprint_create"),
    path("sprints/<int:sprint_id>/editar/", views.sprint_edit, name="sprint_edit"),
    path("sprints/<int:sprint_id>/eliminar/", views.sprint_delete, name="sprint_delete"),

    # 📊 Kanban Board
    path("kanban/", views.kanban_board, name="kanban_board"),
    path("tarea/<int:tarea_id>/cambiar-estado/", views.cambiar_estado_tarea, name="cambiar_estado_tarea"),

    # 🧱 Épicas
    path("epicas/", views.epica_list, name="epica_list"),
    path("epicas/nueva/", views.epica_create, name="epica_create"),
    path("epicas/<int:epica_id>/", views.epica_detail, name="epica_detail"),
    path("epicas/<int:epica_id>/editar/", views.epica_edit, name="epica_edit"),
    path("epicas/<int:epica_id>/eliminar/", views.epica_delete, name="epica_delete"),
    path("proyectos/nuevo/", views.proyecto_create, name="proyecto_create"),
]
