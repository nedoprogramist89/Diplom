# Удаление модели видеокомнат BigBlueButton (откат функционала)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('hackathons', '0008_hackathonvideoroom'),
    ]

    operations = [
        migrations.DeleteModel(
            name='HackathonVideoRoom',
        ),
    ]
