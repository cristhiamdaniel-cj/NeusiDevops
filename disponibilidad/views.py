from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
import json

from .models import DisponibilidadSemanal, HorarioDisponibilidad

@login_required
def mi_disponibilidad(request):
    """Vista principal para que el usuario vea y edite su disponibilidad"""
    semana_actual = DisponibilidadSemanal.obtener_semana_actual()
    puede_editar, mensaje_edicion = DisponibilidadSemanal.puede_editar_usuario(request.user)
    
    # Obtener o crear la disponibilidad semanal
    disponibilidad, created = DisponibilidadSemanal.objects.get_or_create(
        usuario=request.user,
        semana_inicio=semana_actual,
        defaults={'actualizado_por': request.user}
    )
    
    # Crear matriz de horarios (7 d??as x 24 horas)
    horarios_matriz = {}
    for dia in range(7):
        horarios_matriz[dia] = {}
        for hora in range(24):
            try:
                horario = HorarioDisponibilidad.objects.get(
                    disponibilidad_semanal=disponibilidad,
                    dia_semana=dia,
                    hora=hora
                )
            except HorarioDisponibilidad.DoesNotExist:
                horario = None
            horarios_matriz[dia][hora] = horario
    
    context = {
        'disponibilidad': disponibilidad,
        'horarios_matriz': horarios_matriz,
        'puede_editar': puede_editar,
        'mensaje_edicion': mensaje_edicion,
        'dias_semana': HorarioDisponibilidad.DIAS_SEMANA,
        'horas': range(24),
        'estados': HorarioDisponibilidad.ESTADOS_DISPONIBILIDAD,
    }
    
    return render(request, 'disponibilidad/mi_disponibilidad.html', context)

@login_required
@require_POST
def actualizar_horario(request):
    """Ajax endpoint para actualizar un horario espec??fico"""
    try:
        data = json.loads(request.body)
        dia_semana = int(data['dia_semana'])
        hora = int(data['hora'])
        nuevo_estado = data['estado']
        
        semana_actual = DisponibilidadSemanal.obtener_semana_actual()
        puede_editar, mensaje = DisponibilidadSemanal.puede_editar_usuario(request.user)
        
        if not puede_editar:
            return JsonResponse({
                'success': False,
                'error': mensaje
            })
        
        # Obtener o crear disponibilidad semanal
        disponibilidad, _ = DisponibilidadSemanal.objects.get_or_create(
            usuario=request.user,
            semana_inicio=semana_actual,
            defaults={'actualizado_por': request.user}
        )
        
        # Actualizar u crear horario
        horario, created = HorarioDisponibilidad.objects.update_or_create(
            disponibilidad_semanal=disponibilidad,
            dia_semana=dia_semana,
            hora=hora,
            defaults={
                'estado': nuevo_estado,
                'notas': ''
            }
        )
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Horario actualizado correctamente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def ver_disponibilidad_equipo(request):
    """Vista para ver la disponibilidad de todo el equipo"""
    semana_actual = DisponibilidadSemanal.obtener_semana_actual()
    
    # Obtener TODOS los usuarios del sistema
    todos_usuarios = User.objects.all().order_by('first_name', 'last_name')
    
    # Filtrar por usuario si se solicita
    usuario_filtrado = request.GET.get('usuario')
    if usuario_filtrado:
        try:
            todos_usuarios = todos_usuarios.filter(id=usuario_filtrado)
        except (ValueError, User.DoesNotExist):
            pass
    
    # Organizar datos por usuario
    equipo_disponibilidad = {}
    for usuario in todos_usuarios:
        # Intentar obtener la disponibilidad de este usuario
        try:
            disp = DisponibilidadSemanal.objects.get(
                usuario=usuario,
                semana_inicio=semana_actual
            )
        except DisponibilidadSemanal.DoesNotExist:
            disp = None
        
        usuario_data = {
            'usuario': usuario,
            'disponibilidad': disp,
            'horarios': {}
        }
        
        # Crear matriz de horarios para este usuario
        for dia in range(7):
            usuario_data['horarios'][dia] = {}
            for hora in range(24):
                if disp:
                    try:
                        horario = disp.horarios.get(dia_semana=dia, hora=hora)
                        usuario_data['horarios'][dia][hora] = horario
                    except HorarioDisponibilidad.DoesNotExist:
                        usuario_data['horarios'][dia][hora] = None
                else:
                    usuario_data['horarios'][dia][hora] = None
        
        equipo_disponibilidad[usuario.id] = usuario_data
    
    context = {
        'equipo_disponibilidad': equipo_disponibilidad,
        'semana_actual': semana_actual,
        'dias_semana': HorarioDisponibilidad.DIAS_SEMANA,
        'horas': range(24),
        'todos_usuarios': User.objects.all().order_by('first_name', 'last_name'),
        'usuario_filtrado': usuario_filtrado,
    }
    
    return render(request, 'disponibilidad/equipo_disponibilidad.html', context)