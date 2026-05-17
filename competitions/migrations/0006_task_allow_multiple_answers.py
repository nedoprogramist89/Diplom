# Migration: Task.allow_multiple_answers — один или несколько вариантов ответа

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0005_initial_subject_tasktype_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='allow_multiple_answers',
            field=models.BooleanField(
                default=False,
                help_text='Для типа «Выбрать правильный вариант»: один ответ или несколько.',
                verbose_name='Несколько вариантов ответа',
            ),
        ),
    ]
