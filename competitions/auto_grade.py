"""
Автоматическая оценка текстовых отправок: частичные баллы для соответствий и множественного выбора.

Соответствия (match): за каждую верно сопоставленную строку начисляется доля max_score; итог округляется
до целого (школьное правило «чем ближе к полному ответу — тем ближе к max_score»).

Несколько верных вариантов (MC multi): учитывается «чистый» зачёт — верные отмеченные минус лишние отмеченные
неверные; полученное значение сравнивается с числом обязательных правильных вариантов и переводится в баллы.
Один вариант (MC single) остаётся зачёт или незачёт по единственному выбору.
"""

from __future__ import annotations


def solution_status_from_score(score: int) -> str:
    """Автопроверка: при нуле баллов — отклонено, иначе зачтено (в т.ч. частично)."""
    return 'accepted' if score > 0 else 'rejected'


def _task_type_weight(task) -> int:
    tt = getattr(task, 'task_type', None)
    raw = getattr(tt, 'partial_weight_percent', 100) if tt else 100
    try:
        weight = int(raw)
    except (TypeError, ValueError):
        weight = 100
    return max(0, min(100, weight))


def _apply_weight(task, score: int) -> int:
    if score <= 0:
        return 0
    max_sc = max(0, int(getattr(task, 'max_score', 0) or 0))
    weighted = int(round(score * _task_type_weight(task) / 100))
    return max(0, min(max_sc, weighted))


def _partial_enabled(task) -> bool:
    tt = getattr(task, 'task_type', None)
    if not tt:
        return True
    return bool(getattr(tt, 'auto_partial_enabled', True))


def _proportional_points(correct_units: int, total_units: int, max_score: int) -> int:
    if total_units <= 0 or max_score <= 0 or correct_units <= 0:
        return 0
    correct_units = min(correct_units, total_units)
    return min(max_score, int(round(correct_units * max_score / total_units)))


def count_match_correct(task, content: str) -> tuple[int, int]:
    """
    Для типа match: (число верных позиций, число пар в задании).
    Неверная длина ответа или нечисловой фрагмент даёт 0 из n (оценка будет 0).
    """
    if getattr(task.task_type, 'slug', None) != 'match':
        return 0, 0
    pairs = list(task.matching_pairs.all().order_by('order', 'pk'))
    n = len(pairs)
    if n == 0:
        return 0, 0
    parts = [x.strip() for x in (content or '').split(',') if x.strip()]
    if len(parts) != n:
        return 0, n
    ok = 0
    for expected, piece in zip(pairs, parts):
        try:
            if int(piece) == expected.pk:
                ok += 1
        except ValueError:
            pass
    return ok, n


def compute_match_score(task, content: str) -> int:
    ok, n = count_match_correct(task, content)
    if _partial_enabled(task):
        raw = _proportional_points(ok, n, task.max_score)
    else:
        raw = task.max_score if n > 0 and ok == n else 0
    return _apply_weight(task, raw)


def compute_mc_multi_score(task, selected_ids: set) -> int:
    """Частичные баллы за выбор нескольких правильных вариантов."""
    correct_ids = set(task.options.filter(is_correct=True).values_list('pk', flat=True))
    n_req = len(correct_ids)
    max_sc = task.max_score
    if n_req == 0 or max_sc <= 0:
        return 0
    if _partial_enabled(task):
        matched = len(selected_ids & correct_ids)
        wrong_pick = len(selected_ids - correct_ids)
        effective = matched - wrong_pick
        raw = _proportional_points(effective, n_req, max_sc)
    else:
        raw = max_sc if selected_ids == correct_ids else 0
    return _apply_weight(task, raw)


def compute_mc_single_score(task, option_pk: int | None) -> int:
    """Один вариант: полный max_score или 0."""
    if option_pk is None:
        return 0
    opt = task.options.filter(pk=option_pk).first()
    if not opt:
        return 0
    raw = task.max_score if opt.is_correct else 0
    return _apply_weight(task, raw)
