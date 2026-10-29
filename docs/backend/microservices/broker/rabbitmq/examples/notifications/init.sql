-- Данные «Задачника». В жизни это отдельный сервис, к которому ходят по API
CREATE SCHEMA tasker;

CREATE TABLE tasker.users (
    id    INT PRIMARY KEY,
    name  TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE tasker.tasks (
    id          INT PRIMARY KEY,
    title       TEXT NOT NULL,
    author_id   INT NOT NULL REFERENCES tasker.users,
    assignee_id INT REFERENCES tasker.users,
    status      TEXT NOT NULL DEFAULT 'open',  -- open | done
    due_date    DATE
);

CREATE TABLE tasker.comments (
    id        INT PRIMARY KEY,
    task_id   INT NOT NULL REFERENCES tasker.tasks,
    author_id INT NOT NULL REFERENCES tasker.users,
    text      TEXT NOT NULL
);

INSERT INTO tasker.users VALUES
    (1, 'Анна',  'anna@example.com'),
    (2, 'Борис', 'boris@example.com'),
    (3, 'Вера',  'vera@example.com'),
    (4, 'Глеб',  'gleb@example.com');

INSERT INTO tasker.tasks VALUES
    (1, 'Подготовить релиз 2.0',       1, 2, 'open', CURRENT_DATE - 2),
    (2, 'Обновить документацию API',   2, 3, 'open', CURRENT_DATE + 5),
    (3, 'Настроить резервные копии',   1, 4, 'open', CURRENT_DATE + 1),
    (4, 'Починить вход через почту',   1, 2, 'done', NULL);

INSERT INTO tasker.comments VALUES
    (1, 1, 1, 'Не забудь обновить changelog'),
    (2, 2, 1, 'Добавь примеры ответов с ошибками');

-- Данные сервиса уведомлений
CREATE SCHEMA notify;

CREATE TABLE notify.user_settings (
    user_id    INT PRIMARY KEY,
    timezone   TEXT NOT NULL DEFAULT 'Europe/Moscow',
    quiet_from TIME NOT NULL DEFAULT '22:00',
    quiet_to   TIME NOT NULL DEFAULT '08:00'
);

CREATE TABLE notify.unsubscribes (
    user_id  INT NOT NULL,
    category TEXT NOT NULL,  -- tasks | comments | digest
    PRIMARY KEY (user_id, category)
);

-- Одни и те же шаблоны для событий, дайджеста и ручных рассылок
CREATE TABLE notify.templates (
    name    TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    body    TEXT NOT NULL
);

-- История отправок. Уникальный notification_id не даёт отправить письмо дважды
CREATE TABLE notify.notifications (
    notification_id TEXT PRIMARY KEY,
    user_id         INT NOT NULL,
    channel         TEXT NOT NULL,
    category        TEXT NOT NULL,
    status          TEXT NOT NULL,  -- pending | sent | skipped | deferred | queued
    reason          TEXT,
    send_after      TIMESTAMPTZ,
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at         TIMESTAMPTZ
);

-- Запуски планировщика: одна строка на задание и период
CREATE TABLE notify.scheduler_runs (
    job         TEXT NOT NULL,
    period      TEXT NOT NULL,
    status      TEXT NOT NULL,  -- started | done
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    PRIMARY KEY (job, period)
);

INSERT INTO notify.user_settings (user_id) VALUES (1), (2), (3), (4);
INSERT INTO notify.unsubscribes VALUES (3, 'comments');

INSERT INTO notify.templates VALUES
('task.assigned',
 'Вам назначена задача «{{ task.title }}»',
 '{{ user.name }}, вам назначили задачу «{{ task.title }}».
{% if task.due_date %}Срок: {{ task.due_date }}.{% endif %}'),
('comment.created',
 'Новый комментарий к задаче «{{ task.title }}»',
 '{{ user.name }}, {{ author.name }} пишет: {{ comment.text }}'),
('digest.weekly',
 'Сводка за неделю {{ period }}',
 '{{ user.name }}, открытых задач: {{ tasks | length }}.
{% for task in tasks %}- {{ task.title }}{% if task.overdue %} (просрочена){% endif %}
{% endfor %}');
