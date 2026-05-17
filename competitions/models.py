"""
Модели соревнований: курсовая — базовый набор; диплом — расширение под хакатоны и РЭУ.
Разделение задач: по предмету (математика, русский и т.д.) и по типу (решить пример, выбрать вариант).
"""
from django.db import models
from django.conf import settings


class Subject(models.Model):
    """Предмет / раздел: математика, русский язык, информатика и т.д."""
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Код', max_length=50, unique=True)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class TaskType(models.Model):
    """Тип задания: решить пример, выбрать правильный вариант, краткий ответ и т.д."""
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('Код', max_length=50, unique=True)
    order = models.PositiveIntegerField('Порядок', default=0)
    auto_partial_enabled = models.BooleanField(
        'Частичная автооценка включена',
        default=True,
        help_text='Если выключено, для этого типа задач автопроверка работает по схеме 0 / max.',
    )
    partial_weight_percent = models.PositiveSmallIntegerField(
        'Вес типа в автооценке, %',
        default=100,
        help_text='Применяется к результату автопроверки: 100 = без изменений, 80 = 80% от балла.',
    )

    class Meta:
        verbose_name = 'Тип задания'
        verbose_name_plural = 'Типы заданий'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def is_multiple_choice(self):
        return self.slug == 'multiple_choice'

    @property
    def is_matching(self):
        return self.slug == 'match'


class Competition(models.Model):
    """Соревнование по программированию (или хакатон на этапе диплома)."""
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('published', 'Опубликовано'),
        ('registration', 'Регистрация'),
        ('running', 'Идёт'),
        ('finished', 'Завершено'),
    ]
    AUDIENCE_CHOICES = [
        ('open', 'Открыто для всех'),
        ('school_5_8', 'Школьники 5-8 класс'),
        ('school_9_11', 'Школьники 9-11 класс'),
        ('students', 'Студенты'),
        ('teachers', 'Педагоги'),
    ]
    LEVEL_CHOICES = [
        ('any', 'Любой'),
        ('beginner', 'Начальный'),
        ('intermediate', 'Средний'),
        ('advanced', 'Продвинутый'),
    ]
    title = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    audience = models.CharField(
        'Целевая аудитория',
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='open',
    )
    level = models.CharField(
        'Уровень',
        max_length=20,
        choices=LEVEL_CHOICES,
        default='any',
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
    )
    start_time = models.DateTimeField('Начало', null=True, blank=True)
    end_time = models.DateTimeField('Окончание', null=True, blank=True)
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
    max_participants = models.PositiveIntegerField(
        'Лимит участников',
        null=True,
        blank=True,
        help_text='Если пусто — без лимита.',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_competitions',
        verbose_name='Создатель',
    )

    class Meta:
        verbose_name = 'Соревнование'
        verbose_name_plural = 'Соревнования'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_registration_open(self):
        """Регистрация открыта, если статус соревнования «Регистрация»."""
        return self.status == 'registration'

    def is_running(self):
        return self.status == 'running'

    def is_finished(self):
        return self.status == 'finished'

    def age_label(self):
        if self.min_age and self.max_age:
            return f'{self.min_age}-{self.max_age} лет'
        if self.min_age:
            return f'{self.min_age}+'
        if self.max_age:
            return f'до {self.max_age}'
        return ''

    def slots_left(self):
        if not self.max_participants:
            return None
        current = self.participations.count()
        return max(0, self.max_participants - current)


