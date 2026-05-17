"""
Разграничение прав по ролям.

Роли (accounts.User.role):
  • participant (Участник) — по умолчанию. Может: регистрироваться на соревнования, отправлять решения,
    смотреть свои решения и результаты. Не может: создавать соревнования, редактировать задачи/соревнования,
    смотреть чужие решения, выставлять баллы.
  • organizer (Организатор) — может всё то же + создавать соревнования и полностью управлять ими
    (редактирование, задачи, объявления, список участников, оценка решений). Редактирует только свои соревнования.
  • jury (Жюри) — может всё то же, что участник + просмотр всех решений и участников по любому соревнованию,
    выставление баллов/статуса/комментариев. Не может: создавать соревнования, редактировать соревнования и задачи.
  • staff (is_staff) — полный доступ + панель управления /admin/.

Функции проверки: can_create_competition (только organizer/staff), can_edit_competition (только создатель/staff),
can_grade_solutions (создатель соревнования, jury или staff), can_view_participants_list (создатель, jury, staff).
"""
from django.contrib.auth.mixins import UserPassesTestMixin
from rest_framework.permissions import BasePermission

from .models import Competition, Participation


def _role(user):
    if not user or not user.is_authenticated:
        return None
    return getattr(user, 'role', None)


def can_create_competition(user):
    """Создавать соревнования могут только организатор или staff."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return _role(user) == 'organizer'


def can_edit_competition(user, competition):
    """Редактировать соревнование и задачи может только создатель этого соревнования или staff."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return competition.created_by_id == user.id


def can_view_tasks(user, competition):
    """Задачи видят все, если соревнование опубликовано/идёт/завершено; черновик — только редактор."""
    if competition.status in ('published', 'registration', 'running', 'finished'):
        return True
    return can_edit_competition(user, competition)


def can_grade_solutions(user, competition):
    """Просматривать все решения и выставлять баллы/статус могут создатель соревнования, жюри или staff."""
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    if competition.created_by_id == user.id:
        return True
    return _role(user) == 'jury'


def can_view_all_solutions(user, competition):
    """Видеть список всех решений по задачам соревнования — те же, кто может оценивать."""
    return can_grade_solutions(user, competition)


def can_view_participants_list(user, competition):
    """Список участников видят создатель соревнования, жюри и staff (для проверки и оценки)."""
    return can_edit_competition(user, competition) or can_grade_solutions(user, competition)


def is_participant(user, competition):
    """Пользователь зарегистрирован на соревнование."""
    if not user.is_authenticated:
        return False
    return Participation.objects.filter(competition=competition, user=user).exists()


def can_submit_solutions(user, competition):
    """Отправлять решения может зарегистрированный участник, когда соревнование идёт."""
    if not user.is_authenticated:
        return False
    if not competition.is_running():
        return False
    return is_participant(user, competition)


class IsOrganizerOrReadOnly(BasePermission):
    """Изменять объект может только создатель соревнования или staff (для DRF)."""

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        competition = getattr(obj, 'competition', obj)
        if not isinstance(competition, Competition):
            return False
        return can_edit_competition(request.user, competition)


class CanEditCompetitionMixin(UserPassesTestMixin):
    """Mixin для CBV: доступ только у создателя соревнования или staff."""

    def test_func(self):
        competition = self.get_competition()
        return competition and can_edit_competition(self.request.user, competition)

    def get_competition(self):
        """Переопределить в наследнике: вернуть Competition по self.kwargs или self.object."""
        if hasattr(self, 'object') and self.object:
            return getattr(self.object, 'competition', self.object)
        return None


class CanCreateCompetitionMixin(UserPassesTestMixin):
    """Mixin для CBV: доступ только у организатора или staff (создание соревнования)."""

    def test_func(self):
        return can_create_competition(self.request.user)


class CanGradeSolutionsMixin(UserPassesTestMixin):
    """Mixin для CBV: доступ только у создателя соревнования, жюри или staff (просмотр всех решений, оценка)."""

    def test_func(self):
        competition = self.get_competition()
        return competition and can_grade_solutions(self.request.user, competition)

    def get_competition(self):
        """Переопределить в наследнике."""
        return None


class CanViewParticipantsListMixin(UserPassesTestMixin):
    """Mixin для CBV: список участников видят создатель, жюри, staff."""

    def test_func(self):
        competition = self.get_competition()
        return competition and can_view_participants_list(self.request.user, competition)

    def get_competition(self):
        """Переопределить в наследнике."""
        return None
