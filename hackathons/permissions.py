"""Права на хакатоны: те же роли, что и для соревнований (организатор / staff)."""
from competitions.permissions import can_create_competition


def can_create_hackathon(user):
    return can_create_competition(user)


def can_edit_hackathon(user, hackathon):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return hackathon.created_by_id == user.id
