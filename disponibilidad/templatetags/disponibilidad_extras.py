# disponibilidad/templatetags/disponibilidad_extras.py
from django import template
from datetime import timedelta

register = template.Library()

@register.filter
def add_days(d, n):
    """Suma n días a una fecha (d + n)."""
    try:
        return d + timedelta(days=int(n))
    except Exception:
        return d
