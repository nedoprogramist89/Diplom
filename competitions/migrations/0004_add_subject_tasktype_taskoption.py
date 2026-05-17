# Migration: Subject, TaskType, TaskOption; Task.subject, Task.task_type

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0003_add_announcement'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название')),
                ('slug', models.SlugField(max_length=50, unique=True, verbose_name='Код')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Предмет',
                'verbose_name_plural': 'Предметы',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='TaskType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Название')),
                ('slug', models.SlugField(max_length=50, unique=True, verbose_name='Код')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
            ],
            options={
                'verbose_name': 'Тип задания',
                'verbose_name_plural': 'Типы заданий',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.AddField(
            model_name='task',
            name='subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='competitions.subject', verbose_name='Предмет'),
        ),
        migrations.AddField(
            model_name='task',
            name='task_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='competitions.tasktype', verbose_name='Тип задания'),
        ),
        migrations.CreateModel(
            name='TaskOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=500, verbose_name='Текст варианта')),
                ('is_correct', models.BooleanField(default=False, verbose_name='Правильный ответ')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='competitions.task', verbose_name='Задача')),
            ],
            options={
                'verbose_name': 'Вариант ответа',
                'verbose_name_plural': 'Варианты ответов',
                'ordering': ['task', 'order', 'pk'],
            },
        ),
    ]
