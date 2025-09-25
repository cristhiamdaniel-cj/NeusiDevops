# backlog/forms.py - Mejorado y completo
from django import forms
from .models import Tarea, Daily, Evidencia, Sprint


class DailyForm(forms.ModelForm):
    class Meta:
        model = Daily
        fields = ["que_hizo_ayer", "que_hara_hoy", "impedimentos"]
        labels = {
            "que_hizo_ayer": "✅ ¿Qué hiciste ayer?",
            "que_hara_hoy": "📌 ¿Qué harás hoy?",
            "impedimentos": "⚠️ Impedimentos",
        }
        widgets = {
            "que_hizo_ayer": forms.Textarea(attrs={
                "rows": 2, "class": "form-control", "placeholder": "Describe brevemente lo que completaste ayer..."
            }),
            "que_hara_hoy": forms.Textarea(attrs={
                "rows": 2, "class": "form-control", "placeholder": "Indica lo que planeas trabajar hoy..."
            }),
            "impedimentos": forms.Textarea(attrs={
                "rows": 2, "class": "form-control", "placeholder": "Menciona si tienes bloqueos o impedimentos..."
            }),
        }


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ["titulo", "descripcion", "criterios_aceptacion", "categoria", "asignado_a", "sprint"]
        labels = {
            "titulo": "Título de la tarea",
            "descripcion": "Descripción",
            "criterios_aceptacion": "Criterios de aceptación",
            "categoria": "Categoría (Matriz Eisenhower)",
            "asignado_a": "Responsable",
            "sprint": "Sprint asignado",
        }
        help_texts = {
            "criterios_aceptacion": "Explica claramente las condiciones para dar por completada esta tarea.",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Escribe un título corto y claro"
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3, "class": "form-control", "placeholder": "Describe los detalles de la tarea..."
            }),
            "criterios_aceptacion": forms.Textarea(attrs={
                "rows": 4, "class": "form-control", "placeholder": "Ejemplo: Se considera completada cuando..."
            }),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "asignado_a": forms.Select(attrs={"class": "form-select"}),
            "sprint": forms.Select(attrs={"class": "form-select"}),
        }


class EvidenciaForm(forms.ModelForm):
    class Meta:
        model = Evidencia
        fields = ["comentario", "archivo"]
        labels = {
            "comentario": "💬 Comentario",
            "archivo": "📎 Archivo adjunto (opcional)",
        }
        widgets = {
            "comentario": forms.Textarea(attrs={
                "rows": 3, "class": "form-control", "placeholder": "Agrega un comentario sobre el progreso o adjunta un archivo..."
            }),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        """Validación extra: al menos comentario o archivo"""
        cleaned_data = super().clean()
        comentario = cleaned_data.get("comentario")
        archivo = cleaned_data.get("archivo")

        if not comentario and not archivo:
            raise forms.ValidationError("❌ Debes agregar al menos un comentario o un archivo como evidencia.")

        return cleaned_data

class SprintForm(forms.ModelForm):
    class Meta:
        model = Sprint
        fields = ["nombre", "inicio", "fin"]
        widgets = {
            "inicio": forms.DateInput(attrs={"type": "date"}),
            "fin": forms.DateInput(attrs={"type": "date"}),
        }