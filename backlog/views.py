from functools import wraps
from datetime import time, datetime, timedelta
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import JsonResponse
from django.utils.timezone import localtime, now
from django.db.models import Q, Count
from django.core.paginator import Paginator

from .models import Tarea, Sprint, Integrante, Daily, Evidencia, Epica, Proyecto
from .forms import (
    TareaForm, DailyForm, EvidenciaForm, SprintForm, EpicaForm, ProyectoForm
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

# ==============================
# Scope por proyectos (Visualizador / Product Owner)
# ==============================

def _proyectos_autorizados_qs(integrante: Integrante):
    """
    QS de proyectos visibles para el integrante según PermisoProyecto.
    Requiere que PermisoProyecto tenga: proyecto(FK)->related_name='permisos_integrantes'
    y un booleano 'activo'. Ajusta el related_name si usaste otro.
    """
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
    """Restringe Tarea por proyectos autorizados (vía epica__proyecto) para visualizadores/PO."""
    if not integrante or not integrante.es_visualizador():
        return qs
    proys = _proyectos_autorizados_qs(integrante)
    if not proys.exists():
        return qs.none()
    return qs.filter(epica__proyecto__in=proys).distinct()

def _filtrar_por_proyectos_autorizados_epicas(qs, integrante: Integrante):
    """Restringe Epica por proyecto para visualizadores/PO."""
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
    """
    Verdadero si el integrante está asignado a la tarea
    (ya sea por el M2M `asignados` o por el FK legado `asignado_a`).
    """
    if not integrante:
        return False
    if tarea.asignado_a_id == getattr(integrante, "id", None):
        return True
    return tarea.asignados.filter(id=integrante.id).exists()

def _queryset_visible_tareas(integrante: Integrante, puede_ver_todo: bool):
    """
    Construye el queryset base de tareas según permisos:
    - Admin: ve todo.
    - Visualizador/PO: SOLO tareas de sus proyectos autorizados.
    - Usuario normal: solo tareas que le corresponden (M2M o FK).
    """
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

    # Miembro normal → solo lo propio
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

# Nota: mantenemos este decorador pero NO lo usamos en evidencias;
# los checks se hacen dentro de cada vista para permitir responsable/admin/permisos.
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
# Vistas de Tareas
# ==============================

@login_required
def editar_tarea(request, tarea_id):
    """Editar una tarea existente (admin o responsable o rol con puede_editar_tareas)."""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    es_responsable = _es_responsable(tarea, integrante)
    puede_editar_rol = bool(integrante and integrante.puede_editar_tareas())

    if not (es_admin or es_responsable or puede_editar_rol):
        messages.error(request, "❌ No tienes permisos para editar tareas.")
        return redirect("backlog_lista")

    if request.method == "POST":
        form = TareaForm(request.POST, request.FILES, instance=tarea)
        if form.is_valid():
            tarea_actualizada = form.save()
            messages.success(request, f"✅ Tarea '{tarea_actualizada.titulo}' actualizada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = TareaForm(instance=tarea)

    return render(request, "backlog/editar_tarea.html", {"form": form, "tarea": tarea})

@login_required
@requiere_permiso_crear_tareas
def nueva_tarea(request):
    """Crear una nueva tarea en el backlog"""
    if request.method == "POST":
        form = TareaForm(request.POST, request.FILES)
        if form.is_valid():
            tarea = form.save()
            messages.success(request, f"✅ Tarea '{tarea.titulo}' creada correctamente.")
            return redirect("backlog_lista")
        else:
            messages.error(request, "⚠️ Revisa los campos del formulario.")
    else:
        form = TareaForm()
    return render(request, "backlog/nueva_tarea.html", {"form": form})

@login_required
def detalle_tarea(request, tarea_id):
    """Vista detallada de una tarea con evidencias y permisos según rol"""
    tarea = get_object_or_404(
        Tarea.objects.select_related("sprint", "epica").prefetch_related("asignados__user"),
        id=tarea_id
    )

    evidencias = tarea.evidencias.all().order_by("-creado_en")
    form = EvidenciaForm()

    integrante, es_admin, _, _ = _flags_usuario(request)

    # Es responsable si está en la lista M2M o es el asignado principal
    es_responsable = _es_responsable(tarea, integrante)

    # Definir permisos efectivos
    puede_editar = bool(es_admin or es_responsable or (integrante and integrante.puede_editar_tareas()))
    puede_cerrar = bool(es_admin or es_responsable)

    return render(request, "backlog/detalle_tarea.html", {
        "tarea": tarea,
        "evidencias": evidencias,
        "form": form,
        "tiene_permisos_admin": es_admin,
        "puede_editar": puede_editar,
        "puede_cerrar": puede_cerrar,
    })

# -------- Evidencias (sin decorador restrictivo) --------

@login_required
def agregar_evidencia(request, tarea_id):
    """Agregar evidencia a una tarea (admin, responsable o rol con permiso)."""
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
    """Editar evidencia (admin, responsable o rol con permiso)."""
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
    """Eliminar evidencia (admin, creador, o responsable de la tarea)."""
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
    """Cerrar una tarea con informe obligatorio (responsable o admin)"""
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

@login_required
def daily_view(request, integrante_id=None):
    # Visualizador no registra dailies
    _, es_admin, es_visualizador, _ = _flags_usuario(request)
    if es_visualizador:
        messages.warning(request, "El rol Visualizador no puede registrar dailies.")
        return redirect("daily_resumen")

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
    hora_actual = localtime().time()

    if request.method == "POST":
        form = DailyForm(request.POST)
        if form.is_valid():
            daily, created = Daily.objects.get_or_create(
                integrante=integrante,
                fecha=fecha_actual,
                defaults=form.cleaned_data
            )
            if not created:
                for field, value in form.cleaned_data.items():
                    setattr(daily, field, value)

            if not en_ventana_daily(hora_actual):
                daily.fuera_horario = True
                messages.warning(
                    request,
                    "⚠️ Daily registrado fuera del horario (5:00–9:00 AM). "
                    "Se notificará a los administradores y se tomará como evidencia."
                )
            else:
                daily.fuera_horario = False
                messages.success(request, "✅ Daily registrado correctamente en horario.")

            daily.save()
            return redirect("daily_resumen")
    else:
        try:
            daily_existente = Daily.objects.get(integrante=integrante, fecha=fecha_actual)
            form = DailyForm(instance=daily_existente)
        except Daily.DoesNotExist:
            form = DailyForm()

    return render(request, "backlog/daily_form.html", {
        "form": form,
        "integrante": integrante,
        "fecha_actual": localtime().strftime("%Y-%m-%d %H:%M"),
    })

@login_required
def daily_personal(request):
    # Visualizador: redirige a resumen directamente
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
    puede_filtrar = es_admin or es_visualizador  # admin y visualizador pueden filtrar/ver

    fecha_limite = datetime.now().date() - timedelta(days=7)

    if not puede_filtrar:
        # Usuario normal: solo sus dailies
        registros = Daily.objects.filter(integrante=integrante, fecha__gte=fecha_limite).order_by("-fecha") if integrante else Daily.objects.none()
        integrantes = []
        persona_id = None
    else:
        if es_admin:
            # Admin ve todo
            registros = Daily.objects.select_related("integrante__user").filter(fecha__gte=fecha_limite).order_by("-fecha")
            integrantes = Integrante.objects.select_related("user").all().order_by("user__first_name", "user__last_name")
        else:
            # Visualizador/PO: restringir por proyectos autorizados
            proyectos = _proyectos_autorizados_qs(integrante)
            if not proyectos.exists():
                registros = Daily.objects.none()
                integrantes = []
            else:
                ids_legacy = Tarea.objects.filter(epica__proyecto__in=proyectos).values_list("asignado_a_id", flat=True)
                ids_m2m = Tarea.objects.filter(epica__proyecto__in=proyectos).values_list("asignados__id", flat=True)
                ids_integrantes = {i for i in list(ids_legacy) + list(ids_m2m) if i is not None}

                registros = (
                    Daily.objects
                    .select_related("integrante__user")
                    .filter(integrante_id__in=ids_integrantes, fecha__gte=fecha_limite)
                    .order_by("-fecha")
                )
                integrantes = (
                    Integrante.objects
                    .select_related("user")
                    .filter(id__in=ids_integrantes)
                    .order_by("user__first_name", "user__last_name")
                )

        # Filtro por persona (respetando scope)
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                pid = int(persona_id)
                registros = registros.filter(integrante__id=pid)
            except (ValueError, Integrante.DoesNotExist):
                pass

    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
        "tiene_permisos_admin": es_admin,
        "puede_filtrar": puede_filtrar,
        "persona_id": persona_id if puede_filtrar else None,
    })

