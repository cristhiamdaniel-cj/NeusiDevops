from django.urls import path
from . import views

app_name = 'disponibilidad'

urlpatterns = [
    path('', views.mi_disponibilidad, name='mi_disponibilidad'),
    path('equipo/', views.ver_disponibilidad_equipo, name='equipo_disponibilidad'),
    path('actualizar-horario/', views.actualizar_horario, name='actualizar_horario'),
]
