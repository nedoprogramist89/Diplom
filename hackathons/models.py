"""Хакатоны: отдельная сущность от олимпиад/соревнований — команды, треки, офлайн/онлайн, призы."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Hackathon(models.Model):
    """Мероприятие формата хакатон (48ч, демо, жюри) — не путать с турниром по задачам."""

    FORMAT_ONLINE = 'online'
    FORMAT_OFFLINE = 'offline'
    FORMAT_HYBRID = 'hybrid'
    FORMAT_CHOICES = [
        (FORMAT_ONLINE, 'Онлайн'),
        (FORMAT_OFFLINE, 'Офлайн'),
        (FORMAT_HYBRID, 'Гибрид'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_REGISTRATION = 'registration'
    STATUS_ONGOING = 'ongoing'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Анонс'),
        (STATUS_REGISTRATION, 'Регистрация'),
        (STATUS_ONGOING, 'Идёт хакатон'),
        (STATUS_FINISHED, 'Завершён'),
    ]
    AUDIENCE_CHOICES = [
        ('open', 'Открыто для всех'),
        ('school_7_11', 'Школьники 7-11 класс'),
        ('students', 'Студенты'),
        ('mixed', 'Смешанные команды'),
        ('professionals', 'Профессионалы'),
    ]
    LEVEL_CHOICES = [
        ('any', 'Любой'),
        ('starter', 'Стартер'),
        ('product', 'Продуктовый'),
        ('pro', 'Профи'),
    ]

    title = models.CharField('Название', max_length=255)
    slug = models.SlugField('URL-фрагмент', max_length=80, unique=True, allow_unicode=True)
    tagline = models.CharField('Короткий слоган', max_length=220, blank=True)
    description = models.TextField('О мероприятии', blank=True)
    audience = models.CharField(
        'Целевая аудитория',
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='open',
    )
    level = models.CharField(
        'Уровень сложности',
        max_length=20,
        choices=LEVEL_CHOICES,
        default='any',
    )
    format = models.CharField('Формат', max_length=16, choices=FORMAT_CHOICES, default=FORMAT_ONLINE)
    venue = models.CharField('Площадка / город', max_length=255, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    registration_opens_at = models.DateTimeField('Регистрация с', null=True, blank=True)
    registration_closes_at = models.DateTimeField('Регистрация до', null=True, blank=True)
    starts_at = models.DateTimeField('Старт хакинга', null=True, blank=True)
    ends_at = models.DateTimeField('Дедлайн сдачи / демо', null=True, blank=True)
    min_age = models.PositiveSmallIntegerField(
        'Возраст от',
        null=True,
        blank=True,
        help_text='Например, 11.',
    )
    max_age = models.PositiveSmallIntegerField(
        'Возраст до',
        null=True,
        blank=True,
        help_text='Например, 15.',
    )

    max_teams = models.PositiveIntegerField('Макс. команд', null=True, blank=True)
    min_team_size = models.PositiveSmallIntegerField('Минимум участников в команде', default=1)
    max_team_size = models.PositiveSmallIntegerField('Максимум участников в команде', default=5)
    allow_user_team_creation = models.BooleanField(
        'Разрешить участникам создавать команды',
        default=True,
        help_text='Если выключено, команды формирует организатор.',
    )
    tracks = models.TextField(
        'Направления (треки)',
        blank=True,
        help_text='Каждая строка — отдельный трек: FinTech, EdTech, …',
    )
    prizes = models.TextField('Призы и номинации', blank=True)
    rules = models.TextField('Правила и требования к проектам', blank=True)
    results_summary = models.TextField(
        'Итоги / победители (публично)',
        blank=True,
        help_text='Краткий публичный итог: победители, номинации, ссылки на проекты.',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_hackathons',
        verbose_name='Организатор',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Хакатон'
        verbose_name_plural = 'Хакатоны'
        ordering = ['-starts_at', '-created_at']

    def __str__(self):
        return self.title

    def is_registration_open(self):
        if self.status != self.STATUS_REGISTRATION:
            return False
        now = timezone.now()
        if self.registration_opens_at and now < self.registration_opens_at:
            return False
        if self.registration_closes_at and now > self.registration_closes_at:
            return False
        return True

    def is_ongoing(self):
        return self.status == self.STATUS_ONGOING

    def is_finished(self):
        return self.status == self.STATUS_FINISHED

    def tracks_list(self):
        if not (self.tracks or '').strip():
            return []
        return [line.strip() for line in self.tracks.splitlines() if line.strip()]

    def age_label(self):
        if self.min_age and self.max_age:
            return f'{self.min_age}-{self.max_age} лет'
        if self.min_age:
            return f'{self.min_age}+'
        if self.max_age:
            return f'до {self.max_age}'
        return ''

    def slots_left(self):
        if not self.max_teams:
            return None
        current = self.registrations.count()
        return max(0, self.max_teams - current)


class HackathonRegistration(models.Model):
    """Заявка участника (или капитана команды): одна запись на пользователя на хакатон."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hackathon_registrations',
        verbose_name='Участник',
    )
    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name='Хакатон',
    )
    team = models.ForeignKey(
        'HackathonTeam',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='Команда',
    )
    team_name = models.CharField('Название команды', max_length=120, blank=True)
    looking_for_team = models.BooleanField('Ищу команду', default=False)
    comment = models.CharField('Комментарий для организаторов', max_length=500, blank=True)
    registered_at = models.DateTimeField('Зарегистрирован', auto_now_add=True)

    class Meta:
        verbose_name = 'Регистрация на хакатон'
        verbose_name_plural = 'Регистрации на хакатоны'
        unique_together = [['user', 'hackathon']]

    def __str__(self):
        return f'{self.user.username} — {self.hackathon.title}'

    @property
    def is_captain(self):
        if not self.team_id:
            return False
        return self.team.team_members.filter(
            user_id=self.user_id,
            role=HackathonTeamMember.ROLE_CAPTAIN,
        ).exists()


