# Инструкция: размещение CompetitionHub на сервере (хостинг)

Документ описывает, как вынести проект **CompetitionHub** из локального `runserver` на сервер в интернете, чтобы работали: сайт, загрузка файлов (решения, материалы задач), админка `/admin/`, REST API `/api/`, восстановление пароля по почте.

Рекомендуемый вариант: **VPS с Linux** (Ubuntu 22.04/24.04) + **PostgreSQL** + **Gunicorn** + **Nginx**. Это стандартная схема для Django и подходит для дипломной демонстрации и реальной эксплуатации в учебном заведении.

---

## 1. Что понадобится

| Компонент | Назначение |
|-----------|------------|
| VPS или выделенный сервер | 1–2 ГБ ОЗУ минимум, 2+ ГБ для комфорта |
| Доменное имя (по желанию) | Например `competitionhub.example.ru` |
| PostgreSQL 14+ | Основная база (не SQLite на продакшене) |
| Python 3.11+ | Совпадает с `requirements.txt` |
| Nginx | Раздача статики, медиа, прокси к Gunicorn |
| SSL-сертификат | Let's Encrypt (бесплатно) при HTTPS |

**Не подходит для продакшена:** только `python manage.py runserver` — это сервер разработки, он не рассчитан на постоянную работу и внешний доступ.

---

## 2. Схема работы на сервере

```
Браузер пользователя
        ↓  HTTPS (443) / HTTP (80)
      Nginx  — отдаёт /static/ и /media/ с диска
        ↓  прокси на 127.0.0.1:8000
     Gunicorn  — Django (config.wsgi)
        ↓
   PostgreSQL
```

---

## 3. Подготовка сервера (Ubuntu)

Подключитесь по SSH и установите пакеты:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib nginx git
```

Создайте пользователя для приложения (не работайте от root):

```bash
sudo adduser --disabled-password --gecos "" competitionhub
sudo usermod -aG www-data competitionhub
```

Создайте каталог проекта:

```bash
sudo mkdir -p /var/www/competitionhub
sudo chown competitionhub:www-data /var/www/competitionhub
```

---

## 4. База данных PostgreSQL

```bash
sudo -u postgres psql
```

В консоли PostgreSQL:

```sql
CREATE USER competitionhub_user WITH PASSWORD 'надёжный_пароль';
CREATE DATABASE competitions_db OWNER competitionhub_user ENCODING 'UTF8';
\q
```

Проверка подключения:

```bash
psql -h 127.0.0.1 -U competitionhub_user -d competitions_db
```

---

## 5. Код проекта на сервере

Под пользователем `competitionhub`:

```bash
sudo su - competitionhub
cd /var/www/competitionhub
```

Скопируйте проект (один из способов):

- `git clone <url-репозитория> .`
- или загрузите архив и распакуйте в `/var/www/competitionhub`

Виртуальное окружение и зависимости:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 6. Файл `.env` для продакшена

Скопируйте шаблон и отредактируйте:

```bash
cp .env.example .env
nano .env
```

**Пример для сервера** (подставьте свои значения):

```env
SECRET_KEY=длинная-случайная-строка-сгенерируйте-отдельно
DEBUG=False
ALLOWED_HOSTS=your-domain.ru,www.your-domain.ru,IP_СЕРВЕРА
CSRF_TRUSTED_ORIGINS=https://your-domain.ru,https://www.your-domain.ru

DB_NAME=competitions_db
DB_USER=competitionhub_user
DB_PASSWORD=надёжный_пароль
DB_HOST=127.0.0.1
DB_PORT=5432

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@your-domain.ru
EMAIL_HOST_PASSWORD=пароль_приложения
DEFAULT_FROM_EMAIL=noreply@your-domain.ru
```

**Важно:**

- `SECRET_KEY` — сгенерируйте новый, не используйте значение из репозитория.
- `DEBUG=False` на боевом сервере.
- `ALLOWED_HOSTS` — домен и IP через запятую **без пробелов**.
- `CSRF_TRUSTED_ORIGINS` — обязателен при **HTTPS**, с префиксом `https://`.
- Не коммитьте `.env` в git.

Сгенерировать `SECRET_KEY` на сервере:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## 7. Миграции, статика, суперпользователь

```bash
cd /var/www/competitionhub
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Папки после `collectstatic`:

- `staticfiles/` — CSS и JS для Nginx (`/static/`)
- `media/` — загружаемые файлы пользователей (`/media/`), создаётся при первых загрузках

Права на запись в `media/`:

```bash
chmod -R u+rwX,g+rwX /var/www/competitionhub/media
```

---

## 8. Gunicorn (запуск Django)

Проверка вручную:

```bash
cd /var/www/competitionhub
source venv/bin/activate
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Откройте в браузере `http://IP_СЕРВЕРА:8000` (если порт открыт) или настройте Nginx сразу.

