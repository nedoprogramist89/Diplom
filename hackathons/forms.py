from django import forms
from django.utils.text import slugify

from competitions.forms import DateTimeLocalInput, DATETIME_LOCAL_INPUT_FORMATS

from .models import Hackathon, HackathonRegistration, HackathonChatMessage, HackathonTeam


class HackathonForm(forms.ModelForm):
    class Meta:
        model = Hackathon
        fields = (
            'title',
            'tagline',
            'description',
            'audience',
            'level',
            'format',
            'venue',
            'status',
            'registration_opens_at',
            'registration_closes_at',
            'starts_at',
            'ends_at',
            'min_age',
            'max_age',
            'max_teams',
            'min_team_size',
            'max_team_size',
            'allow_user_team_creation',
            'tracks',
            'prizes',
            'rules',
            'results_summary',
        )
        widgets = {
            'registration_opens_at': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
            'registration_closes_at': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
            'starts_at': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
            'ends_at': DateTimeLocalInput(attrs={'class': 'input-datetime'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            'registration_opens_at',
            'registration_closes_at',
            'starts_at',
            'ends_at',
        ):
            self.fields[field_name].input_formats = DATETIME_LOCAL_INPUT_FORMATS
            self.fields[field_name].required = False

    def clean(self):
        cleaned = super().clean()
        min_age = cleaned.get('min_age')
        max_age = cleaned.get('max_age')
        min_team_size = cleaned.get('min_team_size')
        max_team_size = cleaned.get('max_team_size')
        if min_age is not None and max_age is not None and min_age > max_age:
            self.add_error('max_age', 'Возраст "до" должен быть не меньше возраста "от".')
        if min_team_size and max_team_size and min_team_size > max_team_size:
            self.add_error('max_team_size', 'Максимум команды должен быть не меньше минимума.')
        return cleaned


def unique_slug_for_title(title, exclude_pk=None):
    base = slugify(title, allow_unicode=True)[:72] or 'hackathon'
    slug = base
    n = 1
    qs = Hackathon.objects.filter(slug=slug)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.exists():
        slug = f'{base}-{n}'
        n += 1
        qs = Hackathon.objects.filter(slug=slug)
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
    return slug


class HackathonRegistrationForm(forms.ModelForm):
    class Meta:
        model = HackathonRegistration
        fields = ('team_name', 'looking_for_team', 'comment')
        widgets = {
            'team_name': forms.TextInput(
                attrs={
                    'placeholder': 'Например: Team Aurora (можно оставить пустым, если ищу команду)',
                    'maxlength': '120',
                }
            ),
            'comment': forms.TextInput(
                attrs={
                    'placeholder': 'Стек, роль, ссылка на GitHub — по желанию',
                    'maxlength': '500',
                }
            ),
        }


class HackathonChatMessageForm(forms.ModelForm):
    class Meta:
        model = HackathonChatMessage
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(
                attrs={
                    'rows': 3,
                    'maxlength': '2000',
                    'placeholder': 'Введите сообщение...',
                }
            )
        }


class HackathonTeamCreateForm(forms.ModelForm):
    class Meta:
        model = HackathonTeam
        fields = ('name',)
        widgets = {
            'name': forms.TextInput(
                attrs={
                    'placeholder': 'Название команды',
                    'maxlength': '120',
                }
            ),
        }
