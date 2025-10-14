from functools import wraps
from datetime import time, datetime, timedelta

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
    """Editar una tarea existente"""
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
    evidencias = tarea.evidencias.all().order_by("-creado_en")  # ✅ corregido
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
        "form": form,
        "evidencia": evidencia,
        "tarea": tarea,
    })


@login_required
def cerrar_tarea(request, tarea_id):
    """Cerrar una tarea con informe obligatorio"""
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
    return render(request, "backlog/home.html")


# ==============================
# Daily
# ==============================

@login_required
def daily_view(request, integrante_id=None):
    if integrante_id is None:
        try:
            integrante = request.user.integrante
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
    else:
        integrante = get_object_or_404(Integrante, id=integrante_id)
        if integrante.user != request.user:
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

            # 🚨 Verificar si es fuera de horario (7 a 9 am)
            if not (time(7, 0) <= hora_actual <= time(9, 0)):
                daily.fuera_horario = True
                messages.warning(
                    request,
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
    integrante = getattr(request.user, 'integrante', None)
    if not integrante:
        integrante, _ = Integrante.objects.get_or_create(
            user=request.user,
            defaults={'rol': 'Miembro'}
        )
        messages.info(request, "Se creó tu perfil de integrante automáticamente.")
    return daily_view(request, integrante.id)


@login_required
def daily_resumen(request):
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if tiene_permisos_admin:
        registros = Daily.objects.select_related("integrante__user").order_by("-fecha")
        integrantes = Integrante.objects.all()
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                registros = registros.filter(integrante__id=persona_id)
            except (Integrante.DoesNotExist, ValueError):
                pass
    else:
        registros = Daily.objects.filter(integrante=usuario_integrante).order_by("-fecha") if usuario_integrante else Daily.objects.none()
        integrantes = []

    fecha_limite = datetime.now().date() - timedelta(days=7)
    registros = registros.filter(fecha__gte=fecha_limite)

    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
        "tiene_permisos_admin": tiene_permisos_admin,
    })


# ==============================
# Backlog
# ==============================

@login_required
def backlog_lista(request):
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if tiene_permisos_admin:
        tareas = Tarea.objects.all().select_related("asignado_a", "sprint", "epica")
        integrantes = Integrante.objects.all()
        epicas = Epica.objects.all()
    else:
        tareas = Tarea.objects.filter(asignado_a=usuario_integrante).select_related("sprint", "epica") if usuario_integrante else Tarea.objects.none()
        integrantes = []
        epicas = Epica.objects.filter(tareas__asignado_a=usuario_integrante).distinct()

    sprints = Sprint.objects.all()

    # ✅ CAPTURAR PARÁMETROS DE LOS FILTROS
    persona_id = request.GET.get("persona")
    sprint_id = request.GET.get("sprint")
    estado = request.GET.get("estado")
    epica_id = request.GET.get("epica")

    # ✅ FILTRAR POR PERSONA
    if persona_id and persona_id != "":
        try:
            tareas = tareas.filter(asignado_a__id=persona_id)
        except (ValueError, Integrante.DoesNotExist):
            pass

    # ✅ FILTRAR POR SPRINT
    if sprint_id and sprint_id != "":
        try:
            tareas = tareas.filter(sprint__id=sprint_id)
        except (ValueError, Sprint.DoesNotExist):
            pass

    # ✅ FILTRAR POR ÉPICA
    if epica_id and epica_id != "":
        try:
            tareas = tareas.filter(epica__id=epica_id)
        except (ValueError, Epica.DoesNotExist):
            pass

    # ✅ FILTRAR POR ESTADO (abiertas/cerradas)
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
        "estado": estado,
        "persona_id": persona_id,
        "sprint_id": sprint_id,
        "epica_id": epica_id,
        "tiene_permisos_admin": tiene_permisos_admin,
    })


@login_required
def backlog_matriz(request):
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if tiene_permisos_admin:
        tareas = Tarea.objects.all().select_related("asignado_a", "sprint", "epica")
        integrantes = Integrante.objects.all()
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                tareas = tareas.filter(asignado_a__id=persona_id)
            except (Integrante.DoesNotExist, ValueError):
                pass
    else:
        tareas = Tarea.objects.filter(asignado_a=usuario_integrante).select_related("sprint", "epica") if usuario_integrante else Tarea.objects.none()
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
    })


# ==============================
# Checklist de tareas
# ==============================

@login_required
def checklist_view(request, integrante_id):
    """Checklist de tareas pendientes de un integrante"""
    integrante = get_object_or_404(Integrante, id=integrante_id)

    # 🔒 Si no eres admin, solo puedes ver tu propio checklist
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if not tiene_permisos_admin and integrante != usuario_integrante:
        messages.error(request, "❌ No puedes ver el checklist de otro integrante.")
        return redirect("backlog_lista")

    # Filtramos tareas abiertas asignadas a este integrante
    tareas = Tarea.objects.filter(
        asignado_a=integrante,
        completada=False
    ).select_related("sprint").order_by("sprint__inicio", "categoria")

    return render(request, "backlog/checklist.html", {
        "integrante": integrante,
        "tareas": tareas,
    })


@login_required
@requiere_permiso_evidencias
def eliminar_evidencia(request, tarea_id, evidencia_id):
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencia = get_object_or_404(Evidencia, id=evidencia_id, tarea=tarea)

    # 🔒 Solo el creador o un admin puede eliminar
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

    # Solo administradores pueden eliminar
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

    return render(request, "backlog/confirmar_eliminar_daily.html", {
        "daily": daily,
    })


