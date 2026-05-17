"""
Окно доступности задачи по датам opens_at / closes_at (поверх статуса соревнования).
Редактирование и жюри видят условие всегда; участникам и гостям — по расписанию.
"""
from django.utils import timezone

from .permissions import can_edit_competition, can_grade_solutions, can_submit_solutions


def task_schedule_gate(task):
    """
    Состояние расписания без учёта ролей.
    Возвращает одно из: 'before_open' | 'open' | 'closed'.
    """
    now = timezone.now()
    if task.opens_at and now < task.opens_at:
        return 'before_open'
    if task.closes_at and now > task.closes_at:
        return 'closed'
    return 'open'


def user_bypasses_task_schedule_for_view(user, competition):
    """Организатор / жюри / staff — полный просмотр условия вне окна."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, 'is_staff', False):
        return True
    if can_edit_competition(user, competition):
        return True
    if can_grade_solutions(user, competition):
        return True
    return False


def user_can_view_task_content(user, task):
    """Показывать ли полный текст условия."""
    if user_bypasses_task_schedule_for_view(user, task.competition):
        return True
    return task_schedule_gate(task) == 'open'


def user_can_submit_to_task_scheduled(user, task):
    """
    Можно ли отправить решение с учётом окна задачи.
    Staff может обойти окно (сервисные случаи).
    """
    if not can_submit_solutions(user, task.competition):
        return False
    if user and getattr(user, 'is_staff', False):
        return True
    return task_schedule_gate(task) == 'open'
