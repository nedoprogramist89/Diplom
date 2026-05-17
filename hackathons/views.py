from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Count, Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import (
    HackathonForm,
    HackathonRegistrationForm,
    HackathonChatMessageForm,
    HackathonTeamCreateForm,
    unique_slug_for_title,
)
from .models import (
    Hackathon,
    HackathonRegistration,
    HackathonChatMessage,
    HackathonTeam,
    HackathonTeamMember,
)
from .permissions import can_create_hackathon, can_edit_hackathon
from .schedule import get_hackathon_phases


class CanCreateHackathonMixin:
    """Проверка права создавать хакатоны (организатор / staff)."""

    def dispatch(self, request, *args, **kwargs):
        if not can_create_hackathon(request.user):
            messages.error(
                request,
                'Создавать хакатоны могут только пользователи с ролью «Организатор» или администраторы.',
            )
            return redirect('hackathons:list')
        return super().dispatch(request, *args, **kwargs)


class CanEditHackathonMixin(UserPassesTestMixin):
    def get_hackathon(self):
        return get_object_or_404(Hackathon, pk=self.kwargs['pk'])

    def test_func(self):
        return can_edit_hackathon(self.request.user, self.get_hackathon())


def _team_member_role(team, user):
    if not user.is_authenticated:
        return None
    return (
        HackathonTeamMember.objects.filter(team=team, user=user)
        .values_list('role', flat=True)
        .first()
    )


def _user_hackathon_membership(hackathon, user):
    if not user.is_authenticated:
        return None
    return (
        HackathonTeamMember.objects.select_related('team')
        .filter(hackathon=hackathon, user=user)
        .first()
    )


