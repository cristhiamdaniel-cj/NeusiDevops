from django import template
register = template.Library()

@register.filter
def index(lst, i):
    try:
        return lst[int(i)]
    except Exception:
        return None
