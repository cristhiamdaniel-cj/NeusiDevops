from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import localtime
from datetime import time
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from .models import Tarea, Sprint, Integrante, Daily
from .forms import TareaForm, DailyForm
# Agregar al inicio de backlog/views.py
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import localtime
from django.utils import timezone
from datetime import time
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse

from .models import Tarea, Sprint, Integrante, Daily
from .forms import TareaForm, DailyForm

# Decorador para verificar permisos de creación de tareas
def requiere_permiso_crear_tareas(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            integrante = request.user.integrante
            if not integrante.puede_crear_tareas():
                messages.error(request, "❌ No tienes permisos para crear tareas. Solo Daniel Campos y Andrés Gómez pueden crear tareas.")
                return redirect("backlog_lista")
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Decorador para verificar permisos de agregar evidencias
def requiere_permiso_evidencias(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        try:
            integrante = request.user.integrante
            if not integrante.puede_agregar_evidencias():
                messages.error(request, "❌ No tienes permisos para agregar evidencias. Solo Daniel Campos y Andrés Gómez pueden agregar evidencias.")
                return redirect("backlog_lista")
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Vista actualizada para nueva tarea (SOLO Daniel y Andrés)
@login_required
@requiere_permiso_crear_tareas
def nueva_tarea(request):
    """Crear una nueva tarea en el backlog - SOLO Daniel Campos y Andrés Gómez"""
    if request.method == "POST":
        form = TareaForm(request.POST)
        if form.is_valid():
            tarea = form.save()
            messages.success(request, f"✅ Tarea '{tarea.titulo}' creada correctamente por {request.user.first_name}.")
            return redirect("backlog_lista")
    else:
        form = TareaForm()
    return render(request, "backlog/nueva_tarea.html", {"form": form})

# Vista actualizada para agregar evidencias (SOLO Daniel y Andrés)
@login_required
@requiere_permiso_evidencias
def agregar_evidencia(request, tarea_id):
    """Agregar evidencia a una tarea - SOLO Daniel Campos y Andrés Gómez"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    if request.method == "POST":
        comentario = request.POST.get("comentario", "")
        archivo = request.FILES.get("archivo")
        
        if comentario or archivo:
            evidencia = Evidencia.objects.create(
                tarea=tarea,
                comentario=comentario,
                archivo=archivo
            )
            messages.success(request, f"✅ Evidencia agregada correctamente por {request.user.first_name}.")
        else:
            messages.error(request, "❌ Debes agregar al menos un comentario o archivo.")
    
    return redirect("detalle_tarea", tarea_id=tarea.id)

# Agregar estas vistas al archivo backlog/views.py

@login_required
def detalle_tarea(request, tarea_id):
    """Vista detallada de una tarea"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    evidencias = tarea.evidencias.all().order_by('-fecha')
    
    return render(request, "backlog/detalle_tarea.html", {
        "tarea": tarea,
        "evidencias": evidencias,
    })


@login_required
def cerrar_tarea(request, tarea_id):
    """Cerrar una tarea con confirmación y archivo obligatorio"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    
    # Verificar que el usuario puede cerrar esta tarea
    if tarea.asignado_a.user != request.user:
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
            return render(request, "backlog/cerrar_tarea.html", {"tarea": tarea})
        
        if confirmacion != "confirmo":
            messages.error(request, "❌ Debes confirmar que estás seguro de cerrar la tarea.")
            return render(request, "backlog/cerrar_tarea.html", {"tarea": tarea})
        
        # Cerrar la tarea
        tarea.completada = True
        tarea.fecha_cierre = timezone.now()
        tarea.informe_cierre = informe
        tarea.save()
        
        messages.success(request, f"✅ La tarea '{tarea.titulo}' fue cerrada exitosamente.")
        return redirect("backlog_lista")
    
    return render(request, "backlog/cerrar_tarea.html", {"tarea": tarea})




# 🔑 Login
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.check_password("neusi123"):  # 👈 si aún usa la clave por defecto
                messages.warning(request, "⚠️ Debes cambiar tu contraseña antes de continuar.")
                return redirect("change_password")
            return redirect("backlog_lista")
        else:
            messages.error(request, "Usuario o contraseña incorrectos")
    return render(request, "auth/login.html")


from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Evita que cierre la sesión después de cambiar la contraseña
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Contraseña cambiada correctamente.")
            return redirect("backlog_lista")  # Redirige a donde quieras después
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "auth/change_password.html", {"form": form})


# 🚪 Logout
def logout_view(request):
    """Cerrar sesión y redirigir al login"""
    logout(request)
    return redirect("login")


# 🏠 Home
@login_required
def home(request):
    """Página principal"""
    return render(request, "backlog/home.html")


# 📅 Daily
# Actualización de views.py - Sección Daily

@login_required
def daily_view(request, integrante_id=None):
    """Registrar el Daily - solo el usuario puede registrar su propio daily"""
    
    # Si no se especifica integrante_id, usar el del usuario actual
    if integrante_id is None:
        try:
            integrante = request.user.integrante
        except AttributeError:
            messages.error(request, "❌ No tienes un perfil de integrante asociado.")
            return redirect("home")
    else:
        integrante = get_object_or_404(Integrante, id=integrante_id)
        
        # Verificar que el usuario solo pueda acceder a su propio daily
        if integrante.user != request.user:
            messages.error(request, "❌ Solo puedes registrar tu propio daily.")
            return redirect("daily_personal")

    if request.method == "POST":
        form = DailyForm(request.POST)
        if form.is_valid():
            fecha_actual = localtime().date()
            hora_actual = localtime().time()

            # Validar rango 7–8am (hora Bogotá)
            if not (time(7, 0) <= hora_actual <= time(8, 0)):
                messages.error(request, "❌ El Daily solo se puede registrar entre las 7:00 y 8:00 AM (hora Bogotá).")
                return render(request, "backlog/daily_form.html", {
                    "form": form,
                    "integrante": integrante,
                    "fecha_actual": localtime().strftime("%Y-%m-%d %H:%M"),
                })

            daily, created = Daily.objects.get_or_create(
                integrante=integrante,
                fecha=fecha_actual,
                defaults=form.cleaned_data
            )
            if not created:
                # Si ya existe, actualizar
                for field, value in form.cleaned_data.items():
                    setattr(daily, field, value)
                daily.save()

            messages.success(request, "✅ Daily registrado correctamente.")
            return redirect("daily_resumen")
    else:
        # Si ya registró hoy, cargar los datos existentes
        fecha_actual = localtime().date()
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
    """Acceso directo al daily personal del usuario autenticado"""
    try:
        integrante = request.user.integrante
        return daily_view(request, integrante.id)
    except AttributeError:
        messages.error(request, "❌ No tienes un perfil de integrante asociado.")
        return redirect("home")


# Actualización de la vista daily_resumen en views.py



# 📊 Backlog matriz
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Tarea, Sprint, Integrante, Daily

@login_required
def mover_tarea(request, tarea_id):
    """Actualizar categoría de tarea arrastrada en la matriz."""
    if request.method == "POST":
        tarea = get_object_or_404(Tarea, id=tarea_id)
        nueva_categoria = request.POST.get("categoria")
        
        # Mapeo de IDs de cuadrantes a códigos de categoría
        categoria_map = {
            "ui": "UI",
            "nui": "NUI", 
            "uni": "UNI",
            "nuni": "NUNI"
        }

        if nueva_categoria in categoria_map:
            tarea.categoria = categoria_map[nueva_categoria]
            tarea.save()
            return JsonResponse({"status": "ok", "nueva_categoria": tarea.categoria})

        return JsonResponse({"status": "error", "msg": "Categoría inválida"}, status=400)

    return JsonResponse({"status": "error", "msg": "Método no permitido"}, status=405)



# ✅ Checklist personal
@login_required
def checklist_view(request, integrante_id):
    """Checklist de tareas pendientes de un integrante"""
    integrante = get_object_or_404(Integrante, id=integrante_id)
    tareas = Tarea.objects.filter(asignado_a=integrante, completada=False)
    return render(request, "backlog/checklist.html", {"integrante": integrante, "tareas": tareas})


# 🔒 Cerrar tarea
@login_required
def cerrar_tarea(request, tarea_id):
    """Cerrar una tarea"""
    tarea = get_object_or_404(Tarea, id=tarea_id)
    tarea.completada = True
    tarea.save()
    messages.info(request, f"📌 La tarea '{tarea.titulo}' fue cerrada.")
    return redirect("backlog_lista")



# Agregar al final de backlog/views.py para validaciones adicionales

# Middleware personalizado o función auxiliar para validar permisos
def validar_permisos_usuario(request):
    """Función auxiliar para validar permisos del usuario"""
    try:
        integrante = request.user.integrante
        return {
            'puede_crear_tareas': integrante.puede_crear_tareas(),
            'puede_agregar_evidencias': integrante.puede_agregar_evidencias(),
            'rol': integrante.rol
        }
    except AttributeError:
        return {
            'puede_crear_tareas': False,
            'puede_agregar_evidencias': False,
            'rol': 'Sin rol asignado'
        }

# Vista mejorada de backlog lista con información de permisos

# Nota: También deberías actualizar otras vistas como home, detalle_tarea, etc.
# para pasar la información de permisos al contexto del template


# backlog/views.py - Vistas actualizadas con filtros por permisos

@login_required
def backlog_lista(request):
    """Vista del backlog en lista con filtros basados en permisos"""
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    # Determinar qué tareas mostrar según permisos
    if tiene_permisos_admin:
        # Daniel y Andrés ven todas las tareas
        tareas = Tarea.objects.all().select_related("asignado_a", "sprint")
        integrantes = Integrante.objects.all()  # Mostrar todos los integrantes en filtros
    else:
        # Resto del equipo solo ve sus propias tareas
        if usuario_integrante:
            tareas = Tarea.objects.filter(asignado_a=usuario_integrante).select_related("asignado_a", "sprint")
        else:
            tareas = Tarea.objects.none()
        integrantes = []  # No mostrar filtro de integrantes

    sprints = Sprint.objects.all()

    # Aplicar filtros solo si el usuario tiene permisos
    if tiene_permisos_admin:
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                integrante_filtro = Integrante.objects.get(id=persona_id)
                tareas = tareas.filter(asignado_a=integrante_filtro)
            except (Integrante.DoesNotExist, ValueError):
                pass

        sprint_id = request.GET.get("sprint")
        if sprint_id:
            try:
                sprint_filtro = Sprint.objects.get(id=sprint_id)
                tareas = tareas.filter(sprint=sprint_filtro)
            except (Sprint.DoesNotExist, ValueError):
                pass

    # Filtro de estado disponible para todos
    estado = request.GET.get("estado")
    if estado == "abiertas":
        tareas = tareas.filter(completada=False)
    elif estado == "cerradas":
        tareas = tareas.filter(completada=True)

    tareas = tareas.order_by("sprint__inicio", "categoria")

    return render(request, "backlog/backlog_lista.html", {
        "tareas": tareas,
        "sprints": sprints,
        "integrantes": integrantes,  # Solo Daniel/Andrés verán la lista completa
        "estado": estado,
        "tiene_permisos_admin": tiene_permisos_admin,
        "persona_id": request.GET.get("persona", ""),
        "sprint_id": request.GET.get("sprint", ""),
    })


@login_required
def backlog_matriz(request):
    """Vista de la matriz de Eisenhower con filtros basados en permisos"""
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    # Determinar qué tareas mostrar según permisos
    if tiene_permisos_admin:
        # Daniel y Andrés pueden ver todas las tareas
        tareas = Tarea.objects.all().select_related("asignado_a", "sprint")
        integrantes = Integrante.objects.all()
        
        # Aplicar filtros si están presentes
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                integrante_filtro = Integrante.objects.get(id=persona_id)
                tareas = tareas.filter(asignado_a=integrante_filtro)
            except (Integrante.DoesNotExist, ValueError):
                pass
    else:
        # Resto del equipo solo ve sus propias tareas
        if usuario_integrante:
            tareas = Tarea.objects.filter(asignado_a=usuario_integrante).select_related("asignado_a", "sprint")
        else:
            tareas = Tarea.objects.none()
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
        "persona_id": request.GET.get("persona", ""),
    })


@login_required
def daily_resumen(request):
    """Resumen de dailies con filtros basados en permisos"""
    try:
        usuario_integrante = request.user.integrante
        tiene_permisos_admin = usuario_integrante.puede_crear_tareas()
    except AttributeError:
        tiene_permisos_admin = False
        usuario_integrante = None

    if tiene_permisos_admin:
        # Daniel y Andrés ven todos los dailies
        registros = Daily.objects.select_related('integrante__user').order_by("-fecha", "integrante__user__first_name")
        integrantes = Integrante.objects.all()
        
        # Aplicar filtros si están presentes
        persona_id = request.GET.get("persona")
        if persona_id:
            try:
                integrante_filtro = Integrante.objects.get(id=persona_id)
                registros = registros.filter(integrante=integrante_filtro)
            except (Integrante.DoesNotExist, ValueError):
                pass
    else:
        # Resto del equipo solo ve su propio daily
        if usuario_integrante:
            registros = Daily.objects.filter(integrante=usuario_integrante).order_by("-fecha")
        else:
            registros = Daily.objects.none()
        integrantes = []

    # Filtro por fecha para mostrar solo dailies recientes (últimos 7 días)
    from datetime import datetime, timedelta
    fecha_limite = datetime.now().date() - timedelta(days=7)
    registros = registros.filter(fecha__gte=fecha_limite)
    
    return render(request, "backlog/daily_resumen.html", {
        "registros": registros,
        "integrantes": integrantes,
        "tiene_permisos_admin": tiene_permisos_admin,
        "persona_id": request.GET.get("persona", ""),
    })