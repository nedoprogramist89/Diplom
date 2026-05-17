# Migration: add theme field to User

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='theme',
            field=models.CharField(
                blank=True,
                choices=[('dark', 'Тёмная'), ('light', 'Светлая')],
                default='dark',
                max_length=10,
                verbose_name='Тема оформления',
            ),
        ),
    ]
