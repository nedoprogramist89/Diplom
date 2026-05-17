from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0006_task_allow_multiple_answers'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='opens_at',
            field=models.DateTimeField(
                blank=True,
                help_text='До этого времени участникам не показывается условие и не принимаются решения.',
                null=True,
                verbose_name='Открыть для участников с',
            ),
        ),
        migrations.AddField(
            model_name='task',
            name='closes_at',
            field=models.DateTimeField(
                blank=True,
                help_text='После этого времени участники не могут отправлять новые решения (жюри и организатор видят всё).',
                null=True,
                verbose_name='Закрыть приём решений',
            ),
        ),
    ]
