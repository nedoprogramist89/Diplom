"""
Веб-представления: регистрация, вход, выход, профиль, смена темы, сброс пароля.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.views import (
    LoginView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView, UpdateView, DetailView, ListView
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.mail import send_mail
from .forms import RegistrationForm, ProfileEditForm
from .models import User, InAppNotification


class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = False  # всегда показывать форму входа по /accounts/login/
    success_url = reverse_lazy('competitions:home')


class RegistrationView(CreateView):
    model = User
    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('competitions:home')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect(self.success_url)


def logout_view(request):
    logout(request)
    return redirect('competitions:home')


class NotificationListView(LoginRequiredMixin, ListView):
    """Лента внутренних уведомлений (без email)."""
    model = InAppNotification
    context_object_name = 'notifications'
    template_name = 'accounts/notifications_list.html'
    paginate_by = 40

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notifications_unread'] = self.get_queryset().filter(read_at__isnull=True).count()
        return context


@login_required
@require_POST
def notifications_mark_all_read(request):
    InAppNotification.objects.filter(user=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return redirect('accounts:notifications')


@login_required
def notification_follow(request, pk):
    """Помечает уведомление прочитанным и переходит по сохранённой ссылке (только свой путь)."""
    notification = get_object_or_404(InAppNotification, pk=pk, user=request.user)
    notification.mark_read()
    raw = (notification.link or '').strip()
    if raw.startswith('/') and not raw.startswith('//'):
        return redirect(raw)
    return redirect('accounts:notifications')


class ProfileView(LoginRequiredMixin, DetailView):
    """Просмотр своего профиля: данные и список участий в соревнованиях."""
    model = User
    context_object_name = 'profile_user'
    template_name = 'accounts/profile.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from competitions.models import Participation
        context['participations'] = (
            Participation.objects
            .filter(user=self.request.user)
            .select_related('competition')
            .order_by('-registered_at')[:20]
        )
        return context


class ProfilePublicView(DetailView):
    """Публичный профиль любого пользователя по username (без email)."""
    model = User
    context_object_name = 'profile_user'
    template_name = 'accounts/profile_public.html'
    slug_url_kwarg = 'username'
    slug_field = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from competitions.models import Participation
        context['participations'] = (
            Participation.objects
            .filter(user=self.object)
            .select_related('competition')
            .order_by('-registered_at')[:25]
        )
        context['is_own_profile'] = (
            self.request.user.is_authenticated and self.request.user.pk == self.object.pk
        )
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileEditForm
    template_name = 'accounts/profile_edit.html'
    context_object_name = 'profile_user'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse('accounts:profile')


@require_POST
def theme_save_view(request):
    """Сохраняет выбранную тему для авторизованного пользователя (JSON)."""
    if not request.user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'auth_required'}, status=401)
    theme = (request.POST.get('theme') or '').strip()
    if theme not in ('dark', 'light'):
        return JsonResponse({'ok': False, 'error': 'invalid_theme'}, status=400)
    request.user.theme = theme
    request.user.save(update_fields=['theme'])
    return JsonResponse({'ok': True, 'theme': theme})


@login_required
def send_test_email_view(request):
    """
    Отправка тестового письма на email пользователя, чтобы проверить настройки SMTP.
    """
    user = request.user
    if not user.email:
        messages.error(request, 'У вашего профиля не указан email. Добавьте его в настройках профиля.')
        return redirect('accounts:profile_edit')
    subject = 'Тестовое письмо — CompetitionHub'
    message = (
        'Это тестовое письмо для проверки отправки почты в CompetitionHub.\n\n'
        'Если вы видите это сообщение в своём почтовом ящике, значит настройки email работают корректно.'
    )
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception as e:
        if settings.DEBUG:
            messages.error(request, f'Ошибка отправки: {e}')
        else:
            messages.error(
                request,
                'Не удалось отправить письмо. Проверьте настройки почты на сервере (EMAIL_BACKEND/SMTP).',
            )
    else:
        messages.success(request, 'Тестовое письмо отправлено на ваш email.')
    return redirect('accounts:profile')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')
    from_email = settings.DEFAULT_FROM_EMAIL


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('accounts:password_change_done')


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'accounts/password_change_done.html'
