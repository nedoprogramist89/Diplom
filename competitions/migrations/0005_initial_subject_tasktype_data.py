# Data migration: initial Subject and TaskType records

from django.db import migrations


def create_initial_data(apps, schema_editor):
    Subject = apps.get_model('competitions', 'Subject')
    TaskType = apps.get_model('competitions', 'TaskType')
    subjects = [
        (1, 'Математика', 'math'),
        (2, 'Русский язык', 'russian'),
        (3, 'Информатика', 'informatics'),
        (4, 'Физика', 'physics'),
        (5, 'Обществознание', 'social'),
        (6, 'История', 'history'),
        (7, 'Иностранный язык', 'foreign'),
        (8, 'Другое', 'other'),
    ]
    for order, name, slug in subjects:
        Subject.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})
    task_types = [
        (1, 'Решить пример / задачу', 'solve'),
        (2, 'Выбрать правильный вариант', 'multiple_choice'),
        (3, 'Краткий ответ', 'short_answer'),
        (4, 'Установить соответствие', 'match'),
        (5, 'Развёрнутый ответ (код/текст)', 'open_answer'),
    ]
    for order, name, slug in task_types:
        TaskType.objects.get_or_create(slug=slug, defaults={'name': name, 'order': order})


def reverse_data(apps, schema_editor):
    Subject = apps.get_model('competitions', 'Subject')
    TaskType = apps.get_model('competitions', 'TaskType')
    Subject.objects.all().delete()
    TaskType.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0004_add_subject_tasktype_taskoption'),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_data),
    ]
