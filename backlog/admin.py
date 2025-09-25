from django.contrib import admin
from .models import Sprint

@admin.register(Sprint)
class SprintAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "inicio", "fin")
    list_filter = ("inicio", "fin")
    search_fields = ("nombre",)
