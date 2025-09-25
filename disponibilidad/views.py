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
    
    # Obtener todas las disponibilidades de la semana actual
    disponibilidades = DisponibilidadSemanal.objects.filter(
        semana_inicio=semana_actual
    ).select_related('usuario').prefetch_related('horarios')
    
    # Organizar datos por usuario
    equipo_disponibilidad = {}
    for disp in disponibilidades:
        usuario_data = {
            'usuario': disp.usuario,
            'disponibilidad': disp,
            'horarios': {}
        }
        
        # Crear matriz de horarios para este usuario
        for dia in range(7):
            usuario_data['horarios'][dia] = {}
            for hora in range(24):
                try:
                    horario = disp.horarios.get(dia_semana=dia, hora=hora)
                    usuario_data['horarios'][dia][hora] = horario
                except HorarioDisponibilidad.DoesNotExist:
                    usuario_data['horarios'][dia][hora] = None
        
        equipo_disponibilidad[disp.usuario.id] = usuario_data
    
    context = {
        'equipo_disponibilidad': equipo_disponibilidad,
        'semana_actual': semana_actual,
        'dias_semana': HorarioDisponibilidad.DIAS_SEMANA,
        'horas': range(24),
    }
    
    return render(request, 'disponibilidad/equipo_disponibilidad.html', context)
