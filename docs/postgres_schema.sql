-- Курсовая: соревнования по программированию
-- Диплом: хакатоны + соревнования (на примере вуза), команды, роли, фазы, задачи/тесты, решения, оценивание, рейтинг
--
-- Скрипт можно выполнять в pgAdmin. Он идемпотентный: использует IF NOT EXISTS/защиту от duplicate.
-- Ничего внешнего/зарубежного не требуется.

BEGIN;

-- Базовые расширения (опционально)
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------- Справочники (расширяемые) ----------

CREATE TABLE IF NOT EXISTS role (
  code text PRIMARY KEY,                -- participant / organizer / jury / admin / mentor ...
  title text NOT NULL
);

INSERT INTO role(code, title) VALUES
  ('participant', 'Участник'),
  ('organizer', 'Организатор'),
  ('jury', 'Жюри'),
  ('admin', 'Администратор')
ON CONFLICT (code) DO NOTHING;


CREATE TABLE IF NOT EXISTS event_type (
  code text PRIMARY KEY,                -- competition / hackathon
  title text NOT NULL
);

INSERT INTO event_type(code, title) VALUES
  ('competition', 'Соревнование'),
  ('hackathon', 'Хакатон')
ON CONFLICT (code) DO NOTHING;


CREATE TABLE IF NOT EXISTS event_status (
  code text PRIMARY KEY,                -- draft/published/registration/running/finished/cancelled
  title text NOT NULL,
  sort_order int NOT NULL DEFAULT 0
);

INSERT INTO event_status(code, title, sort_order) VALUES
  ('draft', 'Черновик', 10),
  ('published', 'Опубликовано', 20),
  ('registration', 'Регистрация', 30),
  ('running', 'Идёт', 40),
  ('finished', 'Завершено', 50),
  ('cancelled', 'Отменено', 60)
ON CONFLICT (code) DO NOTHING;


CREATE TABLE IF NOT EXISTS submission_status (
  code text PRIMARY KEY,                -- pending/accepted/rejected
  title text NOT NULL,
  sort_order int NOT NULL DEFAULT 0
);

INSERT INTO submission_status(code, title, sort_order) VALUES
  ('pending', 'На проверке', 10),
  ('accepted', 'Зачтено', 20),
  ('rejected', 'Отклонено', 30)
ON CONFLICT (code) DO NOTHING;


CREATE TABLE IF NOT EXISTS verdict (
  code text PRIMARY KEY,                -- ok/wa/tle/mle/re/ce/partial/manual ...
  title text NOT NULL,
  sort_order int NOT NULL DEFAULT 0
);

INSERT INTO verdict(code, title, sort_order) VALUES
  ('ok', 'Accepted', 10),
  ('wa', 'Wrong Answer', 20),
  ('tle', 'Time Limit', 30),
  ('mle', 'Memory Limit', 40),
  ('re', 'Runtime Error', 50),
  ('ce', 'Compile Error', 60),
  ('partial', 'Partial', 70),
  ('manual', 'Manual review', 80)
ON CONFLICT (code) DO NOTHING;


-- ---------- Организации / структура вуза (задел под РЭУ) ----------

CREATE TABLE IF NOT EXISTS organization (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  short_name text,
  kind text NOT NULL DEFAULT 'university',  -- university/faculty/department/company/club/other
  parent_id bigint REFERENCES organization(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_organization_parent ON organization(parent_id);


-- ---------- Пользователи ----------
-- Примечание: Django обычно использует свои таблицы auth_user.
-- Эта таблица — доменная (для SQL-проекта/документации) и может быть использована как отдельная модель.
-- Если в Django оставляешь AUTH_USER_MODEL, можно синхронизировать структуру с ORM или пометить как managed = False.

CREATE TABLE IF NOT EXISTS user_account (
  id bigserial PRIMARY KEY,
  username text NOT NULL,
  email citext NOT NULL,
  password_hash text,                   -- если используешь Django, хранение пароля будет в своей таблице
  role_code text NOT NULL REFERENCES role(code),
  organization_id bigint REFERENCES organization(id) ON DELETE SET NULL,
  is_active boolean NOT NULL DEFAULT true,
  is_staff boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_account_username UNIQUE(username),
  CONSTRAINT uq_user_account_email UNIQUE(email)
);

CREATE INDEX IF NOT EXISTS idx_user_account_org ON user_account(organization_id);
CREATE INDEX IF NOT EXISTS idx_user_account_role ON user_account(role_code);


-- ---------- Мероприятия: соревнования и хакатоны ----------
-- Единая таблица для расширяемости (тип = competition/hackathon).

CREATE TABLE IF NOT EXISTS event (
  id bigserial PRIMARY KEY,
  type_code text NOT NULL REFERENCES event_type(code),
  status_code text NOT NULL REFERENCES event_status(code) DEFAULT 'draft',
  title text NOT NULL,
  description text NOT NULL DEFAULT '',
  location text,                        -- очно/удалённо/адрес (задел)
  starts_at timestamptz,
  ends_at timestamptz,
  registration_starts_at timestamptz,
  registration_ends_at timestamptz,
  created_by_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT chk_event_time_range CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at),
  CONSTRAINT chk_event_reg_range CHECK (registration_ends_at IS NULL OR registration_starts_at IS NULL OR registration_ends_at >= registration_starts_at)
);

CREATE INDEX IF NOT EXISTS idx_event_type ON event(type_code);
CREATE INDEX IF NOT EXISTS idx_event_status ON event(status_code);
CREATE INDEX IF NOT EXISTS idx_event_creator ON event(created_by_user_id);


-- Фазы (особенно полезно для хакатонов; для соревнований можно оставить 1 фазу)
CREATE TABLE IF NOT EXISTS event_phase (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  title text NOT NULL,
  starts_at timestamptz,
  ends_at timestamptz,
  sort_order int NOT NULL DEFAULT 0,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT chk_phase_time_range CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at)
);

