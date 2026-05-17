"""Формы для соревнований: создание/редактирование задач, отправка решений."""
import sys
from random import Random

from django import forms
from django.forms.models import BaseModelFormSet, modelformset_factory
from django.utils import timezone

from .models import Task, Solution, TaskOption, Competition, TaskMatchingPair


class TaskForm(forms.ModelForm):
    """Создание / редактирование задачи: виджеты и порядок полей."""

    MODE_ONE = 'one'
    MODE_MANY = 'many'

    answer_mode = forms.ChoiceField(
        label='Как участник отмечает ответы',
        choices=[
            (MODE_ONE, 'Один вариант из списка (как в обычном тесте)'),
            (
                MODE_MANY,
                'Несколько вариантов сразу (школьные задачи «отметить все верные»)',
            ),
        ],
        initial=MODE_ONE,
        widget=forms.Select(attrs={'class': 'input-task-answer-mode'}),
        help_text='Используется только если тип задачи «Выбрать правильный вариант».',
    )

    class Meta:
        model = Task
        fields = (
            'task_type',
            'subject',
            'title',
            'description',
            'organizer_material',
            'max_score',
            'order',
            'opens_at',
            'closes_at',
            'expected_output',
        )
        widgets = {
            'task_type': forms.Select(attrs={'class': 'input-task-type'}),
            'subject': forms.Select(attrs={'class': 'input-task-subject'}),
            'title': forms.TextInput(
                attrs={
                    'class': 'input-task-title',
                    'placeholder': 'Краткий заголовок задачи для списков',
                    'autocomplete': 'off',
                    'maxlength': '255',
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'class': 'input-task-description',
                    'placeholder': 'Полное условие задачи — как нужно понять задачу участникам.',
                    'rows': 14,
                }
            ),
            'max_score': forms.NumberInput(attrs={'class': 'input-score', 'min': 1, 'max': 10000}),
            'order': forms.NumberInput(attrs={'class': 'input-order', 'min': 0}),
            'expected_output': forms.Textarea(
                attrs={
                    'class': 'input-expected',
                    'placeholder': 'Если нужна автоматическая сверка (опционально).',
                    'rows': 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _mod = sys.modules[__name__]
        _DTI = _mod.DateTimeLocalInput
        _formats = _mod.DATETIME_LOCAL_INPUT_FORMATS
        for fn in ('opens_at', 'closes_at'):
            self.fields[fn].widget = _DTI(attrs={'class': 'input-datetime'})
            self.fields[fn].required = False
            self.fields[fn].input_formats = _formats
        if self.instance.pk:
            val = (
                TaskForm.MODE_MANY
                if self.instance.allow_multiple_answers
                else TaskForm.MODE_ONE
            )
            self.fields['answer_mode'].initial = val

    def clean(self):
        data = super().clean()
        o = data.get('opens_at')
        c = data.get('closes_at')
        if o and c and o >= c:
            raise forms.ValidationError(
                'Время «Открыть с» должно быть раньше времени «Закрыть приём».'
            )
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        tt = self.cleaned_data.get('task_type')
        slug = getattr(tt, 'slug', None)
        if slug == 'multiple_choice':
            obj.allow_multiple_answers = (
                self.cleaned_data['answer_mode'] == TaskForm.MODE_MANY
            )
        else:
            obj.allow_multiple_answers = False
        if commit:
            obj.save()
        return obj


class TaskOptionForm(forms.ModelForm):
    """Один вариант ответа (MC) — удобный многострочный текст."""

    class Meta:
        model = TaskOption
        fields = ('text', 'is_correct', 'order')
        labels = {
            'is_correct': 'Правильный ответ',
            'order': 'Порядок в списке',
        }
        help_texts = {
            'is_correct': (
                'Включите для строк, которые при проверке считаются верными ответами '
                '(можно несколько галочек, если включён режим «несколько вариантов»).'
            ),
            'order': (
                'Чем меньше число, тем выше вариант в списке у участника (0 — первая строка, 1 — вторая…).'
            ),
        }
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'class': 'task-option-body',
                    'rows': 2,
                    'placeholder': 'Текст этого варианта ответа',
                }
            ),
            'order': forms.NumberInput(attrs={'class': 'task-option-order', 'min': 0}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'task-option-correct'}),
        }

    def clean_text(self):
        data = self.cleaned_data.get('text', '') or ''
        return data.strip()


