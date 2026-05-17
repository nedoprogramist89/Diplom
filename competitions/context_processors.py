"""
Контекст для шаблонов: права по ролям (для отображения кнопок в шапке и т.д.).
"""
from .permissions import can_create_competition


def roles(request):
    """Добавляет в контекст флаги прав для текущего пользователя."""
    return {
        'user_can_create_competition': can_create_competition(request.user) if request.user.is_authenticated else False,
    }
