"""
Модель пользователя: расширяемая под роли (участник, организатор, жюри) на этапе диплома.
"""
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Пользователь системы: участник соревнований, организатор, преподаватель."""
    email = models.EmailField('Email', unique=True, blank=False)
    organization = models.CharField('Организация', max_length=255, blank=True)
    ROLE_CHOICES = [
        ('participant', 'Участник'),
        ('organizer', 'Организатор'),
        ('jury', 'Жюри'),
    ]
    ROLE_DESCRIPTIONS = {
        'participant': 'Регистрация на соревнования, отправка решений, просмотр своих решений и результатов. Не может создавать соревнования, редактировать задачи или выставлять баллы другим.',
        'organizer': 'Всё, что может участник, плюс создание соревнований и полное управление своими соревнованиями (задачи, объявления, участники). Может оценивать решения в своих соревнованиях.',
        'jury': 'Всё, что может участник, плюс просмотр всех решений и списка участников по любому соревнованию, выставление баллов и статусов. Не может создавать соревнования и редактировать задачи.',
    }
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=ROLE_CHOICES,
        default='participant',
    )
    THEME_CHOICES = [
        ('dark', 'Тёмная'),
        ('light', 'Светлая'),
    ]
    theme = models.CharField(
        'Тема оформления',
        max_length=10,
        choices=THEME_CHOICES,
        default='dark',
        blank=True,
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username or self.email

    def get_role_description(self):
        """Описание прав текущей роли пользователя."""
        return self.ROLE_DESCRIPTIONS.get(self.role, '')


class InAppNotification(models.Model):
    """Внутреннее уведомление в ленте кабинета (без email)."""

    KIND_CHOICES = [
        ('announcement', 'Объявление'),
        ('grade', 'Проверка решения'),
        ('system', 'Системное'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='in_app_notifications',
        verbose_name='Пользователь',
    )
    kind = models.CharField(
        'Тип',
        max_length=20,
        choices=KIND_CHOICES,
        default='system',
        db_index=True,
    )
    title = models.CharField('Заголовок', max_length=255)
    body = models.TextField('Текст', blank=True)
    link = models.CharField(
        'Ссылка',
        max_length=500,
        blank=True,
        help_text='Относительный путь, например /competitions/1/',
    )
    read_at = models.DateTimeField('Прочитано', null=True, blank=True, db_index=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f'{self.user_id} · {self.title[:40]}'

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
