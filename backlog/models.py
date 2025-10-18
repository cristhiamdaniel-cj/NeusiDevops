# backlog/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError


# ==============================
# Validadores
# ==============================
def validar_story_points(value):
    """
    Story points usuales en planning (serie Fibonacci corta).
    Permite nulo/blank en el campo, pero si viene valor debe ser uno de estos.
    """
    if value is None:
        return
    validos = (1, 2, 3, 5, 8, 13, 21)
    if value not in validos:
        raise ValidationError(f"Los story points deben ser uno de: {', '.join(map(str, validos))}.")


# ==============================
# Integrante
# ==============================
class Integrante(models.Model):
    """
    Relación 1 a 1 con User de Django.
    Se usa para asignar roles y permisos personalizados.
    """
    ROL_PERMISOS = {
        "Lider Bases de datos": ["crear_tareas", "agregar_evidencias", "editar_tareas"],
        "Scrum Master / PO": ["crear_tareas", "agregar_evidencias", "editar_tareas"],
        "Visualizador": [],
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    # ==== Métodos de permisos ====
    def puede_crear_tareas(self):
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return "crear_tareas" in permisos

    def puede_agregar_evidencias(self):
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return "agregar_evidencias" in permisos

    def puede_editar_tareas(self):
        permisos = self.ROL_PERMISOS.get(self.rol, [])
        return "editar_tareas" in permisos

    def es_visualizador(self):
        return self.rol == "Visualizador"


# ==============================
# Proyecto (normalizado)
# ==============================
class Proyecto(models.Model):
    codigo = models.CharField(
        max_length=30,
        unique=True,
        help_text="Identificador corto del proyecto (ej. NEUCONTA, CPS, JURIDICO)."
    )
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


# ==============================
# Sprint
# ==============================
class Sprint(models.Model):
    nombre = models.CharField(max_length=50, default="Sprint")
    inicio = models.DateField()
    fin = models.DateField()

    def __str__(self):
        return f"{self.nombre} ({self.inicio} - {self.fin})"


# ==============================
# Épica
# ==============================
class Epica(models.Model):
    ESTADO_CHOICES = [
        ("PROPUESTA", "Propuesta"),
        ("ACTIVA", "Activa"),
        ("EN_PAUSA", "En pausa"),
        ("CERRADA", "Cerrada"),
    ]
    PRIORIDAD_CHOICES = [
        ("ALTA", "Alta"),
        ("MEDIA", "Media"),
        ("BAJA", "Baja"),
    ]

    # Nuevo: código legible de la épica (opcional pero recomendable)
    codigo = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="Código legible de la épica (ej. NEUSI-001)."
    )

    titulo = models.CharField(max_length=200, unique=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="ACTIVA")
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD_CHOICES, default="MEDIA")

    # Nuevo: relación con Proyecto (normalizado)
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="epicas",
        help_text="Proyecto al que pertenece esta épica."
    )

    # Nuevo: fechas macro de la épica
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    # Nuevo: KPIs / criterios de éxito
    kpis = models.TextField(blank=True, help_text="Métricas clave esperadas para la épica")

    # Nuevo: avance manual (0–100). Si no se define, se usa el cálculo por tareas.
    avance_manual = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="0–100. Si se deja vacío, se calcula por tareas."
    )

    # Nuevo: URL de documentos (Drive/Notion/Repo)
    documentos_url = models.URLField(blank=True, help_text="Enlace a carpeta o documento maestro")

    owner = models.ForeignKey(
        Integrante, on_delete=models.SET_NULL, null=True, blank=True, related_name="epicas_propias"
    )

    # Puede abarcar varios sprints
    sprints = models.ManyToManyField(Sprint, blank=True, related_name="epicas")

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada_en"]

    def __str__(self):
        pref = f"{self.codigo} - " if self.codigo else ""
        return f"{pref}{self.titulo}"

    # ===== Métricas y utilidades =====
    @property
    def total_tareas(self) -> int:
        return self.tareas.count()

    @property
    def tareas_completadas(self) -> int:
        return self.tareas.filter(completada=True).count()

    @property
    def progreso_calculado(self) -> float:
        total = self.total_tareas
        return round((self.tareas_completadas / total) * 100.0, 2) if total else 0.0

    @property
    def avance(self) -> float:
        """
        Avance efectivo mostrado:
        - Si hay 'avance_manual', úsalo.
        - Si no, usa 'progreso_calculado' por tareas.
        """
        return float(self.avance_manual) if self.avance_manual is not None else self.progreso_calculado

    # Útil para mostrar en admin/listas
    def sprints_list(self):
        return ", ".join(str(s) for s in self.sprints.all())
    sprints_list.short_description = "Sprints"

    # Validaciones de consistencia
    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha fin.")
        if self.avance_manual is not None and not (0 <= self.avance_manual <= 100):
            raise ValidationError("El avance manual debe estar entre 0 y 100.")


# ==============================
# Tarea
# ==============================
class Tarea(models.Model):
    MATRIZ_CHOICES = [
        ("UI", "Urgente e Importante"),
        ("NUI", "No Urgente e Importante"),
        ("UNI", "Urgente y No Importante"),
        ("NUNI", "No Urgente y No Importante"),
    ]

    # Estados de workflow
    ESTADO_CHOICES = [
        ("NUEVO", "Nuevo"),
        ("APROBADO", "Aprobado"),
        ("EN_PROGRESO", "En Progreso"),
        ("COMPLETADO", "Completado"),
        ("BLOQUEADO", "Bloqueado"),
    ]

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    criterios_aceptacion = models.TextField(
        blank=True,
        help_text="Criterios que deben cumplirse para cerrar esta tarea"
    )
    categoria = models.CharField(max_length=4, choices=MATRIZ_CHOICES)

    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="NUEVO",
        help_text="Estado actual de la tarea en el workflow"
    )

    # Story points / Puntuación de esfuerzo
    esfuerzo_sp = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[validar_story_points],
        help_text="Story points (1, 2, 3, 5, 8, 13, 21)"
    )

    # FK a Épica (opcional)
    epica = models.ForeignKey(
        Epica, on_delete=models.SET_NULL, null=True, blank=True, related_name="tareas"
    )

    asignado_a = models.ForeignKey(
        Integrante,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas"
    )
    sprint = models.ForeignKey(Sprint, on_delete=models.CASCADE)

    completada = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    informe_cierre = models.FileField(
        upload_to="informes_cierre/",
        blank=True,
        null=True,
        help_text="Archivo requerido para cerrar la tarea"
    )

    def __str__(self):
        return f"{self.titulo} ({self.get_categoria_display()})"

    @property
    def esfuerzo_display(self):
        return self.esfuerzo_sp if self.esfuerzo_sp is not None else "-"


# ==============================
# Evidencia
# ==============================
class Evidencia(models.Model):
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name="evidencias")
    comentario = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to="evidencias/", blank=True, null=True)

    # Permitimos nulos para compatibilidad con datos viejos
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # Fechas
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f"Evidencia de {self.tarea.titulo} ({self.creado_por})"


# ==============================
# Daily
# ==============================
class Daily(models.Model):
    integrante = models.ForeignKey("Integrante", on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    hora = models.TimeField(default=timezone.now)
    que_hizo_ayer = models.TextField()
    que_hara_hoy = models.TextField()
    impedimentos = models.TextField(blank=True, null=True)

    # Campo para marcar registros por fuera de la ventana 5–9 AM
    fuera_horario = models.BooleanField(default=False)

    def __str__(self):
        return f"Daily {self.integrante} - {self.fecha}"
