from django import template

register = template.Library()

@register.filter(name='pluck')
def pluck(iterable, attr):
    if iterable is None:
        return []

    result = []

    for item in iterable:
        try:
            value = item
            for part in attr.split('__'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
                    if callable(value):
                        value = value()
            result.append(value)
        except:
            result.append(None)

    return result
