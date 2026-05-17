"""
Сервер разработки: порт по умолчанию из RUNSERVER_PORT (.env) или 8888.
На Windows порты вроде 8000–8043 иногда попадают в excluded port range (Hyper-V и т.п.)
и дают «You don't have permission to access that port» — 8888 обычно свободен.
Явный аргумент `python manage.py runserver 127.0.0.1:8000` по-прежнему задаёт адрес и порт.
"""
import os

from django.contrib.staticfiles.management.commands.runserver import (
    Command as StaticFilesRunserverCommand,
)


class Command(StaticFilesRunserverCommand):
    default_port = os.getenv('RUNSERVER_PORT', '8888')
