# backlog/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import (
    Tarea, Daily, Evidencia, Sprint, Epica, Proyecto,
    Integrante, BloqueTarea, Subtarea,EvidenciaSubtarea,
)

# ==============================
# Daily
# ==============================
from django import forms
from .models import Daily, DailyItem

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
                "rows": 2,
                "class": "form-control",
                "placeholder": "Describe brevemente lo que completaste ayer..."
            }),
            "que_hara_hoy": forms.Textarea(attrs={
                "rows": 2,
                "class": "form-control",
                "placeholder": "Indica lo que planeas trabajar hoy..."
            }),
            "impedimentos": forms.Textarea(attrs={
                "rows": 2,
                "class": "form-control",
                "placeholder": "Menciona si tienes bloqueos o impedimentos...(si no tienes, deja este campo en blanco)"
            }),
        }


# ==============================
# DailyItem (línea de daily)
# ==============================
class DailyItemForm(forms.ModelForm):
    class Meta:
        model = DailyItem
        fields = [
            "tipo",
            "descripcion",
            "tarea",
            "subtarea",
            "minutos",
            "evidencia_url",
        ]
        labels = {
            "tipo": "Tipo de actividad",
            "descripcion": "Descripción o comentario",
            "tarea": "Asociar a Tarea",
            "subtarea": "Asociar a Subtarea",
            "minutos": "Minutos dedicados",
            "evidencia_url": "URL de evidencia (opcional)",
        }
        widgets = {
            "tipo": forms.Select(
                choices=[("AYER", "Ayer"), ("HOY", "Hoy")],
                attrs={"class": "form-select"}
            ),
            "descripcion": forms.Textarea(attrs={
                "rows": 2,
                "class": "form-control",
                "placeholder": "Describe brevemente la actividad realizada o planificada..."
            }),
            "tarea": forms.Select(attrs={"class": "form-select"}),
            "subtarea": forms.Select(attrs={"class": "form-select"}),
            "minutos": forms.NumberInput(attrs={
                "class": "form-control", "min": 0, "placeholder": "Ej. 30"
            }),
            "evidencia_url": forms.URLInput(attrs={
                "class": "form-control", "placeholder": "https://..."
            }),
        }

    def clean(self):
        cleaned = super().clean()
        tarea = cleaned.get("tarea")
        subtarea = cleaned.get("subtarea")
        if tarea and subtarea:
            raise forms.ValidationError("Seleccione solo Tarea o Subtarea (no ambas).")
        if not cleaned.get("descripcion") and not tarea and not subtarea:
            raise forms.ValidationError("Debe indicar una descripción o asociar tarea/subtarea.")
        return cleaned

# ==============================
# Tarea (macro)
# ==============================
class TareaForm(forms.ModelForm):
    ESFUERZO_CHOICES = [(None, "— Selecciona —")] + [(v, str(v)) for v in (1, 2, 3, 5, 8, 13, 21)]

    esfuerzo_sp = forms.TypedChoiceField(
        required=False,
        coerce=lambda v: int(v) if v not in (None, "",) else None,
        empty_value=None,
        choices=ESFUERZO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Puntuación de esfuerzo (Story Points)",
        help_text="Story points estimados (1, 2, 3, 5, 8, 13, 21). Opcional."
    )

    estado = forms.ChoiceField(
        choices=Tarea.ESTADO_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Estado (Kanban)",
        help_text="Selecciona el estado actual de la tarea.",
        required=True,
    )

    asignados = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Integrante.objects.select_related("user").all().order_by(
            "user__first_name", "user__last_name"
        ),
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
        label="Responsables (pueden ser varios)",
        help_text="Tip: Ctrl/⌘ para seleccionar varios."
    )

    class Meta:
        model = Tarea
        fields = [
            "epica", "titulo", "descripcion", "criterios_aceptacion",
            "categoria", "estado", "sprint",
            "asignados", "esfuerzo_sp",
        ]
        labels = {
            "epica": "Épica (opcional)",
            "titulo": "Título de la tarea",
            "descripcion": "Descripción",
            "criterios_aceptacion": "Criterios de aceptación",
            "categoria": "Categoría (Matriz Eisenhower)",
            "estado": "Estado (Kanban)",
            "sprint": "Sprint asignado",
        }
        widgets = {
            "epica": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Escribe un título corto y claro"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Describe los detalles de la tarea..."}),
            "criterios_aceptacion": forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Ejemplo: Se considera completada cuando..."}),
            "categoria": forms.Select(attrs={"class": "form-select"}),
            "sprint": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["epica"].queryset = Epica.objects.select_related("proyecto").order_by(
            "proyecto__codigo", "titulo"
        )
        # Si solo tenía el FK legado, preinicializa M2M
        if self.instance and self.instance.pk and not self.instance.asignados.exists() and self.instance.asignado_a_id:
            self.initial.setdefault("asignados", [self.instance.asignado_a_id])

    def clean_esfuerzo_sp(self):
        v = self.cleaned_data.get("esfuerzo_sp")
        validos = {1, 2, 3, 5, 8, 13, 21}
        if v in (None, ""):
            return None
        if v not in validos:
            raise forms.ValidationError("Los story points deben ser uno de: 1, 2, 3, 5, 8, 13 o 21.")
        return v

    def clean_estado(self):
        est = self.cleaned_data.get("estado")
        validos = {c[0] for c in Tarea.ESTADO_CHOICES}
        if est not in validos:
            raise forms.ValidationError("Estado no válido.")
        return est

    def save(self, commit=True):
        tarea = super().save(commit=False)
        asignados_qs = self.cleaned_data.get("asignados")
        if asignados_qs is not None:
            asignados_list = list(asignados_qs)
            tarea.asignado_a = asignados_list[0] if len(asignados_list) == 1 else None
        if commit:
            tarea.save()
            self.save_m2m()
        return tarea


