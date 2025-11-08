# -*- coding: utf-8 -*-
from functools import wraps
from datetime import time, datetime, timedelta
import json
from django.views.decorators.cache import cache_page
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import localtime, now
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.db import transaction
from django.views.decorators.http import require_http_methods, require_POST
from django.forms.models import model_to_dict
from django.utils.timezone import localtime
from django.db import transaction
from .models import (
    Tarea, Sprint, Integrante, Daily, Evidencia, Epica, Proyecto,
    BloqueTarea, Subtarea,EvidenciaSubtarea
)
from .forms import (
    TareaForm, DailyForm, EvidenciaForm, SprintForm, EpicaForm, ProyectoForm,
    BloqueFormSet, TareaEstadoForm, SubtareaForm, BloqueTareaForm,
)

# ==============================
# Helpers de permisos / Daily window
# ==============================

DAILY_INICIO = time(5, 0)   # 5:00 AM
DAILY_FIN    = time(9, 0)   # 9:00 AM

def en_ventana_daily(hora):
    """True si la hora local está entre 5:00 y 9:00 AM (inclusive)."""
    return DAILY_INICIO <= hora <= DAILY_FIN

def _flags_usuario(request):
    """
    Devuelve:
      - integrante: Integrante|None (auto-creado si falta)
      - puede_admin: bool (roles admin)
      - es_visualizador: bool (roles visualización global por proyecto)
      - puede_ver_todo: bool (admin o visualizador)
    """
    integrante = getattr(request.user, "integrante", None)
    if request.user.is_authenticated and integrante is None:
        integrante, _ = Integrante.objects.get_or_create(
            user=request.user,
            defaults={'rol': Integrante.ROL_MIEMBRO}
        )

    puede_admin = bool(integrante and integrante.es_admin())
    es_visualizador = bool(integrante and integrante.es_visualizador())
    puede_ver_todo = bool(puede_admin or es_visualizador)
    return integrante, puede_admin, es_visualizador, puede_ver_todo


def _sync_subtareas_fechas(bloque: BloqueTarea):
    """
    Alinea todas las subtareas del bloque con las fechas del bloque.
    """
    if not bloque:
        return
    Subtarea.objects.filter(bloque=bloque).update(
        fecha_inicio=bloque.fecha_inicio,
        fecha_fin=bloque.fecha_fin
    )

# ==============================
# Scope por proyectos (Visualizador / Product Owner)
# ==============================

def _proyectos_autorizados_qs(integrante: Integrante):
    if not integrante:
        return Proyecto.objects.none()
    if integrante.es_admin():
        return Proyecto.objects.all()
    if integrante.es_visualizador():
        return Proyecto.objects.filter(
            permisos_integrantes__integrante=integrante,
            permisos_integrantes__activo=True,
            activo=True
        ).distinct()
    return Proyecto.objects.none()

def _filtrar_por_proyectos_autorizados_tareas(qs, integrante: Integrante):
    if not integrante or not integrante.es_visualizador():
        return qs
    proys = _proyectos_autorizados_qs(integrante)
    if not proys.exists():
        return qs.none()
    return qs.filter(epica__proyecto__in=proys).distinct()

def _filtrar_por_proyectos_autorizados_epicas(qs, integrante: Integrante):
    if not integrante or not integrante.es_visualizador():
        return qs
    proys = _proyectos_autorizados_qs(integrante)
    if not proys.exists():
        return qs.none()
    return qs.filter(proyecto__in=proys).distinct()

def _es_admin(request):
    integrante = getattr(request.user, "integrante", None)
    return bool(integrante and integrante.es_admin())

def _es_responsable(tarea: Tarea, integrante: Integrante) -> bool:
    if not integrante:
        return False
    if tarea.asignado_a_id == getattr(integrante, "id", None):
        return True
    return tarea.asignados.filter(id=integrante.id).exists()

# === Conjunto de roles "administrativos" ===
ADMIN_ROLES = {
    "Scrum Master / PO",
    "Arquitecto de Software y Director General",
    "Coordinadora de Gestión Humana y Administrativa",
}

def _es_admin_neusi(integrante: Integrante | None) -> bool:
    try:
        nombre_rol = getattr(getattr(integrante, "rol", None), "nombre", None)
        if nombre_rol in ADMIN_ROLES:
            return True
    except Exception:
        pass
    try:
        return bool(integrante and integrante.es_admin())
    except Exception:
        return False

def _puede_crud_subtareas(tarea: Tarea, integrante: Integrante | None) -> bool:
    return bool(_es_admin_neusi(integrante) or _es_responsable(tarea, integrante))

def _queryset_visible_tareas(integrante: Integrante, puede_ver_todo: bool):
    base = (
        Tarea.objects
        .select_related("asignado_a__user", "sprint", "epica", "epica__proyecto")
        .prefetch_related("asignados__user")
    )

    if not integrante:
        return Tarea.objects.none()

    if integrante.es_admin():
        return base

    if integrante.es_visualizador():
        return _filtrar_por_proyectos_autorizados_tareas(base, integrante)

    return base.filter(Q(asignados=integrante) | Q(asignado_a=integrante)).distinct()

# ==============================
# Decoradores de permisos
# ==============================

