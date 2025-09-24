#!/bin/bash
# Script para limpiar duplicados y configurar home como página inicial

set -e

echo "🔧 Ajustando backlog/urls.py..."
cat > backlog/urls.py << 'EOF'
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # 👈 raíz apunta al home
    path('checklist/<int:integrante_id>/', views.checklist_view, name='checklist'),
    path('cerrar/<int:tarea_id>/', views.cerrar_tarea, name='cerrar_tarea'),
    path('lista/', views.backlog_lista, name='backlog_lista'),
    path('matriz/', views.backlog_matriz, name='backlog_matriz'),
    path('nueva/', views.nueva_tarea, name='nueva_tarea'),
    path('daily/<int:integrante_id>/', views.daily_view, name='daily_view'),
    path('daily/resumen/', views.daily_resumen, name='daily_resumen'),
]
EOF
echo "✅ urls.py actualizado (raíz apunta a home)."

echo "🔧 Ajustando backlog/views.py..."
cat > backlog/views.py << 'EOF'
from django.shortcuts import render, redirect, get_object_or_404
from .models import Tarea, Sprint, Integrante, Daily
from .forms import TareaForm, DailyForm
from datetime import date

# 🏠 Home
def home(request):
    return render(request, "backlog/home.html")

# ✅ Daily
def daily_view(request, integrante_id):
    integrante = get_object_or_404(Integrante, id=integrante_id)

    if request.method == "POST":
        form = DailyForm(request.POST)
        if form.is_valid():
            daily, created = Daily.objects.get_or_create(
                integrante=integrante, fecha=date.today(),
                defaults=form.cleaned_data
            )
            if not created:
                daily.que_hizo_ayer = form.cleaned_data["que_hizo_ayer"]
                daily.que_hara_hoy = form.cleaned_data["que_hara_hoy"]
                daily.impedimentos = form.cleaned_data["impedimentos"]
                daily.save()
            return redirect("daily_resumen")
    else:
        form = DailyForm()

    return render(request, "backlog/daily_form.html", {
        "form": form,
        "integrante": integrante,
    })

def daily_resumen(request):
    integrantes = Integrante.objects.all()
    registros = Daily.objects.order_by("-fecha")
    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
    })

# 📋 Backlog lista y matriz
def backlog_lista(request):
    persona_id = request.GET.get("persona")
    sprint_id = request.GET.get("sprint")
    estado = request.GET.get("estado")

    tareas = Tarea.objects.all().order_by("sprint__inicio", "categoria")
    integrantes = Integrante.objects.all()
    sprints = Sprint.objects.all()

    if persona_id and persona_id.isdigit():
        tareas = tareas.filter(asignado_a_id=int(persona_id))
    if sprint_id and sprint_id.isdigit():
        tareas = tareas.filter(sprint_id=int(sprint_id))
    if estado == "abiertas":
        tareas = tareas.filter(completada=False)
    elif estado == "cerradas":
        tareas = tareas.filter(completada=True)

    return render(request, "backlog/backlog_lista.html", {
        "tareas": tareas,
        "integrantes": integrantes,
        "sprints": sprints,
        "persona_id": persona_id,
        "sprint_id": sprint_id,
        "estado": estado,
    })

def backlog_matriz(request):
    persona_id = request.GET.get("persona")
    sprint_id = request.GET.get("sprint")
    estado = request.GET.get("estado")

    tareas = Tarea.objects.all().order_by("categoria")
    integrantes = Integrante.objects.all()
    sprints = Sprint.objects.all()

    if persona_id and persona_id.isdigit():
        tareas = tareas.filter(asignado_a_id=int(persona_id))
    if sprint_id and sprint_id.isdigit():
        tareas = tareas.filter(sprint_id=int(sprint_id))
    if estado == "abiertas":
        tareas = tareas.filter(completada=False)
    elif estado == "cerradas":
        tareas = tareas.filter(completada=True)

    return render(request, "backlog/backlog_matriz.html", {
        "tareas": tareas,
        "integrantes": integrantes,
        "sprints": sprints,
        "persona_id": persona_id,
        "sprint_id": sprint_id,
        "estado": estado,
    })

# ➕ Nueva tarea
def nueva_tarea(request):
    if request.method == "POST":
        form = TareaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("backlog_lista")
    else:
        form = TareaForm()
    return render(request, "backlog/nueva_tarea.html", {"form": form})

# ✅ Checklist
def checklist_view(request, integrante_id):
    integrante = get_object_or_404(Integrante, id=integrante_id)
    tareas = Tarea.objects.filter(asignado_a=integrante, completada=False)
    return render(request, "backlog/checklist.html", {"integrante": integrante, "tareas": tareas})

def cerrar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    tarea.completada = True
    tarea.save()
    return redirect("backlog_lista")
EOF
echo "✅ views.py limpiado y optimizado."

# Eliminar backlog.html si existe
if [ -f "backlog/templates/backlog/backlog.html" ]; then
    rm backlog/templates/backlog/backlog.html
    echo "🗑️ backlog.html eliminado (duplicado innecesario)."
fi

echo "🎉 Limpieza completada. Ahora la raíz muestra home.html"

