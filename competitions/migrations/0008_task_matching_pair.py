import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0007_task_opens_closes_schedule'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskMatchingPair',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок слева сверху вниз')),
                ('left_text', models.CharField(blank=True, default='', max_length=500, verbose_name='Слева (что нужно сопоставить)')),
                ('right_text', models.CharField(blank=True, default='', max_length=500, verbose_name='Справа (правильное соответствие)')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='matching_pairs', to='competitions.task', verbose_name='Задача')),
            ],
            options={
                'verbose_name': 'Пара соответствий',
                'verbose_name_plural': 'Пары соответствий',
                'ordering': ['task', 'order', 'pk'],
            },
        ),
    ]