def requiere_permiso_crear_tareas(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            integrante = request.user.integrante
            if not integrante.puede_crear_tareas():
                messages.error(request, "❌ No tienes permisos para crear/administrar.")
                return redirect("backlog_lista")
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def requiere_permiso_evidencias(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            integrante = request.user.integrante
            if not integrante.puede_agregar_evidencias():
                messages.error(request, "❌ No tienes permisos para agregar evidencias.")
                return redirect("backlog_lista")
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ==============================
# Vistas de Tareas (Tarea = Macro)
# ==============================

@login_required
def editar_tarea(request, tarea_id):
    """
    Editar Tarea Macro:
    - Admin NEUSI: pueden editar todo y los BLOQUES.
    - Responsable (asignado): SOLO puede cambiar el 'estado'.
    """
    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, _, _, _ = _flags_usuario(request)

    es_admin = _es_admin_neusi(integrante)
    es_resp  = _es_responsable(tarea, integrante)

    if not (es_admin or es_resp):
        messages.error(request, "❌ No tienes permisos para editar esta tarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    FormClass = TareaForm if es_admin else TareaEstadoForm

    if request.method == "POST":
        form = FormClass(request.POST, request.FILES, instance=tarea)
        formset = None
        if es_admin:
            formset = BloqueFormSet(
                request.POST, request.FILES, instance=tarea, prefix="bloques"
            )

        ok_form = form.is_valid()
        ok_set  = True if formset is None else formset.is_valid()

        if ok_form and ok_set:
            form.save()
            if formset:
                formset.save()
                # sincronizar fechas de subtareas con cada bloque actualizado
                for b in tarea.bloques.all():
                    _sync_subtareas_fechas(b)
            messages.success(request, "✅ Cambios guardados correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        else:
            if not ok_form:
                messages.error(request, "⚠️ Revisa el formulario de la tarea.")
            if formset and not ok_set:
                messages.error(request, "⚠️ Revisa los bloques: hay errores.")
    else:
        form = FormClass(instance=tarea)
        formset = BloqueFormSet(instance=tarea, prefix="bloques") if es_admin else None

    return render(
        request,
        "backlog/editar_tarea.html",
        {
            "tarea": tarea,
            "form": form,
            "formset": formset,
            "puede_editar_bloques": es_admin,
            "solo_estado": (not es_admin),
        },
    )

@login_required
@requiere_permiso_crear_tareas
def nueva_tarea(request):
    """
    ÚNICA forma de crear tareas (macro) con bloques opcionales.
    """
    if request.method == "POST":
        form = TareaForm(request.POST, request.FILES)
        formset = BloqueFormSet(request.POST, prefix="bloques")  # bound

        if not form.is_valid():
            messages.error(request, "⚠️ Corrige los errores del formulario de la tarea.")
            return render(request, "backlog/nueva_tarea.html", {"form": form, "formset": formset})

        tarea = form.save(commit=False)
        if hasattr(tarea, "es_macro"):
            tarea.es_macro = True
        if hasattr(tarea, "creada_por") and hasattr(request.user, "integrante"):
            tarea.creada_por = request.user.integrante
        tarea.save()
        form.save_m2m()

        formset = BloqueFormSet(request.POST, prefix="bloques", instance=tarea)
        all_empty = all(f.empty_permitted and not f.has_changed() for f in formset.forms)

        if formset.is_valid():
            if not all_empty:
                formset.save()
            messages.success(request, "✅ Tarea creada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)

        tarea.delete()
        messages.error(request, "⚠️ Corrige los errores en los bloques.")
        return render(request, "backlog/nueva_tarea.html", {"form": form, "formset": formset})

    form = TareaForm()
    formset = BloqueFormSet(prefix="bloques")
    return render(request, "backlog/nueva_tarea.html", {"form": form, "formset": formset})

@login_required
def detalle_tarea(request, tarea_id):
    tarea = get_object_or_404(
        Tarea.objects.select_related("sprint", "epica").prefetch_related("asignados__user"),
        id=tarea_id
    )

    evidencias = tarea.evidencias.all().order_by("-creado_en")
    form = EvidenciaForm()

    integrante, _, _, _ = _flags_usuario(request)
    es_admin = _es_admin_neusi(integrante)
    es_responsable = _es_responsable(tarea, integrante)

    puede_editar = bool(es_admin or es_responsable or (integrante and integrante.puede_editar_tareas()))
    puede_cerrar = bool(es_admin or es_responsable)

    return render(request, "backlog/detalle_tarea.html", {
        "tarea": tarea,
        "evidencias": evidencias,
        "form": form,
        "tiene_permisos_admin": es_admin,
        "es_admin": es_admin,                 # <-- para templates que usen esta clave
        "puede_editar": puede_editar,
        "puede_cerrar": puede_cerrar,
        "es_responsable": es_responsable,
    })

# -------- Evidencias --------

@login_required
def agregar_evidencia(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not (es_admin or _es_responsable(tarea, integrante) or (integrante and integrante.puede_agregar_evidencias())):
        messages.error(request, "❌ No tienes permisos para agregar evidencias a esta tarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        form = EvidenciaForm(request.POST, request.FILES)
        if form.is_valid():
            evidencia = form.save(commit=False)
            evidencia.tarea = tarea
            evidencia.creado_por = request.user
            evidencia.save()
            messages.success(request, "✅ Evidencia agregada correctamente.")
        else:
            messages.error(request, "❌ Error al agregar la evidencia. Revisa el formulario.")
    return redirect("detalle_tarea", tarea_id=tarea.id)

@login_required
def editar_evidencia(request, tarea_id, evidencia_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencia = get_object_or_404(Evidencia, id=evidencia_id, tarea=tarea)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not (es_admin or _es_responsable(tarea, integrante) or (integrante and integrante.puede_agregar_evidencias())):
        messages.error(request, "❌ No tienes permisos para editar esta evidencia.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        form = EvidenciaForm(request.POST, request.FILES, instance=evidencia)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Evidencia editada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        messages.error(request, "⚠️ Revisa los campos del formulario.")

    return render(request, "backlog/editar_evidencia.html", {
        "form": EvidenciaForm(instance=evidencia),
        "evidencia": evidencia,
        "tarea": tarea,
    })

@login_required
def eliminar_evidencia(request, tarea_id, evidencia_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencia = get_object_or_404(Evidencia, id=evidencia_id, tarea=tarea)
    integrante, es_admin, _, _ = _flags_usuario(request)

    puede = (
        es_admin
        or (evidencia.creado_por_id == request.user.id)
        or _es_responsable(tarea, integrante)
        or (integrante and integrante.puede_agregar_evidencias())
    )
    if not puede:
        messages.error(request, "❌ No tienes permisos para eliminar esta evidencia.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        evidencia.delete()
        messages.success(request, "🗑️ Evidencia eliminada correctamente.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    return render(request, "backlog/confirmar_eliminar_evidencia.html", {
        "tarea": tarea,
        "evidencia": evidencia,
    })

@login_required
def cerrar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not es_admin and not _es_responsable(tarea, integrante):
        messages.error(request, "❌ Solo responsables o administradores pueden cerrar la tarea.")
        return redirect("backlog_lista")

    if tarea.completada:
        messages.warning(request, "⚠️ Esta tarea ya está cerrada.")
        return redirect("backlog_lista")

    if request.method == "POST":
        informe = request.FILES.get("informe_cierre")
        confirmacion = request.POST.get("confirmacion")
        if not informe:
            messages.error(request, "❌ Debes adjuntar un informe para cerrar la tarea.")
        elif confirmacion != "confirmo":
            messages.error(request, "❌ Debes confirmar el cierre de la tarea.")
        else:
            tarea.completada = True
            tarea.fecha_cierre = now()
            tarea.informe_cierre = informe
            tarea.save()
            messages.success(request, f"✅ La tarea '{tarea.titulo}' fue cerrada.")
            return redirect("backlog_lista")

    return render(request, "backlog/cerrar_tarea.html", {"tarea": tarea})

# ==============================
# Autenticación
# ==============================

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.check_password("neusi123"):
                messages.warning(request, "⚠️ Debes cambiar tu contraseña.")
                return redirect("change_password")
            return redirect("backlog_lista")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    return render(request, "auth/login.html")

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Contraseña cambiada correctamente.")
            return redirect("backlog_lista")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "auth/change_password.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required
def home(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)
    return render(request, "backlog/home.html", {
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
        "es_visualizador": es_visualizador,
    })

# ==============================
# Daily
# ==============================
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localtime
from django.views.decorators.http import require_http_methods, require_POST

# Modelos usados en este bloque
from .models import Daily, DailyItem, Integrante, Tarea
# Nota: este bloque usa helpers definidos en tu archivo:
#   - en_ventana_daily(hora)
#   - _flags_usuario(request)
#   - _proyectos_autorizados_qs(integrante)


# === Helper: obtener o crear el Daily del día actual ===
def _get_or_create_today_daily(integrante):
    """Devuelve el Daily de hoy (creándolo si no existe) respetando la unicidad."""
    f_hoy = localtime().date()
    daily, _ = Daily.objects.get_or_create(
        integrante=integrante,
        fecha=f_hoy,
        defaults={}
    )
    return daily


@login_required
def daily_view(request, integrante_id=None):
    _, es_admin, es_visualizador, _ = _flags_usuario(request)
    if es_visualizador:
        messages.warning(request, "El rol Visualizador no puede registrar dailies.")
        return redirect("daily_resumen")

    # integrante actual
    if integrante_id is None:
        try:
            integrante = request.user.integrante
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
    else:
        integrante = get_object_or_404(Integrante, id=integrante_id)
        if integrante.user != request.user and not es_admin:
            messages.error(request, "❌ Solo puedes registrar tu propio daily.")
            return redirect("daily_personal")

    fecha_actual = localtime().date()
    hora_actual  = localtime().time()

    if request.method == "POST":
        form = DailyForm(request.POST)
        if form.is_valid():
            # 1) crear/actualizar cabecera
            daily, created = Daily.objects.get_or_create(
                integrante=integrante,
                fecha=fecha_actual,
                defaults=form.cleaned_data
            )
            if not created:
                for f, v in form.cleaned_data.items():
                    setattr(daily, f, v)

            # fuera de horario
            daily.fuera_horario = not en_ventana_daily(hora_actual)
            daily.save()

            # 2) si enviaron enlace de tarea/subtarea, crear la línea HOY
            link_tipo   = (request.POST.get("link_tipo") or "").lower()
            tarea_id    = request.POST.get("tarea_id") or ""
            subtarea_id = request.POST.get("subtarea_id") or ""

            # Validación simple: no ambas
            if tarea_id and subtarea_id:
                messages.error(request, "Selecciona solo Tarea o Subtarea (no ambas).")
                return redirect("daily_personal")

            descripcion_hoy = (form.cleaned_data.get("que_hara_hoy") or "").strip()

            try:
                if link_tipo == "tarea" and tarea_id:
                    DailyItem.objects.create(
                        daily=daily, tipo="HOY",
                        descripcion=descripcion_hoy,
                        tarea_id=int(tarea_id)
                    )
                elif link_tipo == "subtarea" and subtarea_id:
                    DailyItem.objects.create(
                        daily=daily, tipo="HOY",
                        descripcion=descripcion_hoy,
                        subtarea_id=int(subtarea_id)
                    )
                # si no eligió enlace, no se crea línea (solo header)
            except ValueError:
                messages.error(request, "IDs de enlace inválidos.")
                return redirect("daily_personal")

            messages.success(request, "✅ Daily guardado" + (" y línea de HOY enlazada." if (tarea_id or subtarea_id) else "."))
            return redirect("daily_resumen")
    else:
        try:
            daily_existente = Daily.objects.get(integrante=integrante, fecha=fecha_actual)
            form = DailyForm(instance=daily_existente)
        except Daily.DoesNotExist:
            form = DailyForm()

    daily_actual = Daily.objects.filter(integrante=integrante, fecha=fecha_actual).first()

    return render(request, "backlog/daily_form.html", {
        "form": form,
        "integrante": integrante,
        "daily": daily_actual,              # puede ser None en primer ingreso
        "fecha_actual": localtime().strftime("%Y-%m-%d %H:%M"),
    })

@login_required
def daily_personal(request):
    integrante, _, es_visualizador, _ = _flags_usuario(request)
    if es_visualizador:
        messages.info(request, "Eres Visualizador: solo puedes consultar dailies.")
        return redirect("daily_resumen")

    if not integrante:
        integrante, _ = Integrante.objects.get_or_create(
            user=request.user,
            defaults={'rol': Integrante.ROL_MIEMBRO}
        )
        messages.info(request, "Se creó tu perfil de integrante automáticamente.")
    return daily_view(request, integrante.id)


@login_required
def daily_resumen(request):
    integrante, es_admin, es_visualizador, _ = _flags_usuario(request)
    puede_filtrar = es_admin or es_visualizador
    fecha_limite = datetime.now().date() - timedelta(days=7)

    if not puede_filtrar:
        registros = Daily.objects.filter(
            integrante=integrante, fecha__gte=fecha_limite
        ).select_related("integrante__user", "sprint").order_by("-fecha") if integrante else Daily.objects.none()
        integrantes = []
        persona_id = None
    else:
        if es_admin:
            registros = Daily.objects.select_related(
                "integrante__user", "sprint"
            ).filter(fecha__gte=fecha_limite).order_by("-fecha")
            integrantes = Integrante.objects.select_related("user").all().order_by("user__first_name", "user__last_name")
        else:
            proyectos = _proyectos_autorizados_qs(integrante)
            if not proyectos.exists():
                registros = Daily.objects.none()
                integrantes = []
            else:
                ids_legacy = Tarea.objects.filter(epica__proyecto__in=proyectos).values_list("asignado_a_id", flat=True)
                ids_m2m = Tarea.objects.filter(epica__proyecto__in=proyectos).values_list("asignados__id", flat=True)
                ids_integrantes = {i for i in list(ids_legacy) + list(ids_m2m) if i is not None}

                registros = Daily.objects.select_related(
                    "integrante__user", "sprint"
                ).filter(integrante_id__in=ids_integrantes, fecha__gte=fecha_limite).order_by("-fecha")
                integrantes = Integrante.objects.select_related("user").filter(
                    id__in=ids_integrantes
                ).order_by("user__first_name", "user__last_name")

        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                pid = int(persona_id)
                registros = registros.filter(integrante__id=pid)
            except (ValueError, Integrante.DoesNotExist):
                pass

    # === Añadir métricas de alineación para visualización ===
    for d in registros:
        try:
            d.metricas = d.alineacion
        except Exception:
            d.metricas = {'porcentaje': 0, 'alineados': 0, 'no_alineados': 0, 'total': 0, 'ids_no_alineados': []}

    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
        "tiene_permisos_admin": es_admin,
        "puede_filtrar": puede_filtrar,
        "persona_id": persona_id if puede_filtrar else None,
    })


# === CRUD de DailyItem (líneas) ===

@login_required
@require_POST
def dailyitem_create(request, daily_id):
    daily = get_object_or_404(Daily.objects.select_related("integrante"), id=daily_id)
    owner = getattr(request.user, "integrante", None)
    if not owner or (owner.id != daily.integrante_id and not owner.es_admin()):
        return JsonResponse({"error": "Sin permisos para agregar líneas a este daily."}, status=403)

    tipo = (request.POST.get("tipo") or "").upper()
    descripcion = (request.POST.get("descripcion") or "").strip()
    minutos = request.POST.get("minutos")
    evidencia_url = (request.POST.get("evidencia_url") or "").strip()
    tarea_id = request.POST.get("tarea_id")
    subtarea_id = request.POST.get("subtarea_id")

    if tipo not in {"AYER", "HOY"}:
        return JsonResponse({"error": "Tipo inválido (debe ser AYER u HOY)."}, status=400)

    if not descripcion and not tarea_id and not subtarea_id:
        return JsonResponse({"error": "Debe indicar descripción o asociar una tarea/subtarea."}, status=400)

    if tarea_id and subtarea_id:
        return JsonResponse({"error": "Seleccione solo Tarea o Subtarea (no ambas)."}, status=400)

    kwargs = dict(daily=daily, tipo=tipo, descripcion=descripcion, evidencia_url=evidencia_url or "")
    if minutos:
        try:
            kwargs["minutos"] = int(minutos)
        except ValueError:
            return JsonResponse({"error": "Minutos debe ser numérico."}, status=400)

    if tarea_id:
        kwargs["tarea_id"] = tarea_id
    if subtarea_id:
        kwargs["subtarea_id"] = subtarea_id

    item = DailyItem.objects.create(**kwargs)
    return JsonResponse({"success": True, "item": {"id": item.id, "tipo": item.tipo, "descripcion": item.descripcion}})


@login_required
@require_http_methods(["POST"])
def dailyitem_edit(request, item_id):
    item = get_object_or_404(DailyItem.objects.select_related("daily__integrante"), id=item_id)
    owner = getattr(request.user, "integrante", None)
    if not owner or (owner.id != item.daily.integrante_id and not owner.es_admin()):
        return JsonResponse({"error": "Sin permisos para editar esta línea."}, status=403)

    tipo = (request.POST.get("tipo") or item.tipo).upper()
    descripcion = (request.POST.get("descripcion") or item.descripcion).strip()
    evidencia_url = (request.POST.get("evidencia_url") or item.evidencia_url).strip()
    tarea_id = request.POST.get("tarea_id")
    subtarea_id = request.POST.get("subtarea_id")
    minutos_raw = request.POST.get("minutos")

    if tipo not in {"AYER", "HOY"}:
        return JsonResponse({"error": "Tipo inválido."}, status=400)

    if tarea_id and subtarea_id:
        return JsonResponse({"error": "Seleccione solo Tarea o Subtarea (no ambas)."}, status=400)

    item.tipo = tipo
    item.descripcion = descripcion
    item.evidencia_url = evidencia_url

    if minutos_raw is not None:
        if minutos_raw == "":
            item.minutos = None
        else:
            try:
                item.minutos = int(minutos_raw)
            except ValueError:
                return JsonResponse({"error": "Minutos debe ser numérico."}, status=400)

    if tarea_id is not None:
        item.tarea_id = tarea_id or None
    if subtarea_id is not None:
        item.subtarea_id = subtarea_id or None

    if item.tarea_id and item.subtarea_id:
        return JsonResponse({"error": "Seleccione solo Tarea o Subtarea (no ambas)."}, status=400)

    item.save()
    return JsonResponse({"success": True})


@login_required
@require_POST
def dailyitem_delete(request, item_id):
    item = get_object_or_404(DailyItem.objects.select_related("daily__integrante"), id=item_id)
    owner = getattr(request.user, "integrante", None)
    if not owner or (owner.id != item.daily.integrante_id and not owner.es_admin()):
        return JsonResponse({"error": "Sin permisos para eliminar esta línea."}, status=403)

    item.delete()
    return JsonResponse({"success": True})


@login_required
def daily_items_json(request, daily_id):
    daily = get_object_or_404(Daily.objects.select_related("integrante__user"), id=daily_id)
    owner = getattr(request.user, "integrante", None)
    if not owner:
        return JsonResponse({"error": "No autenticado."}, status=401)
    if owner.id != daily.integrante_id and not (owner.es_admin() or owner.es_visualizador()):
        return JsonResponse({"error": "Sin permisos para ver estas líneas."}, status=403)

    items = (
        DailyItem.objects
        .filter(daily=daily)
        .select_related("tarea", "subtarea")
        .order_by("tipo", "id")
        .values("id", "tipo", "descripcion", "minutos", "evidencia_url", "tarea_id", "subtarea_id")
    )
    return JsonResponse({"daily": daily.id, "integrante": str(daily.integrante), "items": list(items)})

# backlog/views.py
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render, redirect
from datetime import datetime, timedelta

@login_required
def reporte_enlaces_daily(request):
    """
    Panel maestro (solo admins): lista Tareas/Subtareas y los dailies en los que se enlazaron.
    Filtros:
      - date_from, date_to (YYYY-MM-DD) | por defecto últimos 30 días
      - integrante (id)
      - include_closed=1 (incluye COMPLETADO/cerrada)
    Muestra la descripción escrita para HOY con fallback:
      DailyItem.descripcion  ->  si vacío, usa Daily.que_hara_hoy
    """
    integrante = getattr(request.user, "integrante", None)
    if not integrante or not integrante.es_admin():
        return redirect("home")

    # ---- Filtros de fecha ----
    today = timezone.localdate()
    default_from = today - timedelta(days=30)
    date_from_str = request.GET.get("date_from") or default_from.isoformat()
    date_to_str   = request.GET.get("date_to")   or today.isoformat()
    integrante_id = request.GET.get("integrante") or ""
    include_closed = request.GET.get("include_closed") == "1"

    def parse_date(s, fb):
        try: return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception: return fb

    date_from = parse_date(date_from_str, default_from)
    date_to   = parse_date(date_to_str, today)

    # ---- Base: solo líneas de HOY con enlace a tarea o subtarea en el rango ----
    base = (
        DailyItem.objects
        .select_related(
            "daily", "daily__integrante", "daily__sprint",
            "tarea", "tarea__epica", "tarea__sprint", "tarea__asignado_a",
            "subtarea", "subtarea__bloque", "subtarea__bloque__tarea", "subtarea__responsable",
        )
        .filter(
            daily__fecha__gte=date_from,
            daily__fecha__lte=date_to,
            tipo="HOY",
        )
        .exclude(tarea__isnull=True, subtarea__isnull=True)
    )

    if integrante_id:
        try:
            base = base.filter(daily__integrante_id=int(integrante_id))
        except ValueError:
            pass

    if not include_closed:
        base = base.exclude(Q(tarea__estado="COMPLETADO") | Q(tarea__completada=True))
        base = base.exclude(Q(subtarea__estado="cerrada") | Q(subtarea__estado="COMPLETADO"))

    # ---- Agrupación por objetivo (tarea/subtarea) ----
    grupos = {}

    def add_enlace(clave, row, it):
        bucket = grupos.setdefault(clave, {
            "tipo": row["tipo"],                 # "TAREA" | "SUBTAREA"
            "tarea_id": row.get("tarea_id"),
            "tarea_titulo": row.get("tarea_titulo"),
            "tarea_estado": row.get("tarea_estado"),
            "tarea_sprint": row.get("tarea_sprint"),
            "asignado": row.get("asignado"),
            "subtarea_id": row.get("subtarea_id"),
            "subtarea_titulo": row.get("subtarea_titulo"),
            "subtarea_estado": row.get("subtarea_estado"),
            "subtarea_bloque": row.get("subtarea_bloque"),
            "enlaces": [],  # [{fecha, integrante, descripcion}]
        })
        # Fallback de descripción: DailyItem.descripcion -> Daily.que_hara_hoy
        desc = (it.descripcion or it.daily.que_hara_hoy or "").strip()
        bucket["enlaces"].append({
            "fecha": it.daily.fecha.strftime("%b. %-d, %Y") if hasattr(it.daily.fecha, "strftime") else str(it.daily.fecha),
            "integrante": str(it.daily.integrante),
            "descripcion": desc,
        })

    for it in base.order_by("id"):
        if it.subtarea_id:
            st = it.subtarea
            tarea_padre = getattr(st, "tarea", None)  # property en tu modelo Subtarea
            row = {
                "tipo": "SUBTAREA",
                "subtarea_id": it.subtarea_id,
                "subtarea_titulo": st.titulo if st else "",
                "subtarea_estado": (st.estado if st else ""),
                "subtarea_bloque": (st.bloque.etiqueta() if st and st.bloque else ""),
                "tarea_id": getattr(tarea_padre, "id", None),
                "tarea_titulo": getattr(tarea_padre, "titulo", ""),
                "tarea_estado": getattr(tarea_padre, "estado", ""),
                "tarea_sprint": str(getattr(tarea_padre, "sprint", "")) if tarea_padre else "",
                "asignado": str(getattr(st, "responsable", "") or "—"),
            }
            add_enlace(("SUBTAREA", it.subtarea_id), row, it)

        elif it.tarea_id:
            t = it.tarea
            row = {
                "tipo": "TAREA",
                "tarea_id": it.tarea_id,
                "tarea_titulo": t.titulo if t else "",
                "tarea_estado": (t.estado if t else ""),
                "tarea_sprint": str(getattr(t, "sprint", "")) if t else "",
                "asignado": (t.responsables_list if hasattr(t, "responsables_list") else (str(t.asignado_a) if t and t.asignado_a_id else "—")),
                "subtarea_id": None,
                "subtarea_titulo": "",
                "subtarea_estado": "",
                "subtarea_bloque": "",
            }
            add_enlace(("TAREA", it.tarea_id), row, it)

    resultados = list(grupos.values())
    resultados.sort(key=lambda r: (r["tipo"], (r.get("subtarea_titulo") or r.get("tarea_titulo") or "").lower()))

    integrantes_opts = Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name")

    return render(request, "backlog/reporte_enlaces_daily.html", {
        "resultados": resultados,
        "integrantes": integrantes_opts,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "sel_integrante": integrante_id,
        "include_closed": include_closed,
        "es_admin": True,
    })

# ==============================
# Opciones para Daily (Tareas/Subtareas asignadas)
# ==============================
from django.views.decorators.http import require_GET

@login_required
@require_GET
def daily_tareas_opciones(request):
    """
    Devuelve en JSON las Tareas asignadas al integrante actual
    que NO están completadas (estado != COMPLETADO y completada=False).
    """
    integrante = getattr(request.user, "integrante", None)
    if not integrante:
        return JsonResponse({"results": []})

    qs = (
        Tarea.objects
        .filter(
            Q(asignado_a=integrante) | Q(asignados=integrante),
            completada=False
        )
        .exclude(estado="COMPLETADO")
        .select_related("sprint", "epica")
        .distinct()
        .order_by("sprint__inicio", "titulo")
        .values("id", "titulo")
    )
    # Formato simple: [{id, titulo}]
    return JsonResponse(list(qs), safe=False)


@login_required
@require_GET
def daily_subtareas_opciones(request):
    """
    Devuelve en JSON las Subtareas asignadas al integrante actual
    que NO están cerradas (estado != 'cerrada').
    """
    integrante = getattr(request.user, "integrante", None)
    if not integrante:
        return JsonResponse({"results": []})

    qs = (
        Subtarea.objects
        .filter(responsable=integrante)
        .exclude(estado="cerrada")  # estados definidos en ESTADO_SUBTAREA
        .select_related("bloque__tarea")
        .order_by("bloque__tarea__sprint__inicio", "bloque__indice", "id")
        .values("id", "titulo")
    )
    # Formato simple: [{id, titulo}]
    return JsonResponse(list(qs), safe=False)

# ==============================
# Backlog
# ==============================
@login_required
def backlog_lista(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    group_by  = request.GET.get("group", "epica")
    expand_id = request.GET.get("expand")

    tareas = (
        _queryset_visible_tareas(integrante, puede_ver_todo)
        .select_related("sprint", "epica", "epica__proyecto")
        .prefetch_related("asignados__user")
    )

    sprints = Sprint.objects.all().order_by("inicio")

    if puede_ver_todo:
        ids_a = tareas.values_list("asignado_a_id", flat=True)
        ids_m = tareas.values_list("asignados__id", flat=True)
        ids_set = {i for i in list(ids_a) + list(ids_m) if i is not None}
        integrantes = (
            Integrante.objects
            .select_related("user")
            .filter(id__in=ids_set) if es_visualizador else
            Integrante.objects.select_related("user").all()
        )
        integrantes = integrantes.order_by("user__first_name", "user__last_name").distinct()

        epicas = Epica.objects.filter(tareas__isnull=False).distinct().order_by("titulo")
        if es_visualizador:
            epicas = _filtrar_por_proyectos_autorizados_epicas(epicas, integrante)
    else:
        integrantes = []
        epicas = (
            Epica.objects
            .filter(Q(tareas__asignados=integrante) | Q(tareas__asignado_a=integrante))
            .distinct()
            .order_by("titulo")
        )

    aplicar_filtros = request.GET.get("filtrar") == "1"
    persona_id = request.GET.get("persona") if aplicar_filtros else None
    sprint_id  = request.GET.get("sprint")  if aplicar_filtros else None
    estado     = request.GET.get("estado")  if aplicar_filtros else None
    epica_id   = request.GET.get("epica")   if aplicar_filtros else None

    if aplicar_filtros:
        if persona_id:
            try:
                pid = int(persona_id)
                tareas = tareas.filter(Q(asignados__id=pid) | Q(asignado_a__id=pid)).distinct()
            except ValueError:
                pass
        if sprint_id:
            try:
                tareas = tareas.filter(sprint__id=int(sprint_id))
            except ValueError:
                pass
        if epica_id:
            try:
                tareas = tareas.filter(epica__id=int(epica_id))
            except ValueError:
                pass
        if estado == "abiertas":
            tareas = tareas.filter(completada=False)
        elif estado == "cerradas":
            tareas = tareas.filter(completada=True)

    if group_by == "proyecto":
        tareas = tareas.order_by("epica__proyecto__nombre", "sprint__inicio", "categoria", "titulo")
    elif group_by == "epica":
        tareas = tareas.order_by("epica__titulo", "sprint__inicio", "categoria", "titulo")
    elif group_by == "sprint":
        tareas = tareas.order_by("sprint__inicio", "categoria", "titulo")
    else:
        tareas = tareas.order_by("sprint__inicio", "categoria", "titulo")

    grouped = None
    paginator = None
    PAGE_SIZE = 25

    if group_by in ("proyecto", "epica", "sprint"):
        grouped = {}
        for t in tareas:
            if group_by == "proyecto":
                k = t.epica.proyecto if (t.epica and hasattr(t.epica, "proyecto")) else None
            elif group_by == "epica":
                k = t.epica
            else:
                k = t.sprint
            grouped.setdefault(k, []).append(t)
    else:
        paginator = Paginator(tareas, PAGE_SIZE)
        page_number = request.GET.get("page")
        tareas = paginator.get_page(page_number)

    return render(request, "backlog/backlog_lista.html", {
        "tareas": tareas,
        "grouped": grouped,
        "group_by": group_by,
        "expand_id": expand_id,
        "paginator": paginator,
        "sprints": sprints,
        "integrantes": integrantes,
        "epicas": epicas,
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
        "es_visualizador": es_visualizador,
        "estado": estado if aplicar_filtros else "",
        "persona_id": persona_id if aplicar_filtros else "",
        "sprint_id": sprint_id if aplicar_filtros else "",
        "epica_id": epica_id if aplicar_filtros else "",
    })

#===========MATRIZ HZ================
from django.utils import timezone
from django.db.models import Q
from django.shortcuts import render

def _activos_por_defecto(qs, include_closed: bool, show_old: bool, sprint_id: str | None):
    """
    Aplica:
      - ocultar COMPLETADO/completada salvo include_closed=1
      - ocultar sprints viejos (fin < hoy-2d) salvo show_old=1
      - filtrar por sprint si viene sprint_id
    """
    today = timezone.localdate()
    limite = today - timezone.timedelta(days=2)

    if not include_closed:
        qs = qs.exclude(estado="COMPLETADO").exclude(completada=True)

    if sprint_id:
        qs = qs.filter(sprint_id=sprint_id)
    else:
        if not show_old:
            qs = qs.filter(Q(sprint__fin__gte=limite) | Q(sprint__fin__isnull=True))

    return qs.select_related("epica", "asignado_a", "sprint").order_by("-id")


@login_required
def backlog_matriz(request):
    """
    Matriz Eisenhower (UI / NUI / UNI / NUNI).
    - Usuarios no admin: solo ven sus tareas (asignado_a o en M2M asignados).
    - Visualizadores: ven lo autorizado por proyecto.
    - Admin: ven todo y pueden filtrar por persona.
    """
    integrante, es_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    include_closed = request.GET.get("include_closed") == "1"
    show_old       = request.GET.get("show_old") == "1"
    sprint_id      = request.GET.get("sprint") or ""
    persona_id     = request.GET.get("persona") or ""

    # Base según permisos (reusa la lógica central de visibilidad)
    base = _queryset_visible_tareas(integrante, puede_ver_todo)

    # Filtros por defecto (oculta cerradas y sprints viejos) + sprint específico
    base = _activos_por_defecto(base, include_closed, show_old, sprint_id)

    # Filtro por persona: habilitado para admin o visualizador
    if (es_admin or es_visualizador) and persona_id:
        try:
            pid = int(persona_id)
            base = base.filter(Q(asignado_a_id=pid) | Q(asignados__id=pid)).distinct()
        except ValueError:
            pass

    # Cuadrantes
    ui   = base.filter(categoria="UI")
    nui  = base.filter(categoria="NUI")
    uni  = base.filter(categoria="UNI")
    nuni = base.filter(categoria="NUNI")

    # Combos
    sprints = Sprint.objects.order_by("-inicio", "-fin")
    if puede_ver_todo:
        # Solo muestra integrantes que aparecen en las tareas visibles (reduce lista)
        ids_a = base.values_list("asignado_a_id", flat=True)
        ids_m = base.values_list("asignados__id", flat=True)
        ids_set = {i for i in list(ids_a) + list(ids_m) if i is not None}
        integrantes_opts = (
            Integrante.objects
            .select_related("user")
            .filter(id__in=ids_set)
            .order_by("user__first_name", "user__last_name")
            .distinct()
        )
    else:
        integrantes_opts = []

    ctx = {
        "ui": ui,
        "nui": nui,
        "uni": uni,
        "nuni": nuni,
        "tiene_permisos_admin": es_admin,
        "integrantes": integrantes_opts,
        "persona_id": persona_id if (es_admin or es_visualizador) else "",
        "sprints": sprints,
        "sprint_id": sprint_id,
        "include_closed": include_closed,
        "show_old": show_old,
    }
    return render(request, "backlog/backlog_matriz.html", ctx)

# ==============================
# Checklist de tareas
# ==============================

@login_required
def checklist_view(request, integrante_id):
    integrante_obj = get_object_or_404(Integrante, id=integrante_id)

    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.es_admin()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if not tiene_permisos_admin and integrante_obj != usuario_integrante:
        messages.error(request, "❌ No puedes ver el checklist de otro integrante.")
        return redirect("backlog_lista")

    tareas = (Tarea.objects
              .filter(Q(asignados=integrante_obj) | Q(asignado_a=integrante_obj), completada=False)
              .select_related("sprint")
              .prefetch_related("asignados__user")
              .distinct()
              .order_by("sprint__inicio", "categoria"))

    return render(request, "backlog/checklist.html", {
        "integrante": integrante_obj,
        "tareas": tareas,
    })

# ==============================
# Daily: eliminar
# ==============================

@login_required
def eliminar_daily(request, daily_id):
    daily = get_object_or_404(Daily, id=daily_id)

    try:
        if not request.user.integrante.es_admin():
            messages.error(request, "❌ No tienes permisos para eliminar dailies.")
            return redirect("daily_resumen")
    except AttributeError:
        messages.error(request, "❌ No tienes un perfil de integrante válido.")
        return redirect("home")

    if request.method == "POST":
        daily.delete()
        messages.success(request, "🗑️ Daily eliminado correctamente.")
        return redirect("daily_resumen")

    return render(request, "backlog/confirmar_eliminar_daily.html", {"daily": daily})

# ==============================
# Sprints
# ==============================

@login_required
def sprint_list(request):
    try:
        tiene_permisos_admin = request.user.integrante.es_admin()
    except AttributeError:
        tiene_permisos_admin = False

    sprints = Sprint.objects.all().order_by("inicio")
    return render(request, "backlog/sprint_list.html", {
        "sprints": sprints,
        "tiene_permisos_admin": tiene_permisos_admin,
    })

@login_required
def sprint_create(request):
    if not request.user.integrante.es_admin():
        messages.error(request, "❌ No tienes permisos para crear sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        form = SprintForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Sprint creado correctamente.")
            return redirect("sprint_list")
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = SprintForm()

    return render(request, "backlog/sprint_form.html", {"form": form, "modo": "crear"})

@login_required
def sprint_edit(request, sprint_id):
    sprint = get_object_or_404(Sprint, id=sprint_id)

    if not request.user.integrante.es_admin():
        messages.error(request, "❌ No tienes permisos para editar sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        form = SprintForm(request.POST, instance=sprint)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Sprint actualizado correctamente.")
            return redirect("sprint_list")
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = SprintForm(instance=sprint)
    return render(request, "backlog/sprint_form.html", {"form": form})

@login_required
def sprint_delete(request, sprint_id):
    sprint = get_object_or_404(Sprint, id=sprint_id)

    if not request.user.integrante.es_admin():
        messages.error(request, "❌ No tienes permisos para eliminar sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        sprint.delete()
        messages.success(request, "🗑️ Sprint eliminado correctamente.")
        return redirect("sprint_list")

    return render(request, "backlog/confirmar_eliminar_sprint.html", {"sprint": sprint})

# ==============================
# Daily (admin crea de otros)
# ==============================

@login_required
def daily_create_admin(request):
    try:
        if not request.user.integrante.es_admin():
            messages.error(request, "❌ No tienes permisos para crear dailys de otros integrantes.")
            return redirect("daily_resumen")
    except AttributeError:
        messages.error(request, "❌ No tienes un perfil de integrante válido.")
        return redirect("home")

    if request.method == "POST":
        integrante_id = request.POST.get("integrante")
        integrante = get_object_or_404(Integrante, id=integrante_id)
        form = DailyForm(request.POST)
        if form.is_valid():
            daily = form.save(commit=False)
            daily.integrante = integrante
            hora_actual = localtime().time()
            if not en_ventana_daily(hora_actual):
                daily.fuera_horario = True
            daily.save()
            messages.success(request, f"✅ Daily registrado para {integrante.user.first_name}.")
            return redirect("daily_resumen")
    else:
        form = DailyForm()

    integrantes = Integrante.objects.select_related("user").all().order_by("user__first_name", "user__last_name")
    return render(request, "backlog/daily_create_admin.html", {
        "form": form,
        "integrantes": integrantes,
    })

# ==============================
# Tareas: eliminar
# ==============================

@login_required
def eliminar_tarea(request, tarea_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)

    try:
        if not request.user.integrante.es_admin():
            messages.error(request, "❌ No tienes permisos para eliminar tareas.")
            return redirect("backlog_lista")
    except AttributeError:
        messages.error(request, "❌ No tienes un perfil de integrante válido.")
        return redirect("home")

    if request.method == "POST":
        titulo_tarea = tarea.titulo
        tarea.delete()
        messages.success(request, f"🗑️ Tarea '{titulo_tarea}' eliminada correctamente.")
        return redirect("backlog_lista")

    return render(request, "backlog/confirmar_eliminar_tarea.html", {
        "tarea": tarea,
    })

# ==============================
# Kanban
# ==============================
@login_required
def kanban_board(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)
    tareas = _queryset_visible_tareas(integrante, puede_ver_todo)

    # ---- Filtros GET ----
    persona_id     = request.GET.get("persona") if puede_ver_todo else None
    epica_id       = request.GET.get("epica")   if puede_ver_todo else None
    sprint_id      = request.GET.get("sprint") or ""
    include_closed = request.GET.get("include_closed") == "1"   # por defecto NO ver cerradas
    show_old       = request.GET.get("show_old") == "1"         # por defecto NO ver sprints viejos

    # Persona (solo admin/visualizador)
    if persona_id and puede_ver_todo:
        try:
            pid = int(persona_id)
            tareas = tareas.filter(Q(asignados__id=pid) | Q(asignado_a__id=pid)).distinct()
        except ValueError:
            pass

    # Épica (solo admin/visualizador)
    if epica_id and puede_ver_todo:
        try:
            tareas = tareas.filter(epica__id=int(epica_id))
        except ValueError:
            pass

    # Sprint específico
    if sprint_id:
        try:
            tareas = tareas.filter(sprint__id=int(sprint_id))
        except ValueError:
            pass
    else:
        # Ocultar sprints “viejos” si no se marca show_old
        if not show_old:
            hoy = timezone.localdate()
            limite = hoy - timedelta(days=2)
            tareas = tareas.filter(Q(sprint__fin__isnull=True) | Q(sprint__fin__gte=limite))

    # Ocultar cerradas (COMPLETADO/completada) por defecto
    if not include_closed:
        tareas = tareas.exclude(estado__iexact="COMPLETADO").exclude(completada=True)

    # ---- Combos ----
    if puede_ver_todo:
        ids_a = tareas.values_list("asignado_a_id", flat=True)
        ids_m = tareas.values_list("asignados__id", flat=True)
        ids_set = {i for i in list(ids_a) + list(ids_m) if i is not None}
        integrantes = (
            Integrante.objects.select_related("user").filter(id__in=ids_set)
            if es_visualizador else
            Integrante.objects.select_related("user").all()
        ).order_by("user__first_name", "user__last_name")

        epicas = Epica.objects.all().order_by("titulo")
        if es_visualizador:
            epicas = _filtrar_por_proyectos_autorizados_epicas(epicas, integrante)
    else:
        integrantes = []
        epicas = Epica.objects.filter(
            Q(tareas__asignados=integrante) | Q(tareas__asignado_a=integrante)
        ).distinct().order_by("titulo")

    sprints = Sprint.objects.all().order_by("-inicio")

    # ---- Columnas ----
    estados = {
        "nuevo":        tareas.filter(estado__iexact="NUEVO").order_by("-id"),
        "en_progreso":  tareas.filter(estado__iexact="EN_PROGRESO").order_by("-id"),
        "completado":   tareas.filter(estado__iexact="COMPLETADO").order_by("-id"),
        "bloqueado":    tareas.filter(estado__iexact="BLOQUEADO").order_by("-id"),
    }

    return render(request, "backlog/kanban_board.html", {
        **estados,
        "integrantes": integrantes,
        "epicas": epicas,
        "sprints": sprints,
        "persona_id": persona_id if puede_ver_todo else None,
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
        "include_closed": include_closed,
        "show_old": show_old,
        "sprint_id": sprint_id,
    })
    
@login_required
def cambiar_estado_tarea(request, tarea_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not es_admin and not _es_responsable(tarea, integrante):
        return JsonResponse({"error": "Solo responsables o administradores pueden mover la tarea"}, status=403)

    try:
        data = json.loads(request.body)
        nuevo_estado = data.get("estado", "").upper()
        observacion  = (data.get("observacion") or "").strip()

        estados_validos = ["NUEVO", "EN_PROGRESO", "COMPLETADO", "BLOQUEADO"]
        if nuevo_estado not in estados_validos:
            return JsonResponse({"error": "Estado no válido"}, status=400)

        estado_anterior = tarea.estado
        tarea.estado = nuevo_estado

        if nuevo_estado == "COMPLETADO":
            tarea.completada = True
            if not tarea.fecha_cierre:
                tarea.fecha_cierre = now()
        else:
            tarea.completada = False
            tarea.fecha_cierre = None

        tarea.save()

        if nuevo_estado == "EN_PROGRESO" and observacion:
            Evidencia.objects.create(
                tarea=tarea,
                comentario=f"[OBS ESTADO] {observacion}\n(De: {estado_anterior} → EN_PROGRESO)",
                creado_por=request.user
            )

        return JsonResponse({
            "success": True,
            "tarea_id": tarea.id,
            "nuevo_estado": nuevo_estado,
            "mensaje": f"Tarea movida a {tarea.get_estado_display()}"
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ==============================
# Matriz: cambiar categoría (DnD)
# ==============================

@login_required
def cambiar_categoria_tarea(request, tarea_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not es_admin and not _es_responsable(tarea, integrante):
        return JsonResponse({"error": "Solo responsables o administradores pueden mover la tarea"}, status=403)

    try:
        data = json.loads(request.body)
        nueva_categoria = data.get("categoria", "").upper()
        categorias_validas = ["UI", "NUI", "UNI", "NUNI"]
        if nueva_categoria not in categorias_validas:
            return JsonResponse({"error": "Categoría no válida"}, status=400)

        tarea.categoria = nueva_categoria
        tarea.save()

        return JsonResponse({
            "success": True,
            "tarea_id": tarea.id,
            "nueva_categoria": nueva_categoria,
            "mensaje": f"Tarea movida a {tarea.get_categoria_display()}"
        })
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

# ==============================
# CRUD de Épicas
# ==============================

@login_required
def epica_list(request):
    integrante, admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    if admin:
        epicas = (
            Epica.objects
            .select_related("owner", "proyecto")
            .prefetch_related("owners__user", "sprints")
            .order_by("-creada_en")
        )
    elif es_visualizador:
        epicas = (
            _filtrar_por_proyectos_autorizados_epicas(
                Epica.objects.select_related("owner", "proyecto").prefetch_related("owners__user", "sprints"),
                integrante
            )
            .order_by("-creada_en")
        )
    else:
        if integrante:
            epicas = (
                Epica.objects
                .filter(
                    Q(tareas__asignados=integrante) |
                    Q(tareas__asignado_a=integrante) |
                    Q(owner=integrante) |
                    Q(owners=integrante)
                )
                .select_related("owner", "proyecto")
                .prefetch_related("owners__user", "sprints")
                .distinct()
                .order_by("-creada_en")
            )
        else:
            epicas = Epica.objects.none()

    proyecto_id = request.GET.get("proyecto")
    if proyecto_id:
        try:
            epicas = epicas.filter(proyecto_id=int(proyecto_id))
        except ValueError:
            pass

    if admin:
        proyectos = Proyecto.objects.filter(activo=True).order_by("codigo")
    elif es_visualizador:
        proyectos = _proyectos_autorizados_qs(integrante).order_by("codigo")
    else:
        proyectos = Proyecto.objects.filter(
            activo=True, epicas__tareas__asignados=integrante
        ).distinct().order_by("codigo")

    context = {
        "epicas": epicas,
        "admin": admin,
        "proyectos": proyectos,
        "proyecto_id": proyecto_id,
    }
    return render(request, "backlog/epica_list.html", context)

@login_required
def epica_create(request):
    if not _es_admin(request):
        messages.error(request, "❌ No tienes permisos para crear épicas.")
        return redirect("epica_list")

    if request.method == "POST":
        form = EpicaForm(request.POST)
        if form.is_valid():
            epica = form.save()
            messages.success(request, "✅ Épica creada correctamente.")
            return redirect("epica_detail", epica_id=epica.id)
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = EpicaForm()

    return render(request, "backlog/epica_form.html", {"form": form, "modo": "crear"})

@login_required
def epica_edit(request, epica_id):
    if not _es_admin(request):
        messages.error(request, "❌ No tienes permisos para editar épicas.")
        return redirect("epica_list")

    epica = get_object_or_404(Epica, pk=epica_id)

    if request.method == "POST":
        form = EpicaForm(request.POST, instance=epica)
        if form.is_valid():
            epica = form.save()
            messages.success(request, "✏️ Épica actualizada correctamente.")
            return redirect("epica_detail", epica_id=epica.id)
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = EpicaForm(instance=epica)

    return render(request, "backlog/epica_form.html", {"form": form, "modo": "editar", "epica": epica})

@login_required
def epica_delete(request, epica_id):
    if not _es_admin(request):
        messages.error(request, "❌ No tienes permisos para eliminar épicas.")
        return redirect("epica_list")

    epica = get_object_or_404(Epica, pk=epica_id)

    if request.method == "POST":
        titulo = epica.titulo
        epica.delete()
        messages.success(request, f"🗑️ Épica '{titulo}' eliminada correctamente.")
        return redirect("epica_list")

    return render(request, "backlog/epica_confirm_delete.html", {"epica": epica})

# ==============================
# Detalle de Épica
# ==============================

@login_required
def epica_detail(request, epica_id):
    integrante, es_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    epica = (
        Epica.objects
        .select_related("owner", "proyecto")
        .prefetch_related("owners__user", "sprints")
        .get(pk=epica_id)
    )

    if es_visualizador and not es_admin:
        proyectos = _proyectos_autorizados_qs(integrante)
        if not proyectos.filter(id=getattr(epica.proyecto, "id", None)).exists():
            messages.error(request, "❌ No tienes permisos para ver esta épica.")
            return redirect("epica_list")

    if not puede_ver_todo and not es_visualizador:
        es_owner = bool(
            integrante and (
                epica.owner_id == integrante.id or epica.owners.filter(id=integrante.id).exists()
            )
        )
        tiene_tareas = epica.tareas.filter(
            Q(asignados=integrante) | Q(asignado_a=integrante)
        ).exists() if integrante else False

        if not (tiene_tareas or es_owner):
            messages.error(request, "❌ No tienes permisos para ver esta épica.")
            return redirect("epica_list")

    tareas_qs = (
        epica.tareas
        .select_related("asignado_a__user", "sprint")
        .prefetch_related("asignados__user")
        .order_by("estado", "categoria", "titulo")
    )

    total_tareas = tareas_qs.count()
    completadas = tareas_qs.filter(completada=True).count()
    progreso_calculado = round((completadas / total_tareas) * 100.0, 2) if total_tareas else 0.0
    avance_efectivo = epica.avance

    estados = {
        "NUEVO": tareas_qs.filter(estado__iexact="NUEVO"),
        "EN_PROGRESO": tareas_qs.filter(estado__iexact="EN_PROGRESO"),
        "BLOQUEADO": tareas_qs.filter(estado__iexact="BLOQUEADO"),
        "COMPLETADO": tareas_qs.filter(estado__iexact="COMPLETADO"),
    }

    conteos_por_estado = (
        tareas_qs.values("estado")
        .annotate(total=Count("id"))
        .order_by()
    )
    conteos_map = {c["estado"]: c["total"] for c in conteos_por_estado}

    context = {
        "epica": epica,
        "tareas": tareas_qs,
        "estados": estados,
        "conteos": conteos_map,
        "total_tareas": total_tareas,
        "tareas_completadas": completadas,
        "progreso_calculado": progreso_calculado,
        "avance_efectivo": avance_efectivo,
        "puede_ver_todo": puede_ver_todo,
        "es_admin": es_admin,
        "es_visualizador": es_visualizador,
    }
    return render(request, "backlog/epica_detail.html", context)

# ==============================
# Crear Proyecto (desde botón ➕)
# ==============================
@login_required
def proyecto_create(request):
    if not _es_admin(request):
        messages.error(request, "❌ No tienes permisos para crear proyectos.")
        return redirect("epica_list")

    if request.method == "POST":
        form = ProyectoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Proyecto creado correctamente.")
            return redirect("epica_create")
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = ProyectoForm()

    return render(request, "backlog/proyecto_form.html", {"form": form})

# ==============================
# Bloques y Subtareas (CRUD)
# ==============================

@login_required
def bloque_edit(request, bloque_id):
    bloque = get_object_or_404(BloqueTarea.objects.select_related("tarea"), id=bloque_id)
    tarea = bloque.tarea
    integrante, _, _, _ = _flags_usuario(request)

    if not _es_admin_neusi(integrante):
        messages.error(request, "❌ No tienes permisos para editar bloques.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        form = BloqueTareaForm(request.POST, instance=bloque)
        if form.is_valid():
            bloque = form.save()
            _sync_subtareas_fechas(bloque)  # sincroniza todas las subtareas del bloque
            messages.success(request, "✏️ Bloque actualizado correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        messages.error(request, "⚠️ Revisa los campos del bloque.")
    else:
        form = BloqueTareaForm(instance=bloque)

    return render(request, "backlog/bloque_form.html", {
        "form": form,
        "tarea": tarea,
        "bloque": bloque,
        "modo": "editar",
    })
@login_required
def subtarea_create(request, bloque_id):
    bloque = get_object_or_404(BloqueTarea.objects.select_related("tarea"), id=bloque_id)
    tarea = bloque.tarea
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not _puede_crud_subtareas(tarea, integrante):
        messages.error(request, "❌ No tienes permisos para gestionar subtareas en esta tarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        form = SubtareaForm(
            request.POST,
            tarea=tarea,
            bloque=bloque,
            es_admin=es_admin,
            instance=Subtarea(bloque=bloque),  # << clave
        )
        if form.is_valid():
            form.save(commit=True)
            messages.success(request, "✅ Subtarea creada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        messages.error(request, "⚠️ Revisa los campos de la subtarea.")
    else:
        form = SubtareaForm(
            tarea=tarea,
            bloque=bloque,
            es_admin=es_admin,
            instance=Subtarea(bloque=bloque),  # << clave
        )

    return render(request, "backlog/subtarea_form.html", {
        "form": form,
        "tarea": tarea,
        "bloque": bloque,
        "modo": "crear",
    })
@login_required
def subtarea_edit(request, subtarea_id):
    subtarea = get_object_or_404(Subtarea.objects.select_related("bloque__tarea"), id=subtarea_id)
    bloque = subtarea.bloque
    tarea = bloque.tarea
    integrante, _, _, _ = _flags_usuario(request)
    es_admin = _es_admin_neusi(integrante)

    if not _puede_crud_subtareas(tarea, integrante):
        messages.error(request, "❌ No tienes permisos para gestionar subtareas en esta tarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        form = SubtareaForm(request.POST, instance=subtarea, tarea=tarea, bloque=bloque, es_admin=es_admin)
        if form.is_valid():
            obj = form.save(commit=True)  # fuerza bloque y fechas
            messages.success(request, "✏️ Subtarea actualizada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        messages.error(request, "⚠️ Revisa los campos de la subtarea.")
    else:
        form = SubtareaForm(instance=subtarea, tarea=tarea, bloque=bloque, es_admin=es_admin)

    return render(request, "backlog/subtarea_form.html", {
        "form": form,
        "tarea": tarea,
        "bloque": bloque,
        "subtarea": subtarea,
        "modo": "editar",
    })

@login_required
def subtarea_delete(request, subtarea_id):
    subtarea = get_object_or_404(Subtarea.objects.select_related("bloque__tarea"), id=subtarea_id)
    tarea = subtarea.bloque.tarea
    integrante, _, _, _ = _flags_usuario(request)

    if not _puede_crud_subtareas(tarea, integrante):
        messages.error(request, "❌ No tienes permisos para eliminar subtareas en esta tarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        subtarea.delete()
        messages.success(request, "🗑️ Subtarea eliminada correctamente.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    return render(request, "backlog/subtarea_confirm_delete.html", {
        "tarea": tarea,
        "subtarea": subtarea,
    })

# ===== Subtareas: cambiar estado rápido =====
@login_required
def subtarea_cambiar_estado(request, subtarea_id):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    st = get_object_or_404(Subtarea.objects.select_related("bloque__tarea", "responsable"), id=subtarea_id)
    tarea = st.bloque.tarea
    integrante, es_admin, _, _ = _flags_usuario(request)

    es_resp_macro = _es_responsable(tarea, integrante)
    es_resp_st = (st.responsable_id == getattr(integrante, "id", None))
    if not (es_admin or es_resp_macro or es_resp_st):
        return JsonResponse({"error": "Sin permisos para cambiar estado."}, status=403)

    try:
        nuevo = (request.POST.get("estado") or "").upper()
        validos = {c[0] for c in Subtarea.ESTADO_CHOICES}
        if nuevo not in validos:
            return JsonResponse({"error": "Estado no válido."}, status=400)
        st.estado = nuevo
        st.save(update_fields=["estado"])
        return JsonResponse({"success": True, "estado": st.get_estado_display()})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ===== Evidencias por Subtarea =====
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied

def _puede_en_subtarea(subtarea, integrante, tarea) -> bool:
    """Admin, responsable de la Tarea macro o responsable directo de la Subtarea."""
    if _es_admin_neusi(integrante):
        return True
    if _es_responsable(tarea, integrante):
        return True
    return bool(integrante and subtarea.responsable_id == getattr(integrante, "id", None))

@login_required
@require_http_methods(["GET", "POST"])
def agregar_evidencia_subtarea(request, subtarea_id):
    subtarea = get_object_or_404(Subtarea.objects.select_related("bloque__tarea"), id=subtarea_id)
    tarea = subtarea.bloque.tarea
    integrante, _, _, _ = _flags_usuario(request)

    if not _puede_en_subtarea(subtarea, integrante, tarea):
        messages.error(request, "❌ No tienes permisos para registrar evidencias en esta subtarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        comentario = (request.POST.get("comentario") or "").strip()
        archivo = request.FILES.get("archivo")
        if not comentario and not archivo:
            messages.error(request, "⚠️ Agrega al menos un comentario o un archivo.")
            return render(request, "backlog/subtarea_evidencia_form.html", {
                "modo": "crear",
                "tarea": tarea,
                "subtarea": subtarea,
                "evidencia": None,
            })
        EvidenciaSubtarea.objects.create(
            subtarea=subtarea,
            comentario=comentario or "",
            archivo=archivo,
            creado_por=request.user,
        )
        messages.success(request, "✅ Evidencia registrada en la subtarea.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    # GET: mostrar formulario
    return render(request, "backlog/subtarea_evidencia_form.html", {
        "modo": "crear",
        "tarea": tarea,
        "subtarea": subtarea,
        "evidencia": None,
    })


@login_required
@require_http_methods(["GET", "POST"])
def editar_evidencia_subtarea(request, subtarea_id, evid_id):
    subtarea = get_object_or_404(Subtarea.objects.select_related("bloque__tarea"), id=subtarea_id)
    tarea = subtarea.bloque.tarea
    evidencia = get_object_or_404(EvidenciaSubtarea, id=evid_id, subtarea=subtarea)
    integrante, _, _, _ = _flags_usuario(request)

    if not _puede_en_subtarea(subtarea, integrante, tarea) and evidencia.creado_por_id != request.user.id:
        messages.error(request, "❌ No tienes permisos para editar esta evidencia.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        comentario = (request.POST.get("comentario") or "").strip()
        archivo = request.FILES.get("archivo")
        if not comentario and not archivo and not evidencia.archivo:
            messages.error(request, "⚠️ Debes dejar comentario o adjuntar archivo.")
            return render(request, "backlog/subtarea_evidencia_form.html", {
                "modo": "editar",
                "tarea": tarea,
                "subtarea": subtarea,
                "evidencia": evidencia,
            })
        evidencia.comentario = comentario
        if archivo:
            evidencia.archivo = archivo
        evidencia.save()
        messages.success(request, "✏️ Evidencia actualizada.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    return render(request, "backlog/subtarea_evidencia_form.html", {
        "modo": "editar",
        "tarea": tarea,
        "subtarea": subtarea,
        "evidencia": evidencia,
    })

@login_required
@require_http_methods(["GET", "POST"])
def eliminar_evidencia_subtarea(request, subtarea_id, evid_id):
    subtarea = get_object_or_404(Subtarea.objects.select_related("bloque__tarea"), id=subtarea_id)
    tarea = subtarea.bloque.tarea
    evidencia = get_object_or_404(EvidenciaSubtarea, id=evid_id, subtarea=subtarea)
    integrante, _, _, _ = _flags_usuario(request)

    if not _puede_en_subtarea(subtarea, integrante, tarea) and evidencia.creado_por_id != request.user.id:
        messages.error(request, "❌ No tienes permisos para eliminar esta evidencia.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    if request.method == "POST":
        evidencia.delete()
        messages.success(request, "🗑️ Evidencia eliminada.")
        return redirect("detalle_tarea", tarea_id=tarea.id)

    return render(request, "backlog/subtarea_evidencia_confirm_delete.html", {
        "tarea": tarea,
        "subtarea": subtarea,
        "evidencia": evidencia,
    })

# views.py
from django.shortcuts import render
from django.db.models import (
    Count, Sum, Q, Case, When, F, FloatField, IntegerField
)
from django.db.models.functions import Upper
from django.utils import timezone
from datetime import timedelta, date

from .models import Proyecto, Sprint, Epica, Tarea, Subtarea, Daily, Integrante

# ===============================
# Helpers internos
# ===============================
def _sprint_actual():
    hoy = timezone.localdate()
    return Sprint.objects.filter(inicio__lte=hoy, fin__gte=hoy).order_by("-inicio").first()

def _business_days(d1: date, d2: date) -> int:
    """Cuenta días hábiles inclusive entre d1 y d2."""
    if not d1 or not d2 or d2 < d1:
        return 0
    days = 0
    cur = d1
    while cur <= d2:
        if cur.weekday() < 5:  # lunes–viernes
            days += 1
        cur += timedelta(days=1)
    return days

# ===============================
# DASHBOARD PRINCIPAL (cache 45s)
# ===============================
@cache_page(45, key_prefix="dashboard_neusi")
def dashboard_neusi(request):
    # ------- Filtros -------
    sprint_actual = _sprint_actual()
    sprint_id = request.GET.get("sprint") or (sprint_actual.id if sprint_actual else None)
    proyecto_id = request.GET.get("proyecto")
    integrante_id = request.GET.get("integrante")
    scope = request.GET.get("scope", "sprint")  # sprint | global

    tareas = (
        Tarea.objects
        .select_related("epica", "sprint", "asignado_a", "epica__proyecto")
        .prefetch_related("asignados", "bloques__subtareas")
    )
    if sprint_id:
        tareas = tareas.filter(sprint_id=sprint_id)
    if proyecto_id:
        tareas = tareas.filter(epica__proyecto_id=proyecto_id)
    if integrante_id:
        tareas = tareas.filter(Q(asignado_a_id=integrante_id) | Q(asignados__id=integrante_id)).distinct()

    # ===== Normalización de estado para TAREA (HU) =====
    tareas_u = tareas.annotate(estado_u=Upper("estado"))

    cards = tareas_u.aggregate(
        hu_total=Count("id"),
        hu_new=Count("id", filter=Q(estado_u="NUEVO")),
        hu_inprog=Count("id", filter=Q(estado_u="EN_PROGRESO")),
        hu_blocked=Count("id", filter=Q(estado_u="BLOQUEADO")),
        hu_done=Count("id", filter=Q(estado_u__in=["COMPLETADO", "COMPLETADA"])),
        sp_planned=Sum("esfuerzo_sp"),
        sp_completed=Sum("esfuerzo_sp", filter=Q(estado_u__in=["COMPLETADO", "COMPLETADA"])),
    )

    # Datos para gráfica de HU por estado (doughnut)
    hu_labels = ["Nuevo", "En progreso", "Bloqueado", "Completado"]
    hu_data = [
        cards.get("hu_new") or 0,
        cards.get("hu_inprog") or 0,
        cards.get("hu_blocked") or 0,
        cards.get("hu_done") or 0,
    ]

    # ------- HU con progreso por subtareas -------
    tareas_con_metricas = (
        tareas
        .annotate(
            total_st=Count("bloques__subtareas", distinct=True),
            cerradas_st=Count(
                "bloques__subtareas",
                filter=Q(bloques__subtareas__estado__in=["entregada", "cerrada", "COMPLETADO", "completado"]),
                distinct=True,
            ),
        )
        .annotate(
            progreso=Case(
                When(total_st__gt=0, then=100.0 * F("cerradas_st") / F("total_st")),
                default=0.0, output_field=FloatField()
            )
        )
        .order_by("-id")
    )

    # ------- HU por responsable -------
    hu_por_resp = (
        tareas_u
        .values("asignado_a__user__first_name", "asignado_a__user__last_name", "asignado_a_id")
        .annotate(
            total=Count("id", distinct=True),
            new=Count("id", filter=Q(estado_u="NUEVO"), distinct=True),
            inprog=Count("id", filter=Q(estado_u="EN_PROGRESO"), distinct=True),
            blocked=Count("id", filter=Q(estado_u="BLOQUEADO"), distinct=True),
            done=Count("id", filter=Q(estado_u__in=["COMPLETADO", "COMPLETADA"]), distinct=True),
        )
        .order_by("-total")
    )

    # ------- Subtareas: normalización de estado -------
    subtareas_qs = Subtarea.objects.all()
    if sprint_id:
        subtareas_qs = subtareas_qs.filter(bloque__tarea__sprint_id=sprint_id)
    if proyecto_id:
        subtareas_qs = subtareas_qs.filter(bloque__tarea__epica__proyecto_id=proyecto_id)
    if integrante_id:
        subtareas_qs = subtareas_qs.filter(responsable_id=integrante_id)

    st_u = subtareas_qs.annotate(estado_u=Upper("estado"))

    subtareas_stats = st_u.aggregate(
        st_total=Count("id"),
        st_nuevo=Count("id", filter=Q(estado_u__in=["NUEVO", "PENDIENTE"])),
        st_prog=Count("id", filter=Q(estado_u="EN_PROGRESO")),
        st_bloq=Count("id", filter=Q(estado_u="BLOQUEADO")),
        st_comp=Count("id", filter=Q(estado_u__in=["ENTREGADA", "COMPLETADO", "CERRADA"])),
    )

    subtareas_por_responsable = (
        st_u
        .values("responsable__user__first_name", "responsable__user__last_name")
        .annotate(
            nuevo=Sum(Case(When(estado_u__in=["NUEVO", "PENDIENTE"], then=1), default=0, output_field=IntegerField())),
            prog=Sum(Case(When(estado_u="EN_PROGRESO", then=1), default=0, output_field=IntegerField())),
            bloq=Sum(Case(When(estado_u="BLOQUEADO", then=1), default=0, output_field=IntegerField())),
            comp=Sum(Case(When(estado_u__in=["ENTREGADA", "COMPLETADO", "CERRADA"], then=1), default=0, output_field=IntegerField())),
            total=Count("id"),
        )
        .order_by("responsable__user__first_name", "responsable__user__last_name")
    )

    st_res_tot = st_u.aggregate(
        nuevo=Count("id", filter=Q(estado_u__in=["NUEVO", "PENDIENTE"])),
        prog=Count("id", filter=Q(estado_u="EN_PROGRESO")),
        bloq=Count("id", filter=Q(estado_u="BLOQUEADO")),
        comp=Count("id", filter=Q(estado_u__in=["ENTREGADA", "COMPLETADO", "CERRADA"])),
        total=Count("id"),
    )

    # ------- Velocidad por sprint (SP) -------
    ultimos_sprints = list(Sprint.objects.order_by("-inicio")[:5])[::-1]
    vel_labels, vel_planned, vel_done = [], [], []
    for sp in ultimos_sprints:
        qs_sp = Tarea.objects.filter(sprint=sp).annotate(estado_u=Upper("estado"))
        if proyecto_id:
            qs_sp = qs_sp.filter(epica__proyecto_id=proyecto_id)
        vel_labels.append(sp.nombre)
        vel_planned.append(qs_sp.aggregate(Sum("esfuerzo_sp"))["esfuerzo_sp__sum"] or 0)
        vel_done.append(qs_sp.filter(estado_u__in=["COMPLETADO", "COMPLETADA"]).aggregate(Sum("esfuerzo_sp"))["esfuerzo_sp__sum"] or 0)

    # ===============================
    # MÉTRICAS DE DAILY POR INTEGRANTE
    # ===============================
    if scope == "global" or not sprint_id:
        fin_rango = timezone.localdate()
        ini_rango = fin_rango - timedelta(days=29)
    else:
        sp = Sprint.objects.filter(id=sprint_id).first()
        ini_rango = sp.inicio if sp else None
        fin_rango = sp.fin if sp else None

    integrantes = list(Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name"))
    if proyecto_id:
        integ_ids_en_proyecto = (
            Tarea.objects.filter(epica__proyecto_id=proyecto_id)
            .values_list("asignado_a_id", flat=True)
        )
        integrantes = [i for i in integrantes if i.id in set(integ_ids_en_proyecto)]

    total_habiles = _business_days(ini_rango, fin_rango) if (ini_rango and fin_rango) else 0
    tabla_daily = []

    for integ in integrantes:
        dails = Daily.objects.filter(integrante=integ)
        if ini_rango and fin_rango:
            dails = dails.filter(fecha__range=(ini_rango, fin_rango))

        present = dails.count()
        on_time = dails.filter(fuera_horario=False).count()
        delayed = dails.filter(fuera_horario=True).count()
        no_done = max(total_habiles - present, 0)

        alin_ok = 0
        alin_tot = 0
        for d in dails.prefetch_related("items"):
            met = d.alineacion
            alin_ok += met.get("alineados", 0)
            alin_tot += met.get("total", 0)
        efectividad = (100.0 * alin_ok / alin_tot) if alin_tot else 0.0

        participacion = (100.0 * present / total_habiles) if total_habiles else 0.0
        cumplimiento = (100.0 * on_time / total_habiles) if total_habiles else 0.0
        retrasos = (100.0 * delayed / total_habiles) if total_habiles else 0.0
        no_completado = (100.0 * no_done / total_habiles) if total_habiles else 0.0

        nombre = integ.user.get_full_name() or integ.user.username
        tabla_daily.append(dict(
            integrante=nombre.title(),
            cumplimiento=cumplimiento,
            retrasos=retrasos,
            no_completado=no_completado,
            efectividad=efectividad,
            participacion=participacion,
        ))
    tabla_daily.sort(key=lambda r: r["integrante"])

    ctx = {
        "proyectos": Proyecto.objects.filter(activo=True).order_by("codigo"),
        "sprints": Sprint.objects.order_by("-inicio"),
        "sprint_id": int(sprint_id) if sprint_id else None,
        "proyecto_id": int(proyecto_id) if proyecto_id else None,
        "scope": scope,
        "ini_rango": ini_rango,
        "fin_rango": fin_rango,
        "dias_habiles": total_habiles,

        "cards": cards,
        "hu_labels": hu_labels,
        "hu_data": hu_data,
        "hu_por_resp": list(hu_por_resp),

        "tareas": tareas_con_metricas[:25],

        "subtareas_stats": subtareas_stats,
        "subtareas_por_responsable": list(subtareas_por_responsable),
        "st_res_tot": st_res_tot,

        "vel_labels": vel_labels,
        "vel_planned": vel_planned,
        "vel_done": vel_done,

        "tabla_daily": tabla_daily,
    }
    return render(request, "backlog/dashboard_neusi.html", ctx)

# --- KPI VIEWS (macro vs subtareas, sin doble conteo) ---
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.db.models.functions import Upper, Coalesce
from django.utils import timezone
from datetime import timedelta, date
from django.db.models.functions import Coalesce
from django.db.models import Min
from .models import Proyecto, Sprint, Epica, Tarea, Subtarea, Integrante
from django.contrib.auth.models import User


# ====== Helpers para filtros ======
def _get_filters(request):
    uid = request.GET.get("user_id") or None
    sid = request.GET.get("sprint_id") or None
    pid = request.GET.get("proyecto_id") or None
    return uid, sid, pid


def _qs_tareas(uid, sid, pid):
    qs = (Tarea.objects
          .select_related("sprint", "epica__proyecto", "asignado_a")
          .all())
    if sid:
        qs = qs.filter(sprint_id=sid)
    if pid:
        qs = qs.filter(epica__proyecto_id=pid)
    if uid:
        qs = qs.filter(Q(asignado_a_id=uid) | Q(asignados__id=uid)).distinct()
    return qs


def _qs_subtareas(uid, sid, pid):
    qs = (Subtarea.objects
          .select_related("bloque__tarea__sprint", "responsable", "bloque__tarea__epica__proyecto")
          .all())
    if sid:
        qs = qs.filter(bloque__tarea__sprint_id=sid)
    if pid:
        qs = qs.filter(bloque__tarea__epica__proyecto_id=pid)
    if uid:
        qs = qs.filter(responsable_id=uid)
    return qs


def _q_done_tarea():
    return Q(estado__isnull=False) & Q(estado__iregex=r"^(completad[oa])$")


def _q_done_subtarea():
    # ENTREGADA / COMPLETADO / CERRADA
    return Q(estado__isnull=False) & Q(estado__iregex=r"^(entregada|completado|cerrada)$")


# ============================
# KPI INDIVIDUAL (cache 60s)
# ============================
@cache_page(60, key_prefix="kpi_individual")
def kpi_individual_page(request):
    user_id     = request.GET.get("user_id") or None
    sprint_id   = request.GET.get("sprint_id") or None
    proyecto_id = request.GET.get("proyecto_id") or None

    # ===== TAREAS (HU macro) =====
    tareas = (
        Tarea.objects
        .select_related("epica", "epica__proyecto", "sprint", "asignado_a")
        .annotate(estado_u=Upper("estado"))
    )
    if user_id:
        tareas = tareas.filter(Q(asignado_a_id=user_id) | Q(asignados__id=user_id)).distinct()
    if sprint_id:
        tareas = tareas.filter(sprint_id=sprint_id)
    if proyecto_id:
        tareas = tareas.filter(epica__proyecto_id=proyecto_id)

    sp_macro_planned = tareas.aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"] or 0

    # ===== SUBTAREAS =====
    subtareas = (
        Subtarea.objects
        .select_related("bloque", "bloque__tarea", "bloque__tarea__epica", "bloque__tarea__sprint")
        .annotate(estado_u=Upper("estado"))
    )
    if user_id:
        subtareas = subtareas.filter(responsable_id=user_id)
    if sprint_id:
        subtareas = subtareas.filter(bloque__tarea__sprint_id=sprint_id)
    if proyecto_id:
        subtareas = subtareas.filter(bloque__tarea__epica__proyecto_id=proyecto_id)

    st_done_q = subtareas.filter(estado_u__in=["ENTREGADA", "COMPLETADO", "CERRADA"])
    sp_by_sub_done = st_done_q.aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"] or 0

    total_subtareas = subtareas.count()
    done_subtareas  = st_done_q.count()
    tasa_cumplimiento_sub = round(100 * (done_subtareas / total_subtareas), 1) if total_subtareas else 0.0

    vel_map = {}
    for r in st_done_q.values("bloque__tarea__sprint_id").annotate(sp=Coalesce(Sum("esfuerzo_sp"), 0)):
        sid = r["bloque__tarea__sprint_id"]
        vel_map[sid] = vel_map.get(sid, 0) + (r["sp"] or 0)
    velocidad_prom = round(sum(vel_map.values()) / (len(vel_map) or 1), 2)

    st_inicio = (
        Subtarea.objects
        .filter(bloque__tarea__in=tareas, fecha_inicio__isnull=False)
        .values("bloque__tarea_id")
        .annotate(min_inicio=Min("fecha_inicio"))
    )
    inicio_map = {r["bloque__tarea_id"]: r["min_inicio"] for r in st_inicio}

    deltas = []
    for tid, f_cierre in tareas.filter(estado_u__in=["COMPLETADO", "COMPLETADA"]).values_list("id", "fecha_cierre"):
        ini = inicio_map.get(tid)
        if ini and f_cierre:
            ini_dt = timezone.make_aware(timezone.datetime.combine(ini, timezone.datetime.min.time()))
            deltas.append((f_cierre - ini_dt).days)
    tiempo_prom_cierre = round(sum(deltas) / len(deltas), 2) if deltas else None

    bars_labels = ["Planned (macro)", "Done (por Subtareas)"]
    bars_data   = [sp_macro_planned, sp_by_sub_done]

    resumen_rows = [
        ("Tareas (macro) — Planned", sp_macro_planned, ""),
        ("Subtareas — Done",         "",               sp_by_sub_done),
    ]
    resumen_tot = dict(planned=sp_macro_planned, done=sp_by_sub_done)

    ctx = {
        "users": Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name"),
        "sprints": Sprint.objects.order_by("-inicio"),
        "proyectos": Proyecto.objects.order_by("codigo"),
        "user_id": int(user_id) if user_id else None,
        "sprint_id": int(sprint_id) if sprint_id else None,
        "proyecto_id": int(proyecto_id) if proyecto_id else None,

        "tasa_cumplimiento_sub": tasa_cumplimiento_sub,
        "total_subtareas": total_subtareas,
        "done_subtareas": done_subtareas,

        "velocidad_prom": velocidad_prom,
        "tiempo_prom_cierre": tiempo_prom_cierre,

        "bars_labels": bars_labels,
        "bars_data": bars_data,
        "resumen_rows": resumen_rows,
        "resumen_tot": resumen_tot,
    }
    return render(request, "backlog/kpi/individual.html", ctx)

# ============================
# BURNDOWN PERSONAL (cache 60s)
# ============================
from datetime import timedelta  # si no lo tienes ya

def _daterange(start_date, end_date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


@cache_page(60, key_prefix="kpi_burndown")
def kpi_burndown_page(request):
    uid, sid, pid = _get_filters(request)

    # Sprint actual por defecto si no llega sid
    today = timezone.localdate()
    if not sid:
        cur = Sprint.objects.filter(inicio__lte=today, fin__gte=today).order_by("-inicio").first()
    else:
        cur = Sprint.objects.filter(id=sid).first()

    if not cur:
        ctx = dict(
            users=list(Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name")
                      .values("id", "user__first_name", "user__last_name")),
            sprints=Sprint.objects.order_by("-inicio"),
            proyectos=Proyecto.objects.filter(activo=True).order_by("codigo"),
            user_id=int(uid) if uid else None,
            sprint_id=int(sid) if sid else None,
            proyecto_id=int(pid) if pid else None,
            labels=[], planned=[], done=[], remain=[]
        )
        return render(request, "backlog/kpi/burndown.html", ctx)

    tareas = _qs_tareas(uid, cur.id, pid).annotate(estado_u=Upper("estado"))
    subtareas = _qs_subtareas(uid, cur.id, pid).annotate(estado_u=Upper("estado"))

    planned_total = (tareas.aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"]
                     + subtareas.aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"])

    done_by_day = {}
    for t in tareas.filter(_q_done_tarea()):
        d = getattr(t, "fecha_cierre", None)
        if d:
            d = timezone.localdate(d)
            if cur.inicio <= d <= cur.fin:
                done_by_day[d] = done_by_day.get(d, 0) + (t.esfuerzo_sp or 0)

    for s in subtareas.filter(_q_done_subtarea()):
        d = getattr(s, "fecha_fin", None)
        if d and cur.inicio <= d <= cur.fin:
            done_by_day[d] = done_by_day.get(d, 0) + (s.esfuerzo_sp or 0)

    labels, planned, done, remain = [], [], [], []
    cum_done = 0
    for d in _daterange(cur.inicio, cur.fin):
        labels.append(d.strftime("%d-%b"))
        cum_done += done_by_day.get(d, 0)
        done.append(cum_done)
        planned.append(planned_total)
        remain_val = max(planned_total - cum_done, 0)
        remain.append(remain_val)

    ctx = dict(
        users=list(Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name")
                  .values("id", "user__first_name", "user__last_name")),
        sprints=Sprint.objects.order_by("-inicio"),
        proyectos=Proyecto.objects.filter(activo=True).order_by("codigo"),
        user_id=int(uid) if uid else None,
        sprint_id=cur.id,
        proyecto_id=int(pid) if pid else None,
        labels=labels, planned=planned, done=done, remain=remain,
    )
    return render(request, "backlog/kpi/burndown.html", ctx)



# ==================================
# DISTRIBUCIÓN DE ESFUERZO (cache 60s)
# ==================================
@cache_page(60, key_prefix="kpi_esfuerzo")
def kpi_esfuerzo_page(request):
    user_id     = request.GET.get("user_id") or None
    sprint_id   = request.GET.get("sprint_id") or None
    proyecto_id = request.GET.get("proyecto_id") or None

    tareas = Tarea.objects.annotate(estado_u=Upper("estado"))
    if user_id:
        tareas = tareas.filter(Q(asignado_a_id=user_id) | Q(asignados__id=user_id)).distinct()
    if sprint_id:
        tareas = tareas.filter(sprint_id=sprint_id)
    if proyecto_id:
        tareas = tareas.filter(epica__proyecto_id=proyecto_id)

    subtareas = Subtarea.objects.annotate(estado_u=Upper("estado"))
    if user_id:
        subtareas = subtareas.filter(responsable_id=user_id)
    if sprint_id:
        subtareas = subtareas.filter(bloque__tarea__sprint_id=sprint_id)
    if proyecto_id:
        subtareas = subtareas.filter(bloque__tarea__epica__proyecto_id=proyecto_id)

    planned_macro = tareas.aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"] or 0
    done_by_sub   = subtareas.filter(estado_u__in=["ENTREGADA","COMPLETADO","CERRADA"])\
                             .aggregate(v=Coalesce(Sum("esfuerzo_sp"), 0))["v"] or 0

    labels = ["Planned (macro)", "Done por Subtareas"]
    data   = [planned_macro, done_by_sub]

    rows = [
        ("Tareas (macro) — Planned", planned_macro, ""),
        ("Subtareas — Done", "", done_by_sub),
        ("TOTAL (comparativo)", planned_macro, done_by_sub),
    ]

    ctx = {
        "users": Integrante.objects.select_related("user").order_by("user__first_name","user__last_name"),
        "sprints": Sprint.objects.order_by("-inicio"),
        "proyectos": Proyecto.objects.order_by("codigo"),
        "user_id": int(user_id) if user_id else None,
        "sprint_id": int(sprint_id) if sprint_id else None,
        "proyecto_id": int(proyecto_id) if proyecto_id else None,

        "labels": labels,
        "data": data,
        "rows": rows,
        "planned_macro": planned_macro,
        "done_by_sub": done_by_sub,
    }
    return render(request, "backlog/kpi/esfuerzo.html", ctx)
