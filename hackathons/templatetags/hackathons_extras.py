from django import template

from hackathons.permissions import can_edit_hackathon

register = template.Library()


@register.filter
def user_can_edit_hackathon(hackathon, user):
    return can_edit_hackathon(user, hackathon)
