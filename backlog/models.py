from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import time as dtime

def now_local_time():
    # Evita usar lambda en defaults (no se serializa en migraciones)
    return timezone.localtime().time()
# ==============================
# Validadores
# ==============================
def validar_story_points(value):
    """
    Story points usuales (Fibonacci corta). Permite nulo.
    """
    if value is None:
        return
    validos = (1, 2, 3, 5, 8, 13, 21)
    if value not in validos:
        raise ValidationError(
            f"Los story points deben ser uno de: {', '.join(map(str, validos))}."
        )

# ==============================
# Integrante
# ==============================
class Integrante(models.Model):
    """
    Perfil 1:1 con User. Los permisos se derivan del campo 'rol'.
    """
    # === Roles canónicos usados en la app ===
    ROL_SM_PO = "Scrum Master / PO"
    ROL_ARQ_DIR = "Arquitecto de Software y Director General"
    ROL_GH = "Coordinadora de Gestión Humana y Administrativa"
    # === Roles dueños de producto visualizan solo su proyecto ===
    ROL_VISUALIZADOR = "Visualizador"
    ROL_PO_COOFISAM = "Product Owner Coofisam360"
    ROL_PO = "Product Owner"

    # (Opcionales) otros roles existentes en tu base actual
    ROL_DBA = "Administrador de Bases de Datos (DBA)"
    ROL_LIDER_COMERCIAL = "Líder Comercial"
    ROL_BI = "Especialista en Visualización y BI"
    ROL_DEV_FE = "Desarrollador Frontend"
    ROL_DEV_BE = "Desarrollador Backend"
    ROL_MKT = "Coordinadora de Marketing y Comunicación"
    ROL_CONTABLE = "Contadora General"
    ROL_MIEMBRO = "Miembro"  # fallback

    ROL_CHOICES = [
        (ROL_SM_PO, ROL_SM_PO),
        (ROL_ARQ_DIR, ROL_ARQ_DIR),
        (ROL_GH, ROL_GH),

        (ROL_VISUALIZADOR, ROL_VISUALIZADOR),
        (ROL_PO, ROL_PO),
        (ROL_PO_COOFISAM, ROL_PO_COOFISAM),

        # — Opcionales/actuales en tu BD —
        (ROL_DBA, ROL_DBA),
        (ROL_LIDER_COMERCIAL, ROL_LIDER_COMERCIAL),
        (ROL_BI, ROL_BI),
        (ROL_DEV_FE, ROL_DEV_FE),
        (ROL_DEV_BE, ROL_DEV_BE),
        (ROL_MKT, ROL_MKT),

        (ROL_CONTABLE, ROL_CONTABLE),
        (ROL_MIEMBRO, ROL_MIEMBRO),
    ]

    # Matriz de permisos por rol (explícita)
    ROL_PERMISOS = {
        # Admins (full)
        ROL_SM_PO: {"crear_tareas", "agregar_evidencias", "editar_tareas"},
        ROL_ARQ_DIR: {"crear_tareas", "agregar_evidencias", "editar_tareas"},
        ROL_GH: {"crear_tareas", "agregar_evidencias", "editar_tareas"},

        # Visualizadores (solo lectura)
        ROL_VISUALIZADOR: set(),
        ROL_PO: set(),
        ROL_PO_COOFISAM: set(),

        # Resto de roles → sin permisos de admin (ven solo lo propio por lógica de views)
        ROL_DBA: set(),
        ROL_LIDER_COMERCIAL: set(),
        ROL_BI: set(),
        ROL_DEV_FE: set(),
        ROL_DEV_BE: set(),
        ROL_MKT: set(),
        # (¡Ojo! No repetir ROL_GH aquí)
        ROL_CONTABLE: set(),
        ROL_MIEMBRO: set(),
    }

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="integrante")
    rol = models.CharField(max_length=100, choices=ROL_CHOICES, default=ROL_MIEMBRO, blank=False)

    class Meta:
        managed = False

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    # ===== Helpers de rol =====
    def _perms(self):
        return self.ROL_PERMISOS.get(self.rol, set())

    def es_visualizador(self) -> bool:
        return self.rol in {self.ROL_VISUALIZADOR, self.ROL_PO, self.ROL_PO_COOFISAM}

    def es_admin(self) -> bool:
        # Admin operativo: Scrum/PO, Arq/Director, Gestión Humana, o superuser
        return self.rol in {self.ROL_SM_PO, self.ROL_ARQ_DIR, self.ROL_GH} or getattr(self.user, "is_superuser", False)

    # ===== Permisos consultados por las views =====
    def puede_crear_tareas(self) -> bool:
        return "crear_tareas" in self._perms() or self.es_admin()

    def puede_agregar_evidencias(self) -> bool:
        return "agregar_evidencias" in self._perms() or self.es_admin()

    def puede_editar_tareas(self) -> bool:
        return "editar_tareas" in self._perms() or self.es_admin()