@login_required
def sprint_list(request):
    sprints = Sprint.objects.all().order_by("inicio")
    return render(request, "backlog/sprint_list.html", {"sprints": sprints})


@login_required
def sprint_create(request):
    if not request.user.integrante.puede_crear_tareas():
        messages.error(request, "❌ No tienes permisos para crear sprints.")
        return redirect("sprint_list")

    if request.method == "POST":
        inicio = request.POST.get("inicio")
        fin = request.POST.get("fin")
        nombre = request.POST.get("nombre") or "Sprint"
        Sprint.objects.create(inicio=inicio, fin=fin, nombre=nombre)
        messages.success(request, "✅ Sprint creado correctamente.")
        return redirect("sprint_list")

    return render(request, "backlog/sprint_form.html")


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
            # Validar horario
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


@login_required
def eliminar_tarea(request, tarea_id):
    """Eliminar una tarea - solo para administradores"""
    tarea = get_object_or_404(Tarea, id=tarea_id)

    # Solo administradores pueden eliminar tareas
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
# Kanban (con epicas en contexto)
# ==============================

@login_required
def kanban_board(request):
    """Vista Kanban con estados de workflow - todos los usuarios pueden mover sus tareas"""
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if tiene_permisos_admin:
        tareas = Tarea.objects.all().select_related("asignado_a", "sprint", "epica")
        integrantes = Integrante.objects.all()
        epicas = Epica.objects.all()
        persona_id = request.GET.get("persona")
        epica_id = request.GET.get("epica")
        if persona_id:
            try:
                tareas = tareas.filter(asignado_a__id=persona_id)
            except (Integrante.DoesNotExist, ValueError):
                pass
        if epica_id:
            try:
                tareas = tareas.filter(epica__id=epica_id)
            except (Epica.DoesNotExist, ValueError):
                pass
    else:
        tareas = Tarea.objects.filter(asignado_a=usuario_integrante).select_related("sprint", "epica") if usuario_integrante else Tarea.objects.none()
        integrantes = []
        epicas = Epica.objects.filter(tareas__asignado_a=usuario_integrante).distinct()

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
        "tiene_permisos_admin": tiene_permisos_admin,
    })


@login_required
def cambiar_estado_tarea(request, tarea_id):
    """API para cambiar el estado de una tarea (drag & drop)"""
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    # Verificar permisos: admins pueden mover cualquier tarea, usuarios solo las suyas
    try:
        usuario_integrante = request.user.integrante
        es_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        return JsonResponse({"error": "No tienes perfil de integrante"}, status=403)

    if not es_admin and tarea.asignado_a != usuario_integrante:
        return JsonResponse({"error": "Solo puedes mover tus propias tareas"}, status=403)

    import json
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get("estado", "").upper()
        
        estados_validos = ["NUEVO", "APROBADO", "EN_PROGRESO", "COMPLETADO", "BLOQUEADO"]
        if nuevo_estado not in estados_validos:
            return JsonResponse({"error": "Estado no válido"}, status=400)

        tarea.estado = nuevo_estado
        
        # Si la tarea se marca como COMPLETADO, también marcarla como completada
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
# CRUD de Épicas
# ==============================

@login_required
def epica_list(request):
    try:
        admin = request.user.integrante.puede_crear_tareas()
    except AttributeError:
        admin = False

    if admin:
        epicas = Epica.objects.select_related("owner", "sprint").order_by("-creada_en")
    else:
        # Muestra solo epicas relacionadas a tareas del usuario
        integrante = getattr(request.user, "integrante", None)
        if integrante:
            epicas = Epica.objects.filter(tareas__asignado_a=integrante).distinct().order_by("-creada_en")
        else:
            epicas = Epica.objects.none()

    return render(request, "backlog/epica_list.html", {"epicas": epicas, "admin": admin})


@login_required
@requiere_permiso_crear_tareas
def epica_create(request):
    if request.method == "POST":
        form = EpicaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Épica creada correctamente.")
            return redirect("epica_list")
    else:
        form = EpicaForm()
    return render(request, "backlog/epica_form.html", {"form": form})


@login_required
@requiere_permiso_crear_tareas
def epica_edit(request, epica_id):
    epica = get_object_or_404(Epica, id=epica_id)
    if request.method == "POST":
        form = EpicaForm(request.POST, instance=epica)
        if form.is_valid():
            form.save()
            messages.success(request, "✏️ Épica actualizada correctamente.")
            return redirect("epica_list")
    else:
        form = EpicaForm(instance=epica)
    return render(request, "backlog/epica_form.html", {"form": form, "epica": epica})


@login_required
@requiere_permiso_crear_tareas
def epica_delete(request, epica_id):
    epica = get_object_or_404(Epica, id=epica_id)
    if request.method == "POST":
        titulo = epica.titulo
        epica.delete()
        messages.success(request, f"🗑️ Épica '{titulo}' eliminada correctamente.")
        return redirect("epica_list")
    return render(request, "backlog/epica_confirm_delete.html", {"epica": epica})


@login_required
def epica_detail(request, epica_id):
    epica = get_object_or_404(Epica, id=epica_id)
    tareas = epica.tareas.select_related("asignado_a", "sprint").order_by("sprint__inicio", "categoria", "titulo")
    return render(request, "backlog/epica_detail.html", {
        "epica": epica,
        "tareas": tareas,
    })
