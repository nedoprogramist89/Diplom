"""Дополнительные шаблонные фильтры и теги для приложения соревнований."""
from django import template

from competitions.permissions import can_edit_competition

register = template.Library()


@register.filter
def user_can_edit_competition(competition, user):
    """Право редактировать соревнование (создатель или staff) — для списка и быстрой смены этапа."""
    return can_edit_competition(user, competition)


@register.filter
def get_item(d, key):
    """Возвращает d[key] или None (для отображения лучшего балла по задаче в списке)."""
    if d is None:
        return None
    return d.get(key)


@register.filter
def solution_display(solution, task):
    """Для заданий «выбрать вариант» возвращает текст выбранного варианта (или вариантов), иначе content."""
    if not solution or not task:
        return solution.content if solution else ''
    if task.is_multiple_choice() and solution.content:
        try:
            from competitions.models import TaskOption
            pks = [x.strip() for x in solution.content.split(',') if x.strip()]
            if not pks:
                return solution.content
            opts = TaskOption.objects.filter(task=task, pk__in=pks).order_by('order', 'pk')
            if getattr(task, 'allow_multiple_answers', False):
                return '; '.join(o.text for o in opts) if opts else solution.content
            opt = opts.first()
            return opt.text if opt else solution.content
        except Exception:
            pass
    if task.is_matching() and solution.content:
        try:
            from competitions.models import TaskMatchingPair

            parts = [x.strip() for x in solution.content.split(',') if x.strip()]
            left_rows = list(task.matching_pairs.all().order_by('order', 'pk'))
            if len(parts) != len(left_rows):
                return solution.content
            by_pk = {p.pk: p for p in TaskMatchingPair.objects.filter(task=task)}
            bits = []
            for lo, piece in zip(left_rows, parts):
                try:
                    pk = int(piece)
                except ValueError:
                    return solution.content
                chosen = by_pk.get(pk)
                label = chosen.right_text if chosen else '?'
                bits.append(f'{lo.left_text} → {label}')
            return ' | '.join(bits)
        except Exception:
            pass
    return solution.content