class Task(models.Model):
    """Задача соревнования: условие, ограничения, максимальный балл; предмет и тип задания."""
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Соревнование',
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Предмет',
    )
    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='Тип задания',
    )
    title = models.CharField('Название', max_length=255)
    description = models.TextField('Условие задачи')
    order = models.PositiveIntegerField('Порядок', default=0)
    max_score = models.PositiveIntegerField('Максимальный балл', default=100)
    expected_output = models.TextField('Эталонный ответ (для проверки)', blank=True)
    organizer_material = models.FileField(
        'Материал от организатора',
        upload_to='competition_materials/%Y/%m/',
        null=True,
        blank=True,
        help_text='Можно приложить PDF/архив/документ с примерами или данными.',
    )
    allow_multiple_answers = models.BooleanField(
        'Несколько вариантов ответа',
        default=False,
        help_text='Для типа «Выбрать правильный вариант»: один ответ или несколько.',
    )
    opens_at = models.DateTimeField(
        'Открыть для участников с',
        null=True,
        blank=True,
        help_text='До этого времени участникам не показывается условие и не принимаются решения.',
    )
    closes_at = models.DateTimeField(
        'Закрыть приём решений',
        null=True,
        blank=True,
        help_text='После этого времени участники не могут отправлять новые решения (жюри и организатор видят всё).',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['competition', 'order', 'pk']

    def __str__(self):
        return f'{self.competition.title} — {self.title}'

    def is_multiple_choice(self):
        return self.task_type_id and self.task_type.slug == 'multiple_choice'

    def is_matching(self):
        return self.task_type_id and self.task_type.slug == 'match'


class TaskOption(models.Model):
    """Вариант ответа для заданий типа «выбрать правильный вариант»."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name='Задача',
    )
    text = models.CharField('Текст варианта', max_length=500)
    is_correct = models.BooleanField('Правильный ответ', default=False)
    order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'
        ordering = ['task', 'order', 'pk']

    def __str__(self):
        return self.text[:500] if len(self.text) > 500 else self.text


class TaskMatchingPair(models.Model):
    """Строка задания «Установить соответствие»: элемент слева и правильный ответ справа."""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='matching_pairs',
        verbose_name='Задача',
    )
    order = models.PositiveIntegerField('Порядок слева сверху вниз', default=0)
    left_text = models.CharField('Слева (что нужно сопоставить)', max_length=500, blank=True, default='')
    right_text = models.CharField('Справа (правильное соответствие)', max_length=500, blank=True, default='')

    class Meta:
        verbose_name = 'Пара соответствий'
        verbose_name_plural = 'Пары соответствий'
        ordering = ['task', 'order', 'pk']

    def __str__(self):
        return f'{self.left_text[:40]} → {self.right_text[:40]}'


class Participation(models.Model):
    """Участие пользователя в соревновании (регистрация)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='participations',
        verbose_name='Участник',
    )
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='participations',
        verbose_name='Соревнование',
    )
    registered_at = models.DateTimeField('Зарегистрирован', auto_now_add=True)

    class Meta:
        verbose_name = 'Участие'
        verbose_name_plural = 'Участия'
        unique_together = [['user', 'competition']]

    def __str__(self):
        return f'{self.user.username} — {self.competition.title}'


class Solution(models.Model):
    """Решение задачи: отправка участника и результат проверки."""
    STATUS_CHOICES = [
        ('pending', 'На проверке'),
        ('accepted', 'Зачтено'),
        ('rejected', 'Отклонено'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solutions',
        verbose_name='Участник',
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='solutions',
        verbose_name='Задача',
    )
    content = models.TextField('Код / ответ')
    attachment = models.FileField(
        'Файл решения',
        upload_to='solutions/%Y/%m/',
        null=True,
        blank=True,
        help_text='Опционально: архив проекта, скриншот, презентация и т.п.',
    )
    submitted_at = models.DateTimeField('Отправлено', auto_now_add=True)
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
    )
    score = models.PositiveIntegerField('Баллы', default=0)
    comment = models.TextField('Комментарий', blank=True)

    class Meta:
        verbose_name = 'Решение'
        verbose_name_plural = 'Решения'
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.user.username} — {self.task.title} ({self.status})'


class SolutionGradeEvent(models.Model):
    """История изменений ручной оценки решения (аудит работы жюри/организатора)."""
    solution = models.ForeignKey(
        Solution,
        on_delete=models.CASCADE,
        related_name='grade_events',
        verbose_name='Решение',
    )
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solution_grade_events',
        verbose_name='Кто изменил',
    )
    from_status = models.CharField('Статус до', max_length=20, blank=True)
    to_status = models.CharField('Статус после', max_length=20, blank=True)
    from_score = models.IntegerField('Баллы до', default=0)
    to_score = models.IntegerField('Баллы после', default=0)
    from_comment = models.TextField('Комментарий до', blank=True)
    to_comment = models.TextField('Комментарий после', blank=True)
    note = models.CharField('Причина / заметка', max_length=255, blank=True)
    created_at = models.DateTimeField('Изменено', auto_now_add=True)

    class Meta:
        verbose_name = 'Событие оценивания'
        verbose_name_plural = 'История оценивания'
        ordering = ['-created_at']

    def __str__(self):
        return f'Решение #{self.solution_id}: {self.from_score} → {self.to_score}'


class Announcement(models.Model):
    """Объявление организатора по соревнованию (новости, напоминания)."""
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name='Соревнование',
    )
    title = models.CharField('Заголовок', max_length=255)
    body = models.TextField('Текст')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements',
        verbose_name='Автор',
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)
    is_pinned = models.BooleanField('Закрепить', default=False)

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title
