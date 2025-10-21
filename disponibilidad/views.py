from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.shortcuts import render, redirect
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from .models import DisponibilidadSemanal, DisponibilidadDia

# ⬅️ AJUSTA este import a dónde tengas Integrante
from backlog.models import Integrante  # cambia la ruta si tu modelo está en otro app

# ===== Helpers de permisos basados en tu modelo Integrante =====
def _get_integrante(user):
    return getattr(user, "integrante", None)

def _es_admin(user):
    integ = _get_integrante(user)
    return bool((integ and integ.es_admin()) or getattr(user, "is_superuser", False))

def _es_visualizador(user):
    integ = _get_integrante(user)
    return bool(integ and integ.es_visualizador())

# ===== Navegación de semanas =====
def _get_semana_inicio(request):
    param = request.GET.get("semana")
    if param:
        try:
            fecha = datetime.strptime(param, "%Y-%m-%d").date()
            return fecha - timedelta(days=fecha.weekday())
        except ValueError:
            pass
    return DisponibilidadSemanal.actual_lunes()

def _prev_next(semana_inicio):
    return semana_inicio - timedelta(days=7), semana_inicio + timedelta(days=7)

# ===== Mi disponibilidad (usuario) =====
@login_required
def mi_disponibilidad(request):
    semana_inicio = _get_semana_inicio(request)
    semana, _ = DisponibilidadSemanal.objects.get_or_create(
        usuario=request.user,
        semana_inicio=semana_inicio
    )
    semana.ensure_dias()

    if request.method == "POST":
        cambios = 0
        for i in range(7):
            estado = request.POST.get(f"estado_{i}")
            if estado not in ("D", "N", "R"):
                continue
            dia = semana.dias.get(dia_semana=i)
            dia.tipo = estado
            if estado == "R":
                ini = request.POST.get(f"ini_{i}")
                fin = request.POST.get(f"fin_{i}")
                if not ini or not fin:
                    messages.error(request, f"Debes poner horas para {dia.get_dia_semana_display()} (rango).")
                    continue
                try:
                    h_ini = datetime.strptime(ini, "%H:%M").time()
                    h_fin = datetime.strptime(fin, "%H:%M").time()
                except ValueError:
                    messages.error(request, f"Horas inválidas en {dia.get_dia_semana_display()}.")
                    continue
                if h_ini >= h_fin:
                    messages.error(request, f"Hora inicio ≥ fin en {dia.get_dia_semana_display()}.")
                    continue
                dia.hora_inicio = h_ini
                dia.hora_fin = h_fin
            else:
                dia.hora_inicio = None
                dia.hora_fin = None
            dia.save()
            cambios += 1

        if cambios:
            messages.success(request, "✅ Disponibilidad semanal actualizada.")
        return redirect(f"{request.path}?semana={semana_inicio.isoformat()}")

    prev_w, next_w = _prev_next(semana_inicio)

    context = {
        "semana": semana,
        "prev_w": prev_w,
        "next_w": next_w,
        "hoy": timezone.localdate(),
        # botones superiores
        "home_url": "/",
        "equipo_url": reverse("disponibilidad:equipo_disponibilidad") + f"?semana={semana_inicio.isoformat()}",
        "puede_ver_equipo": _es_admin(request.user) or _es_visualizador(request.user),
    }
    return render(request, "disponibilidad/mi_disponibilidad.html", context)

# ===== Equipo (admin/visualizador) =====
@login_required
def ver_disponibilidad_equipo(request):
    if not (_es_admin(request.user) or _es_visualizador(request.user)):
        return HttpResponseForbidden("Solo administradores/visualizadores.")

    semana_inicio = _get_semana_inicio(request)
    grupo_id = request.GET.get("grupo")

    usuarios = User.objects.all().order_by("first_name", "last_name")
    if grupo_id:
        try:
            g = Group.objects.get(pk=int(grupo_id))
            usuarios = usuarios.filter(groups=g)
        except (ValueError, Group.DoesNotExist):
            messages.error(request, "Grupo inválido.")

    # En lugar de pasar un dict y usar get_item, preparamos filas {user, sem}
    rows = []
    for u in usuarios:
        sem, _ = DisponibilidadSemanal.objects.get_or_create(usuario=u, semana_inicio=semana_inicio)
        sem.ensure_dias()
        rows.append({"user": u, "sem": sem})

    prev_w, next_w = _prev_next(semana_inicio)

    context = {
        "rows": rows,                              # 👈 ahora el template recorre rows
        "semana_inicio": semana_inicio,
        "prev_w": prev_w, "next_w": next_w,
        "grupos": Group.objects.all().order_by("name"),
        "grupo_sel": grupo_id,
        "home_url": "/",
        "mi_url": reverse("disponibilidad:mi_disponibilidad") + f"?semana={semana_inicio.isoformat()}",
    }
    return render(request, "disponibilidad/equipo_disponibilidad.html", context)
