from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import datetime

class DisponibilidadSemanal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='disponibilidades')
    semana_inicio = models.DateField(help_text="Fecha de inicio de la semana (lunes)")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    actualizado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = ['usuario', 'semana_inicio']
        ordering = ['-semana_inicio']
        verbose_name = "Disponibilidad Semanal"
        verbose_name_plural = "Disponibilidades Semanales"
    
    def __str__(self):
        return f"{self.usuario.username} - Semana del {self.semana_inicio}"
    
    @classmethod
    def obtener_semana_actual(cls):
        today = timezone.now().date()
        days_since_monday = today.weekday()
        return today - datetime.timedelta(days=days_since_monday)
    
    @classmethod
    def puede_editar_usuario(cls, user):
        if user.is_staff or user.is_superuser:
            return True, "Admin puede editar cualquier d??a"
        return True, "Modo testing - puede editar"  # Para desarrollo

class HorarioDisponibilidad(models.Model):
    DIAS_SEMANA = [
        (0, 'Lunes'), (1, 'Martes'), (2, 'Mi??rcoles'), (3, 'Jueves'),
        (4, 'Viernes'), (5, 'S??bado'), (6, 'Domingo'),
    ]
    
    ESTADOS_DISPONIBILIDAD = [
        ('disponible', 'Disponible'),
        ('ocupado', 'Ocupado'), 
        ('parcial', 'Parcialmente Disponible'),
    ]
    
    disponibilidad_semanal = models.ForeignKey(DisponibilidadSemanal, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA, validators=[MinValueValidator(0), MaxValueValidator(6)])
    hora = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(23)])
    estado = models.CharField(max_length=20, choices=ESTADOS_DISPONIBILIDAD, default='ocupado')
    notas = models.CharField(max_length=200, blank=True)
    
    class Meta:
        unique_together = ['disponibilidad_semanal', 'dia_semana', 'hora']
        ordering = ['dia_semana', 'hora']
    
    def __str__(self):
        return f"{self.get_dia_semana_display()} {self.hora}:00"