class HackathonTeam(models.Model):
    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name='teams',
        verbose_name='Хакатон',
    )
    name = models.CharField('Название команды', max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_hackathon_teams',
        verbose_name='Кто создал',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        verbose_name = 'Команда хакатона'
        verbose_name_plural = 'Команды хакатона'
        unique_together = [['hackathon', 'name']]
        ordering = ['name', 'pk']

    def __str__(self):
        return f'{self.name} ({self.hackathon.title})'

    def captain_membership(self):
        return self.team_members.filter(role=HackathonTeamMember.ROLE_CAPTAIN).select_related('user').first()

    def members_count(self):
        return self.team_members.filter(role__in=(HackathonTeamMember.ROLE_CAPTAIN, HackathonTeamMember.ROLE_MEMBER)).count()

    def requests_count(self):
        return self.team_members.filter(role=HackathonTeamMember.ROLE_REQUEST).count()

    def has_free_slots(self):
        limit = self.hackathon.max_team_size or 1
        return self.members_count() < limit


class HackathonTeamMember(models.Model):
    ROLE_CAPTAIN = 'captain'
    ROLE_MEMBER = 'member'
    ROLE_REQUEST = 'request'
    ROLE_CHOICES = [
        (ROLE_CAPTAIN, 'Капитан'),
        (ROLE_MEMBER, 'Участник'),
        (ROLE_REQUEST, 'Заявка'),
    ]

    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        verbose_name='Хакатон',
    )
    team = models.ForeignKey(
        HackathonTeam,
        on_delete=models.CASCADE,
        related_name='team_members',
        verbose_name='Команда',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hackathon_team_memberships',
        verbose_name='Пользователь',
    )
    role = models.CharField('Роль', max_length=16, choices=ROLE_CHOICES, default=ROLE_REQUEST)
    joined_at = models.DateTimeField('Дата записи', auto_now_add=True)

    class Meta:
        verbose_name = 'Участник команды хакатона'
        verbose_name_plural = 'Участники команд хакатона'
        unique_together = [
            ['team', 'user'],
            ['hackathon', 'user'],
        ]
        ordering = ['joined_at', 'pk']

    def __str__(self):
        return f'{self.user_id}:{self.team_id}:{self.role}'


class HackathonChatMessage(models.Model):
    CHANNEL_TEAM = 'team'
    CHANNEL_ORGANIZER = 'organizer'
    CHANNEL_CHOICES = [
        (CHANNEL_TEAM, 'Внутри команды'),
        (CHANNEL_ORGANIZER, 'Команда и организатор'),
    ]

    hackathon = models.ForeignKey(
        Hackathon,
        on_delete=models.CASCADE,
        related_name='chat_messages',
        verbose_name='Хакатон',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hackathon_chat_messages',
        verbose_name='Автор',
    )
    team_name = models.CharField('Команда', max_length=120, db_index=True)
    channel = models.CharField('Канал', max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_TEAM)
    body = models.TextField('Сообщение', max_length=2000)
    created_at = models.DateTimeField('Отправлено', auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Сообщение чата хакатона'
        verbose_name_plural = 'Чат хакатона'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.hackathon_id}:{self.team_name}:{self.author_id}'