class HackathonLandingView(ListView):
    """Раздел «Хакатоны»: список + краткое введение в шаблоне."""

    model = Hackathon
    context_object_name = 'hackathons'
    template_name = 'hackathons/hackathon_list.html'
    paginate_by = 12

    def get_queryset(self):
        public_statuses = (
            Hackathon.STATUS_PUBLISHED,
            Hackathon.STATUS_REGISTRATION,
            Hackathon.STATUS_ONGOING,
            Hackathon.STATUS_FINISHED,
        )
        q_vis = Q(status__in=public_statuses)
        user = self.request.user
        if user.is_authenticated:
            q_vis |= Q(status=Hackathon.STATUS_DRAFT, created_by=user)
        qs = (
            Hackathon.objects.filter(q_vis)
            .select_related('created_by')
            .annotate(reg_count=Count('registrations', distinct=True))
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(title__icontains=q)
        st = self.request.GET.get('status', '').strip()
        allowed = {
            Hackathon.STATUS_PUBLISHED,
            Hackathon.STATUS_REGISTRATION,
            Hackathon.STATUS_ONGOING,
            Hackathon.STATUS_FINISHED,
        }
        if st and st in allowed:
            qs = qs.filter(status=st)
        audience = self.request.GET.get('audience', '').strip()
        if audience and audience in {v for v, _ in Hackathon.AUDIENCE_CHOICES}:
            qs = qs.filter(audience=audience)
        level = self.request.GET.get('level', '').strip()
        if level and level in {v for v, _ in Hackathon.LEVEL_CHOICES}:
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
            qs = qs.filter(Q(max_teams__isnull=True) | Q(reg_count__lt=F('max_teams')))
        return qs.order_by('-starts_at', '-created_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['search_q'] = self.request.GET.get('q', '')
        ctx['search_status'] = self.request.GET.get('status', '')
        ctx['search_audience'] = self.request.GET.get('audience', '')
        ctx['search_level'] = self.request.GET.get('level', '')
        ctx['search_age'] = self.request.GET.get('age', '')
        ctx['search_only_free'] = self.request.GET.get('only_free', '')
        ctx['hackathon_status_choices'] = Hackathon.STATUS_CHOICES
        ctx['hackathon_audience_choices'] = Hackathon.AUDIENCE_CHOICES
        ctx['hackathon_level_choices'] = Hackathon.LEVEL_CHOICES
        return ctx


class HackathonDetailView(DetailView):
    model = Hackathon
    context_object_name = 'hackathon'
    template_name = 'hackathons/hackathon_detail.html'

    def get_queryset(self):
        return Hackathon.objects.select_related('created_by').annotate(reg_count=Count('registrations'))

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.status == Hackathon.STATUS_DRAFT and not can_edit_hackathon(self.request.user, obj):
            raise Http404()
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        h = self.object
        ctx['can_edit'] = can_edit_hackathon(user, h)
        reg = None
        is_registered = False
        if user.is_authenticated:
            reg = HackathonRegistration.objects.select_related('team').filter(hackathon=h, user=user).first()
            is_registered = reg is not None
        ctx['is_registered'] = is_registered
        ctx['registration_obj'] = reg
        at_cap = False
        if h.max_teams is not None and h.reg_count >= h.max_teams:
            at_cap = True
        ctx['registration_full'] = at_cap
        ctx['can_register'] = (
            user.is_authenticated
            and not is_registered
            and h.is_registration_open()
            and not at_cap
        )
        ctx['registration_form'] = HackathonRegistrationForm()
        ctx['schedule_phases'] = get_hackathon_phases(h)
        ctx['tracks'] = h.tracks_list()
        ctx['hackathon_status_choices'] = Hackathon.STATUS_CHOICES
        teams = list(h.teams.all().order_by('name'))
        for t in teams:
            t.members_count_ui = t.members_count()
            t.requests_count_ui = t.requests_count()
            captain_m = t.captain_membership()
            t.captain_user_ui = captain_m.user if captain_m else None
            t.has_free_slots_ui = t.members_count_ui < (h.max_team_size or 1)
            t.my_role_ui = _team_member_role(t, user)
        ctx['teams'] = teams

        user_membership = _user_hackathon_membership(h, user)
        ctx['my_team_membership'] = user_membership
        ctx['my_team'] = user_membership.team if user_membership else None
        ctx['my_team_role'] = user_membership.role if user_membership else ''
        ctx['can_create_team'] = bool(
            user.is_authenticated
            and h.is_registration_open()
            and h.allow_user_team_creation
            and user_membership is None
            and is_registered
        )
        ctx['pending_requests_for_my_team'] = []
        ctx['team_member_list_for_my_team'] = []
        if user_membership and user_membership.role == HackathonTeamMember.ROLE_CAPTAIN:
            my_team = user_membership.team
            ctx['pending_requests_for_my_team'] = list(
                my_team.team_members
                .filter(role=HackathonTeamMember.ROLE_REQUEST)
                .select_related('user')
                .order_by('-joined_at')
            )
            ctx['team_member_list_for_my_team'] = list(
                my_team.team_members
                .filter(role__in=(HackathonTeamMember.ROLE_CAPTAIN, HackathonTeamMember.ROLE_MEMBER))
                .select_related('user')
                .order_by('role', 'user__username')
            )

        active_team = ''
        team_choices = [t.name for t in teams]
        if user_membership and user_membership.team_id and user_membership.role in (
            HackathonTeamMember.ROLE_CAPTAIN,
            HackathonTeamMember.ROLE_MEMBER,
        ):
            active_team = user_membership.team.name
        elif ctx['can_edit']:
            requested_team = (self.request.GET.get('team') or '').strip()
            if requested_team in team_choices:
                active_team = requested_team

        can_use_chat = bool(active_team) and (is_registered or ctx['can_edit'])
        team_chat = HackathonChatMessage.objects.none()
        organizer_chat = HackathonChatMessage.objects.none()
        if can_use_chat:
            base = HackathonChatMessage.objects.filter(
                hackathon=h,
                team_name=active_team,
            ).select_related('author')
            team_chat = base.filter(channel=HackathonChatMessage.CHANNEL_TEAM).order_by('-created_at')[:60]
            organizer_chat = base.filter(channel=HackathonChatMessage.CHANNEL_ORGANIZER).order_by('-created_at')[:60]

        ctx['chat_team_choices'] = team_choices
        ctx['chat_active_team'] = active_team
        ctx['chat_available'] = can_use_chat
        ctx['team_chat_messages'] = reversed(list(team_chat))
        ctx['organizer_chat_messages'] = reversed(list(organizer_chat))
        ctx['team_chat_form'] = HackathonChatMessageForm(prefix='team_chat')
        ctx['organizer_chat_form'] = HackathonChatMessageForm(prefix='org_chat')
        ctx['team_create_form'] = HackathonTeamCreateForm()
        ctx['registration_is_captain'] = bool(reg and reg.is_captain)
        return ctx


class HackathonTeamsHubView(DetailView):
    model = Hackathon
    context_object_name = 'hackathon'
    template_name = 'hackathons/hackathon_teams.html'

    def get_queryset(self):
        return Hackathon.objects.select_related('created_by').annotate(reg_count=Count('registrations'))

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.status == Hackathon.STATUS_DRAFT and not can_edit_hackathon(self.request.user, obj):
            raise Http404()
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        h = self.object
        ctx['can_edit'] = can_edit_hackathon(user, h)

        reg = None
        is_registered = False
        if user.is_authenticated:
            reg = HackathonRegistration.objects.select_related('team').filter(hackathon=h, user=user).first()
            is_registered = reg is not None
        ctx['is_registered'] = is_registered
        ctx['registration_obj'] = reg

        teams = list(h.teams.all().order_by('name'))
        for t in teams:
            t.members_count_ui = t.members_count()
            t.requests_count_ui = t.requests_count()
            captain_m = t.captain_membership()
            t.captain_user_ui = captain_m.user if captain_m else None
            t.has_free_slots_ui = t.members_count_ui < (h.max_team_size or 1)
            t.my_role_ui = _team_member_role(t, user)
        ctx['teams'] = teams

        user_membership = _user_hackathon_membership(h, user)
        ctx['my_team_membership'] = user_membership
        ctx['my_team'] = user_membership.team if user_membership else None
        ctx['my_team_role'] = user_membership.role if user_membership else ''
        ctx['can_create_team'] = bool(
            user.is_authenticated
            and h.is_registration_open()
            and h.allow_user_team_creation
            and user_membership is None
            and is_registered
        )
        ctx['pending_requests_for_my_team'] = []
        ctx['team_member_list_for_my_team'] = []
        if user_membership and user_membership.role == HackathonTeamMember.ROLE_CAPTAIN:
            my_team = user_membership.team
            ctx['pending_requests_for_my_team'] = list(
                my_team.team_members
                .filter(role=HackathonTeamMember.ROLE_REQUEST)
                .select_related('user')
                .order_by('-joined_at')
            )
            ctx['team_member_list_for_my_team'] = list(
                my_team.team_members
                .filter(role__in=(HackathonTeamMember.ROLE_CAPTAIN, HackathonTeamMember.ROLE_MEMBER))
                .select_related('user')
                .order_by('role', 'user__username')
            )

        active_team = ''
        team_choices = [t.name for t in teams]
        if user_membership and user_membership.team_id and user_membership.role in (
            HackathonTeamMember.ROLE_CAPTAIN,
            HackathonTeamMember.ROLE_MEMBER,
        ):
            active_team = user_membership.team.name
        elif ctx['can_edit']:
            requested_team = (self.request.GET.get('team') or '').strip()
            if requested_team in team_choices:
                active_team = requested_team

        can_use_chat = bool(active_team) and (is_registered or ctx['can_edit'])
        team_chat = HackathonChatMessage.objects.none()
        organizer_chat = HackathonChatMessage.objects.none()
        if can_use_chat:
            base = HackathonChatMessage.objects.filter(
                hackathon=h,
                team_name=active_team,
            ).select_related('author')
            team_chat = base.filter(channel=HackathonChatMessage.CHANNEL_TEAM).order_by('-created_at')[:60]
            organizer_chat = base.filter(channel=HackathonChatMessage.CHANNEL_ORGANIZER).order_by('-created_at')[:60]

        ctx['chat_team_choices'] = team_choices
        ctx['chat_active_team'] = active_team
        ctx['chat_available'] = can_use_chat
        team_chat_messages = list(reversed(list(team_chat)))
        organizer_chat_messages = list(reversed(list(organizer_chat)))
        ctx['team_chat_messages'] = team_chat_messages
        ctx['organizer_chat_messages'] = organizer_chat_messages
        chat_mode = (self.request.GET.get('chat') or '').strip()
        if chat_mode not in ('team', 'organizer'):
            chat_mode = 'team'
        ctx['chat_mode'] = chat_mode
        if chat_mode == 'organizer':
            ctx['chat_messages'] = organizer_chat_messages
            ctx['chat_form'] = HackathonChatMessageForm(prefix='org_chat')
        else:
            ctx['chat_messages'] = team_chat_messages
            ctx['chat_form'] = HackathonChatMessageForm(prefix='team_chat')
        ctx['team_create_form'] = HackathonTeamCreateForm()
        return ctx


def _redirect_hackathon_quick_status(request, default):
    nxt = (request.POST.get('next') or '').strip()
    if nxt.startswith('/') and not nxt.startswith('//'):
        return redirect(nxt)
    return redirect(default)


class HackathonQuickStatusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        if not can_edit_hackathon(request.user, hackathon):
            messages.error(request, 'Нет прав для смены этапа.')
            return redirect('hackathons:detail', pk=pk)
        new_status = (request.POST.get('status') or '').strip()
        valid = {c for c, _ in Hackathon.STATUS_CHOICES}
        if new_status not in valid:
            messages.error(request, 'Некорректный этап.')
            return redirect('hackathons:detail', pk=pk)
        if hackathon.status == new_status:
            messages.info(request, 'Этап уже установлен.')
            return _redirect_hackathon_quick_status(request, reverse('hackathons:detail', kwargs={'pk': pk}))
        hackathon.status = new_status
        hackathon.save()
        messages.success(request, f'Этап хакатона: «{hackathon.get_status_display()}».')
        return _redirect_hackathon_quick_status(request, reverse('hackathons:detail', kwargs={'pk': pk}))


class HackathonCreateView(LoginRequiredMixin, CanCreateHackathonMixin, CreateView):
    model = Hackathon
    form_class = HackathonForm
    template_name = 'hackathons/hackathon_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.slug = unique_slug_for_title(form.cleaned_data['title'])
        messages.success(self.request, 'Хакатон создан.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('hackathons:detail', kwargs={'pk': self.object.pk})


class HackathonUpdateView(LoginRequiredMixin, CanEditHackathonMixin, UpdateView):
    model = Hackathon
    form_class = HackathonForm
    context_object_name = 'hackathon'
    template_name = 'hackathons/hackathon_form.html'
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs

    def form_valid(self, form):
        messages.success(self.request, 'Изменения сохранены.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('hackathons:detail', kwargs={'pk': self.object.pk})


class HackathonDeleteView(LoginRequiredMixin, CanEditHackathonMixin, DeleteView):
    model = Hackathon
    context_object_name = 'hackathon'
    template_name = 'hackathons/hackathon_confirm_delete.html'
    success_url = reverse_lazy('hackathons:list')
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(created_by=self.request.user)
        return qs

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Хакатон удалён.')
        return super().delete(request, *args, **kwargs)


class HackathonRegisterView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(
            Hackathon.objects.annotate(reg_count=Count('registrations')),
            pk=pk,
        )
        if not hackathon.is_registration_open():
            messages.error(request, 'Регистрация закрыта или ещё не открыта.')
            return redirect('hackathons:detail', pk=pk)
        if HackathonRegistration.objects.filter(hackathon=hackathon, user=request.user).exists():
            messages.info(request, 'Вы уже в списке участников.')
            return redirect('hackathons:detail', pk=pk)
        if hackathon.max_teams is not None and hackathon.reg_count >= hackathon.max_teams:
            messages.error(request, 'Достигнут лимит заявок.')
            return redirect('hackathons:detail', pk=pk)
        form = HackathonRegistrationForm(request.POST)
        if not form.is_valid():
            for err in form.non_field_errors():
                messages.error(request, err)
            for field, errs in form.errors.items():
                for e in errs:
                    messages.error(request, f'{field}: {e}')
            return redirect('hackathons:detail', pk=pk)
        reg = form.save(commit=False)
        reg.user = request.user
        reg.hackathon = hackathon
        reg.save()
        messages.success(request, 'Вы зарегистрированы на хакатон.')
        return redirect('hackathons:detail', pk=pk)


class HackathonUnregisterView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        if not hackathon.is_registration_open():
            messages.error(request, 'Отменить регистрацию можно только пока открыта запись.')
            return redirect('hackathons:detail', pk=pk)
        deleted, _ = HackathonRegistration.objects.filter(hackathon=hackathon, user=request.user).delete()
        if deleted:
            messages.success(request, 'Регистрация отменена.')
        else:
            messages.info(request, 'Заявка не найдена.')
        return redirect('hackathons:detail', pk=pk)


class HackathonParticipantsView(LoginRequiredMixin, ListView):
    model = HackathonRegistration
    context_object_name = 'registrations'
    template_name = 'hackathons/hackathon_participants.html'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        self.hackathon = get_object_or_404(Hackathon, pk=self.kwargs['hackathon_id'])
        if not can_edit_hackathon(request.user, self.hackathon):
            messages.error(request, 'Нет доступа к списку участников.')
            return redirect('hackathons:detail', pk=self.hackathon.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            HackathonRegistration.objects.filter(hackathon=self.hackathon)
            .select_related('user', 'team')
            .order_by('registered_at')
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['hackathon'] = self.hackathon
        ctx['total'] = self.hackathon.registrations.count()
        teams = list(self.hackathon.teams.all())
        for t in teams:
            cap = t.captain_membership()
            t.captain_username = cap.user.username if cap else ''
        ctx['teams'] = teams
        return ctx


class HackathonTeamCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        registration = HackathonRegistration.objects.filter(
            hackathon=hackathon,
            user=request.user,
        ).first()
        if not registration:
            messages.error(request, 'Сначала зарегистрируйтесь на хакатон.')
            return redirect('hackathons:teams', pk=pk)
        if not hackathon.is_registration_open():
            messages.error(request, 'Команды можно формировать только на этапе регистрации.')
            return redirect('hackathons:teams', pk=pk)
        if not hackathon.allow_user_team_creation:
            messages.error(request, 'Создание команд участниками отключено организатором.')
            return redirect('hackathons:teams', pk=pk)
        if _user_hackathon_membership(hackathon, request.user):
            messages.info(request, 'У вас уже есть команда или заявка на вступление.')
            return redirect('hackathons:teams', pk=pk)

        form = HackathonTeamCreateForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Название команды не заполнено.')
            return redirect('hackathons:teams', pk=pk)

        try:
            with transaction.atomic():
                team = form.save(commit=False)
                team.hackathon = hackathon
                team.created_by = request.user
                team.save()
                HackathonTeamMember.objects.create(
                    hackathon=hackathon,
                    team=team,
                    user=request.user,
                    role=HackathonTeamMember.ROLE_CAPTAIN,
                )
                registration.team = team
                registration.team_name = team.name
                registration.save(update_fields=['team', 'team_name'])
        except IntegrityError:
            messages.error(request, 'Команда с таким названием уже существует.')
            return redirect('hackathons:teams', pk=pk)
        messages.success(request, f'Команда «{team.name}» создана, вы назначены капитаном.')
        return redirect('hackathons:teams', pk=pk)


class HackathonAssignTeamView(LoginRequiredMixin, View):
    def post(self, request, hackathon_id, registration_id):
        hackathon = get_object_or_404(Hackathon, pk=hackathon_id)
        if not can_edit_hackathon(request.user, hackathon):
            messages.error(request, 'Нет прав для распределения по командам.')
            return redirect('hackathons:participants', hackathon_id=hackathon_id)

        registration = get_object_or_404(
            HackathonRegistration.objects.select_related('team', 'user'),
            pk=registration_id,
            hackathon=hackathon,
        )
        team_id_raw = (request.POST.get('team_id') or '').strip()
        make_captain = (request.POST.get('make_captain') or '').strip() in ('1', 'on', 'true')
        team = None
        if team_id_raw:
            try:
                team = HackathonTeam.objects.get(pk=int(team_id_raw), hackathon=hackathon)
            except (ValueError, HackathonTeam.DoesNotExist):
                messages.error(request, 'Команда не найдена.')
                return redirect('hackathons:participants', hackathon_id=hackathon_id)

        with transaction.atomic():
            membership = HackathonTeamMember.objects.filter(
                hackathon=hackathon,
                user=registration.user,
            ).first()
            if membership and not team:
                membership.delete()
                registration.team = None
                registration.team_name = ''
                registration.save(update_fields=['team', 'team_name'])
                messages.success(request, 'Участник убран из команды.')
                return redirect('hackathons:participants', hackathon_id=hackathon_id)

            if team:
                if membership:
                    membership.team = team
                    membership.role = HackathonTeamMember.ROLE_MEMBER
                    membership.save(update_fields=['team', 'role'])
                else:
                    membership = HackathonTeamMember.objects.create(
                        hackathon=hackathon,
                        team=team,
                        user=registration.user,
                        role=HackathonTeamMember.ROLE_MEMBER,
                    )
                if make_captain:
                    team.team_members.filter(role=HackathonTeamMember.ROLE_CAPTAIN).update(
                        role=HackathonTeamMember.ROLE_MEMBER
                    )
                    membership.role = HackathonTeamMember.ROLE_CAPTAIN
                    membership.save(update_fields=['role'])
                registration.team = team
                registration.team_name = team.name
                registration.save(update_fields=['team', 'team_name'])

        if team and make_captain:
            messages.success(request, f'Участник назначен в «{team.name}» и выбран капитаном.')
        elif team:
            messages.success(request, f'Участник назначен в команду «{team.name}».')
        return redirect('hackathons:participants', hackathon_id=hackathon_id)


class HackathonTeamRequestJoinView(LoginRequiredMixin, View):
    def post(self, request, pk, team_id):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        team = get_object_or_404(HackathonTeam, pk=team_id, hackathon=hackathon)
        registration = HackathonRegistration.objects.filter(hackathon=hackathon, user=request.user).first()
        if not registration:
            messages.error(request, 'Сначала зарегистрируйтесь на хакатон.')
            return redirect('hackathons:teams', pk=pk)
        if not hackathon.is_registration_open():
            messages.error(request, 'Подача заявок в команды доступна только в регистрации.')
            return redirect('hackathons:teams', pk=pk)
        if _user_hackathon_membership(hackathon, request.user):
            messages.info(request, 'У вас уже есть команда или заявка.')
            return redirect('hackathons:teams', pk=pk)
        if not team.has_free_slots():
            messages.error(request, 'В команде нет свободных мест.')
            return redirect('hackathons:teams', pk=pk)
        HackathonTeamMember.objects.create(
            hackathon=hackathon,
            team=team,
            user=request.user,
            role=HackathonTeamMember.ROLE_REQUEST,
        )
        messages.success(request, f'Заявка в команду «{team.name}» отправлена.')
        return redirect('hackathons:teams', pk=pk)


class HackathonTeamRequestApproveView(LoginRequiredMixin, View):
    def post(self, request, pk, member_id):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        captain_membership = _user_hackathon_membership(hackathon, request.user)
        if not captain_membership or captain_membership.role != HackathonTeamMember.ROLE_CAPTAIN:
            messages.error(request, 'Одобрять заявки может только капитан команды.')
            return redirect('hackathons:teams', pk=pk)
        member = get_object_or_404(
            HackathonTeamMember.objects.select_related('user', 'team'),
            pk=member_id,
            hackathon=hackathon,
            team=captain_membership.team,
            role=HackathonTeamMember.ROLE_REQUEST,
        )
        if not captain_membership.team.has_free_slots():
            messages.error(request, 'В команде нет свободных мест.')
            return redirect('hackathons:teams', pk=pk)
        member.role = HackathonTeamMember.ROLE_MEMBER
        member.save(update_fields=['role'])
        HackathonRegistration.objects.filter(hackathon=hackathon, user=member.user).update(
            team=captain_membership.team,
            team_name=captain_membership.team.name,
        )
        messages.success(request, f'Заявка пользователя {member.user.username} одобрена.')
        return redirect('hackathons:teams', pk=pk)


class HackathonTeamRequestRejectView(LoginRequiredMixin, View):
    def post(self, request, pk, member_id):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        captain_membership = _user_hackathon_membership(hackathon, request.user)
        if not captain_membership or captain_membership.role != HackathonTeamMember.ROLE_CAPTAIN:
            messages.error(request, 'Отклонять заявки может только капитан команды.')
            return redirect('hackathons:teams', pk=pk)
        member = get_object_or_404(
            HackathonTeamMember,
            pk=member_id,
            hackathon=hackathon,
            team=captain_membership.team,
            role=HackathonTeamMember.ROLE_REQUEST,
        )
        username = member.user.username
        member.delete()
        messages.success(request, f'Заявка пользователя {username} отклонена.')
        return redirect('hackathons:teams', pk=pk)


class HackathonTeamTransferCaptainView(LoginRequiredMixin, View):
    def post(self, request, pk, user_id):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        captain_membership = _user_hackathon_membership(hackathon, request.user)
        if not captain_membership or captain_membership.role != HackathonTeamMember.ROLE_CAPTAIN:
            messages.error(request, 'Передавать капитанство может только текущий капитан.')
            return redirect('hackathons:teams', pk=pk)
        team = captain_membership.team
        target = get_object_or_404(
            HackathonTeamMember,
            hackathon=hackathon,
            team=team,
            user_id=user_id,
            role=HackathonTeamMember.ROLE_MEMBER,
        )
        with transaction.atomic():
            captain_membership.role = HackathonTeamMember.ROLE_MEMBER
            captain_membership.save(update_fields=['role'])
            target.role = HackathonTeamMember.ROLE_CAPTAIN
            target.save(update_fields=['role'])
        messages.success(request, f'Капитан передан пользователю {target.user.username}.')
        return redirect('hackathons:teams', pk=pk)


class HackathonTeamLeaveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        membership = _user_hackathon_membership(hackathon, request.user)
        if not membership:
            messages.info(request, 'Вы не состоите в команде.')
            return redirect('hackathons:teams', pk=pk)
        if membership.role == HackathonTeamMember.ROLE_CAPTAIN:
            messages.error(request, 'Капитан не может выйти, пока не передаст роль.')
            return redirect('hackathons:teams', pk=pk)
        team = membership.team
        membership.delete()
        HackathonRegistration.objects.filter(hackathon=hackathon, user=request.user).update(
            team=None,
            team_name='',
        )
        messages.success(request, f'Вы вышли из команды «{team.name}».')
        return redirect('hackathons:teams', pk=pk)


class HackathonTeamDissolveView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        membership = _user_hackathon_membership(hackathon, request.user)
        team_id_raw = (request.POST.get('team_id') or '').strip()
        team_id = membership.team_id if membership else None
        if can_edit_hackathon(request.user, hackathon) and team_id_raw:
            try:
                team_id = int(team_id_raw)
            except ValueError:
                team_id = None
        can_dissolve = bool(
            team_id and (
                (membership and membership.role == HackathonTeamMember.ROLE_CAPTAIN and membership.team_id == team_id)
                or can_edit_hackathon(request.user, hackathon)
            )
        )
        if not can_dissolve:
            messages.error(request, 'Расформировать команду может капитан или организатор.')
            return redirect('hackathons:teams', pk=pk)
        team = get_object_or_404(HackathonTeam, pk=team_id, hackathon=hackathon)
        users_in_team = list(
            HackathonTeamMember.objects.filter(team=team).values_list('user_id', flat=True)
        )
        with transaction.atomic():
            HackathonTeamMember.objects.filter(team=team).delete()
            HackathonRegistration.objects.filter(
                hackathon=hackathon,
                user_id__in=users_in_team,
            ).update(team=None, team_name='')
            team.delete()
        messages.success(request, 'Команда расформирована.')
        return redirect('hackathons:teams', pk=pk)


class HackathonChatPostView(LoginRequiredMixin, View):
    def post(self, request, pk):
        hackathon = get_object_or_404(Hackathon, pk=pk)
        user = request.user
        channel = (request.POST.get('channel') or '').strip()
        if channel not in (
            HackathonChatMessage.CHANNEL_TEAM,
            HackathonChatMessage.CHANNEL_ORGANIZER,
        ):
            messages.error(request, 'Неизвестный канал чата.')
            return redirect('hackathons:teams', pk=pk)

        registration = HackathonRegistration.objects.filter(hackathon=hackathon, user=user).first()
        can_edit = can_edit_hackathon(user, hackathon)
        if not registration and not can_edit:
            messages.error(request, 'Чат доступен только участникам и организаторам.')
            return redirect('hackathons:teams', pk=pk)

        membership = _user_hackathon_membership(hackathon, user)
        if can_edit and not registration:
            team_name = (request.POST.get('team') or '').strip()
        else:
            team_name = (membership.team.name if membership and membership.team_id else '').strip()
            if membership and membership.role == HackathonTeamMember.ROLE_REQUEST:
                messages.error(request, 'Доступ к командному чату откроется после одобрения заявки.')
                return redirect('hackathons:teams', pk=pk)

        if not team_name:
            messages.error(request, 'Для чата нужно указать команду в заявке.')
            return redirect('hackathons:teams', pk=pk)

        prefix = 'team_chat' if channel == HackathonChatMessage.CHANNEL_TEAM else 'org_chat'
        form = HackathonChatMessageForm(request.POST, prefix=prefix)
        if not form.is_valid():
            messages.error(request, 'Сообщение не отправлено: проверьте текст.')
            return redirect(f'{reverse("hackathons:teams", kwargs={"pk": pk})}?team={team_name}')

        msg = form.save(commit=False)
        msg.hackathon = hackathon
        msg.author = user
        msg.team_name = team_name
        msg.channel = channel
        msg.save()
        messages.success(request, 'Сообщение отправлено.')
        return redirect(f'{reverse("hackathons:teams", kwargs={"pk": pk})}?team={team_name}')


