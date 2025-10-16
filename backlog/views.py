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

from .models import Tarea, Sprint, Integrante, Daily, Evidencia, Epica
from .forms import TareaForm, DailyForm, EvidenciaForm, SprintForm, EpicaForm

# ==============================
# Helpers de permisos
# ==============================

def _es_admin(request):
    integrante = getattr(request.user, "integrante", None)
    return bool(integrante and integrante.puede_crear_tareas())

def _flags_usuario(request):
    """
    Devuelve:
      - integrante: Integrante|None
      - puede_admin: bool (Scrum/PO)
      - es_visualizador: bool
      - puede_ver_todo: bool (Scrum/PO o Visualizador)
    """
    integrante = getattr(request.user, "integrante", None)
    puede_admin = bool(integrante and integrante.puede_crear_tareas())
    es_visualizador = bool(integrante and getattr(integrante, "es_visualizador", lambda: False)())
    puede_ver_todo = bool(puede_admin or es_visualizador)
    return integrante, puede_admin, es_visualizador, puede_ver_todo

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
# Vistas de Tareas
# ==============================

@login_required
def editar_tarea(request, tarea_id):
    """Editar una tarea existente (solo admin)"""
    tarea = get_object_or_404(Tarea, id=tarea_id)

    try:
        if not request.user.integrante.puede_crear_tareas():
            messages.error(request, "❌ No tienes permisos para editar tareas.")
            return redirect("backlog_lista")
    except AttributeError:
        messages.error(request, "❌ No tienes un perfil de integrante asociado.")
        return redirect("home")

    if request.method == "POST":
        form = TareaForm(request.POST, instance=tarea)
        if form.is_valid():
            tarea_actualizada = form.save()
            messages.success(request, f"✅ Tarea '{tarea_actualizada.titulo}' actualizada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
    else:
        form = TareaForm(instance=tarea)

    return render(request, "backlog/editar_tarea.html", {"form": form, "tarea": tarea})

@login_required
@requiere_permiso_crear_tareas
def nueva_tarea(request):
    """Crear una nueva tarea en el backlog"""
    if request.method == "POST":
        form = TareaForm(request.POST)
        if form.is_valid():
            tarea = form.save()
            messages.success(request, f"✅ Tarea '{tarea.titulo}' creada correctamente.")
            return redirect("backlog_lista")
    else:
        form = TareaForm()
    return render(request, "backlog/nueva_tarea.html", {"form": form})

@login_required
def detalle_tarea(request, tarea_id):
    """Vista detallada de una tarea con evidencias"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencias = tarea.evidencias.all().order_by("-creado_en")
    form = EvidenciaForm()
    return render(request, "backlog/detalle_tarea.html", {
        "tarea": tarea,
        "evidencias": evidencias,
        "form": form,
    })

@login_required
@requiere_permiso_evidencias
def agregar_evidencia(request, tarea_id):
    """Agregar evidencia a una tarea"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
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
@requiere_permiso_evidencias
def editar_evidencia(request, tarea_id, evidencia_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencia = get_object_or_404(Evidencia, id=evidencia_id, tarea=tarea)
    if request.method == "POST":
        form = EvidenciaForm(request.POST, request.FILES, instance=evidencia)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Evidencia editada correctamente.")
            return redirect("detalle_tarea", tarea_id=tarea.id)
    else:
        form = EvidenciaForm(instance=evidencia)
    return render(request, "backlog/editar_evidencia.html", {
        "form": form, "evidencia": evidencia, "tarea": tarea,
    })

@login_required
def cerrar_tarea(request, tarea_id):
    """Cerrar una tarea con informe obligatorio (solo dueño de la tarea)"""
    tarea = get_object_or_404(Tarea, id=tarea_id)

    if tarea.asignado_a and tarea.asignado_a.user != request.user:
        messages.error(request, "❌ Solo puedes cerrar tus propias tareas.")
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
    integrante = getattr(request.user, "integrante", None)
    tiene_permisos_admin = bool(integrante and integrante.puede_crear_tareas())
    es_visualizador = bool(integrante and getattr(integrante, "es_visualizador", lambda: False)())
    puede_ver_todo = bool(tiene_permisos_admin or es_visualizador)

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
    # ❌ Visualizador no registra dailies
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

            if not (time(7, 0) <= hora_actual <= time(9, 0)):
                daily.fuera_horario = True
                messages.warning(request,
                    "⚠️ Daily registrado fuera del horario (7:00–9:00 AM). "
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
    # ❌ Visualizador: redirige a resumen directamente
    integrante, _, es_visualizador, _ = _flags_usuario(request)
    if es_visualizador:
        messages.info(request, "Eres Visualizador: solo puedes consultar dailies.")
        return redirect("daily_resumen")

    if not integrante:
        integrante, _ = Integrante.objects.get_or_create(
            user=request.user,
            defaults={'rol': 'Miembro'}
        )
        messages.info(request, "Se creó tu perfil de integrante automáticamente.")
    return daily_view(request, integrante.id)

@login_required
def daily_resumen(request):
    integrante, es_admin, es_visualizador, _ = _flags_usuario(request)
    puede_filtrar = es_admin or es_visualizador  # ← admin y visualizador pueden filtrar/ver todo

    if puede_filtrar:
        registros = Daily.objects.select_related("integrante__user").order_by("-fecha")
        integrantes = Integrante.objects.select_related("user").all().order_by(
            "user__first_name", "user__last_name"
        )
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                registros = registros.filter(integrante__id=int(persona_id))
            except (ValueError, Integrante.DoesNotExist):
                pass
    else:
        registros = Daily.objects.filter(integrante=integrante).order_by("-fecha") if integrante else Daily.objects.none()
        integrantes = []
        persona_id = None

    fecha_limite = datetime.now().date() - timedelta(days=7)
    registros = registros.filter(fecha__gte=fecha_limite)

    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
        "tiene_permisos_admin": es_admin,   # sigue controlando el botón Eliminar
        "puede_filtrar": puede_filtrar,     # ← nuevo flag para el template
        "persona_id": persona_id,
    })

# ==============================
# Backlog
# ==============================
@login_required
def backlog_lista(request):
    integrante, tiene_permisos_admin, es_visualizador, puede_ver_todo = _flags_usuario(request)

    # Base visible (admin o visualizador ven TODO)
    if puede_ver_todo:
        tareas = Tarea.objects.all().select_related("asignado_a__user", "sprint", "epica")
        integrantes = (
            Integrante.objects
            .filter(id__in=Tarea.objects.exclude(asignado_a__isnull=True)
                                     .values_list("asignado_a_id", flat=True))
            .select_related("user")
            .distinct()
            .order_by("user__first_name", "user__last_name")
        )
        epicas = Epica.objects.filter(tareas__isnull=False).distinct().order_by("titulo")
    else:
        tareas = (Tarea.objects
                  .filter(asignado_a=integrante)
                  .select_related("sprint", "epica")) if integrante else Tarea.objects.none()
        integrantes = []
        epicas = Epica.objects.filter(tareas__asignado_a=integrante).distinct()

    sprints = Sprint.objects.all().order_by("inicio")

    # Filtros solo si presiona “Filtrar”
    aplicar_filtros = request.GET.get("filtrar") == "1"
    persona_id = request.GET.get("persona") if aplicar_filtros else None
    sprint_id  = request.GET.get("sprint")  if aplicar_filtros else None
    estado     = request.GET.get("estado")  if aplicar_filtros else None
    epica_id   = request.GET.get("epica")   if aplicar_filtros else None

    if aplicar_filtros:
        if persona_id:
            try: tareas = tareas.filter(asignado_a__id=int(persona_id))
            except ValueError: pass
        if sprint_id:
            try: tareas = tareas.filter(sprint__id=int(sprint_id))
            except ValueError: pass
        if epica_id:
            try: tareas = tareas.filter(epica__id=int(epica_id))
            except ValueError: pass
        if estado == "abiertas":
            tareas = tareas.filter(completada=False)
        elif estado == "cerradas":
            tareas = tareas.filter(completada=True)

    tareas = tareas.order_by("sprint__inicio", "categoria", "titulo")

    return render(request, "backlog/backlog_lista.html", {
        "tareas": tareas,
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

    if puede_ver_todo:
        tareas = Tarea.objects.all().select_related("asignado_a__user", "sprint", "epica")
        integrantes = Integrante.objects.all()
        persona_id = request.GET.get("persona")
        if persona_id:
            tareas = tareas.filter(asignado_a__id=persona_id)
    else:
        tareas = Tarea.objects.filter(asignado_a=integrante).select_related("sprint", "epica") if integrante else Tarea.objects.none()
        integrantes = []

    cuadrantes = {
        "ui": tareas.filter(categoria="UI"),
        "nui": tareas.filter(categoria="NUI"),
        "uni": tareas.filter(categoria="UNI"),
        "nuni": tareas.filter(categoria="NUNI"),
    }

    return render(request, "backlog/backlog_matriz.html", {
        **cuadrantes,
        "integrantes": integrantes,
        "tiene_permisos_admin": tiene_permisos_admin,
        "puede_ver_todo": puede_ver_todo,
        "persona_id": request.GET.get("persona"),
    })

# ==============================
# Checklist de tareas
# ==============================

@login_required
def checklist_view(request, integrante_id):
    """Checklist de tareas pendientes de un integrante"""
    integrante = get_object_or_404(Integrante, id=integrante_id)

    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if not tiene_permisos_admin and integrante != usuario_integrante:
        messages.error(request, "❌ No puedes ver el checklist de otro integrante.")
        return redirect("backlog_lista")

    tareas = (Tarea.objects
              .filter(asignado_a=integrante, completada=False)
              .select_related("sprint")
              .order_by("sprint__inicio", "categoria"))

    return render(request, "backlog/checklist.html", {
        "integrante": integrante,
        "tareas": tareas,
    })

@login_required
@requiere_permiso_evidencias
def eliminar_evidencia(request, tarea_id, evidencia_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencia = get_object_or_404(Evidencia, id=evidencia_id, tarea=tarea)

    if evidencia.creado_por != request.user and not request.user.integrante.puede_crear_tareas():
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
def eliminar_daily(request, daily_id):
    daily = get_object_or_404(Daily, id=daily_id)

    try:
        if not request.user.integrante.puede_crear_tareas():
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
        tiene_permisos_admin = request.user.integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False

    sprints = Sprint.objects.all().order_by("inicio")
    return render(request, "backlog/sprint_list.html", {
        "sprints": sprints,
        "tiene_permisos_admin": tiene_permisos_admin,
    })

@login_required
def sprint_create(request):
    if not request.user.integrante.puede_crear_tareas():
        messages.error(request, "❌ No tienes permisos para crear sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        form = SprintForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Sprint creado correctamente.")
            return redirect("sprint_list")
    else:
        form = SprintForm()

    return render(request, "backlog/sprint_form.html", {"form": form, "modo": "crear"})

@login_required
def sprint_edit(request, sprint_id):
    sprint = get_object_or_404(Sprint, id=sprint_id)

    if not request.user.integrante.puede_crear_tareas():
        messages.error(request, "❌ No tienes permisos para editar sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        form = SprintForm(request.POST, instance=sprint)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Sprint actualizado correctamente.")
            return redirect("sprint_list")
    else:
        form = SprintForm(instance=sprint)
    return render(request, "backlog/sprint_form.html", {"form": form})

@login_required
def sprint_delete(request, sprint_id):
    sprint = get_object_or_404(Sprint, id=sprint_id)

    if not request.user.integrante.puede_crear_tareas():
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
        if not request.user.integrante.puede_crear_tareas():
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
            if not (time(7, 0) <= hora_actual <= time(9, 0)):
                daily.fuera_horario = True
            daily.save()
            messages.success(request, f"✅ Daily registrado para {integrante.user.first_name}.")
            return redirect("daily_resumen")
    else:
        form = DailyForm()

    integrantes = Integrante.objects.all()
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
        if not request.user.integrante.puede_crear_tareas():
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

    if puede_ver_todo:
        tareas = Tarea.objects.all().select_related("asignado_a__user", "sprint", "epica")
        integrantes = Integrante.objects.all()
        epicas = Epica.objects.all()
        persona_id = request.GET.get("persona")
        epica_id = request.GET.get("epica")
        if persona_id:
            tareas = tareas.filter(asignado_a__id=persona_id)
        if epica_id:
            tareas = tareas.filter(epica__id=epica_id)
    else:
        tareas = Tarea.objects.filter(asignado_a=integrante).select_related("sprint", "epica") if integrante else Tarea.objects.none()
        integrantes = []
        epicas = Epica.objects.filter(tareas__asignado_a=integrante).distinct()
        persona_id = None

    estados = {
        "nuevo": tareas.filter(estado="NUEVO"),
        "aprobado": tareas.filter(estado="APROBADO"),
        "en_progreso": tareas.filter(estado="EN_PROGRESO"),
        "completado": tareas.filter(estado="COMPLETADO"),
        "bloqueado": tareas.filter(estado="BLOQUEADO"),
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

    try:
        usuario_integrante = request.user.integrante
        es_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        return JsonResponse({"error": "No tienes perfil de integrante"}, status=403)

    if not es_admin and tarea.asignado_a != usuario_integrante:
        return JsonResponse({"error": "Solo puedes mover tus propias tareas"}, status=403)

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

    try:
        usuario_integrante = request.user.integrante
        es_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        return JsonResponse({"error": "No tienes perfil de integrante"}, status=403)

    if not es_admin and tarea.asignado_a != usuario_integrante:
        return JsonResponse({"error": "Solo puedes mover tus propias tareas"}, status=403)

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

    if puede_ver_todo:
        epicas = (Epica.objects
                  .select_related("owner")
                  .prefetch_related("sprints")
                  .order_by("-creada_en"))
    else:
        if integrante:
            epicas = (Epica.objects
                      .filter(tareas__asignado_a=integrante)
                      .select_related("owner")
                      .prefetch_related("sprints")
                      .distinct()
                      .order_by("-creada_en"))
        else:
            epicas = Epica.objects.none()

    return render(request, "backlog/epica_list.html", {"epicas": epicas, "admin": admin})

@login_required
def epica_create(request):
    if not _es_admin(request):
        messages.error(request, "❌ No tienes permisos para crear épicas.")
        return redirect("epica_list")

    if request.method == "POST":
        form = EpicaForm(request.POST)
        if form.is_valid():
            epica = form.save(commit=False)
            epica.save()
            form.save_m2m()  # M2M sprints
            messages.success(request, "✅ Épica creada correctamente.")
            return redirect("epica_detail", epica_id=epica.id)
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
            epica = form.save(commit=False)
            epica.save()
            form.save_m2m()  # M2M sprints
            messages.success(request, "✏️ Épica actualizada correctamente.")
            return redirect("epica_detail", epica_id=epica.id)
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
        messages.success(request, f"🗑️ Épica '{titulo}' eliminada.")
        return redirect("epica_list")

    return render(request, "backlog/epica_confirm_delete.html", {"epica": epica})

@login_required
def epica_detail(request, epica_id):
    epica = (Epica.objects
             .select_related("owner")
             .prefetch_related("sprints")
             .get(pk=epica_id))

    tareas = (epica.tareas
              .select_related("asignado_a__user", "sprint")
              .order_by("estado", "categoria", "titulo"))

    return render(request, "backlog/epica_detail.html", {
        "epica": epica,
        "tareas": tareas,
    })
