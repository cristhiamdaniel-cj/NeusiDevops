# backlog/urls.py - Actualizado con daily personal
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('', views.home, name='home'),
    path('checklist/<int:integrante_id>/', views.checklist_view, name='checklist'),
    path('tarea/<int:tarea_id>/', views.detalle_tarea, name='detalle_tarea'),
    path('tarea/<int:tarea_id>/cerrar/', views.cerrar_tarea, name='cerrar_tarea'),
    path('tarea/<int:tarea_id>/evidencia/', views.agregar_evidencia, name='agregar_evidencia'),
    path('lista/', views.backlog_lista, name='backlog_lista'),
    path('matriz/', views.backlog_matriz, name='backlog_matriz'),
    path('nueva/', views.nueva_tarea, name='nueva_tarea'),
    path('daily/', views.daily_personal, name='daily_personal'),  # Nueva ruta personal
    path('daily/<int:integrante_id>/', views.daily_view, name='daily_view'),  # Solo para admin
    path('daily/resumen/', views.daily_resumen, name='daily_resumen'),
    path("change-password/", views.change_password, name="change_password"),
]