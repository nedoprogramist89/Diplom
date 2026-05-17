import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_theme'),
    ]

    operations = [
        migrations.CreateModel(
            name='InAppNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('announcement', 'Объявление'), ('grade', 'Проверка решения'), ('system', 'Системное')], db_index=True, default='system', max_length=20, verbose_name='Тип')),
                ('title', models.CharField(max_length=255, verbose_name='Заголовок')),
                ('body', models.TextField(blank=True, verbose_name='Текст')),
                ('link', models.CharField(blank=True, help_text='Относительный путь, например /competitions/1/', max_length=500, verbose_name='Ссылка')),
                ('read_at', models.DateTimeField(blank=True, db_index=True, null=True, verbose_name='Прочитано')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создано')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='in_app_notifications', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Уведомление',
                'verbose_name_plural': 'Уведомления',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='inappnotification',
            index=models.Index(fields=['user', '-created_at'], name='accounts_in_user_id_6e8bde_idx'),
        ),
    ]
