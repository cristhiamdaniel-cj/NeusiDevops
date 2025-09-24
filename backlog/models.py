# backlog/models.py - Actualización del modelo Tarea
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Integrantes de NEUSI (usamos User + rol)
# Agregar al modelo Integrante en backlog/models.py

class Integrante(models.Model):
    # Definir roles con permisos específicos
    ROL_PERMISOS = {
        'Lider Bases de datos': ['crear_tareas', 'agregar_evidencias', 'editar_tareas'],
        'Scrum Master / PO': ['crear_tareas', 'agregar_evidencias', 'editar_tareas'],
    }
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
    
    def puede_crear_tareas(self):
        """Verifica si el integrante puede crear tareas"""
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return 'crear_tareas' in permisos
    
    def puede_agregar_evidencias(self):
        """Verifica si el integrante puede agregar evidencias"""
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return 'agregar_evidencias' in permisos
    
    def puede_editar_tareas(self):
        """Verifica si el integrante puede editar tareas"""
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return 'editar_tareas' in permisos

# Sprint de 1 semana
class Sprint(models.Model):
    inicio = models.DateField()
    fin = models.DateField()

    def __str__(self):
        return f"Sprint {self.inicio} - {self.fin}"


# Tareas clasificadas en la matriz de Eisenhower
class Tarea(models.Model):
    MATRIZ_CHOICES = [
        ('UI', 'Urgente e Importante'),
        ('NUI', 'No Urgente e Importante'),
        ('UNI', 'Urgente y No Importante'),
        ('NUNI', 'No Urgente y No Importante'),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    criterios_aceptacion = models.TextField(blank=True, help_text="Criterios que deben cumplirse para cerrar esta tarea")
    categoria = models.CharField(max_length=4, choices=MATRIZ_CHOICES)
    asignado_a = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True)
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE)
    completada = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    informe_cierre = models.FileField(upload_to="informes_cierre/", blank=True, null=True, help_text="Archivo requerido para cerrar la tarea")

    def __str__(self):
        return f"{self.titulo} ({self.get_categoria_display()})"


# Evidencias asociadas a las tareas
class Evidencia(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="evidencias")
    comentario = models.TextField(blank=True)
    archivo = models.FileField(upload_to="evidencias/", blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidencia de {self.tarea.titulo}"


class Daily(models.Model):
    integrante = models.ForeignKey("Integrante", on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    hora = models.TimeField(default=timezone.now)
    que_hizo_ayer = models.TextField()
    que_hara_hoy = models.TextField()
    impedimentos = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Daily {self.integrante} - {self.fecha}"