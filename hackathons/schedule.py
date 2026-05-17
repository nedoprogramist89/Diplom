"""Фазы хакатона для визуальной шкалы на странице (не жёсткий state machine)."""


def get_hackathon_phases(hackathon):
    """
    Возвращает список dict: title, description, date_line, state
    state: past | current | future (как у соревнований — общие стили шкалы)
    """
    from django.utils import timezone

    now = timezone.now()
    phases = []

    def state_for(opened, closed):
        if closed and now > closed:
            return 'past'
        if opened and now < opened:
            return 'future'
        if opened and closed and opened <= now <= closed:
            return 'current'
        if opened and not closed and now >= opened:
            return 'current'
        if not opened and not closed:
            return 'future'
        return 'past'

    reg_open = hackathon.registration_opens_at
    reg_close = hackathon.registration_closes_at
    phases.append({
        'key': 'registration',
        'title': 'Регистрация',
        'description': 'Подай заявку, укажи команду или отметь «ищу команду».',
        'date_line': _fmt_range(reg_open, reg_close),
        'state': state_for(reg_open, reg_close),
    })

    hack_open = hackathon.starts_at
    hack_close = hackathon.ends_at
    phases.append({
        'key': 'hacking',
        'title': 'Хакинг',
        'description': 'Разработка прототипа, менторство, интеграции.',
        'date_line': _fmt_range(hack_open, hack_close),
        'state': state_for(hack_open, hack_close),
    })

    wrap_line = hackathon.ends_at.strftime('%d.%m.%Y %H:%M') if hackathon.ends_at else 'После хакинга'
    if hackathon.is_finished():
        wrap_state = 'past'
    elif hackathon.ends_at and now > hackathon.ends_at:
        wrap_state = 'current'
    else:
        wrap_state = 'future'
    phases.append({
        'key': 'wrap',
        'title': 'Демо и итоги',
        'description': 'Питчи перед жюри, награждение, нетворкинг.',
        'date_line': wrap_line,
        'state': wrap_state,
    })

    if hackathon.status == hackathon.STATUS_FINISHED:
        for i, p in enumerate(phases):
            p['state'] = 'current' if i == len(phases) - 1 else 'past'
    return phases


def _fmt_range(a, b):
    if not a and not b:
        return 'Даты уточняются'
    if a and b:
        return f'{a.strftime("%d.%m.%Y %H:%M")} — {b.strftime("%d.%m.%Y %H:%M")}'
    if a:
        return f'с {a.strftime("%d.%m.%Y %H:%M")}'
    if b:
        return f'до {b.strftime("%d.%m.%Y %H:%M")}'
    return '—'
