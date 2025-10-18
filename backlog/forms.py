# backlog/forms.py
from django import forms

from .models import (
    Tarea,
    Daily,
    Evidencia,
    Sprint,
    Epica,
    Proyecto,
)

# ==============================
# Daily
# ==============================
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
                "rows": 2, "class": "form-control",
                "placeholder": "Describe brevemente lo que completaste ayer..."
            }),
            "que_hara_hoy": forms.Textarea(attrs={
                "rows": 2, "class": "form-control",
                "placeholder": "Indica lo que planeas trabajar hoy..."
            }),
            "impedimentos": forms.Textarea(attrs={
                "rows": 2, "class": "form-control",
                "placeholder": "Menciona si tienes bloqueos o impedimentos..."
            }),
        }


# ==============================
# Tarea
# ==============================
class TareaForm(forms.ModelForm):
    # Combo de story points (opcional)
    ESFUERZO_CHOICES = [(None, "— Selecciona —")] + [
        (v, str(v)) for v in (1, 2, 3, 5, 8, 13, 21)
    ]

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
        }
        help_texts = {
            "criterios_aceptacion": "Explica claramente las condiciones para dar por completada esta tarea.",
        }
        widgets = {
            "epica": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Escribe un título corto y claro"
            }),
            "descripcion": forms.Textarea(attrs={
                "rows": 3, "class": "form-control",
                "placeholder": "Describe los detalles de la tarea..."
            }),
            "criterios_aceptacion": forms.Textarea(attrs={
                "rows": 4, "class": "form-control",
                "placeholder": "Ejemplo: Se considera completada cuando..."
            }),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "asignado_a": forms.Select(attrs={"class": "form-select"}),
            "sprint": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordena épicas por proyecto y título para mejor UX
        self.fields["epica"].queryset = Epica.objects.select_related("proyecto").order_by(
            "proyecto__codigo", "titulo"
        )

    def clean_esfuerzo_sp(self):
        v = self.cleaned_data.get("esfuerzo_sp")
        validos = {1, 2, 3, 5, 8, 13, 21}
        if v in (None, ""):
            return None
        if v not in validos:
            raise forms.ValidationError(
                "Los story points deben ser uno de: 1, 2, 3, 5, 8, 13 o 21."
            )
        return v


# ==============================
# Evidencia
# ==============================
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
                "rows": 3, "class": "form-control",
                "placeholder": "Agrega un comentario sobre el progreso o adjunta un archivo..."
            }),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        comentario = cleaned_data.get("comentario")
        archivo = cleaned_data.get("archivo")
        if not comentario and not archivo:
            raise forms.ValidationError(
                "❌ Debes agregar al menos un comentario o un archivo como evidencia."
            )
        return cleaned_data


# ==============================
# Sprint
# ==============================
class SprintForm(forms.ModelForm):
    class Meta:
        model = Sprint
        fields = ["nombre", "inicio", "fin"]
        widgets = {
            "inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
        }


# ==============================
# Proyecto
# ==============================
class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = ["codigo", "nombre", "activo"]
        labels = {
            "codigo": "Código (único)",
            "nombre": "Nombre del proyecto",
            "activo": "Activo",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "NEUCONTA"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Neusi - Contabilidad"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_codigo(self):
        v = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not v:
            raise forms.ValidationError("El código del proyecto es obligatorio.")
        return v


# ==============================
# Épica (actualizada con Proyecto y campos nuevos)
# ==============================
class EpicaForm(forms.ModelForm):
    class Meta:
        model = Epica
        # Incluye los campos nuevos que ya usas en vistas/templates:
        fields = [
            "codigo",
            "proyecto",
            "titulo",
            "descripcion",
            "estado",
            "prioridad",
            "owner",
            "sprints",
            "fecha_inicio",
            "fecha_fin",
            "kpis",
            "avance_manual",   # porcentaje opcional (0-100)
            "documentos_url",
        ]
        labels = {
            "codigo": "Código (ej. NEUSI-001)",
            "proyecto": "Proyecto",
            "titulo": "Título",
            "descripcion": "Descripción",
            "estado": "Estado",
            "prioridad": "Prioridad",
            "owner": "Owner (opcional)",
            "sprints": "Sprints relacionados",
            "fecha_inicio": "Fecha inicio",
            "fecha_fin": "Fecha fin",
            "kpis": "KPIs o Criterios de éxito",
            "avance_manual": "Avance manual (%)",
            "documentos_url": "Documentos asociados (URL)",
        }
        help_texts = {
            "avance_manual": "Si lo defines, se mostrará como avance principal. Déjalo vacío para usar progreso por tareas.",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "NEUSI-001"}),
            "proyecto": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la épica"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "prioridad": forms.Select(attrs={"class": "form-select"}),
            "owner": forms.Select(attrs={"class": "form-select"}),
            "sprints": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "kpis": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Métricas clave, criterios de éxito…"}),
            "avance_manual": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "documentos_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo proyectos activos en el selector, ordenados por código
        self.fields["proyecto"].queryset = Proyecto.objects.filter(activo=True).order_by("codigo")
        # Ordena sprints por fecha de inicio
        self.fields["sprints"].queryset = Sprint.objects.all().order_by("inicio")

    def clean_codigo(self):
        v = (self.cleaned_data.get("codigo") or "").strip().upper()
        # Permitir vacío si decides autogenerarlo en señales/admin; si no, exige:
        # if not v: raise forms.ValidationError("El código es obligatorio.")
        return v

    def clean_avance_manual(self):
        v = self.cleaned_data.get("avance_manual")
        if v in (None, ""):
            return None
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise forms.ValidationError("Debe ser un número entre 0 y 100.")
        if not (0 <= v <= 100):
            raise forms.ValidationError("El avance manual debe estar entre 0 y 100.")
        return v
