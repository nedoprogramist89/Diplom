"""
API: CRUD соревнований, задач, участие, решения, рейтинг.
"""
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Max
from rest_framework.exceptions import ValidationError

from .models import Competition, Task, Participation, Solution, SolutionGradeEvent
from .serializers import (
    CompetitionSerializer,
    TaskSerializer,
    ParticipationSerializer,
    SolutionSerializer,
    SolutionSubmitSerializer,
    ResultEntrySerializer,
)
from .permissions import (
    can_create_competition,
    can_edit_competition,
    can_grade_solutions,
    can_submit_solutions,
    can_view_participants_list,
    is_participant,
)
from .auto_grade import (
    compute_match_score,
    compute_mc_multi_score,
    compute_mc_single_score,
    solution_status_from_score,
)
from .task_visibility import user_can_submit_to_task_scheduled


# ——— Соревнования ———

class CompetitionListCreateAPIView(generics.ListCreateAPIView):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(status__in=('published', 'registration', 'running', 'finished'))
        return qs.order_by('-created_at')

    def create(self, request, *args, **kwargs):
        if not can_create_competition(request.user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Создавать соревнования могут только пользователи с ролью «Организатор» или администратор.')
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class CompetitionRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Competition.objects.all()
    serializer_class = CompetitionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

    def update(self, request, *args, **kwargs):
        comp = self.get_object()
        if not can_edit_competition(request.user, comp):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Редактировать соревнование может только его создатель или администратор.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        comp = self.get_object()
        if not can_edit_competition(request.user, comp):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Удалить соревнование может только его создатель или администратор.')
        return super().destroy(request, *args, **kwargs)


# ——— Задачи ———

class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_queryset(self):
        comp = self.get_competition()
        return comp.tasks.all()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        comp = self.get_competition()
        context['hide_expected_output'] = not can_edit_competition(self.request.user, comp)
        return context

    def check_can_edit(self):
        comp = self.get_competition()
        if not can_edit_competition(self.request.user, comp):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только организатор может создавать/редактировать задачи.')

    def list(self, request, *args, **kwargs):
        comp = self.get_competition()
        if comp.status not in ('published', 'registration', 'running', 'finished') and not can_edit_competition(request.user, comp):
            return Response({'detail': 'Не найдено.'}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        self.check_can_edit()
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(competition=self.get_competition())


class TaskRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return [IsAuthenticated()]
        return [IsAuthenticatedOrReadOnly()]

    def get_queryset(self):
        return Task.objects.select_related('competition')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        task = self.get_object()
        context['hide_expected_output'] = not can_edit_competition(self.request.user, task.competition)
        return context

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_edit_competition(request.user, task.competition):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только организатор может редактировать задачи.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if not can_edit_competition(request.user, task.competition):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только организатор может удалять задачи.')
        return super().destroy(request, *args, **kwargs)


# ——— Участие ———

class ParticipationListAPIView(generics.ListAPIView):
    """Список участников соревнования (создатель соревнования, жюри, staff)."""
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        comp = get_object_or_404(Competition, pk=self.kwargs['competition_id'])
        if not can_view_participants_list(self.request.user, comp):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только организатор соревнования или жюри могут просматривать список участников.')
        return comp.participations.select_related('user')


class MyParticipationsAPIView(generics.ListAPIView):
    """Мои регистрации на соревнования."""
    serializer_class = ParticipationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.participations.select_related('competition')


class RegisterAPIView(APIView):
    """Зарегистрироваться на соревнование."""
    permission_classes = [IsAuthenticated]

    def post(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if not comp.is_registration_open():
            return Response(
                {'detail': 'Регистрация закрыта.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        part, created = Participation.objects.get_or_create(
            user=request.user,
            competition=comp,
        )
        return Response(
            {'detail': 'Вы зарегистрированы.' if created else 'Вы уже были зарегистрированы.'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnregisterAPIView(APIView):
    """Отменить регистрацию."""
    permission_classes = [IsAuthenticated]

    def post(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if not comp.is_registration_open():
            return Response(
                {'detail': 'Нельзя отменить регистрацию после закрытия.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = Participation.objects.filter(user=request.user, competition=comp).delete()
        return Response(
            {'detail': 'Регистрация отменена.' if deleted else 'Вы не были зарегистрированы.'},
            status=status.HTTP_200_OK,
        )


# ——— Решения ———

class SolutionListAPIView(generics.ListAPIView):
    """Список решений по задаче: свои — участник; все — создатель соревнования, жюри, staff."""
    serializer_class = SolutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if can_grade_solutions(self.request.user, task.competition):
            return task.solutions.select_related('user').order_by('-submitted_at')
        return task.solutions.filter(user=self.request.user).select_related('user').order_by('-submitted_at')


class SolutionSubmitAPIView(generics.CreateAPIView):
    """Отправить решение."""
    serializer_class = SolutionSubmitSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, task_id):
        task = get_object_or_404(
            Task.objects.select_related('task_type').prefetch_related(
                'matching_pairs',
                'options',
            ),
            pk=task_id,
        )
        if not can_submit_solutions(request.user, task.competition):
            return Response(
                {'detail': 'Нельзя отправить решение: вы не участник или соревнование не идёт.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user_can_submit_to_task_scheduled(request.user, task):
            return Response(
                {
                    'detail': 'Окно приёма решений по этой задаче закрыто или ещё не открыто.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        solution = Solution(
            user=request.user,
            task=task,
            content=serializer.validated_data['content'],
        )
        tt_slug = getattr(task.task_type, 'slug', None)
        if tt_slug == 'multiple_choice':
            raw = (solution.content or '').strip()
            if getattr(task, 'allow_multiple_answers', False):
                try:
                    ids = {int(x) for x in raw.split(',') if x.strip()}
                except ValueError:
                    ids = set()
                sc = compute_mc_multi_score(task, ids)
            else:
                try:
                    pk = int(raw)
                except ValueError:
                    pk = None
                sc = compute_mc_single_score(task, pk)
            solution.status = solution_status_from_score(sc)
            solution.score = sc
        elif tt_slug == 'match':
            submission = (solution.content or '').strip()
            sc = compute_match_score(task, submission)
            solution.status = solution_status_from_score(sc)
            solution.score = sc
        elif task.expected_output.strip():
            user_answer = solution.content.strip()
            expected = task.expected_output.strip()
            if user_answer == expected:
                solution.status = 'accepted'
                solution.score = task.max_score
            else:
                solution.status = 'rejected'
                solution.score = 0
        solution.save()
        return Response(
            SolutionSerializer(solution).data,
            status=status.HTTP_201_CREATED,
        )


class SolutionRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    """Просмотр/обновление решения (оценка — создатель соревнования, жюри, staff)."""
    serializer_class = SolutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Solution.objects.select_related('user', 'task', 'task__competition')
        sol = qs.filter(pk=self.kwargs.get('pk')).first()
        if not sol:
            return qs.none()
        if can_grade_solutions(self.request.user, sol.task.competition):
            return qs
        return qs.filter(user=self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        sol = self.get_object()
        context['can_grade'] = can_grade_solutions(self.request.user, sol.task.competition)
        return context

    def update(self, request, *args, **kwargs):
        sol = self.get_object()
        if not can_grade_solutions(request.user, sol.task.competition):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Выставлять баллы и статус могут только организатор соревнования, жюри или администратор.')
        new_score = request.data.get('score', None)
        if new_score is not None:
            try:
                score_i = int(new_score)
            except (TypeError, ValueError):
                raise ValidationError({'score': 'Некорректное значение баллов.'})
            if score_i > sol.task.max_score:
                raise ValidationError({'score': f'Баллы не могут превышать максимум задачи ({sol.task.max_score}).'})
        before = {
            'status': sol.status,
            'score': sol.score,
            'comment': sol.comment or '',
        }
        response = super().update(request, *args, **kwargs)
        sol.refresh_from_db(fields=('status', 'score', 'comment'))
        after = {
            'status': sol.status,
            'score': sol.score,
            'comment': sol.comment or '',
        }
        if before != after:
            SolutionGradeEvent.objects.create(
                solution=sol,
                graded_by=request.user,
                from_status=before['status'],
                to_status=after['status'],
                from_score=before['score'],
                to_score=after['score'],
                from_comment=before['comment'],
                to_comment=after['comment'],
                note='Изменение через API',
            )
        return response


# ——— Рейтинг ———

class CompetitionResultsAPIView(APIView):
    """Таблица результатов соревнования (участники и сумма баллов)."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if comp.status not in ('running', 'finished'):
            return Response({'detail': 'Результаты пока недоступны.'}, status=status.HTTP_404_NOT_FOUND)
        participations = comp.participations.select_related('user')
        result = []
        for p in participations:
            by_task = (
                Solution.objects
                .filter(user=p.user, task__competition=comp)
                .values('task')
                .annotate(best=Max('score'))
            )
            total = sum(x['best'] for x in by_task)
            result.append({
                'user_id': p.user.id,
                'username': p.user.username,
                'total_score': total,
            })
        result.sort(key=lambda x: -x['total_score'])
        serializer = ResultEntrySerializer(result, many=True)
        return Response(serializer.data)