# --- Form minimalista para responsables (solo pueden cambiar estado) ---
class TareaEstadoForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = ["estado"]
        labels = {"estado": "Estado (Kanban)"}
        help_texts = {"estado": "Solo puedes actualizar el estado de la tarea."}
        widgets = {"estado": forms.Select(attrs={"class": "form-select"})}

    def clean_estado(self):
        est = self.cleaned_data.get("estado")
        validos = {c[0] for c in Tarea.ESTADO_CHOICES}
        if est not in validos:
            raise forms.ValidationError("Estado no válido.")
        return est


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
# Épica
# ==============================
class EpicaForm(forms.ModelForm):
    owners = forms.ModelMultipleChoiceField(
        queryset=Integrante.objects.select_related("user").all(),
        required=True,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
        label="Responsables del producto",
        help_text="Selecciona uno o varios integrantes encargados de esta épica."
    )

    class Meta:
        model = Epica
        fields = [
            "codigo", "proyecto", "titulo", "descripcion", "estado", "prioridad",
            "owners", "sprints", "fecha_inicio", "fecha_fin", "kpis",
            "avance_manual", "documentos_url",
        ]
        labels = {
            "codigo": "Código (ej. NEUSI-001)",
            "proyecto": "Proyecto",
            "titulo": "Título",
            "descripcion": "Descripción",
            "estado": "Estado",
            "prioridad": "Prioridad",
            "owners": "Responsables del producto",
            "sprints": "Sprints relacionados",
            "fecha_inicio": "Fecha de inicio",
            "fecha_fin": "Fecha de fin",
            "kpis": "KPIs o Criterios de éxito",
            "avance_manual": "Avance manual (%)",
            "documentos_url": "Documentos asociados (URL)",
        }
        help_texts = {
            "avance_manual": "Si lo defines, se mostrará como avance principal. "
                             "Déjalo vacío para usar el progreso automático por tareas.",
        }
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control", "placeholder": "NEUSI-001"}),
            "proyecto": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la épica"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción general de la épica"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "prioridad": forms.Select(attrs={"class": "form-select"}),
            "owners": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
            "sprints": forms.SelectMultiple(attrs={"class": "form-select", "size": 6}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "kpis": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Métricas clave, criterios de éxito…"}),
            "avance_manual": forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
            "documentos_url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proyecto"].queryset = Proyecto.objects.filter(activo=True).order_by("codigo")
        self.fields["sprints"].queryset = Sprint.objects.all().order_by("inicio")
        self.fields["owners"].queryset = (
            Integrante.objects.select_related("user").order_by("user__first_name", "user__last_name")
        )
        if self.instance and self.instance.pk:
            self.fields["owners"].initial = self.instance.owners.values_list("pk", flat=True)

    def clean_codigo(self):
        v = (self.cleaned_data.get("codigo") or "").strip().upper()
        return v or None

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

    def save(self, commit=True):
        epica = super().save(commit=False)
        if commit:
            epica.save()
        self.save_m2m()
        seleccion = list(self.cleaned_data.get("owners") or [])
        epica.owner = seleccion[0] if len(seleccion) == 1 else None
        if commit:
            epica.save(update_fields=["owner"])
        return epica


