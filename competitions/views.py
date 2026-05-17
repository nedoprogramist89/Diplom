"""
Веб-представления: соревнования, задачи, участие, решения, рейтинг.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    View,
)
from django.urls import reverse_lazy, reverse
from django.db.models import Max, Count, Q, F
from django.http import HttpResponse, Http404
from django.forms import modelformset_factory
from django.utils import timezone
from django.utils.text import slugify
from django.template.loader import render_to_string
import csv
from io import StringIO

from .auto_grade import (
    compute_match_score,
    compute_mc_multi_score,
    compute_mc_single_score,
    solution_status_from_score,
)
from .models import (
    Competition,
    Task,
    Participation,
    Solution,
    SolutionGradeEvent,
    Announcement,
    Subject,
    TaskType,
    TaskOption,
    TaskMatchingPair,
)
from .forms import (
    SolutionSubmitForm,
    CompetitionForm,
    TaskForm,
    TaskOptionForm,
    TaskMatchingPairFormSet,
    TaskMatchingPairFormSetForPost,
)
from .schedule import get_competition_schedule_phases
from .permissions import (
    can_create_competition,
    can_edit_competition,
    can_view_tasks,
    can_submit_solutions,
    can_grade_solutions,
    is_participant,
    CanEditCompetitionMixin,
    CanGradeSolutionsMixin,
    CanViewParticipantsListMixin,
)
from .task_visibility import (
    task_schedule_gate,
    user_can_view_task_content,
    user_can_submit_to_task_scheduled,
)


def _task_schedule_maps(user, tasks):
    gates, view_ok, submit_ok = {}, {}, {}
    for t in tasks:
        gates[t.pk] = task_schedule_gate(t)
        view_ok[t.pk] = user_can_view_task_content(user, t)
        submit_ok[t.pk] = user_can_submit_to_task_scheduled(user, t)
    return gates, view_ok, submit_ok


def home_view(request):
    """Главная страница."""
    from django.db.models import Count

    from hackathons.models import Hackathon

    stats = {
        'competitions_count': Competition.objects.filter(
            status__in=('published', 'registration', 'running', 'finished')
        ).count(),
        'participants_count': Participation.objects.values('user').distinct().count(),
    }
    recent = Competition.objects.filter(
        status__in=('published', 'registration', 'running')
    ).order_by('-created_at')[:6]
    hackathons_recent = Hackathon.objects.filter(
        status__in=(
            Hackathon.STATUS_PUBLISHED,
            Hackathon.STATUS_REGISTRATION,
            Hackathon.STATUS_ONGOING,
        )
    ).order_by('-starts_at', '-created_at')[:4]
    hackathons_count = Hackathon.objects.filter(
        status__in=(
            Hackathon.STATUS_PUBLISHED,
            Hackathon.STATUS_REGISTRATION,
            Hackathon.STATUS_ONGOING,
            Hackathon.STATUS_FINISHED,
        )
    ).count()
    my_active = []
    if request.user.is_authenticated:
        my_active = (
            Participation.objects
            .filter(user=request.user, competition__status__in=('registration', 'running'))
            .select_related('competition')
            .order_by('-registered_at')[:10]
        )
    event_feed = []
    now = timezone.now()
    for c in Competition.objects.filter(
        status__in=('registration', 'running', 'published')
    ).order_by('start_time', '-created_at')[:8]:
        when = c.start_time or c.created_at
        event_feed.append(
            {
                'kind': 'competition',
                'title': c.title,
                'status': c.get_status_display(),
                'when': when,
                'is_past': bool(when and when < now),
                'url': reverse('competitions:detail', kwargs={'pk': c.pk}),
            }
        )
    for h in Hackathon.objects.filter(
        status__in=(Hackathon.STATUS_REGISTRATION, Hackathon.STATUS_ONGOING, Hackathon.STATUS_PUBLISHED)
    ).order_by('starts_at', '-created_at')[:8]:
        when = h.starts_at or h.registration_opens_at or h.created_at
        event_feed.append(
            {
                'kind': 'hackathon',
                'title': h.title,
                'status': h.get_status_display(),
                'when': when,
                'is_past': bool(when and when < now),
                'url': reverse('hackathons:detail', kwargs={'pk': h.pk}),
            }
        )
    event_feed.sort(key=lambda x: x['when'] or now)
    quick_actions = [
        {'label': 'Публичные результаты', 'url': reverse('competitions:public_results')},
        {'label': 'Архив мероприятий', 'url': reverse('competitions:archive')},
    ]
    if request.user.is_authenticated:
        quick_actions.append({'label': 'Мои участия', 'url': reverse('accounts:profile')})
        if can_create_competition(request.user):
            quick_actions.append({'label': 'Создать соревнование', 'url': reverse('competitions:create')})
            quick_actions.append({'label': 'Создать хакатон', 'url': reverse('hackathons:create')})
    return render(request, 'competitions/home.html', {
        'stats': stats,
        'recent_competitions': recent,
        'hackathons_recent': hackathons_recent,
        'hackathons_count': hackathons_count,
        'my_active_participations': my_active,
        'event_feed': event_feed[:12],
        'quick_actions': quick_actions,
    })


class CompetitionListView(ListView):
    model = Competition
    context_object_name = 'competitions'
    template_name = 'competitions/competition_list.html'
    paginate_by = 10

    def get_queryset(self):
        qs = (
            Competition.objects.filter(status__in=('published', 'registration', 'running', 'finished'))
            .select_related('created_by')
            .annotate(
                task_count=Count('tasks', distinct=True),
                participant_count=Count('participations', distinct=True),
            )
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        status = self.request.GET.get('status', '').strip()
        if status and status in ('published', 'registration', 'running', 'finished'):
            qs = qs.filter(status=status)
        audience = self.request.GET.get('audience', '').strip()
        if audience and audience in {v for v, _ in Competition.AUDIENCE_CHOICES}:
            qs = qs.filter(audience=audience)
        level = self.request.GET.get('level', '').strip()
        if level and level in {v for v, _ in Competition.LEVEL_CHOICES}:
            qs = qs.filter(level=level)
        age_raw = self.request.GET.get('age', '').strip()
        if age_raw:
            try:
                age = int(age_raw)
            except ValueError:
                age = None
            if age is not None and age >= 0:
                qs = qs.filter(
                    Q(min_age__isnull=True) | Q(min_age__lte=age),
                    Q(max_age__isnull=True) | Q(max_age__gte=age),
                )
        only_free = self.request.GET.get('only_free', '').strip() in ('1', 'true', 'on')
        if only_free:
            qs = qs.filter(Q(max_participants__isnull=True) | Q(participant_count__lt=F('max_participants')))
        return qs.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_q'] = self.request.GET.get('q', '')
        context['search_status'] = self.request.GET.get('status', '')
        context['search_audience'] = self.request.GET.get('audience', '')
        context['search_level'] = self.request.GET.get('level', '')
        context['search_age'] = self.request.GET.get('age', '')
        context['search_only_free'] = self.request.GET.get('only_free', '')
        context['competition_status_choices'] = Competition.STATUS_CHOICES
        context['competition_audience_choices'] = Competition.AUDIENCE_CHOICES
        context['competition_level_choices'] = Competition.LEVEL_CHOICES
        return context


class CompetitionDetailView(DetailView):
    model = Competition
    context_object_name = 'competition'
    template_name = 'competitions/competition_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_edit'] = can_edit_competition(self.request.user, self.object)
        context['can_grade'] = can_grade_solutions(self.request.user, self.object)
        context['is_participant'] = is_participant(self.request.user, self.object)
        context['can_register'] = (
            self.request.user.is_authenticated
            and not context['is_participant']
            and self.object.is_registration_open()
        )
        context['can_submit'] = can_submit_solutions(self.request.user, self.object)
        context['tasks_visible'] = can_view_tasks(self.request.user, self.object)
        tl = []
        if context['tasks_visible']:
            tl = list(self.object.tasks.select_related('subject', 'task_type').all())
        context['task_list'] = tl
        gates, _, submit_ok = _task_schedule_maps(self.request.user, tl)
        context['task_schedule_gates'] = gates
        context['task_submit_scheduled'] = submit_ok
        context['announcements'] = self.object.announcements.all()[:10]
        context['schedule_phases'] = get_competition_schedule_phases(self.object)
        context['competition_status_choices'] = Competition.STATUS_CHOICES
        return context


def _redirect_quick_status(request, default):
    nxt = (request.POST.get('next') or '').strip()
    if nxt.startswith('/') and not nxt.startswith('//'):
        return redirect(nxt)
    return redirect(default)


class CompetitionQuickStatusView(LoginRequiredMixin, View):
    """Смена статуса (этапа) соревнования без полной формы редактирования."""

    def post(self, request, pk):
        competition = get_object_or_404(Competition, pk=pk)
        if not can_edit_competition(request.user, competition):
            messages.error(request, 'Нет прав для смены этапа.')
            return redirect('competitions:detail', pk=pk)
        new_status = (request.POST.get('status') or '').strip()
        valid = {c for c, _ in Competition.STATUS_CHOICES}
        if new_status not in valid:
            messages.error(request, 'Некорректный этап.')
            return redirect('competitions:detail', pk=pk)
        if competition.status == new_status:
            messages.info(request, 'Этап уже установлен.')
            return _redirect_quick_status(request, reverse('competitions:detail', kwargs={'pk': pk}))
        competition.status = new_status
        competition.save()
        messages.success(request, f'Этап соревнования: «{competition.get_status_display()}».')
        return _redirect_quick_status(request, reverse('competitions:detail', kwargs={'pk': pk}))


class CompetitionCreateView(LoginRequiredMixin, CreateView):
    """Создавать соревнования могут только пользователи с ролью «Организатор» или staff."""
    model = Competition
    form_class = CompetitionForm
    template_name = 'competitions/competition_form.html'
    success_url = reverse_lazy('competitions:list')

    def dispatch(self, request, *args, **kwargs):
        if not can_create_competition(request.user):
            messages.error(
                request,
                'Создавать соревнования могут только пользователи с ролью «Организатор». '
                'Обратитесь к администратору для смены роли.'
            )
            return redirect('competitions:list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class CompetitionUpdateView(LoginRequiredMixin, UpdateView):
    model = Competition
    form_class = CompetitionForm
    context_object_name = 'competition'
    template_name = 'competitions/competition_form.html'
    success_url = reverse_lazy('competitions:list')

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs


class CompetitionDeleteView(LoginRequiredMixin, DeleteView):
    model = Competition
    context_object_name = 'competition'
    template_name = 'competitions/competition_confirm_delete.html'
    success_url = reverse_lazy('competitions:list')

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs


# ——— Задачи (доступ только у организатора/создателя) ———

class TaskListView(LoginRequiredMixin, ListView):
    """Список задач соревнования (видят участники и гости, если соревнование открыто)."""
    model = Task
    context_object_name = 'tasks'
    template_name = 'competitions/task_list.html'
    paginate_by = 20

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_queryset(self):
        comp = self.get_competition()
        if not can_view_tasks(self.request.user, comp):
            return Task.objects.none()
        qs = comp.tasks.select_related('subject', 'task_type').all()
        subject_id = self.request.GET.get('subject', '').strip()
        if subject_id and subject_id.isdigit():
            qs = qs.filter(subject_id=int(subject_id))
        task_type_id = self.request.GET.get('task_type', '').strip()
        if task_type_id and task_type_id.isdigit():
            qs = qs.filter(task_type_id=int(task_type_id))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comp = self.get_competition()
        context['competition'] = comp
        context['can_edit'] = can_edit_competition(self.request.user, comp)
        context['can_grade'] = can_grade_solutions(self.request.user, comp)
        context['can_submit'] = can_submit_solutions(self.request.user, comp)
        context['task_best_scores'] = {}
        if self.request.user.is_authenticated and comp:
            best = (
                Solution.objects
                .filter(task__competition=comp, user=self.request.user)
                .values('task')
                .annotate(best=Max('score'))
            )
            context['task_best_scores'] = {x['task']: x['best'] for x in best}
        context['subjects'] = Subject.objects.all()
        context['task_types'] = TaskType.objects.all()
        try:
            context['filter_subject_id'] = int(self.request.GET.get('subject', 0)) or None
        except (ValueError, TypeError):
            context['filter_subject_id'] = None
        try:
            context['filter_task_type_id'] = int(self.request.GET.get('task_type', 0)) or None
        except (ValueError, TypeError):
            context['filter_task_type_id'] = None
        gs, vw, sb = _task_schedule_maps(self.request.user, list(context['tasks']))
        context['task_schedule_gates'] = gs
        context['task_can_view_body'] = vw
        context['task_submit_scheduled'] = sb
        return context


class TaskDetailView(DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'competitions/task_detail.html'

    def get_queryset(self):
        qs = (
            Task.objects.select_related(
                'competition', 'subject', 'task_type',
            )
            .prefetch_related('options', 'matching_pairs')
        )
        pk = self.kwargs.get(self.pk_url_kwarg)
        task = qs.filter(pk=pk).first() if pk else None
        if not task:
            return Task.objects.none()
        if not can_view_tasks(self.request.user, task.competition):
            return Task.objects.none()
        return qs.filter(pk=pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comp = self.object.competition
        context['competition'] = comp
        context['can_edit'] = can_edit_competition(self.request.user, comp)
        context['can_grade'] = can_grade_solutions(self.request.user, comp)
        context['can_submit'] = can_submit_solutions(self.request.user, comp)
        context['task_schedule_gate'] = task_schedule_gate(self.object)
        context['can_view_task_body'] = user_can_view_task_content(self.request.user, self.object)
        context['can_submit_task_now'] = user_can_submit_to_task_scheduled(
            self.request.user,
            self.object,
        )
        context['matching_pairs'] = (
            self.object.matching_pairs.all().order_by('order', 'pk')
            if self.object.is_matching()
            else TaskMatchingPair.objects.none()
        )
        context['show_matching_key'] = context['can_edit'] or context['can_grade']
        return context


def _purge_task_collections_not_for_slug(task_obj, slug):
    """При смене типа задачи убирает варианты MC и пары соответствий, не относящиеся к выбранному типу."""
    if slug != 'multiple_choice':
        TaskOption.objects.filter(task=task_obj).delete()
    if slug != 'match':
        TaskMatchingPair.objects.filter(task=task_obj).delete()


class TaskCreateView(LoginRequiredMixin, CanEditCompetitionMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'competitions/task_form.html'

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['competition'] = self.get_competition()
        context['subjects'] = Subject.objects.all()
        context['task_types'] = TaskType.objects.all()
        context['option_formset'] = TaskOptionFormSet(
            queryset=TaskOption.objects.none(),
            prefix='options',
        )
        context['match_pair_formset'] = TaskMatchingPairFormSet(
            queryset=TaskMatchingPair.objects.none(),
            prefix='match_pairs',
        )
        context['task'] = None
        return context

    def post(self, request, *args, **kwargs):
        competition = self.get_competition()
        form = TaskForm(request.POST, request.FILES)

        tt_raw = request.POST.get('task_type')
        try:
            tt_pk = int(tt_raw)
        except (TypeError, ValueError):
            tt_pk = None
        mc = tt_pk is not None and TaskType.objects.filter(pk=tt_pk, slug='multiple_choice').exists()
        is_match = tt_pk is not None and TaskType.objects.filter(pk=tt_pk, slug='match').exists()

        formset = (
            TaskOptionFormSetForPost(request.POST, queryset=TaskOption.objects.none(), prefix='options')
            if mc
            else None
        )
        match_formset = (
            TaskMatchingPairFormSetForPost(
                request.POST,
                queryset=TaskMatchingPair.objects.none(),
                prefix='match_pairs',
            )
            if is_match
            else None
        )

        formsets_ok = (formset is None or formset.is_valid()) and (
            match_formset is None or match_formset.is_valid()
        )
        if form.is_valid() and formsets_ok:
            self.object = form.save(commit=False)
            self.object.competition_id = competition.pk
            self.object.save()
            slug = getattr(self.object.task_type, 'slug', None)

            if slug == 'multiple_choice' and formset:
                for option in formset.save(commit=False):
                    if getattr(option, 'text', '').strip():
                        option.task_id = self.object.pk
                        option.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                formset.save_m2m()
            elif slug == 'match' and match_formset:
                for row in match_formset.save(commit=False):
                    lt = (row.left_text or '').strip()
                    rt = (row.right_text or '').strip()
                    if not lt or not rt:
                        continue
                    row.task_id = self.object.pk
                    row.save()
                for obj in match_formset.deleted_objects:
                    obj.delete()
                match_formset.save_m2m()

            _purge_task_collections_not_for_slug(self.object, slug)

            messages.success(request, 'Задача создана.')
            return redirect(self.get_success_url())

        context = self.get_context_data(form=form)
        context['option_formset'] = formset if mc else None
        context['match_pair_formset'] = match_formset if is_match else None
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('competitions:task_list', kwargs={'competition_id': self.get_competition().pk})


# Для отображения — 1 дополнительная строка; при POST принимаем до 20 форм
TaskOptionFormSet = modelformset_factory(
    TaskOption,
    form=TaskOptionForm,
    extra=2,
    can_delete=True,
    fields=('text', 'is_correct', 'order'),
)
TaskOptionFormSetForPost = modelformset_factory(
    TaskOption,
    form=TaskOptionForm,
    extra=30,
    can_delete=True,
    fields=('text', 'is_correct', 'order'),
)


class TaskUpdateView(LoginRequiredMixin, CanEditCompetitionMixin, UpdateView):
    model = Task
    form_class = TaskForm
    context_object_name = 'task'
    template_name = 'competitions/task_form.html'

    def get_competition(self):
        obj = self.get_object()
        return obj.competition if obj else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['competition'] = self.object.competition
        context['subjects'] = Subject.objects.all()
        context['task_types'] = TaskType.objects.all()
        if self.object and self.object.is_multiple_choice():
            context['option_formset'] = TaskOptionFormSet(
                queryset=self.object.options.all(),
                prefix='options',
            )
            context['task'] = self.object
        else:
            context['option_formset'] = None
        if self.object and self.object.is_matching():
            context['match_pair_formset'] = TaskMatchingPairFormSet(
                queryset=self.object.matching_pairs.all(),
                prefix='match_pairs',
            )
            context.setdefault('task', self.object)
        else:
            context['match_pair_formset'] = None
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        tt_raw = request.POST.get('task_type')
        try:
            tt_pk = int(tt_raw)
        except (TypeError, ValueError):
            tt_pk = None
        requested_mc = tt_pk is not None and TaskType.objects.filter(
            pk=tt_pk, slug='multiple_choice'
        ).exists()
        requested_match = tt_pk is not None and TaskType.objects.filter(pk=tt_pk, slug='match').exists()
        formset = None
        match_formset = None
        if requested_mc:
            formset = TaskOptionFormSetForPost(
                request.POST,
                queryset=self.object.options.all(),
                prefix='options',
            )
        elif requested_match:
            match_formset = TaskMatchingPairFormSetForPost(
                request.POST,
                queryset=self.object.matching_pairs.all(),
                prefix='match_pairs',
            )
        mc_ok = formset is None or formset.is_valid()
        match_ok = match_formset is None or match_formset.is_valid()
        if form.is_valid() and mc_ok and match_ok:
            self.object = form.save()
            slug = getattr(self.object.task_type, 'slug', None)
            if slug == 'multiple_choice' and formset:
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.task = self.object
                    obj.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                formset.save_m2m()
            elif slug == 'match' and match_formset:
                for row in match_formset.save(commit=False):
                    lt = (row.left_text or '').strip()
                    rt = (row.right_text or '').strip()
                    if not lt or not rt:
                        continue
                    row.task = self.object
                    row.save()
                for obj in match_formset.deleted_objects:
                    obj.delete()
                match_formset.save_m2m()
            _purge_task_collections_not_for_slug(self.object, slug)
            messages.success(request, 'Задача сохранена.')
            return redirect(self.get_success_url())
        context = self.get_context_data(form=form)
        context['option_formset'] = formset if requested_mc else None
        context['match_pair_formset'] = match_formset if requested_match else None
        return self.render_to_response(context)

    def get_success_url(self):
        return reverse('competitions:task_list', kwargs={'competition_id': self.object.competition_id})


class TaskDeleteView(LoginRequiredMixin, CanEditCompetitionMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    template_name = 'competitions/task_confirm_delete.html'

    def get_competition(self):
        obj = self.get_object()
        return obj.competition if obj else None

    def get_success_url(self):
        return reverse('competitions:task_list', kwargs={'competition_id': self.object.competition_id})


# ——— Участие (регистрация на соревнование) ———

class RegisterParticipationView(LoginRequiredMixin, View):
    """Зарегистрироваться на соревнование."""

    def post(self, request, competition_id):
        competition = get_object_or_404(
            Competition.objects.annotate(participant_count=Count('participations')),
            pk=competition_id,
        )
        if not competition.is_registration_open():
            messages.error(request, 'Регистрация на это соревнование закрыта.')
            return redirect('competitions:detail', pk=competition_id)
        if is_participant(request.user, competition):
            messages.info(request, 'Вы уже зарегистрированы.')
            return redirect('competitions:detail', pk=competition_id)
        if competition.max_participants is not None and competition.participant_count >= competition.max_participants:
            messages.error(request, 'Достигнут лимит участников.')
            return redirect('competitions:detail', pk=competition_id)
        Participation.objects.get_or_create(user=request.user, competition=competition)
        messages.success(request, 'Вы зарегистрированы на соревнование.')
        return redirect('competitions:detail', pk=competition_id)


class UnregisterParticipationView(LoginRequiredMixin, View):
    """Отменить регистрацию (только пока регистрация открыта)."""

    def post(self, request, competition_id):
        competition = get_object_or_404(Competition, pk=competition_id)
        if not competition.is_registration_open():
            messages.error(request, 'Нельзя отменить регистрацию после закрытия.')
            return redirect('competitions:detail', pk=competition_id)
        Participation.objects.filter(user=request.user, competition=competition).delete()
        messages.success(request, 'Регистрация отменена.')
        return redirect('competitions:detail', pk=competition_id)


class CompetitionCertificateView(LoginRequiredMixin, DetailView):
    model = Competition

    def _build_context(self, competition):
        is_joined = Participation.objects.filter(
            user=self.request.user,
            competition=competition,
        ).exists()
        if not is_joined:
            raise Http404('Сертификат доступен только зарегистрированным участникам.')
        if competition.status != 'finished':
            raise Http404('Сертификат появляется после завершения соревнования.')
        best_score = (
            Solution.objects.filter(user=self.request.user, task__competition=competition)
            .aggregate(best=Max('score'))
            .get('best')
            or 0
        )
        return {
            'competition': competition,
            'issued_to': self.request.user,
            'issued_at': timezone.now(),
            'best_score': best_score,
            'certificate_code': f'CERT-{competition.pk}-{self.request.user.pk}',
            'download_name': (
                f'certificate_{competition.pk}_{slugify(self.request.user.username) or self.request.user.pk}.html'
            ),
        }

    def get(self, request, *args, **kwargs):
        competition = self.get_object()
        context = self._build_context(competition)
        html = render_to_string('competitions/certificate.html', context, request=request)
        resp = HttpResponse(html, content_type='text/html; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="{context["download_name"]}"'
        return resp


class CompetitionParticipantsView(LoginRequiredMixin, CanViewParticipantsListMixin, ListView):
    """Список участников соревнования (создатель, жюри, staff)."""
    model = Participation
    context_object_name = 'participants'
    template_name = 'competitions/competition_participants.html'
    paginate_by = 50

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_queryset(self):
        competition = self.get_competition()
        return competition.participations.select_related('user').order_by('registered_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        competition = self.get_competition()
        context['competition'] = competition
        context['total_participants'] = competition.participations.count()
        return context


# ——— Решения ———

class SolutionSubmitView(LoginRequiredMixin, CreateView):
    model = Solution
    template_name = 'competitions/solution_form.html'

    def dispatch(self, request, *args, **kwargs):
        task = get_object_or_404(
            Task.objects.select_related('competition').prefetch_related(
                'options',
                'matching_pairs',
            ),
            pk=self.kwargs['task_id'],
        )
        if not user_can_submit_to_task_scheduled(request.user, task):
            messages.error(
                request,
                'Сейчас нельзя отправить решение по этой задаче: окно приёма закрыто или ещё не открыто, '
                'либо вы не участник активного тура.',
            )
            return redirect('competitions:task_detail', pk=task.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_task(self):
        return get_object_or_404(
            Task.objects.select_related('task_type').prefetch_related(
                'options',
                'matching_pairs',
            ),
            pk=self.kwargs['task_id'],
        )

    def get_form_class(self):
        return SolutionSubmitForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['task'] = self.get_task()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = self.get_task()
        context['competition'] = context['task'].competition
        return context

    def form_valid(self, form):
        task = self.get_task()
        if not user_can_submit_to_task_scheduled(self.request.user, task):
            messages.error(
                self.request,
                'Отправить решение сейчас нельзя: окно задачи закрыто или вы не можете участвовать.',
            )
            return redirect('competitions:task_detail', pk=task.pk)
        form.instance.user = self.request.user
        form.instance.task = task
        if task.is_multiple_choice():
            if getattr(task, 'allow_multiple_answers', False):
                selected_ids = set(
                    int(x) for x in form.cleaned_data['content'].split(',') if x.strip()
                )
                sc = compute_mc_multi_score(task, selected_ids)
                form.instance.status = solution_status_from_score(sc)
                form.instance.score = sc
            else:
                opt = form.cleaned_data.get('selected_option')
                if opt:
                    form.instance.content = str(opt.pk)
                    sc = compute_mc_single_score(task, opt.pk)
                    form.instance.status = solution_status_from_score(sc)
                    form.instance.score = sc
                else:
                    form.instance.status = 'rejected'
                    form.instance.score = 0
        elif task.is_matching():
            submission = (form.cleaned_data.get('content') or '').strip()
            form.instance.content = submission
            sc = compute_match_score(task, submission)
            form.instance.status = solution_status_from_score(sc)
            form.instance.score = sc
        elif task.expected_output.strip():
            user_answer = form.cleaned_data['content'].strip()
            expected = task.expected_output.strip()
            if user_answer == expected:
                form.instance.status = 'accepted'
                form.instance.score = task.max_score
            else:
                form.instance.status = 'rejected'
                form.instance.score = 0
        response = super().form_valid(form)
        messages.success(self.request, 'Решение отправлено.')
        return response

    def get_success_url(self):
        return reverse('competitions:task_detail', kwargs={'pk': self.object.task_id})


class MySolutionsListView(LoginRequiredMixin, ListView):
    """Мои решения по задаче (участник видит только свои)."""
    model = Solution
    context_object_name = 'solutions'
    template_name = 'competitions/solution_list.html'
    paginate_by = 20

    def get_queryset(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not can_view_tasks(self.request.user, task.competition):
            return Solution.objects.none()
        return Solution.objects.filter(task=task, user=self.request.user).order_by('-submitted_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = get_object_or_404(Task, pk=self.kwargs['task_id'])
        context['competition'] = context['task'].competition
        context['can_grade'] = can_grade_solutions(self.request.user, context['competition'])
        return context


class AllSolutionsForTaskView(LoginRequiredMixin, CanGradeSolutionsMixin, ListView):
    """Все решения по задаче (для жюри и организатора — проверка и оценка)."""
    model = Solution
    context_object_name = 'solutions'
    template_name = 'competitions/solution_list_all.html'
    paginate_by = 25

    def get_competition(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        return task.competition

    def get_queryset(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not can_grade_solutions(self.request.user, task.competition):
            return Solution.objects.none()
        return Solution.objects.filter(task=task).select_related('user').order_by('-submitted_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        context['task'] = task
        context['competition'] = task.competition
        return context


class SolutionGradeView(LoginRequiredMixin, UpdateView):
    """Оценка решения: статус, баллы, комментарий (жюри и создатель соревнования)."""
    model = Solution
    fields = ('status', 'score', 'comment')
    context_object_name = 'solution'
    template_name = 'competitions/solution_grade.html'

    def get_queryset(self):
        qs = Solution.objects.select_related('task', 'task__competition', 'user')
        sol = qs.filter(pk=self.kwargs.get('pk')).first()
        if not sol or not can_grade_solutions(self.request.user, sol.task.competition):
            return Solution.objects.none()
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = self.object.task
        context['competition'] = self.object.task.competition
        context['grade_history'] = self.object.grade_events.select_related('graded_by')[:15]
        return context

    def form_valid(self, form):
        task_max = self.object.task.max_score
        if form.cleaned_data.get('score', 0) > task_max:
            form.add_error('score', f'Баллы не могут превышать максимум задачи ({task_max}).')
            return self.form_invalid(form)
        before = {
            'status': self.object.status,
            'score': self.object.score,
            'comment': self.object.comment or '',
        }
        response = super().form_valid(form)
        sol = self.object
        after = {
            'status': sol.status,
            'score': sol.score,
            'comment': sol.comment or '',
        }
        if before != after:
            SolutionGradeEvent.objects.create(
                solution=sol,
                graded_by=self.request.user,
                from_status=before['status'],
                to_status=after['status'],
                from_score=before['score'],
                to_score=after['score'],
                from_comment=before['comment'],
                to_comment=after['comment'],
                note='Изменение через веб-форму',
            )
        title = sol.task.title
        from accounts.notifications import bulk_notify

        body = (
            f'Баллы: {sol.score}. '
            f'{sol.get_status_display()}. '
            + (sol.comment or '').strip()
        ).strip()
        bulk_notify(
            [sol.user_id],
            kind='grade',
            title=f'Задача «{title}»: результат проверки',
            body=body[:1900],
            link=reverse('competitions:task_detail', kwargs={'pk': sol.task_id}),
        )
        return response

    def get_success_url(self):
        return reverse('competitions:solution_list_all', kwargs={'task_id': self.object.task_id})


# ——— Рейтинг / результаты ———

class PublicResultsHubView(ListView):
    """Публичный список соревнований, у которых доступна таблица результатов."""
    template_name = 'competitions/public_results_hub.html'
    context_object_name = 'competitions'
    paginate_by = 20

    def get_queryset(self):
        return (
            Competition.objects.filter(status__in=('running', 'finished'))
            .select_related('created_by')
            .annotate(participant_count=Count('participations', distinct=True))
            .order_by('-end_time', '-start_time', '-created_at')
        )


class EventsArchiveView(ListView):
    """Архив завершённых соревнований и хакатонов (публичный)."""
    template_name = 'competitions/events_archive.html'
    context_object_name = 'competitions_finished'
    paginate_by = 20

    def get_queryset(self):
        return (
            Competition.objects.filter(status='finished')
            .annotate(participant_count=Count('participations', distinct=True))
            .order_by('-end_time', '-created_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from hackathons.models import Hackathon

        context['hackathons_finished'] = (
            Hackathon.objects.filter(status=Hackathon.STATUS_FINISHED)
            .annotate(reg_count=Count('registrations', distinct=True))
            .order_by('-ends_at', '-created_at')[:50]
        )
        return context

class CompetitionResultsView(ListView):
    """Таблица результатов соревнования: участники и сумма баллов."""
    template_name = 'competitions/competition_results.html'
    context_object_name = 'results'
    paginate_by = 50

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_queryset(self):
        comp = self.get_competition()
        if comp.status not in ('running', 'finished'):
            return []
        participations = comp.participations.select_related('user')
        result = []
        for p in participations:
            # Сумма лучших баллов по каждой задаче (любая отправка, берём max score по задаче)
            by_task = (
                Solution.objects
                .filter(user=p.user, task__competition=comp)
                .values('task')
                .annotate(best=Max('score'))
            )
            total = sum(x['best'] for x in by_task)
            result.append({
                'user': p.user,
                'total_score': total,
                'participant': p,
            })
        result.sort(key=lambda x: -x['total_score'])
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        comp = self.get_competition()
        context['competition'] = comp
        context['can_edit'] = can_edit_competition(self.request.user, comp)
        # Для участника — его место и баллы (по полному списку до пагинации)
        results_list = list(self.get_queryset())
        context['my_result'] = None
        if self.request.user.is_authenticated and results_list:
            for i, r in enumerate(results_list, 1):
                if r['user'].pk == self.request.user.pk:
                    context['my_result'] = {'place': i, 'total': r['total_score'], 'total_participants': len(results_list)}
                    break
        return context


class CompetitionResultsExportCSVView(LoginRequiredMixin, View):
    """Экспорт результатов соревнования в CSV (только организатор / staff)."""

    def get(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if not can_edit_competition(request.user, comp):
            return HttpResponse('Доступ запрещён.', status=403)
        if comp.status not in ('running', 'finished'):
            return HttpResponse('Результаты недоступны.', status=404)
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
            result.append({'place': 0, 'username': p.user.username, 'total_score': total})
        result.sort(key=lambda x: -x['total_score'])
        for i, r in enumerate(result, 1):
            r['place'] = i
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(['Место', 'Участник', 'Баллы'])
        for r in result:
            w.writerow([r['place'], r['username'], r['total_score']])
        body = '\ufeff' + buf.getvalue()
        resp = HttpResponse(body, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="results_{comp.pk}.csv"'
        return resp


class CompetitionParticipantsExportCSVView(LoginRequiredMixin, View):
    """Экспорт списка зарегистрированных участников (CSV)."""

    def get(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if not can_edit_competition(request.user, comp):
            return HttpResponse('Доступ запрещён.', status=403)
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(['username', 'email', 'registered_at'])
        for p in (
            Participation.objects.filter(competition=comp)
            .select_related('user')
            .order_by('registered_at')
        ):
            u = p.user
            w.writerow([u.username, getattr(u, 'email', '') or '', p.registered_at.isoformat()])
        body = '\ufeff' + buf.getvalue()
        resp = HttpResponse(body, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="participants_{comp.pk}.csv"'
        return resp


class CompetitionSolutionsExportCSVView(LoginRequiredMixin, View):
    """Экспорт всех отправленных решений по турниру (по строке на попытку)."""

    _MAX_CONTENT = 8000

    def get(self, request, competition_id):
        comp = get_object_or_404(Competition, pk=competition_id)
        if not can_edit_competition(request.user, comp):
            return HttpResponse('Доступ запрещён.', status=403)
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                'task_id',
                'task_title',
                'username',
                'email',
                'submitted_at',
                'status',
                'score',
                'comment',
                'content',
            ]
        )
        qs = (
            Solution.objects.filter(task__competition=comp)
            .select_related('user', 'task')
            .order_by('task_id', '-submitted_at')
        )
        for sol in qs:
            u = sol.user
            txt = sol.content or ''
            if len(txt) > self._MAX_CONTENT:
                txt = txt[: self._MAX_CONTENT] + '\n...[обрезано]'
            w.writerow(
                [
                    sol.task_id,
                    sol.task.title,
                    u.username,
                    getattr(u, 'email', '') or '',
                    sol.submitted_at.isoformat(),
                    sol.get_status_display(),
                    sol.score,
                    sol.comment or '',
                    txt,
                ]
            )
        body = '\ufeff' + buf.getvalue()
        resp = HttpResponse(body, content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = f'attachment; filename="solutions_{comp.pk}.csv"'
        return resp


# ——— Объявления ———

class AnnouncementCreateView(LoginRequiredMixin, CanEditCompetitionMixin, CreateView):
    model = Announcement
    fields = ('title', 'body', 'is_pinned')
    template_name = 'competitions/announcement_form.html'

    def get_competition(self):
        return get_object_or_404(Competition, pk=self.kwargs['competition_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['competition'] = self.get_competition()
        return context

    def form_valid(self, form):
        form.instance.competition = self.get_competition()
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        comp = form.instance.competition
        from accounts.notifications import notify_competition_participants

        notify_competition_participants(
            comp.pk,
            kind='announcement',
            title=f'Объявление: {form.instance.title}',
            body=(form.instance.body or '')[:2000],
            link=reverse('competitions:detail', kwargs={'pk': comp.pk}),
        )
        return response

    def get_success_url(self):
        return reverse('competitions:detail', kwargs={'pk': self.get_competition().pk})


class AnnouncementUpdateView(LoginRequiredMixin, CanEditCompetitionMixin, UpdateView):
    model = Announcement
    fields = ('title', 'body', 'is_pinned')
    context_object_name = 'announcement'
    template_name = 'competitions/announcement_form.html'

    def get_competition(self):
        return self.get_object().competition

    def get_queryset(self):
        if self.request.user.is_staff:
            return Announcement.objects.all()
        return Announcement.objects.filter(competition__created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['competition'] = self.get_object().competition
        return context

    def get_success_url(self):
        return reverse('competitions:detail', kwargs={'pk': self.get_object().competition_id})


class AnnouncementDeleteView(LoginRequiredMixin, CanEditCompetitionMixin, DeleteView):
    model = Announcement
    context_object_name = 'announcement'
    template_name = 'competitions/announcement_confirm_delete.html'

    def get_competition(self):
        return self.get_object().competition

    def get_queryset(self):
        qs = Announcement.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(competition__created_by=self.request.user)
        return qs

    def get_success_url(self):
        return reverse('competitions:detail', kwargs={'pk': self.get_object().competition_id})
