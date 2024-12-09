from django import template

from acctmarket.utils.choices import Rating

register = template.Library()


@register.filter
def star_rating(value):
    try:
        rating = Rating(value)
    except (ValueError, TypeError):
        rating = Rating.THREE_STARS
    else:
        return rating.label

    return rating
