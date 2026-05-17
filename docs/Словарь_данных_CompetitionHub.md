# Словарь данных WEB-приложения «CompetitionHub»

Документ для пояснительной записки (раздел проектирования данных, приложение к физической схеме).  
**СУБД:** PostgreSQL (на этапе отладки допускается SQLite с теми же именами таблиц Django).  
**Источник:** модели `accounts`, `competitions`, `hackathons` (Django ORM).

**Формат таблицы:** между столбцами — **2 пробела**. Скопируйте блок таблицы в Word; при необходимости «Преобразовать в таблицу» с разделителем «другой» (2 пробела).

---

Объект  Реквизит  Тип данных  Ключи и ограничения  Назначение
accounts_user  id  BIGSERIAL  PK  Уникальный идентификатор пользователя
accounts_user  password  VARCHAR(128)  NOT NULL  Хеш пароля (Django PBKDF2 и др., без открытого текста)
accounts_user  last_login  TIMESTAMPTZ   NULL  Время последнего входа
accounts_user  is_superuser  BOOLEAN  NOT NULL, по умолчанию FALSE  Признак суперпользователя Django
accounts_user  username  VARCHAR(150)  NOT NULL, UNIQUE  Логин (имя пользователя)
accounts_user  first_name  VARCHAR(150)   NOT NULL по умолчанию пусто  Имя
accounts_user  last_name  VARCHAR(150)   Отчество/фамилия (поле Django)  
accounts_user  email  VARCHAR(254)  NOT NULL, UNIQUE  Электронная почта (логин для восстановления пароля)
accounts_user  is_staff  BOOLEAN  NOT NULL, по умолчанию FALSE  Доступ к панели управления /admin/
accounts_user  is_active  BOOLEAN  NOT NULL, по умолчанию TRUE  Признак активной учётной записи
accounts_user  date_joined  TIMESTAMPTZ  NOT NULL  Дата регистрации в системе
accounts_user  organization  VARCHAR(255)   NOT NULL по умолчанию пусто  Организация (учебное заведение, команда)
accounts_user  role  VARCHAR(20)  NOT NULL, CHECK participant/organizer/jury, по умолчанию participant  Роль в приложении: участник, организатор, жюри
accounts_user  theme  VARCHAR(10)  NOT NULL, CHECK dark/light, по умолчанию dark  Тема интерфейса (тёмная / светлая)
accounts_inappnotification  id  BIGSERIAL  PK  Идентификатор уведомления в кабинете
accounts_inappnotification  user_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Получатель уведомления
accounts_inappnotification  kind  VARCHAR(20)  NOT NULL, CHECK announcement/grade/system, INDEX  Тип: объявление, оценка, системное
accounts_inappnotification  title  VARCHAR(255)  NOT NULL  Заголовок
accounts_inappnotification  body  TEXT   NOT NULL по умолчанию пусто  Текст уведомления
accounts_inappnotification  link  VARCHAR(500)   Относительный URL (например /competitions/1/)  
accounts_inappnotification  read_at  TIMESTAMPTZ   NULL, INDEX  Время прочтения (NULL — не прочитано)
accounts_inappnotification  created_at  TIMESTAMPTZ  NOT NULL, INDEX  Время создания
accounts_inappnotification  INDEX(user_id, created_at DESC)   —  Составной индекс ленты уведомлений  
competitions_subject  id  BIGSERIAL  PK  Идентификатор предмета (справочник)
competitions_subject  name  VARCHAR(100)  NOT NULL  Название предмета (математика, информатика, …)
competitions_subject  slug  VARCHAR(50)  NOT NULL, UNIQUE  Машинный код предмета
competitions_subject  order  INTEGER  NOT NULL, ≥ 0, по умолчанию 0  Порядок сортировки в списке
competitions_tasktype  id  BIGSERIAL  PK  Идентификатор типа задания (справочник)
competitions_tasktype  name  VARCHAR(100)  NOT NULL  Название типа (краткий ответ, выбор варианта, …)
competitions_tasktype  slug  VARCHAR(50)  NOT NULL, UNIQUE  Код типа (multiple_choice, match, …)
competitions_tasktype  order  INTEGER  NOT NULL, ≥ 0  Порядок в списке
competitions_tasktype  auto_partial_enabled  BOOLEAN  NOT NULL, по умолчанию TRUE  Разрешена ли частичная автооценка для типа
competitions_tasktype  partial_weight_percent  SMALLINT  NOT NULL, 0–100, по умолчанию 100  Вес типа в автооценке, %
competitions_competition  id  BIGSERIAL  PK  Идентификатор соревнования
competitions_competition  title  VARCHAR(255)  NOT NULL  Название турнира
competitions_competition  description  TEXT   NOT NULL по умолчанию пусто  Описание и регламент (текст)
competitions_competition  audience  VARCHAR(20)  NOT NULL, CHECK open/school_5_8/school_9_11/students/teachers  Целевая аудитория
competitions_competition  level  VARCHAR(20)  NOT NULL, CHECK any/beginner/intermediate/advanced  Уровень сложности
competitions_competition  status  VARCHAR(20)  NOT NULL, CHECK draft/published/registration/running/finished  Этап жизненного цикла турнира
competitions_competition  start_time  TIMESTAMPTZ   NULL  Плановое начало проведения
competitions_competition  end_time  TIMESTAMPTZ   NULL  Плановое окончание
competitions_competition  min_age  SMALLINT   NULL, ≥ 0  Минимальный возраст участника
competitions_competition  max_age  SMALLINT   NULL, ≥ 0  Максимальный возраст участника
competitions_competition  max_participants  INTEGER   NULL, ≥ 0  Лимит числа участников (NULL — без лимита)
competitions_competition  created_at  TIMESTAMPTZ  NOT NULL  Дата создания записи
competitions_competition  updated_at  TIMESTAMPTZ  NOT NULL  Дата последнего изменения
competitions_competition  created_by_id  BIGINT   FK → accounts_user(id) ON DELETE SET NULL  Организатор-создатель
competitions_task  id  BIGSERIAL  PK  Идентификатор задачи турнира
competitions_task  competition_id  BIGINT  NOT NULL, FK → competitions_competition(id) ON DELETE CASCADE  Соревнование-владелец
competitions_task  subject_id  BIGINT   FK → competitions_subject(id) ON DELETE SET NULL  Предмет (необязательно)
competitions_task  task_type_id  BIGINT   FK → competitions_tasktype(id) ON DELETE SET NULL  Тип задания
competitions_task  title  VARCHAR(255)  NOT NULL  Название задачи
competitions_task  description  TEXT  NOT NULL  Условие задачи
competitions_task  order  INTEGER  NOT NULL, ≥ 0  Порядок в списке задач
competitions_task  max_score  INTEGER  NOT NULL, ≥ 0, по умолчанию 100  Максимальный балл
competitions_task  expected_output  TEXT   Not NULL по умолчанию пусто  Эталонный ответ для автопроверки
competitions_task  organizer_material  VARCHAR(100)   NULL  Путь к файлу материала организатора (media/)
competitions_task  allow_multiple_answers  BOOLEAN  NOT NULL, по умолчанию FALSE  Несколько правильных вариантов (тип «выбор»)
competitions_task  opens_at  TIMESTAMPTZ   NULL  Время открытия задачи для участников
competitions_task  closes_at  TIMESTAMPTZ   NULL  Дедлайн приёма решений
competitions_task  created_at  TIMESTAMPTZ  NOT NULL  Создание
competitions_task  updated_at  TIMESTAMPTZ  NOT NULL  Изменение
competitions_taskoption  id  BIGSERIAL  PK  Идентификатор варианта ответа
competitions_taskoption  task_id  BIGINT  NOT NULL, FK → competitions_task(id) ON DELETE CASCADE  Задача
competitions_taskoption  text  VARCHAR(500)  NOT NULL  Текст варианта
competitions_taskoption  is_correct  BOOLEAN  NOT NULL, по умолчанию FALSE  Признак правильного варианта
competitions_taskoption  order  INTEGER  NOT NULL, ≥ 0  Порядок отображения
competitions_taskmatchingpair  id  BIGSERIAL  PK  Идентификатор пары «установить соответствие»
competitions_taskmatchingpair  task_id  BIGINT  NOT NULL, FK → competitions_task(id) ON DELETE CASCADE  Задача
competitions_taskmatchingpair  order  INTEGER  NOT NULL, ≥ 0  Порядок строки слева сверху вниз
competitions_taskmatchingpair  left_text  VARCHAR(500)  NOT NULL по умолчанию пусто  Элемент слева
competitions_taskmatchingpair  right_text  VARCHAR(500)  NOT NULL по умолчанию пусто  Правильное соответствие справа
competitions_participation  id  BIGSERIAL  PK  Идентификатор участия (регистрации)
competitions_participation  user_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Участник
competitions_participation  competition_id  BIGINT  NOT NULL, FK → competitions_competition(id) ON DELETE CASCADE  Соревнование
competitions_participation  registered_at  TIMESTAMPTZ  NOT NULL  Время регистрации
competitions_participation  UNIQUE(user_id, competition_id)   —  Один пользователь — одна регистрация на турнир  
competitions_solution  id  BIGSERIAL  PK  Идентификатор решения (попытки)
competitions_solution  user_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Участник, сдавший работу
competitions_solution  task_id  BIGINT  NOT NULL, FK → competitions_task(id) ON DELETE CASCADE  Задача
competitions_solution  content  TEXT  NOT NULL  Текст / код ответа
competitions_solution  attachment  VARCHAR(100)   NULL  Путь к прикреплённому файлу (media/solutions/…)
competitions_solution  submitted_at  TIMESTAMPTZ  NOT NULL  Время отправки
competitions_solution  status  VARCHAR(20)  NOT NULL, CHECK pending/accepted/rejected, по умолчанию pending  Статус проверки
competitions_solution  score  INTEGER  NOT NULL, ≥ 0, по умолчанию 0  Начисленные баллы
competitions_solution  comment  TEXT   Not NULL по умолчанию пусто  Комментарий жюри/организатора
competitions_solutiongradeevent  id  BIGSERIAL  PK  Идентификатор события в журнале оценивания
competitions_solutiongradeevent  solution_id  BIGINT  NOT NULL, FK → competitions_solution(id) ON DELETE CASCADE  Оцениваемое решение
competitions_solutiongradeevent  graded_by_id  BIGINT   FK → accounts_user(id) ON DELETE SET NULL  Кто изменил оценку
competitions_solutiongradeevent  from_status  VARCHAR(20)   Not NULL по умолчанию пусто  Статус до изменения
competitions_solutiongradeevent  to_status  VARCHAR(20)   Статус после изменения  
competitions_solutiongradeevent  from_score  INTEGER  NOT NULL, по умолчанию 0  Баллы до
competitions_solutiongradeevent  to_score  INTEGER  NOT NULL, по умолчанию 0  Баллы после
competitions_solutiongradeevent  from_comment  TEXT   Комментарий до  
competitions_solutiongradeevent  to_comment  TEXT   Комментарий после  
competitions_solutiongradeevent  note  VARCHAR(255)   Причина/заметка к изменению  
competitions_solutiongradeevent  created_at  TIMESTAMPTZ  NOT NULL  Время изменения оценки
competitions_announcement  id  BIGSERIAL  PK  Идентификатор объявления
competitions_announcement  competition_id  BIGINT  NOT NULL, FK → competitions_competition(id) ON DELETE CASCADE  Соревнование
competitions_announcement  title  VARCHAR(255)  NOT NULL  Заголовок объявления
competitions_announcement  body  TEXT  NOT NULL  Текст объявления
competitions_announcement  created_by_id  BIGINT   FK → accounts_user(id) ON DELETE SET NULL  Автор (организатор)
competitions_announcement  created_at  TIMESTAMPTZ  NOT NULL  Создание
competitions_announcement  updated_at  TIMESTAMPTZ  NOT NULL  Изменение
competitions_announcement  is_pinned  BOOLEAN  NOT NULL, по умолчанию FALSE  Закрепить вверху списка
hackathons_hackathon  id  BIGSERIAL  PK  Идентификатор хакатона
hackathons_hackathon  title  VARCHAR(255)  NOT NULL  Название мероприятия
hackathons_hackathon  slug  VARCHAR(80)  NOT NULL, UNIQUE  URL-фрагмент (транслит/unicode)
hackathons_hackathon  tagline  VARCHAR(220)   Краткий слоган  
hackathons_hackathon  description  TEXT   Описание хакатона  
hackathons_hackathon  audience  VARCHAR(20)  NOT NULL, CHECK open/school_7_11/students/mixed/professionals  Целевая аудитория
hackathons_hackathon  level  VARCHAR(20)  NOT NULL, CHECK any/starter/product/pro  Уровень
hackathons_hackathon  format  VARCHAR(16)  NOT NULL, CHECK online/offline/hybrid  Формат проведения
hackathons_hackathon  venue  VARCHAR(255)   Площадка / город (офлайн)  
hackathons_hackathon  status  VARCHAR(20)  NOT NULL, CHECK draft/published/registration/ongoing/finished  Статус мероприятия
hackathons_hackathon  registration_opens_at  TIMESTAMPTZ   NULL  Начало окна регистрации
hackathons_hackathon  registration_closes_at  TIMESTAMPTZ   NULL  Конец окна регистрации
hackathons_hackathon  starts_at  TIMESTAMPTZ   NULL  Старт хакинга
hackathons_hackathon  ends_at  TIMESTAMPTZ   NULL  Дедлайн сдачи / демо
hackathons_hackathon  min_age  SMALLINT   NULL  Возраст от
hackathons_hackathon  max_age  SMALLINT   NULL  Возраст до
hackathons_hackathon  max_teams  INTEGER   NULL, ≥ 0  Лимит числа команд
hackathons_hackathon  min_team_size  SMALLINT  NOT NULL, ≥ 1, по умолчанию 1  Минимум участников в команде
hackathons_hackathon  max_team_size  SMALLINT  NOT NULL, ≥ 1, по умолчанию 5  Максимум участников в команде
hackathons_hackathon  allow_user_team_creation  BOOLEAN  NOT NULL, по умолчанию TRUE  Участники могут создавать команды сами
hackathons_hackathon  tracks  TEXT   Список треков (по строке на трек)  
hackathons_hackathon  prizes  TEXT   Призы и номинации  
hackathons_hackathon  rules  TEXT   Правила и требования к проектам  
hackathons_hackathon  results_summary  TEXT   Публичные итоги и победители  
hackathons_hackathon  created_by_id  BIGINT   FK → accounts_user(id) ON DELETE SET NULL  Организатор-создатель
hackathons_hackathon  created_at  TIMESTAMPTZ  NOT NULL  Создание
hackathons_hackathon  updated_at  TIMESTAMPTZ  NOT NULL  Изменение
hackathons_hackathonregistration  id  BIGSERIAL  PK  Идентификатор регистрации на хакатон
hackathons_hackathonregistration  user_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Участник
hackathons_hackathonregistration  hackathon_id  BIGINT  NOT NULL, FK → hackathons_hackathon(id) ON DELETE CASCADE  Хакатон
hackathons_hackathonregistration  team_id  BIGINT   FK → hackathons_hackathonteam(id) ON DELETE SET NULL  Команда (если уже в составе)
hackathons_hackathonregistration  team_name  VARCHAR(120)   Желаемое название команды  
hackathons_hackathonregistration  looking_for_team  BOOLEAN  NOT NULL, по умолчанию FALSE  Ищу команду
hackathons_hackathonregistration  comment  VARCHAR(500)   Комментарий организатору  
hackathons_hackathonregistration  registered_at  TIMESTAMPTZ  NOT NULL  Время регистрации
hackathons_hackathonregistration  UNIQUE(user_id, hackathon_id)   —  Один пользователь — одна заявка на хакатон  
hackathons_hackathonteam  id  BIGSERIAL  PK  Идентификатор команды
hackathons_hackathonteam  hackathon_id  BIGINT  NOT NULL, FK → hackathons_hackathon(id) ON DELETE CASCADE  Хакатон
hackathons_hackathonteam  name  VARCHAR(120)  NOT NULL  Название команды
hackathons_hackathonteam  created_by_id  BIGINT   FK → accounts_user(id) ON DELETE SET NULL  Кто создал команду
hackathons_hackathonteam  created_at  TIMESTAMPTZ  NOT NULL  Время создания
hackathons_hackathonteam  UNIQUE(hackathon_id, name)   —  Уникальное имя команды в рамках хакатона  
hackathons_hackathonteammember  id  BIGSERIAL  PK  Идентификатор участия в команде
hackathons_hackathonteammember  hackathon_id  BIGINT  NOT NULL, FK → hackathons_hackathon(id) ON DELETE CASCADE  Хакатон (денормализация для ограничений)
hackathons_hackathonteammember  team_id  BIGINT  NOT NULL, FK → hackathons_hackathonteam(id) ON DELETE CASCADE  Команда
hackathons_hackathonteammember  user_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Пользователь
hackathons_hackathonteammember  role  VARCHAR(16)  NOT NULL, CHECK captain/member/request  Роль в команде
hackathons_hackathonteammember  joined_at  TIMESTAMPTZ  NOT NULL  Дата включения в команду
hackathons_hackathonteammember  UNIQUE(team_id, user_id)   —  Один пользователь один раз в команде  
hackathons_hackathonteammember  UNIQUE(hackathon_id, user_id)   —  Один пользователь — одна команда на хакатон  
hackathons_hackathonchatmessage  id  BIGSERIAL  PK  Идентификатор сообщения чата
hackathons_hackathonchatmessage  hackathon_id  BIGINT  NOT NULL, FK → hackathons_hackathon(id) ON DELETE CASCADE  Хакатон
hackathons_hackathonchatmessage  author_id  BIGINT  NOT NULL, FK → accounts_user(id) ON DELETE CASCADE  Автор сообщения
hackathons_hackathonchatmessage  team_name  VARCHAR(120)  NOT NULL, INDEX  Имя команды (канал чата)
hackathons_hackathonchatmessage  channel  VARCHAR(20)  NOT NULL, CHECK team/organizer  Канал: внутри команды / с оргкомитетом
hackathons_hackathonchatmessage  body  TEXT  NOT NULL, длина ≤ 2000  Текст сообщения
hackathons_hackathonchatmessage  created_at  TIMESTAMPTZ  NOT NULL, INDEX  Время отправки
django_admin_log  id  INTEGER  PK  Запись журнала панели управления (аудит)
django_admin_log  action_time  TIMESTAMPTZ  NOT NULL  Время действия
django_admin_log  user_id  INTEGER   FK → accounts_user(id) ON DELETE SET NULL  Пользователь staff, выполнивший действие
django_admin_log  content_type_id  INTEGER   FK → django_content_type(id)  Тип изменённого объекта
django_admin_log  object_id  TEXT   Идентификатор объекта (строка)  
django_admin_log  object_repr  VARCHAR(200)   Строковое представление объекта  
django_admin_log  action_flag  SMALLINT  NOT NULL, CHECK 1/2/3  Тип: добавление / изменение / удаление
django_admin_log  change_message  TEXT   JSON-описание изменённых полей  
django_session  session_key  VARCHAR(40)  PK  Ключ сессии веб-пользователя
django_session  session_data  TEXT  NOT NULL  Сериализованные данные сессии
django_session  expire_date  TIMESTAMPTZ  NOT NULL, INDEX  Срок действия сессии
(не таблица БД)  JWT access-токен  sub / user_id / exp  строка JWT, HMAC  Краткоживущий токен API (заголовок Authorization: Bearer)
(не таблица БД)  Файл CSV экспорта  results.csv  HTTP-ответ  —  Выгрузка таблицы результатов соревнования (формируется по запросу, в БД не хранится)

---

## Примечания к словарю

1. **Имена объектов** совпадают с таблицами Django (`<приложение>_<модель>` в нижнем регистре).
2. Поля внешних ключей в БД имеют суффикс `_id` (`user_id`, `competition_id`, …).
3. **CHECK** для перечислений в PostgreSQL задаются на уровне приложения (choices в моделях); при необходимости в приложении Г можно добавить явные `CHECK` в SQL.
4. Служебные таблицы Django (`django_migrations`, `django_content_type`, `auth_permission`, `auth_group` и др.) в словарь **доменной** части не включены; при требовании кафедры — отдельным подразделом «Служебные таблицы фреймворка».
5. Согласование: [логическая схема](Инструкция_логическая_схема_БД_CompetitionHub.md) (сущности), таблицы 3–5 пояснительной записки, `docs/postgres_schema.sql` (расширенный SQL-вариант).