# ==============================
# Backlog
# ==============================
@login_required
def backlog_lista(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    # Conmutador de agrupación (proyecto | epica | sprint | none)
    group_by  = request.GET.get("group", "epica")
    expand_id = request.GET.get("expand")  # id del grupo a expandir (para "ver más")

    # Base visible
    tareas = (
        _queryset_visible_tareas(integrante, puede_ver_todo)
        .select_related("sprint", "epica", "epica__proyecto")
        .prefetch_related("asignados__user")
    )

    # Listas para filtros (acotadas para visualizador)
    sprints = Sprint.objects.all().order_by("inicio")

    if puede_ver_todo:
        # Integrantes visibles: derivados de las tareas visibles (evita ver gente fuera del scope)
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

        # Épicas visibles
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

    # Filtros (solo si presiona “Filtrar”)
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

    # Orden estable según agrupación
    if group_by == "proyecto":
        tareas = tareas.order_by("epica__proyecto__nombre", "sprint__inicio", "categoria", "titulo")
    elif group_by == "epica":
        tareas = tareas.order_by("epica__titulo", "sprint__inicio", "categoria", "titulo")
    elif group_by == "sprint":
        tareas = tareas.order_by("sprint__inicio", "categoria", "titulo")
    else:
        tareas = tareas.order_by("sprint__inicio", "categoria", "titulo")

    # Agrupación / Paginación
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
            else:  # sprint
                k = t.sprint
            grouped.setdefault(k, []).append(t)
        # Sin paginación global en modo agrupado (usamos "ver más" por grupo)
    else:
        paginator = Paginator(tareas, PAGE_SIZE)
        page_number = request.GET.get("page")
        tareas = paginator.get_page(page_number)

    return render(request, "backlog/backlog_lista.html", {
        "tareas": tareas,                   # page o queryset
        "grouped": grouped,                 # dict o None
        "group_by": group_by,
        "expand_id": expand_id,
        "paginator": paginator,             # solo en modo plano
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

@login_required
def backlog_matriz(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    tareas = _queryset_visible_tareas(integrante, puede_ver_todo)
    integrantes = []
    persona_id = request.GET.get("persona")

    if puede_ver_todo:
        # Integrantes visibles derivados de tareas visibles si es visualizador
        ids_a = tareas.values_list("asignado_a_id", flat=True)
        ids_m = tareas.values_list("asignados__id", flat=True)
        ids_set = {i for i in list(ids_a) + list(ids_m) if i is not None}
        integrantes = (
            Integrante.objects.select_related("user")
            .filter(id__in=ids_set) if es_visualizador else
            Integrante.objects.select_related("user").all()
        ).order_by("user__first_name", "user__last_name")

        if persona_id:
            try:
                pid = int(persona_id)
                tareas = tareas.filter(Q(asignados__id=pid) | Q(asignado_a__id=pid)).distinct()
            except ValueError:
                pass

    cuadrantes = {
        "ui":   tareas.filter(categoria__iexact="UI"),
        "nui":  tareas.filter(categoria__iexact="NUI"),
        "uni":  tareas.filter(categoria__iexact="UNI"),
        "nuni": tareas.filter(categoria__iexact="NUNI"),
    }

    return render(request, "backlog/backlog_matriz.html", {
        **cuadrantes,
        "integrantes": integrantes,
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
        "persona_id": persona_id,
    })

# ==============================
# Checklist de tareas
# ==============================

@login_required
def checklist_view(request, integrante_id):
    """Checklist de tareas pendientes de un integrante"""
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
    """Permite a un administrador registrar un Daily para cualquier integrante"""
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
    """Eliminar una tarea - solo para administradores"""
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
# Kanban (con épicas en contexto)
# ==============================

@login_required
def kanban_board(request):
    """Vista Kanban con estados de workflow"""
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)
    tareas = _queryset_visible_tareas(integrante, puede_ver_todo)

    persona_id = request.GET.get("persona") if puede_ver_todo else None
    epica_id = request.GET.get("epica") if puede_ver_todo else None

    if persona_id and puede_ver_todo:
        try:
            pid = int(persona_id)
            tareas = tareas.filter(Q(asignados__id=pid) | Q(asignado_a__id=pid)).distinct()
        except ValueError:
            pass
    if epica_id and puede_ver_todo:
        try:
            tareas = tareas.filter(epica__id=int(epica_id))
        except ValueError:
            pass

    if puede_ver_todo:
        # Integrantes del scope (si es visualizador) o todos (si admin)
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
        ).distinct()

    estados = {
        "nuevo":        tareas.filter(estado__iexact="NUEVO"),
        "aprobado":     tareas.filter(estado__iexact="APROBADO"),
        "en_progreso":  tareas.filter(estado__iexact="EN_PROGRESO"),
        "completado":   tareas.filter(estado__iexact="COMPLETADO"),
        "bloqueado":    tareas.filter(estado__iexact="BLOQUEADO"),
    }

    return render(request, "backlog/kanban_board.html", {
        **estados,
        "integrantes": integrantes,
        "epicas": epicas,
        "persona_id": persona_id if puede_ver_todo else None,
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
    })

@login_required
def cambiar_estado_tarea(request, tarea_id):
    """API para cambiar el estado de una tarea (drag & drop Kanban)"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    tarea = get_object_or_404(Tarea, id=tarea_id)
    integrante, es_admin, _, _ = _flags_usuario(request)

    if not es_admin and not _es_responsable(tarea, integrante):
        return JsonResponse({"error": "Solo responsables o administradores pueden mover la tarea"}, status=403)

    try:
        data = json.loads(request.body)
        nuevo_estado = data.get("estado", "").upper()
        estados_validos = ["NUEVO", "APROBADO", "EN_PROGRESO", "COMPLETADO", "BLOQUEADO"]
        if nuevo_estado not in estados_validos:
            return JsonResponse({"error": "Estado no válido"}, status=400)

        tarea.estado = nuevo_estado
        if nuevo_estado == "COMPLETADO":
            tarea.completada = True
            if not tarea.fecha_cierre:
                tarea.fecha_cierre = now()
        tarea.save()

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
    """
    API para cambiar la categoría (UI/NUI/UNI/NUNI) desde la matriz de Eisenhower.
    """
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
    """
    Lista todas las épicas visibles para el usuario actual.
    - Admin: ve todas
    - Visualizador/PO: solo proyectos autorizados
    - Miembros normales: épicas donde participan
    - Permite filtrar por proyecto (FK normalizado).
    """
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

    # Proyectos listados en el filtro
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
            epica = form.save()  # incluye M2M y owner
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
    """
    Muestra el detalle de una épica:
    - Datos de la épica (proyecto, owners, sprints, KPIs)
    - Tareas asociadas
    - Avance calculado o manual
    - Validación de permisos
    """
    integrante, es_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    epica = (
        Epica.objects
        .select_related("owner", "proyecto")
        .prefetch_related("owners__user", "sprints")
        .get(pk=epica_id)
    )

    # Visualizador/PO: validar scope de proyecto
    if es_visualizador and not es_admin:
        proyectos = _proyectos_autorizados_qs(integrante)
        if not proyectos.filter(id=getattr(epica.proyecto, "id", None)).exists():
            messages.error(request, "❌ No tienes permisos para ver esta épica.")
            return redirect("epica_list")

    # Miembro normal: validar si participa
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

    # ===== Tareas asociadas =====
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
        "APROBADO": tareas_qs.filter(estado__iexact="APROBADO"),
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
