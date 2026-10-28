CREATE SCHEMA IF NOT EXISTS content;

CREATE TABLE IF NOT EXISTS content.tag (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    modified timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content.task (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title text NOT NULL,
    description text,
    done boolean NOT NULL DEFAULT false,
    owner text NOT NULL,
    modified timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS content.task_tag (
    task_id uuid NOT NULL REFERENCES content.task (id) ON DELETE CASCADE,
    tag_id uuid NOT NULL REFERENCES content.tag (id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, tag_id)
);

-- ETL читает изменения по (modified, id): без индекса каждая пачка — полный проход по таблице
CREATE INDEX IF NOT EXISTS task_modified_idx ON content.task (modified, id);
CREATE INDEX IF NOT EXISTS tag_modified_idx ON content.tag (modified, id);
CREATE INDEX IF NOT EXISTS task_tag_tag_idx ON content.task_tag (tag_id);

-- Тестовые данные: 3 метки и 1000 задач
INSERT INTO content.tag (name) VALUES ('дом'), ('работа'), ('срочно');

INSERT INTO content.task (title, owner, done, modified)
SELECT
    (ARRAY['Купить продукты', 'Подготовить отчёт', 'Позвонить врачу', 'Оплатить счета'])[1 + n % 4] || ' №' || n,
    (ARRAY['anna', 'boris'])[1 + n % 2],
    n % 3 = 0,
    now() - (1000 - n) * interval '1 minute'
FROM generate_series(1, 1000) AS n;

INSERT INTO content.task_tag (task_id, tag_id)
SELECT task.id, tag.id
FROM content.task AS task
JOIN content.tag AS tag ON (tag.name = 'работа') = (task.title LIKE 'Подготовить%');
