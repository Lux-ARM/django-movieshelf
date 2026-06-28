from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Retourne d[key] dans un template Django."""
    if d is None:
        return ''
    return d.get(key, '')