# ==============================
# Permisos de Proyecto para visualizadores o dueños de producto
# ==============================
class PermisoProyecto(models.Model):
    integrante = models.ForeignKey(
        "Integrante",
        on_delete=models.CASCADE,
        related_name="permisos_proyectos"
    )
    proyecto = models.ForeignKey(
        "Proyecto",
        on_delete=models.CASCADE,
        related_name="permisos_integrantes"
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = "backlog_permisoproyecto"
        managed = False
        unique_together = ("integrante", "proyecto")

    def __str__(self):
        estado = "Activo" if self.activo else "Inactivo"
        return f"{self.integrante} → {self.proyecto} ({estado})"

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
        managed = False

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

# ==============================
# Sprint
# ==============================
class Sprint(models.Model):
    nombre = models.CharField(max_length=50, default="Sprint")
    inicio = models.DateField()
    fin = models.DateField()

    class Meta:
        managed = False

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

    # Código legible (opcional)
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

    # Proyecto
    proyecto = models.ForeignKey(
        "Proyecto",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="epicas",
        help_text="Proyecto al que pertenece esta épica."
    )

    # Fechas macro
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    # KPIs / criterios de éxito
    kpis = models.TextField(blank=True, help_text="Métricas clave esperadas para la épica")

    # Avance manual (0–100). Si no se define, se calcula por tareas.
    avance_manual = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="0–100. Si se deja vacío, se calcula por tareas."
    )

    # Documentación
    documentos_url = models.URLField(blank=True, help_text="Enlace a carpeta o documento maestro")

    # Responsable único (legado)
    owner = models.ForeignKey(
        "Integrante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="epicas_propias"
    )
    # Varios responsables (nuevo)
    owners = models.ManyToManyField(
        "Integrante",
        blank=True,
        related_name="epicas_cocreadas",
        help_text="Responsables/co-owners de la épica"
    )

    # Puede abarcar varios sprints
    sprints = models.ManyToManyField("Sprint", blank=True, related_name="epicas")

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada_en"]
        managed = False

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
        """Si hay 'avance_manual', úsalo; si no, usa cálculo por tareas."""
        return float(self.avance_manual) if self.avance_manual is not None else self.progreso_calculado

    def sprints_list(self):
        return ", ".join(str(s) for s in self.sprints.all())
    sprints_list.short_description = "Sprints"

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError("La fecha de inicio no puede ser posterior a la fecha fin.")
        if self.avance_manual is not None and not (0 <= self.avance_manual <= 100):
            raise ValidationError("El avance manual debe estar entre 0 y 100.")

# ==============================
# Tarea (tratada como Macro por proceso, sin campos nuevos)
# ==============================
class Tarea(models.Model):
    MATRIZ_CHOICES = [
        ("UI", "Urgente e Importante"),
        ("NUI", "No Urgente e Importante"),
        ("UNI", "Urgente y No Importante"),
        ("NUNI", "No Urgente y No Importante"),
    ]

    ESTADO_CHOICES = [
        ("NUEVO", "Nuevo"),
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

    # Story points
    esfuerzo_sp = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[validar_story_points],
        help_text="Story points (1, 2, 3, 5, 8, 13, 21)"
    )

    # Épica (1-N: una épica, muchas tareas)
    epica = models.ForeignKey(
        "Epica",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas"
    )

    # Varios responsables (nuevo)
    asignados = models.ManyToManyField(
        "Integrante",
        blank=True,
        related_name="tareas_asignadas"
    )

    # Responsable único (legado/compatibilidad)
    asignado_a = models.ForeignKey(
        "Integrante",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tareas_asignadas_legacy"
    )

    sprint = models.ForeignKey("Sprint", on_delete=models.CASCADE)

    completada = models.BooleanField(default=False)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    informe_cierre = models.FileField(
        upload_to="informes_cierre/",
        blank=True,
        null=True,
        help_text="Archivo requerido para cerrar la tarea"
    )

    class Meta:
        managed = False

    def __str__(self):
        return f"{self.titulo} ({self.get_categoria_display()})"

    @property
    def esfuerzo_display(self):
        return self.esfuerzo_sp if self.esfuerzo_sp is not None else "-"

    @property
    def responsables_list(self):
        """Nombres de todos los responsables M2M (o '—' si no hay)."""
        nombres = [str(i) for i in self.asignados.all()]
        return ", ".join(nombres) if nombres else "—"

    # Estos helpers no crean tablas; solo calculan si existieran "bloques" relacionados
    # en otra app/fase. Si no existen, siguen devolviendo (0, 0) y no rompen nada.
    def bloques_cerrados(self):
        if not hasattr(self, "bloques"):
            return (0, 0)
        total = self.bloques.count()
        cerrados = 0
        for b in self.bloques.all():
            qs = getattr(b, "subtareas", None)
            if qs is None:
                continue
            qs = qs.all()
            if qs.exists() and not qs.exclude(estado='cerrada').exists():
                cerrados += 1
        return (cerrados, total)

    def puede_cerrarse_por_bloques(self):
        cerrados, total = self.bloques_cerrados()
        return total > 0 and cerrados == total

