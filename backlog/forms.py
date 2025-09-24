# backlog/forms.py - Actualizado
from django import forms
from .models import Tarea, Daily, Evidencia

class DailyForm(forms.ModelForm):
    class Meta:
        model = Daily
        fields = ["que_hizo_ayer", "que_hara_hoy", "impedimentos"]
        widgets = {
            "que_hizo_ayer": forms.Textarea(attrs={"rows": 2}),
            "que_hara_hoy": forms.Textarea(attrs={"rows": 2}),
            "impedimentos": forms.Textarea(attrs={"rows": 2}),
        }


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ["titulo", "descripcion", "criterios_aceptacion", "categoria", "asignado_a", "sprint"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "criterios_aceptacion": forms.Textarea(attrs={"rows": 4, "placeholder": "Describe qué debe cumplirse para considerar esta tarea como completada..."}),
        }


class EvidenciaForm(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ["comentario", "archivo"]
        widgets = {
            "comentario": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe el progreso o evidencia..."}),
        }