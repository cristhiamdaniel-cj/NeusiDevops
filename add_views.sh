#!/bin/bash
# add_views.sh
# Sobrescribe backlog/views.py y backlog/urls.py

cat > backlog/views.py << 'EOF'
from django.shortcuts import render, redirect, get_object_or_404
from .models import Tarea, Integrante

def backlog_view(request):
    tareas = Tarea.objects.all().order_by('categoria')
    return render(request, "backlog/backlog.html", {"tareas": tareas})

def checklist_view(request, integrante_id):
    integrante = get_object_or_404(Integrante, id=integrante_id)
    tareas = Tarea.objects.filter(asignado_a=integrante, completada=False)
    return render(request, "backlog/checklist.html", {"integrante": integrante, "tareas": tareas})

def cerrar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    tarea.completada = True
    tarea.save()
    return redirect("backlog")
EOF

cat > backlog/urls.py << 'EOF'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.backlog_view, name='backlog'),
    path('checklist/<int:integrante_id>/', views.checklist_view, name='checklist'),
    path('cerrar/<int:tarea_id>/', views.cerrar_tarea, name='cerrar_tarea'),
]
EOF

echo "✅ Vistas y URLs creadas."

