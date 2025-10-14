from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)
