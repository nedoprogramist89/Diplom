"""
Контекст для шаблонов: тема оформления текущего пользователя.
"""
from .notifications import unread_count


def theme(request):
    if request.user.is_authenticated:
        return {'user_theme': getattr(request.user, 'theme', None) or 'dark'}
    return {'user_theme': 'dark'}


def notifications(request):
    return {'unread_notifications_count': unread_count(request.user)}