CREATE INDEX IF NOT EXISTS idx_event_phase_event ON event_phase(event_id);


-- ---------- Участие в мероприятиях ----------

CREATE TABLE IF NOT EXISTS participation (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  registered_at timestamptz NOT NULL DEFAULT now(),
  status text NOT NULL DEFAULT 'active',         -- active/cancelled/banned (расширяемо)
  meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_participation UNIQUE(event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_participation_event ON participation(event_id);
CREATE INDEX IF NOT EXISTS idx_participation_user ON participation(user_id);


-- ---------- Команды (для хакатонов и командных соревнований) ----------

CREATE TABLE IF NOT EXISTS team (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  name text NOT NULL,
  captain_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_team_name_per_event UNIQUE(event_id, name)
);

CREATE INDEX IF NOT EXISTS idx_team_event ON team(event_id);


CREATE TABLE IF NOT EXISTS team_member (
  id bigserial PRIMARY KEY,
  team_id bigint NOT NULL REFERENCES team(id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  role_in_team text NOT NULL DEFAULT 'member', -- member/captain/mentor (расширяемо)
  joined_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_team_member UNIQUE(team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_member_team ON team_member(team_id);
CREATE INDEX IF NOT EXISTS idx_team_member_user ON team_member(user_id);


-- ---------- Задачи (для соревнований и технических этапов хакатона) ----------

CREATE TABLE IF NOT EXISTS task (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  phase_id bigint REFERENCES event_phase(id) ON DELETE SET NULL,
  title text NOT NULL,
  statement text NOT NULL,                      -- условие
  sort_order int NOT NULL DEFAULT 0,
  max_score int NOT NULL DEFAULT 100 CHECK (max_score >= 0),
  time_limit_ms int CHECK (time_limit_ms IS NULL OR time_limit_ms > 0),
  memory_limit_kb int CHECK (memory_limit_kb IS NULL OR memory_limit_kb > 0),
  checker_type text NOT NULL DEFAULT 'expected_output', -- expected_output / testcases / manual
  expected_output text NOT NULL DEFAULT '',      -- для простого сравнения (курсовая)
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  meta jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_task_event ON task(event_id);
CREATE INDEX IF NOT EXISTS idx_task_phase ON task(phase_id);


-- Тест-кейсы (на будущее: автоматическая проверка)
CREATE TABLE IF NOT EXISTS task_testcase (
  id bigserial PRIMARY KEY,
  task_id bigint NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  title text,
  input_data text NOT NULL DEFAULT '',
  expected_output text NOT NULL DEFAULT '',
  is_sample boolean NOT NULL DEFAULT false,
  points int NOT NULL DEFAULT 0 CHECK (points >= 0),
  sort_order int NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_task_testcase_task ON task_testcase(task_id);


-- ---------- Решения / отправки ----------

CREATE TABLE IF NOT EXISTS submission (
  id bigserial PRIMARY KEY,
  task_id bigint NOT NULL REFERENCES task(id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  team_id bigint REFERENCES team(id) ON DELETE SET NULL, -- для командных
  language text,                                -- python/cpp/java/... (расширяемо)
  content text NOT NULL,                        -- код или ответ
  created_at timestamptz NOT NULL DEFAULT now(),
  status_code text NOT NULL REFERENCES submission_status(code) DEFAULT 'pending',
  verdict_code text REFERENCES verdict(code) ON DELETE SET NULL,
  score int NOT NULL DEFAULT 0 CHECK (score >= 0),
  judge_comment text NOT NULL DEFAULT '',
  judged_by_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  judged_at timestamptz,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_submission_task ON submission(task_id);
CREATE INDEX IF NOT EXISTS idx_submission_user ON submission(user_id);
CREATE INDEX IF NOT EXISTS idx_submission_team ON submission(team_id);
CREATE INDEX IF NOT EXISTS idx_submission_status ON submission(status_code);
CREATE INDEX IF NOT EXISTS idx_submission_created_at ON submission(created_at DESC);


-- Результаты по тестам (на будущее, если включишь автопроверку)
CREATE TABLE IF NOT EXISTS submission_run (
  id bigserial PRIMARY KEY,
  submission_id bigint NOT NULL REFERENCES submission(id) ON DELETE CASCADE,
  testcase_id bigint REFERENCES task_testcase(id) ON DELETE SET NULL,
  verdict_code text REFERENCES verdict(code) ON DELETE SET NULL,
  time_ms int CHECK (time_ms IS NULL OR time_ms >= 0),
  memory_kb int CHECK (memory_kb IS NULL OR memory_kb >= 0),
  stdout text NOT NULL DEFAULT '',
  stderr text NOT NULL DEFAULT '',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_submission_run_submission ON submission_run(submission_id);


-- ---------- Роли на мероприятии (жюри/организаторы/менторы) ----------

CREATE TABLE IF NOT EXISTS event_staff (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  user_id bigint NOT NULL REFERENCES user_account(id) ON DELETE CASCADE,
  role_code text NOT NULL REFERENCES role(code), -- organizer/jury/mentor...
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_event_staff UNIQUE(event_id, user_id, role_code)
);

CREATE INDEX IF NOT EXISTS idx_event_staff_event ON event_staff(event_id);
CREATE INDEX IF NOT EXISTS idx_event_staff_user ON event_staff(user_id);


-- ---------- Объявления / материалы ----------

CREATE TABLE IF NOT EXISTS announcement (
  id bigserial PRIMARY KEY,
  event_id bigint NOT NULL REFERENCES event(id) ON DELETE CASCADE,
  title text NOT NULL,
  body text NOT NULL,
  created_by_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  is_pinned boolean NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS idx_announcement_event ON announcement(event_id);


-- Универсальная таблица файловых вложений (пути/ключи хранения укажешь в приложении)
CREATE TABLE IF NOT EXISTS attachment (
  id bigserial PRIMARY KEY,
  entity_type text NOT NULL,                    -- 'task'/'announcement'/'submission'...
  entity_id bigint NOT NULL,
  filename text NOT NULL,
  mime_type text,
  storage_path text NOT NULL,                   -- путь/ключ хранения
  uploaded_by_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  meta jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_attachment_entity ON attachment(entity_type, entity_id);


-- ---------- Приглашения (на будущее: приглашать в команду/на роль) ----------

CREATE TABLE IF NOT EXISTS invitation (
  id bigserial PRIMARY KEY,
  event_id bigint REFERENCES event(id) ON DELETE CASCADE,
  team_id bigint REFERENCES team(id) ON DELETE CASCADE,
  email citext,
  invited_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  role_code text NOT NULL DEFAULT 'participant' REFERENCES role(code),
  token uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  accepted_at timestamptz,
  revoked_at timestamptz,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_invitation_token UNIQUE(token)
);

CREATE INDEX IF NOT EXISTS idx_invitation_event ON invitation(event_id);
CREATE INDEX IF NOT EXISTS idx_invitation_team ON invitation(team_id);


-- ---------- Аудит-лог (удобно для диплома/отчёта) ----------

CREATE TABLE IF NOT EXISTS audit_log (
  id bigserial PRIMARY KEY,
  actor_user_id bigint REFERENCES user_account(id) ON DELETE SET NULL,
  action text NOT NULL,                         -- create/update/delete/login/submit/judge...
  entity_type text NOT NULL,                    -- 'event'/'task'/'submission'...
  entity_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  ip inet,
  user_agent text,
  meta jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON audit_log(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);


-- ---------- Представления для рейтинга (по умолчанию без materialized view) ----------
-- Рейтинг можно считать через запросы; при росте нагрузки можно сделать materialized view и обновлять по расписанию.

CREATE OR REPLACE VIEW v_event_results AS
SELECT
  e.id AS event_id,
  p.user_id,
  ua.username,
  COALESCE(SUM(best_by_task.best_score), 0) AS total_score
FROM event e
JOIN participation p ON p.event_id = e.id
JOIN user_account ua ON ua.id = p.user_id
LEFT JOIN LATERAL (
  SELECT
    t.id AS task_id,
    MAX(s.score) AS best_score
  FROM task t
  LEFT JOIN submission s
    ON s.task_id = t.id
   AND s.user_id = p.user_id
   AND s.status_code = 'accepted'
  WHERE t.event_id = e.id
  GROUP BY t.id
) AS best_by_task ON TRUE
GROUP BY e.id, p.user_id, ua.username;

COMMIT;