### Автозапуск через systemd

Создайте файл `/etc/systemd/system/competitionhub.service` (от root):

```ini
[Unit]
Description=CompetitionHub Gunicorn
After=network.target postgresql.service

[Service]
User=competitionhub
Group=www-data
WorkingDirectory=/var/www/competitionhub
Environment="PATH=/var/www/competitionhub/venv/bin"
ExecStart=/var/www/competitionhub/venv/bin/gunicorn config.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 3 \
    --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable competitionhub
sudo systemctl start competitionhub
sudo systemctl status competitionhub
```

Логи при ошибке:

```bash
sudo journalctl -u competitionhub -n 50 --no-pager
```

---

## 9. Nginx

Создайте `/etc/nginx/sites-available/competitionhub`:

```nginx
server {
    listen 80;
    server_name your-domain.ru www.your-domain.ru;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/competitionhub/staticfiles/;
    }

    location /media/ {
        alias /var/www/competitionhub/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Включите сайт и перезапустите Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/competitionhub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

В DNS домена укажите **A-запись** на IP сервера.

---

## 10. HTTPS (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.ru -d www.your-domain.ru
```

После выпуска сертификата проверьте, что в `.env` указаны `CSRF_TRUSTED_ORIGINS` с `https://`. Перезапустите приложение:

```bash
sudo systemctl restart competitionhub
```

---

## 11. Проверка, что «всё работает»

| Проверка | URL / действие | Ожидание |
|----------|----------------|----------|
| Главная | `/` | Открывается, сайдбар, стили |
| Регистрация и вход | `/accounts/register/`, `/accounts/login/` | Создание пользователя, вход |
| Соревнования | `/competitions/` | Список, карточка |
| Хакатоны | `/hackathons/` | Список |
| Админка | `/admin/` | Вход под `createsuperuser` (нужен `is_staff=True`) |
| API | `/api/` | Ответ API (документация по эндпоинтам в коде) |
| Загрузка файла | отправка решения с вложением | Файл в `media/`, без 404 |
| Почта | сброс пароля в профиле | Письмо приходит (если SMTP настроен) |
| Статика | F12 → Network, CSS | Код 200, не 404 |

Если стили «сломаны» — не выполнен `collectstatic` или неверный `alias` для `/static/` в Nginx.

Если 403 CSRF при входе по HTTPS — проверьте `CSRF_TRUSTED_ORIGINS` в `.env`.

Если `DisallowedHost` — добавьте домен в `ALLOWED_HOSTS`.

---

## 12. Обновление версии на сервере

```bash
sudo su - competitionhub
cd /var/www/competitionhub
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
exit
sudo systemctl restart competitionhub
```

---

## 13. Локальная проверка «как на сервере» (перед выкладкой)

На своём ПК можно имитировать продакшен без Nginx:

```bash
set DEBUG=False
set ALLOWED_HOSTS=127.0.0.1,localhost
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Статику в этом режиме удобнее смотреть через `DEBUG=True` и `runserver`, а перед сдачей — пройти чеклист из п. 11 на реальном VPS.

---

## 14. Частые ошибки

| Симптом | Причина | Решение |
|---------|---------|---------|
| 502 Bad Gateway | Gunicorn не запущен | `systemctl status competitionhub` |
| Стили не грузятся | Нет `collectstatic` или Nginx | п. 7, 9 |
| 404 на картинки/файлы | Нет `location /media/` | п. 9 |
| CSRF verification failed | Нет `CSRF_TRUSTED_ORIGINS` при HTTPS | п. 6 |
| DisallowedHost | Домен не в `ALLOWED_HOSTS` | п. 6 |
| Письма не уходят | `EMAIL_*` не заданы или блокировка SMTP | п. 6, логи |
| 500 после загрузки файла | Нет прав на `media/` | `chmod` на каталог media |

---

## 15. Windows-сервер (кратко)

Gunicorn на Windows не поддерживается официально. Варианты:

- развернуть на **Linux VPS** (рекомендуется);
- или использовать **WSL2** на Windows Server с той же инструкцией внутри Ubuntu;
- для IIS + Django нужна отдельная настройка (HttpPlatformHandler) — сложнее, для диплома обычно не требуется.

---

## 16. Связь с другими документами

| Документ | Содержание |
|----------|------------|
| [README.md](../README.md) | Быстрый локальный запуск |
| [.env.example](../.env.example) | Переменные окружения |
| [Инструкция_схема_взаимодействия_компонентов_CompetitionHub.md](Инструкция_схема_взаимодействия_компонентов_CompetitionHub.md) | Архитектура компонентов |
| [Документ 5](Документ%205) | Руководство пользователя (адреса для пользователей) |

После выкладки замените в руководстве пользователя `http://127.0.0.1:8888` на ваш боевой домен.