# ==============================
# Evidencia
# ==============================
class Evidencia(models.Model):
    tarea = models.ForeignKey("Tarea", on_delete=models.CASCADE, related_name="evidencias")
    comentario = models.TextField(blank=True, null=True)
    archivo = models.FileField(upload_to="evidencias/", blank=True, null=True)

    # Permitimos nulos para compatibilidad con datos viejos
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    # Fechas
    creado_en = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False

    def __str__(self):
        return f"Evidencia de {self.tarea.titulo} ({self.creado_por})"

# ==============================
# Daily
# ==============================
class Daily(models.Model):
    """
    Cabecera del Daily por integrante y fecha.
    Conserva campos legacy, pero promueve registrar líneas en DailyItem.
    """
    integrante = models.ForeignKey("Integrante", on_delete=models.CASCADE, related_name="dailies")
    fecha = models.DateField(default=timezone.localdate)
    hora = models.TimeField(default=now_local_time) # hora de registro

    # --- Legacy (compatibilidad). Puedes dejarlos vacíos si usas DailyItem. ---
    que_hizo_ayer = models.TextField(blank=True, default="")
    que_hara_hoy = models.TextField(blank=True, default="")
    impedimentos = models.TextField(blank=True, null=True)

    # Reglas de negocio
    fuera_horario = models.BooleanField(default=False)  # se recalcula en save()

    # Contexto opcional para filtros/reporte
    sprint = models.ForeignKey("Sprint", on_delete=models.SET_NULL, null=True, blank=True, related_name="dailies")

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backlog_daily"        
        managed = False                    
        constraints = [
            models.UniqueConstraint(fields=("integrante", "fecha"), name="uniq_daily_integrante_fecha"),
        ]
        indexes = [
            models.Index(fields=["fecha"], name="idx_daily_fecha"),
            models.Index(fields=["integrante", "fecha"], name="idx_daily_int_fec"),
        ]

    def __str__(self):
        return f"Daily {self.integrante} - {self.fecha}"

    # ---- Ventana de registro (5:00 a 9:00 hora local) ----
    @staticmethod
    def _en_ventana(hora_local: dtime) -> bool:
        return dtime(5, 0, 0) <= hora_local <= dtime(9, 0, 0)

    def save(self, *args, **kwargs):
        # Recalcular fuera_horario automáticamente según hora de registro
        h = self.hora or timezone.localtime().time()
        self.fuera_horario = not self._en_ventana(h)
        super().save(*args, **kwargs)

    # ---- Métricas de alineación calculadas a partir de DailyItem ----
    @property
    def total_items(self) -> int:
        return self.items.count()

    @property
    def alineacion(self) -> dict:
        """
        Retorna métricas de alineación:
        {
            'porcentaje': int,
            'total': int,
            'alineados': int,
            'no_alineados': int,
            'ids_no_alineados': [ids de DailyItem],
        }
        Regla:
        - Item alineado si:
          a) tiene tarea/subtarea
          b) el responsable coincide con el integrante del daily
          c) y (fecha del daily está dentro de [inicio..fin] del bloque/subtarea/tarea
             o sprint del item == sprint del daily si ambos existen)
        """
        total = self.total_items
        if total == 0:
            return dict(porcentaje=0, total=0, alineados=0, no_alineados=0, ids_no_alineados=[])

        no_ok = []
        f = self.fecha
        s_daily = self.sprint_id

        qs = self.items.select_related("tarea", "subtarea", "subtarea__bloque", "subtarea__responsable", "tarea__asignado_a", "tarea__sprint")
        for it in qs:
            objetivo = it.subtarea or it.tarea
            if not objetivo:
                no_ok.append(it.id); continue

            # Dueño esperado
            responsable = getattr(objetivo, "responsable", None) or getattr(objetivo, "asignado_a", None)
            ok_user = (responsable_id(objetivo) == self.integrante_id)

            # Ventana temporal
            ini, fin = fechas_objetivo(objetivo)
            ok_fecha = (ini is not None and fin is not None and ini <= f <= fin)

            # Sprint
            s_item = getattr(objetivo, "sprint_id", None)
            ok_sprint = (s_daily is not None and s_item is not None and s_daily == s_item)

            if not (ok_user and (ok_fecha or ok_sprint)):
                no_ok.append(it.id)

        alineados = total - len(no_ok)
        pct = round(100 * alineados / total)
        return dict(
            porcentaje=pct,
            total=total,
            alineados=alineados,
            no_alineados=len(no_ok),
            ids_no_alineados=no_ok,
        )


