# backlog/forms.py
from django import forms
from .models import Tarea, Daily, Evidencia, Sprint, Epica


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

from django import forms
from .models import Tarea

class TareaForm(forms.ModelForm):
    # Opcional: definir aquí el selector para controlar UI/UX
    ESFUERZO_CHOICES = [(None, "— Selecciona —")] + [(v, str(v)) for v in (1, 2, 3, 5, 8, 13, 21)]

    # TypedChoiceField para guardar enteros; permite dejarlo vacío (None)
    esfuerzo_sp = forms.TypedChoiceField(
        required=False,
        coerce=lambda v: int(v) if v not in (None, "",) else None,
        empty_value=None,
        choices=ESFUERZO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Puntuación de esfuerzo (Story Points)",
        help_text="Story points estimados (1, 2, 3, 5, 8, 13, 21). Opcional."
    )

    class Meta:
        model = Tarea
        # 🔹 Agregamos 'esfuerzo_sp' al formulario
        fields = [
            "epica", "titulo", "descripcion", "criterios_aceptacion",
            "categoria", "asignado_a", "sprint",
            "esfuerzo_sp",
        ]
        labels = {
            "epica": "Épica (opcional)",
            "titulo": "Título de la tarea",
            "descripcion": "Descripción",
            "criterios_aceptacion": "Criterios de aceptación",
            "categoria": "Categoría (Matriz Eisenhower)",
            "asignado_a": "Responsable",
            "sprint": "Sprint asignado",
            # "esfuerzo_sp": lo definimos arriba para controlar mejor
        }
        help_texts = {
            "criterios_aceptacion": "Explica claramente las condiciones para dar por completada esta tarea.",
            # "esfuerzo_sp": lo definimos arriba
        }
        widgets = {
            "epica": forms.Select(attrs={"class": "form-select"}),
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
            # "esfuerzo_sp": widget ya definido arriba
        }

    # (Opcional) Si quieres que el valor pase también por un validador extra
    # ya tienes el validador en el modelo; esto es redundante, pero útil si quieres
    # devolver error del lado del form antes de llegar al modelo.
    def clean_esfuerzo_sp(self):
        v = self.cleaned_data.get("esfuerzo_sp")
        validos = {1, 2, 3, 5, 8, 13, 21}
        if v is None or v == "":
            return None
        if v not in validos:
            raise forms.ValidationError("Los story points deben ser uno de: 1, 2, 3, 5, 8, 13 o 21.")
        return v

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
            "inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }


# 🔹 Nuevo: EpicaForm sin 'sprint' (usa ManyToMany 'sprints')

class EpicaForm(forms.ModelForm):
    class Meta:
        model = Epica
        fields = ["titulo", "descripcion", "estado", "prioridad", "owner", "sprints"]
        labels = {
            "titulo": "Título",
            "descripcion": "Descripción",
            "estado": "Estado",
            "prioridad": "Prioridad",
            "owner": "Owner (opcional)",
            "sprints": "Sprints relacionados",
        }
        widgets = {
            "titulo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la épica"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "prioridad": forms.Select(attrs={"class": "form-select"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "sprints": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
        }