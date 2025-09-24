#!/bin/bash
# add_models.sh
# Sobrescribe backlog/models.py con los modelos de NEUSI

cat > backlog/models.py << 'EOF'
from django.db import models
from django.contrib.auth.models import User

# Integrantes de NEUSI (usamos User + rol)
class Integrante(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


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
    categoria = models.CharField(max_length=4, choices=MATRIZ_CHOICES)
    asignado_a = models.ForeignKey(Integrante, on_delete=models.SET_NULL, null=True, blank=True)
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE)
    completada = models.BooleanField(default=False)

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
EOF

echo "✅ Modelos creados en backlog/models.py"

