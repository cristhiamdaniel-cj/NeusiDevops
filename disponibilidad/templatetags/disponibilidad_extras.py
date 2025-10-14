from django import template

register = template.Library()

@register.filter
def dict_lookup(dictionary, key):
    """Permite acceder a un diccionario con una clave variable en templates"""
    if dictionary is None:
        return None
    return dictionary.get(key)
