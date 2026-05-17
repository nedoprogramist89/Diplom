## Установка и запуск

   ```bash
   python -m venv venv
   venv\Scripts\activate  
   ```

   ```bash
   pip install -r requirements.txt
   ```
   ```bash
   python manage.py migrate
   ```

   ```bash
   python manage.py createsuperuser
   ```

   ```bash
   python manage.py runserver 127.0.0.1:9000
   ```
  

Сайт: http://127.0.0.1:8888/  
Админка: http://127.0.0.1:8888/admin/

## Размещение на сервере (хостинг)

Пошаговая инструкция для VPS (PostgreSQL, Gunicorn, Nginx, HTTPS, SMTP): [docs/Инструкция_хостинг_CompetitionHub.md](docs/Инструкция_хостинг_CompetitionHub.md).

## Документация для пояснительной записки

Логическая схема БД (рис. 29, подраздел 2.3.2): [docs/Инструкция_логическая_схема_БД_CompetitionHub.md](docs/Инструкция_логическая_схема_БД_CompetitionHub.md).  
Словарь данных (таблица «Объект — Реквизит — Тип — Ключи — Назначение»): [docs/Словарь_данных_CompetitionHub.md](docs/Словарь_данных_CompetitionHub.md).
