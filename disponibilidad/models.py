from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date


def lunes_de(fecha: date) -> date:
    return fecha - timedelta(days=fecha.weekday())


class DisponibilidadSemanal(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="semanas_disponibilidad")
    semana_inicio = models.DateField(help_text="Lunes de la semana")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("usuario", "semana_inicio")
        ordering = ("-semana_inicio",)
        managed = True

    def __str__(self):
        return f"{self.usuario.get_full_name() or self.usuario.username} - {self.semana_inicio}"

    @staticmethod
    def actual_lunes():
        return lunes_de(timezone.localdate())

    @property
    def semana_fin(self):
        return self.semana_inicio + timedelta(days=6)

    def ensure_dias(self):
        existentes = {d.dia_semana for d in self.dias.all()}
        faltantes = [i for i in range(7) if i not in existentes]
        for i in faltantes:
            DisponibilidadDia.objects.create(disponibilidad=self, dia_semana=i, tipo=DisponibilidadDia.Tipo.NO)


class DisponibilidadDia(models.Model):
    class Dia(models.IntegerChoices):
        LUNES = 0, "Lunes"
        MARTES = 1, "Martes"
        MIERCOLES = 2, "Miércoles"
        JUEVES = 3, "Jueves"
        VIERNES = 4, "Viernes"
        SABADO = 5, "Sábado"
        DOMINGO = 6, "Domingo"

    class Tipo(models.TextChoices):
        SI = "D", "Disponible todo el día"
        NO = "N", "No disponible"
        RANGO = "R", "Rango de disponibilidad"

    disponibilidad = models.ForeignKey(DisponibilidadSemanal, on_delete=models.CASCADE, related_name="dias")
    dia_semana = models.IntegerField(choices=Dia.choices)
    tipo = models.CharField(max_length=1, choices=Tipo.choices, default=Tipo.NO)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    notas = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("disponibilidad", "dia_semana")
        ordering = ("dia_semana",)
        managed = False

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.tipo == self.Tipo.RANGO:
            if self.hora_inicio is None or self.hora_fin is None:
                raise ValidationError("Debe indicar hora de inicio y fin para 'Rango'.")
        else:
            self.hora_inicio = None
            self.hora_fin = None

    @property
    def display_corto(self):
        if self.tipo == self.Tipo.SI:
            return "Disponible"
        if self.tipo == self.Tipo.NO:
            return "No"
        if self.hora_inicio and self.hora_fin:
            return f"{self.hora_inicio.strftime('%H:%M')}–{self.hora_fin.strftime('%H:%M')}"
        return "Rango"

    @property
    def display_largo(self):
        if self.tipo == self.Tipo.SI:
            return "Disponible todo el día"
        if self.tipo == self.Tipo.NO:
            return "No disponible"
        if self.hora_inicio and self.hora_fin:
            return f"Disponible de {self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')}"
        return "Rango (sin horas)"
