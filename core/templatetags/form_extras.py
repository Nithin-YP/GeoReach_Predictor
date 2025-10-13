from django import template  # type: ignore

register = template.Library()

@register.filter
def add_class(field, css_class):
    """Add CSS class to form field"""
    try:
        return field.as_widget(attrs={"class": css_class})
    except AttributeError:
        return field