def responsable_id(obj) -> int | None:
    # Subtarea: responsable_id ; Tarea: asignado_a_id (legacy)
    rid = getattr(obj, "responsable_id", None)
    if rid:
        return rid
    return getattr(obj, "asignado_a_id", None)


def fechas_objetivo(obj):
    """
    Devuelve (inicio, fin) para validar la fecha del Daily.
    - Subtarea: usa fecha_inicio/fecha_fin propios; si no, hereda del Bloque.
    - Tarea: intenta inferir de bloques (si existen) o None/None.
    """
    from datetime import date
    ini = getattr(obj, "fecha_inicio", None)
    fin = getattr(obj, "fecha_fin", None)

    # Si es Subtarea y no tiene fechas, usar rango del bloque
    bloque = getattr(obj, "bloque", None)
    if bloque is not None:
        if ini is None and hasattr(bloque, "fecha_inicio"):
            ini = bloque.fecha_inicio
        if fin is None and hasattr(bloque, "fecha_fin"):
            fin = bloque.fecha_fin

    # Si es Tarea y no hay fechas, intentar obtener el min/max de sus bloques
    if getattr(obj, "bloques", None) is not None and (ini is None or fin is None):
        qs = obj.bloques.all()
        if qs.exists():
            min_ini = min((b.fecha_inicio for b in qs if b.fecha_inicio), default=None)
            max_fin = max((b.fecha_fin for b in qs if b.fecha_fin), default=None)
            ini = ini or min_ini
            fin = fin or max_fin

    # Fallback: sin información temporal
    return ini, fin


TIPO_ITEM = [
    ("AYER", "Ayer"),
    ("HOY", "Hoy"),
]

class DailyItem(models.Model):
    """
    Línea del Daily. Puede ser libre o enlazada a Tarea/Subtarea.
    """
    daily = models.ForeignKey(Daily, on_delete=models.CASCADE, related_name="items")
    tipo = models.CharField(max_length=4, choices=TIPO_ITEM)
    descripcion = models.TextField(blank=True, default="")

    # Enlaces opcionales (mutuamente excluyentes)
    tarea = models.ForeignKey("Tarea", on_delete=models.SET_NULL, null=True, blank=True, related_name="daily_items")
    subtarea = models.ForeignKey("Subtarea", on_delete=models.SET_NULL, null=True, blank=True, related_name="daily_items")

    # Esfuerzo/tiempo (opcional)
    minutos = models.PositiveIntegerField(null=True, blank=True)

    # Evidencia simple (URL) o integra luego tu modelo de Evidencia
    evidencia_url = models.URLField(blank=True, default="")

    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "backlog_dailyitem"     # nueva tabla
        managed = False
        indexes = [
            models.Index(fields=["daily_id"], name="idx_ditem_daily"),
            models.Index(fields=["tipo"], name="idx_ditem_tipo"),
            models.Index(fields=["tarea_id"], name="idx_ditem_tarea"),
            models.Index(fields=["subtarea_id"], name="idx_ditem_subtarea"),
        ]

    def __str__(self):
        ref = self.subtarea or self.tarea or "Libre"
        return f"[{self.tipo}] {ref} — {self.descripcion[:40]}"

    def clean(self):
        # Validación de exclusión: tarea XOR subtarea (o ninguna)
        if self.tarea_id and self.subtarea_id:
            raise ValidationError("Seleccione solo Tarea o Subtarea (no ambas).")

    @property
    def es_libre(self) -> bool:
        return not (self.tarea_id or self.subtarea_id)
# =====================================================================
# Bloques y Subtareas dentro de Tarea (macro)
# =====================================================================

ESTADO_SUBTAREA = [
    ('pendiente', 'Pendiente'),
    ('en_progreso', 'En progreso'),
    ('entregada', 'Entregada'),
    ('cerrada', 'Cerrada'),
]

