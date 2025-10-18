from django.contrib import admin
from .models import Integrante, Sprint, Epica, Tarea, Evidencia, Daily, Proyecto


# ==========================
# Integrante
# ==========================
@admin.register(Integrante)
class IntegranteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rol")
    search_fields = ("user__username", "user__first_name", "user__last_name", "rol")
    list_filter = ("rol",)
    ordering = ("user__username",)


# ==========================
# Sprint
# ==========================
@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "inicio", "fin")
    list_filter = ("inicio", "fin")
    search_fields = ("nombre",)
    ordering = ("-inicio",)
# ==========================
# Proyecto y Epica
# ==========================

@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "activo", "creado_en")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")

@admin.register(Epica)
class EpicaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo", "titulo", "proyecto", "estado", "prioridad",
        "progreso",      # <- método de esta clase
        "sprints_list", "creada_en"
    )
    list_filter = ("proyecto", "estado", "prioridad")
    search_fields = ("codigo", "titulo", "descripcion", "kpis")
    autocomplete_fields = ("proyecto", "owner", "sprints")
    readonly_fields = ("progreso", "creada_en", "actualizada_en")  # <- aquí también

    @admin.display(description="Avance (%)")
    def progreso(self, obj):
        # usa la propiedad 'avance' del modelo (manual o calculado)
        return f"{obj.avance:.0f}%"

# ==========================
# Tarea
# ==========================
@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "titulo", "epica", "categoria", "estado",
        "asignado_a", "sprint", "completada", "fecha_cierre"
    )
    search_fields = ("titulo", "descripcion", "asignado_a__user__username", "epica__titulo")
    list_filter = ("categoria", "estado", "completada", "sprint", "epica")
    autocomplete_fields = ("asignado_a", "sprint", "epica")
    date_hierarchy = "fecha_cierre"
    ordering = ("-id",)
    readonly_fields = ("fecha_cierre",)

    fieldsets = (
        ("Información básica", {
            "fields": ("epica", "titulo", "descripcion", "criterios_aceptacion")
        }),
        ("Asignación", {
            "fields": ("categoria", "estado", "asignado_a", "sprint", "completada")
        }),
        ("Cierre", {
            "fields": ("informe_cierre", "fecha_cierre"),
            "classes": ("collapse",),
        }),
    )


# ==========================
# Evidencia
# ==========================
@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ("id", "tarea", "comentario_resumen", "creado_por", "creado_en")
    search_fields = ("tarea__titulo", "comentario", "creado_por__username")
    list_filter = ("creado_en",)
    autocomplete_fields = ("tarea", "creado_por")
    date_hierarchy = "creado_en"
    ordering = ("-creado_en",)

    def comentario_resumen(self, obj):
        return (obj.comentario[:70] + "...") if obj.comentario and len(obj.comentario) > 70 else obj.comentario
    comentario_resumen.short_description = "Comentario"


# ==========================
# Daily
# ==========================
@admin.register(Daily)
class DailyAdmin(admin.ModelAdmin):
    list_display = ("id", "integrante", "fecha", "hora", "fuera_horario")
    search_fields = ("integrante__user__username", "integrante__user__first_name")
    list_filter = ("fuera_horario", "fecha")
    ordering = ("-fecha", "-hora")
