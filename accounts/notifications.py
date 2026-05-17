"""Создание внутренних уведомлений (лента без email)."""

from django.contrib.auth import get_user_model

from competitions.models import Participation


def bulk_notify(users_qs_or_ids, *, kind, title, body='', link='', batch_size=500):
    """
    Создать одинаковое уведомление для множества пользователей.
    users_qs_or_ids — QuerySet пользователей или итерируемый id.
    """
    from accounts.models import InAppNotification

    # Нормализуем вход: поддерживаем QuerySet пользователей, список user_id
    # и queryset вида values_list('user_id', flat=True).
    raw_ids = []
    for item in users_qs_or_ids:
        if item is None:
            continue
        if isinstance(item, int):
            raw_ids.append(item)
            continue
        pk = getattr(item, 'pk', None)
        if pk is not None:
            raw_ids.append(pk)
            continue
        try:
            raw_ids.append(int(item))
        except (TypeError, ValueError):
            continue

    if not raw_ids:
        return

    # Защита от "битых" ссылок: уведомляем только реально существующих пользователей.
    User = get_user_model()
    existing_ids = set(
        User.objects.filter(id__in=raw_ids).values_list('id', flat=True)
    )
    if not existing_ids:
        return

    objs = []
    for uid in raw_ids:
        if uid not in existing_ids:
            continue
        objs.append(
            InAppNotification(
                user_id=uid,
                kind=kind,
                title=title,
                body=body or '',
                link=link or '',
            )
        )
        if len(objs) >= batch_size:
            InAppNotification.objects.bulk_create(objs)
            objs = []
    if objs:
        InAppNotification.objects.bulk_create(objs)


def notify_competition_participants(competition_id, *, kind, title, body='', link='', batch_size=500):
    """Все зарегистрированные участники турнира."""
    qs = Participation.objects.filter(competition_id=competition_id).values_list(
        'user_id',
        flat=True,
    ).distinct()
    bulk_notify(qs, kind=kind, title=title, body=body, link=link, batch_size=batch_size)


def unread_count(user):
    if not getattr(user, 'is_authenticated', False):
        return 0
    from accounts.models import InAppNotification

    return (
        InAppNotification.objects.filter(user=user, read_at__isnull=True).count()
    )