class BloqueTarea(models.Model):
    """
    Bloques que componen una Tarea macro (HU).
    Las fechas deben estar dentro del rango del Sprint de la Tarea.
    """
    tarea = models.ForeignKey("Tarea", on_delete=models.CASCADE, related_name="bloques")
    indice = models.PositiveSmallIntegerField(help_text="Orden del bloque dentro de la tarea (1,2,3,...)")
    nombre = models.CharField(max_length=80, blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        ordering = ['indice', 'id']
        unique_together = (('tarea', 'indice'),)
        managed = False
        db_table = "backlog_bloquetarea"

    def __str__(self):
        return f"{self.tarea.titulo} / {self.etiqueta()}"

    def etiqueta(self):
        return self.nombre or f"Bloque {self.indice}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Coherencia básica
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError('En el bloque, la fecha de inicio no puede ser posterior a la fecha fin.')

        # Validar contra el sprint SOLO si ambas fechas existen
        if self.tarea_id and self.tarea and self.tarea.sprint_id:
            sprint = self.tarea.sprint
            if self.fecha_inicio and self.fecha_fin:
                if self.fecha_inicio < sprint.inicio or self.fecha_fin > sprint.fin:
                    raise ValidationError('Las fechas del bloque deben estar dentro del rango del Sprint de la tarea macro.')

        # Evitar solapamientos SOLO si hay fechas
        if self.fecha_inicio and self.fecha_fin:
            qs = BloqueTarea.objects.filter(tarea_id=self.tarea_id)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            for other in qs:
                if other.fecha_inicio and other.fecha_fin:
                    # hay intersección si inicio <= fin_otro y fin >= inicio_otro
                    if self.fecha_inicio <= other.fecha_fin and self.fecha_fin >= other.fecha_inicio:
                        raise ValidationError('Este bloque se solapa con otro bloque de la misma tarea.')

    @property
    def dias_restantes(self):
        from django.utils import timezone
        return (self.fecha_fin - timezone.localdate()).days

    @property
    def semaforo(self):
        d = self.dias_restantes
        if d > 3:
            return 'verde'
        if 1 < d <= 3:
            return 'amarillo'
        return 'rojo'


class Subtarea(models.Model):
    """
    Subtareas (HUs chicas) dentro de un bloque.
    """
    ESTADOS = [
        ("NUEVO", "Nuevo"),
        ("EN_PROGRESO", "En progreso"),
        ("BLOQUEADO", "Bloqueado"),
        ("COMPLETADO", "Completado"),
    ]

    ESFUERZO_CORTO = [
        (1, "1"),
        (2, "2"),
        (3, "3"),
        (5, "5"),
    ]

    bloque = models.ForeignKey(BloqueTarea, on_delete=models.CASCADE, related_name='subtareas')
    titulo = models.CharField(max_length=160)
    responsable = models.ForeignKey("Integrante", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='subtareas_responsable')
    estado = models.CharField(max_length=20, choices=ESTADO_SUBTAREA, default='pendiente')
    descripcion = models.TextField(blank=True)
    esfuerzo_sp = models.PositiveSmallIntegerField(choices=ESFUERZO_CORTO, null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['bloque__indice', 'id']
        managed = False
        db_table = "backlog_subtarea"

    def __str__(self):
        return f"{self.titulo} ({self.bloque.etiqueta()})"

    @property
    def tarea(self):
        return self.bloque.tarea

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_inicio and self.fecha_fin and self.fecha_inicio > self.fecha_fin:
            raise ValidationError('En la Subtarea, la fecha de inicio no puede ser posterior a la fecha fin.')
        if self.fecha_inicio and (self.fecha_inicio < self.bloque.fecha_inicio or self.fecha_inicio > self.bloque.fecha_fin):
            raise ValidationError('La fecha de inicio debe estar dentro del rango del bloque.')
        if self.fecha_fin and (self.fecha_fin < self.bloque.fecha_inicio or self.fecha_fin > self.bloque.fecha_fin):
            raise ValidationError('La fecha de fin debe estar dentro del rango del bloque.')

# Evidencias específicas de una Subtarea
from django.contrib.auth import get_user_model
User = get_user_model()

class EvidenciaSubtarea(models.Model):
    subtarea   = models.ForeignKey(Subtarea, on_delete=models.CASCADE, related_name="evidencias")
    comentario = models.TextField(blank=True)
    archivo    = models.FileField(upload_to="evidencias_subtareas/%Y/%m", blank=True, null=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name="evid_subt_creador")
    creado_en  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-creado_en",)

    def __str__(self):
        return f"Evidencia ST#{self.subtarea_id} {self.creado_en:%Y-%m-%d %H:%M}"