class TaskMatchingPairForm(forms.ModelForm):
    """Одна пара «элемент слева — верный элемент справа» для типа соответствия."""

    class Meta:
        model = TaskMatchingPair
        fields = ('left_text', 'right_text', 'order')
        labels = {
            'left_text': 'Текст слева (в задании)',
            'right_text': 'Правильный ответ справа',
            'order': 'Порядок показа (0 — первая строка)',
        }
        help_texts = {
            'left_text': 'То, что видит участник слева; для него справа — общий список вариантов.',
            'right_text': 'Тот вариант из списка, который соответствует этой строке.',
            'order': 'Чем меньше число, тем выше строка при показе (0, 1, 2…).',
        }
        widgets = {
            'left_text': forms.Textarea(
                attrs={
                    'class': 'task-match-cell',
                    'rows': 2,
                    'placeholder': 'Например: формулировка A',
                }
            ),
            'right_text': forms.Textarea(
                attrs={
                    'class': 'task-match-cell',
                    'rows': 2,
                    'placeholder': 'Например: определение 1',
                }
            ),
            'order': forms.NumberInput(attrs={'class': 'task-option-order', 'min': 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for fn in ('left_text', 'right_text'):
            self.fields[fn].required = False

    def clean(self):
        data = super().clean()
        if self.cleaned_data.get('DELETE'):
            return data
        l = (data.get('left_text') or '').strip()
        r = (data.get('right_text') or '').strip()
        if not l and not r:
            return data
        if not l or not r:
            raise forms.ValidationError(
                'Заполните оба столбца пары или оставьте строку полностью пустой.'
            )
        data['left_text'] = l
        data['right_text'] = r
        return data


class BaseTaskMatchingPairFormSet(BaseModelFormSet):
    """Минимум две завершённые пары; строка либо пустая, либо с двумя полями (см. форму пары)."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        nonempty = 0
        for form in self.forms:
            cd = getattr(form, 'cleaned_data', None) or {}
            if cd.get('DELETE'):
                continue
            lt = (cd.get('left_text') or '').strip()
            rt = (cd.get('right_text') or '').strip()
            if lt and rt:
                nonempty += 1
        if nonempty < 2:
            raise forms.ValidationError(
                'Нужно указать минимум две пары «слева — справа» для соответствия.'
            )


TaskMatchingPairFormSet = modelformset_factory(
    TaskMatchingPair,
    form=TaskMatchingPairForm,
    formset=BaseTaskMatchingPairFormSet,
    extra=2,
    can_delete=True,
)
TaskMatchingPairFormSetForPost = modelformset_factory(
    TaskMatchingPair,
    form=TaskMatchingPairForm,
    formset=BaseTaskMatchingPairFormSet,
    extra=22,
    can_delete=True,
)


# Формат для input type="datetime-local" (HTML5 календарь с временем)
DATETIME_LOCAL_FORMAT = '%Y-%m-%dT%H:%M'
DATETIME_LOCAL_INPUT_FORMATS = [
    '%Y-%m-%dT%H:%M',      # значение из datetime-local
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%d',
    '%d.%m.%Y %H:%M',
    '%d.%m.%Y',
]


class DateTimeLocalInput(forms.DateTimeInput):
    """Виджет даты и времени с открытием календаря (input type="datetime-local")."""
    input_type = 'datetime-local'
    format = DATETIME_LOCAL_FORMAT

    def __init__(self, **kwargs):
        kwargs.setdefault('format', self.format)
        super().__init__(**kwargs)

    def format_value(self, value):
        if value is None:
            return ''
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        else:
            value = timezone.localtime(value)
        return value.strftime(self.format)


class CompetitionForm(forms.ModelForm):
    """Форма соревнования с полями даты/времени — календарь (datetime-local)."""
    class Meta:
        model = Competition
        fields = (
            'title',
            'description',
            'audience',
            'level',
            'status',
            'start_time',
            'end_time',
            'min_age',
            'max_age',
            'max_participants',
        )
        widgets = {
            'start_time': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
            'end_time': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('start_time', 'end_time'):
            self.fields[field_name].input_formats = DATETIME_LOCAL_INPUT_FORMATS
            self.fields[field_name].required = False

    def clean(self):
        cleaned = super().clean()
        min_age = cleaned.get('min_age')
        max_age = cleaned.get('max_age')
        if min_age is not None and max_age is not None and min_age > max_age:
            self.add_error('max_age', 'Возраст "до" должен быть не меньше возраста "от".')
        return cleaned


class SolutionSubmitForm(forms.ModelForm):
    """Форма отправки решения: вид поля зависит от типа задания."""
    selected_option = forms.ModelChoiceField(
        queryset=TaskOption.objects.none(),
        required=False,
        empty_label='Выберите вариант',
        widget=forms.RadioSelect(),
        label='Вариант ответа',
    )
    selected_options = forms.ModelMultipleChoiceField(
        queryset=TaskOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        label='Варианты ответа',
    )

    class Meta:
        model = Solution
        fields = ('content', 'attachment')

    def __init__(self, *args, task=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = task
        task_slug = task.task_type.slug if task and task.task_type else None
        self._match_rows = ()
        self.fields['attachment'].required = False

        if task and task.is_multiple_choice():
            opts = task.options.all().order_by('order', 'pk')
            if getattr(task, 'allow_multiple_answers', False):
                self.fields['selected_options'].queryset = opts
                self.fields['selected_options'].required = True
                self.fields.pop('selected_option', None)
                self.fields['content'].required = False
                self.fields['content'].widget = forms.HiddenInput()
            else:
                self.fields['selected_option'].queryset = opts
                self.fields['selected_option'].required = True
                self.fields.pop('selected_options', None)
                self.fields['content'].required = False
                self.fields['content'].widget = forms.HiddenInput()
        elif task and task.is_matching():
            self.fields.pop('selected_option', None)
            self.fields.pop('selected_options', None)
            self.fields['content'].required = False
            self.fields['content'].widget = forms.HiddenInput()
            self.fields['attachment'].widget = forms.HiddenInput()
            self._match_rows = tuple(task.matching_pairs.all().order_by('order', 'pk'))
            if self._match_rows:
                rng = Random(task.pk)
                pool = list(self._match_rows)
                rng.shuffle(pool)
                choice_tuples = [
                    ('', '— выберите вариант —'),
                ]
                choice_tuples.extend((str(p.pk), p.right_text) for p in pool)
                for i, lp in enumerate(self._match_rows):
                    self.fields[f'match_row_{i}'] = forms.ChoiceField(
                        label=lp.left_text,
                        choices=choice_tuples,
                        required=True,
                        widget=forms.Select(
                            attrs={'class': 'form-control input-select hz-match-dropdown'}
                        ),
                    )
            else:
                self.fields['content'].widget = forms.Textarea(
                    attrs={'readonly': True, 'class': 'input-text hz-disabled'},
                )
                self.fields['content'].initial = ''
        else:
            self.fields.pop('selected_option', None)
            self.fields.pop('selected_options', None)
            content = self.fields['content']
            content.required = True
            if task_slug == 'short_answer':
                content.label = 'Краткий ответ'
                content.widget = forms.TextInput(attrs={'placeholder': 'Введите краткий ответ', 'class': 'input-text'})
            elif task_slug == 'solve':
                content.label = 'Ответ'
                content.widget = forms.TextInput(attrs={'placeholder': 'Введите ответ', 'class': 'input-text'})
            else:
                content.label = 'Решение / ответ'
                content.widget = forms.Textarea(attrs={'rows': 12, 'placeholder': 'Введите решение или ответ (код/текст)...', 'class': 'input-text'})

    def clean(self):
        data = super().clean()
        if self.task and self.task.is_multiple_choice():
            if getattr(self.task, 'allow_multiple_answers', False):
                opts = data.get('selected_options')
                if not opts:
                    raise forms.ValidationError('Выберите хотя бы один вариант ответа.')
                data['content'] = ','.join(str(pk) for pk in opts.values_list('pk', flat=True))
            else:
                opt = data.get('selected_option')
                if not opt:
                    raise forms.ValidationError('Выберите вариант ответа.')
                data['content'] = str(opt.pk)
        elif self.task and self.task.is_matching():
            rows = getattr(self, '_match_rows', ()) or ()
            if not rows:
                raise forms.ValidationError(
                    'В задаче не настроены пары соответствий — обратитесь к организатору.'
                )
            parts = []
            for i in range(len(rows)):
                key = f'match_row_{i}'
                pk = data.get(key)
                if pk is None or pk == '':
                    raise forms.ValidationError('Выберите ответ справа для каждой строки слева.')
                parts.append(str(pk))
            data['content'] = ','.join(parts)
        return data

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self.task and self.task.is_multiple_choice():
            if getattr(self.task, 'allow_multiple_answers', False):
                opts = self.cleaned_data.get('selected_options')
                if opts:
                    obj.content = ','.join(str(pk) for pk in opts.values_list('pk', flat=True))
            else:
                opt = self.cleaned_data.get('selected_option')
                if opt:
                    obj.content = str(opt.pk)
        if commit:
            obj.save()
        return obj
