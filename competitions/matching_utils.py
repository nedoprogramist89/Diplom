"""Совместимость: полная правильность соответствия (все пары верны)."""

from .auto_grade import count_match_correct


def match_solution_content_is_correct(task, content: str) -> bool:
    if getattr(task.task_type, 'slug', None) != 'match':
        return False
    ok, n = count_match_correct(task, content)
    return n > 0 and ok == n
