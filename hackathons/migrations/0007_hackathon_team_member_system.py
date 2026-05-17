from django.conf import settings
from django.db import migrations, models


def forward_fill_team_members(apps, schema_editor):
    HackathonTeam = apps.get_model('hackathons', 'HackathonTeam')
    HackathonRegistration = apps.get_model('hackathons', 'HackathonRegistration')
    HackathonTeamMember = apps.get_model('hackathons', 'HackathonTeamMember')

    for reg in HackathonRegistration.objects.exclude(team_id__isnull=True):
        HackathonTeamMember.objects.get_or_create(
            hackathon_id=reg.hackathon_id,
            team_id=reg.team_id,
            user_id=reg.user_id,
            defaults={'role': 'member'},
        )

    for team in HackathonTeam.objects.all():
        if team.captain_id:
            captain = HackathonTeamMember.objects.filter(
                hackathon_id=team.hackathon_id,
                team_id=team.id,
                user_id=team.captain_id,
            ).first()
            if captain is None:
                HackathonTeamMember.objects.create(
                    hackathon_id=team.hackathon_id,
                    team_id=team.id,
                    user_id=team.captain_id,
                    role='captain',
                )
            else:
                captain.role = 'captain'
                captain.save(update_fields=['role'])
        else:
            # Если капитан не был задан, назначим первого участника команды.
            first_member = HackathonTeamMember.objects.filter(
                hackathon_id=team.hackathon_id,
                team_id=team.id,
                role='member',
            ).first()
            if first_member:
                first_member.role = 'captain'
                first_member.save(update_fields=['role'])


def backward_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('hackathons', '0006_hackathonteam_hackathonregistration_team'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='hackathon',
            name='allow_user_team_creation',
            field=models.BooleanField(
                default=True,
                help_text='Если выключено, команды формирует организатор.',
                verbose_name='Разрешить участникам создавать команды',
            ),
        ),
        migrations.AddField(
            model_name='hackathon',
            name='max_team_size',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='Максимум участников в команде'),
        ),
        migrations.AddField(
            model_name='hackathon',
            name='min_team_size',
            field=models.PositiveSmallIntegerField(default=1, verbose_name='Минимум участников в команде'),
        ),
        migrations.CreateModel(
            name='HackathonTeamMember',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('captain', 'Капитан'), ('member', 'Участник'), ('request', 'Заявка')], default='request', max_length=16, verbose_name='Роль')),
                ('joined_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата записи')),
                ('hackathon', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='team_memberships', to='hackathons.hackathon', verbose_name='Хакатон')),
                ('team', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='team_members', to='hackathons.hackathonteam', verbose_name='Команда')),
                ('user', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='hackathon_team_memberships', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Участник команды хакатона',
                'verbose_name_plural': 'Участники команд хакатона',
                'ordering': ['joined_at', 'pk'],
                'unique_together': {('team', 'user'), ('hackathon', 'user')},
            },
        ),
        migrations.RunPython(forward_fill_team_members, backward_noop),
        migrations.RemoveField(
            model_name='hackathonteam',
            name='captain',
        ),
    ]
