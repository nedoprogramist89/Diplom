"""
Фазы соревнования для блока расписания на странице турнира.

Порядок совпадает с логической цепочкой статусов Competition.status.
"""

from django.utils import timezone


STATUS_SEQUENCE = ('draft', 'published', 'registration', 'running', 'finished')

PHASE_META = {
    'draft': (
        'Черновик',
        'Подготовка: турнир не показывается участникам в общем режиме.',
    ),
    'published': (
        'Анонс',
        'Опубликовано на платформе; регистрация ещё не открыта.',
    ),
    'registration': (
        'Регистрация',
        'Участники записываются на соревнование.',
    ),
    'running': (
        'Основной раунд',
        'Открыты задачи и приём решений.',
    ),
    'finished': (
        'Завершено',
        'Итоги и просмотр результатов.',
    ),
}


def get_competition_schedule_phases(competition):
    """
    Список фаз с полями: slug, title, description, state (past|current|future), date_line.
    """
    cur = competition.status
    try:
        cur_idx = STATUS_SEQUENCE.index(cur)
    except ValueError:
        cur_idx = 0

    now = timezone.now()
    phases = []
    for i, slug in enumerate(STATUS_SEQUENCE):
        title, description = PHASE_META[slug]
        if i < cur_idx:
            state = 'past'
        elif i == cur_idx:
            state = 'current'
        else:
            state = 'future'

        date_line = ''
        if slug == 'published' and competition.start_time:
            date_line = f'Планируемый старт раунда: {competition.start_time}'
        elif slug == 'registration' and competition.start_time:
            date_line = f'Начало соревнования (план): {competition.start_time}'
        elif slug == 'running':
            if competition.start_time:
                date_line = f'Старт: {competition.start_time}'
            if competition.end_time:
                suffix = f' · Финиш: {competition.end_time}'
                date_line = (date_line + suffix) if date_line else f'Финиш: {competition.end_time}'
        elif slug == 'finished' and competition.end_time:
            date_line = f'Окончание: {competition.end_time}'

        # Подсказка «сейчас» относительно дат (мягкая, без жёсткой автосмены статуса)
        if state == 'current' and slug == 'running' and competition.end_time and now > competition.end_time:
            date_line = (date_line + ' · ') if date_line else ''
            date_line += 'По календарю время раунда истекло — проверьте статус турнира.'

        phases.append(
            {
                'slug': slug,
                'title': title,
                'description': description,
                'state': state,
                'date_line': date_line.strip(),
            }
        )
    return phases
