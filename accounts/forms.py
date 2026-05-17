"""
Формы: регистрация и смена пароля (веб-интерфейс).
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError('Пользователь с таким email уже зарегистрирован.')
        return email


class ProfileEditForm(forms.ModelForm):
    """Редактирование профиля: имя, email, организация, тема (роль — только в админке)."""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'organization', 'theme')
        labels = {
            'username': 'Имя пользователя',
            'email': 'Email',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'organization': 'Организация',
            'theme': 'Тема сайта',
        }