# ==============================
# Bloques y Subtareas
# ==============================
class BloqueTareaForm(forms.ModelForm):
    class Meta:
        model = BloqueTarea
        fields = ["indice", "nombre", "fecha_inicio", "fecha_fin"]
        widgets = {
            "indice": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre (opcional)"}),
            "fecha_inicio": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "fecha_fin": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get("fecha_inicio")
        fin = cleaned.get("fecha_fin")
        if ini and fin and fin < ini:
            raise forms.ValidationError("La fecha fin no puede ser anterior a la fecha inicio.")
        return cleaned


# Formset para CREAR/EDITAR bloques (usado en views)
BloqueFormSet = inlineformset_factory(
    parent_model=Tarea,
    model=BloqueTarea,
    form=BloqueTareaForm,
    fields=["indice", "nombre", "fecha_inicio", "fecha_fin"],
    extra=1,
    can_delete=True,
    max_num=50,
)


class SubtareaForm(forms.ModelForm):
    esfuerzo_sp = forms.TypedChoiceField(
        required=False,
        coerce=lambda v: int(v) if v not in (None, "",) else None,
        empty_value=None,
        choices=[(None, "— Selecciona —")] + [(v, str(v)) for v in (1, 2, 3, 5)],
        label="Esfuerzo (SP)",
        help_text="Story points cortos (1, 2, 3 o 5)."
    )

    class Meta:
        model = Subtarea
        fields = ["bloque", "titulo", "descripcion", "responsable", "estado", "esfuerzo_sp", "fecha_inicio", "fecha_fin"]
        widgets = {
            "bloque": forms.Select(attrs={"class": "form-select"}),
            "titulo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Título de la subtarea"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción breve de la subtarea (opcional)"}),
            "responsable": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
            # fechas: ocultas/solo backend (se heredan del bloque)
            "fecha_inicio": forms.HiddenInput(),
            "fecha_fin": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self._tarea = kwargs.pop("tarea", None)
        self._bloque = kwargs.pop("bloque", None)
        es_admin = kwargs.pop("es_admin", False)
        super().__init__(*args, **kwargs)

        if self._bloque is None and getattr(self.instance, "bloque", None):
            self._bloque = self.instance.bloque
        if self._tarea is None and isinstance(self._bloque, BloqueTarea):
            self._tarea = self._bloque.tarea

        # queryset de responsable (admin ve todos; responsable ve solo los de la macro)
        if es_admin:
            qs_resp = Integrante.objects.select_related("user").all().order_by("user__first_name", "user__last_name")
        else:
            qs_resp = Integrante.objects.none()
            if isinstance(self._tarea, Tarea) and self._tarea.pk:
                ids = set(self._tarea.asignados.values_list("id", flat=True))
                if self._tarea.asignado_a_id:
                    ids.add(self._tarea.asignado_a_id)
                if ids:
                    qs_resp = (
                        Integrante.objects
                        .select_related("user")
                        .filter(id__in=ids)
                        .order_by("user__first_name", "user__last_name")
                    )
            if not qs_resp.exists():
                self.fields["responsable"].help_text = (
                    "No hay responsables definidos en la tarea macro. "
                    "Primero asigna responsables a la macro."
                )
        self.fields["responsable"].queryset = qs_resp

        # inicializar fechas (aunque no se muestran)
        if isinstance(self._bloque, BloqueTarea):
            self.initial.setdefault("fecha_inicio", self._bloque.fecha_inicio)
            self.initial.setdefault("fecha_fin", self._bloque.fecha_fin)

    def clean(self):
        cleaned = super().clean()
        if isinstance(self._bloque, BloqueTarea):
            cleaned["fecha_inicio"] = self._bloque.fecha_inicio
            cleaned["fecha_fin"] = self._bloque.fecha_fin
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        if isinstance(self._bloque, BloqueTarea):
            obj.bloque = self._bloque
            obj.fecha_inicio = self._bloque.fecha_inicio
            obj.fecha_fin = self._bloque.fecha_fin
        if commit:
            obj.save()
            self.save_m2m()
        return obj

class EvidenciaSubtareaForm(forms.ModelForm):
    class Meta:
        model  = EvidenciaSubtarea
        fields = ["comentario", "archivo"]
        labels = {
            "comentario": "💬 Comentario",
            "archivo": "📎 Archivo (opcional)",
        }
        widgets = {
            "comentario": forms.Textarea(attrs={
                "rows": 2, "class": "form-control",
                "placeholder": "Describe el avance o adjunta soporte…"
            }),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

    def clean(self):
        data = super().clean()
        if not data.get("comentario") and not data.get("archivo"):
            raise forms.ValidationError("Debes adjuntar archivo o escribir un comentario.")
        return data
