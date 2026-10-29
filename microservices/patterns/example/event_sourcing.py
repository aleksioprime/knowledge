"""Event Sourcing и CQRS на SQLite: журнал событий задач, снимки и проекция для чтения.

Запуск: python3 event_sourcing.py — база в памяти, файлов не остаётся.
"""
import json
import sqlite3

USERS = {10: 'Аня', 11: 'Борис'}

db = sqlite3.connect(':memory:', isolation_level=None)
db.executescript('''
    -- Модель записи: журнал событий, только добавление
    CREATE TABLE events (
        position INTEGER PRIMARY KEY AUTOINCREMENT,   -- общий порядок для проекций
        task_id  INTEGER NOT NULL,
        version  INTEGER NOT NULL,                    -- номер события внутри задачи
        type     TEXT    NOT NULL,
        data     TEXT    NOT NULL,
        UNIQUE (task_id, version)                     -- защита от параллельной записи
    );
    CREATE TABLE snapshots (task_id INTEGER PRIMARY KEY, version INTEGER, state TEXT);

    -- Модель чтения: готовый ответ на вопрос «сколько открытых задач у пользователя»
    CREATE TABLE open_tasks_by_user (user_id INTEGER PRIMARY KEY, open_count INTEGER NOT NULL);
    CREATE TABLE task_view (task_id INTEGER PRIMARY KEY, assignee INTEGER, is_open INTEGER);
    CREATE TABLE checkpoint (projection TEXT PRIMARY KEY, position INTEGER NOT NULL);
''')


class ConcurrencyError(Exception):
    pass


# ---------- запись: события и восстановление состояния ----------

def apply(state: dict | None, event_type: str, data: dict) -> dict:
    """Чистая функция: состояние + событие → новое состояние."""
    if event_type == 'TaskCreated':
        return {'title': data['title'], 'assignee': None, 'status': 'open'}
    if event_type == 'TaskAssigned':
        return {**state, 'assignee': data['user_id']}
    if event_type == 'TaskCompleted':
        return {**state, 'status': 'done'}
    if event_type == 'TaskReopened':
        return {**state, 'status': 'open'}
    raise ValueError(event_type)


def load(task_id: int, use_snapshot: bool = True) -> tuple[dict | None, int, int]:
    """Возвращает состояние, версию и сколько событий пришлось проиграть."""
    state, version = None, 0
    if use_snapshot:
        row = db.execute('SELECT version, state FROM snapshots WHERE task_id = ?', (task_id,)).fetchone()
        if row:
            version, state = row[0], json.loads(row[1])
    rows = db.execute(
        'SELECT version, type, data FROM events WHERE task_id = ? AND version > ? ORDER BY version',
        (task_id, version),
    ).fetchall()
    for version, event_type, data in rows:
        state = apply(state, event_type, json.loads(data))
    return state, version, len(rows)


def append(task_id: int, expected_version: int, event_type: str, **data) -> None:
    try:
        db.execute(
            'INSERT INTO events (task_id, version, type, data) VALUES (?, ?, ?, ?)',
            (task_id, expected_version + 1, event_type, json.dumps(data, ensure_ascii=False)),
        )
    except sqlite3.IntegrityError:
        raise ConcurrencyError(f'задачу {task_id} уже изменили (ожидали версию {expected_version})') from None


def save_snapshot(task_id: int) -> None:
    state, version, _ = load(task_id)
    db.execute('INSERT OR REPLACE INTO snapshots VALUES (?, ?, ?)', (task_id, version, json.dumps(state)))


# Команды: проверяют правила на восстановленном состоянии и добавляют событие
def create_task(task_id: int, title: str) -> None:
    append(task_id, 0, 'TaskCreated', title=title)


def assign(task_id: int, user_id: int) -> None:
    _, version, _ = load(task_id)
    append(task_id, version, 'TaskAssigned', user_id=user_id)


def complete(task_id: int) -> None:
    state, version, _ = load(task_id)
    if state['status'] == 'done':
        raise ValueError('задача уже выполнена')
    append(task_id, version, 'TaskCompleted')


def reopen(task_id: int) -> None:
    state, version, _ = load(task_id)
    if state['status'] == 'open':
        raise ValueError('задача и так открыта')
    append(task_id, version, 'TaskReopened')


# ---------- чтение: проекция, которая догоняет журнал ----------

def _shift(user_id: int | None, delta: int) -> None:
    if user_id is None or delta == 0:
        return
    db.execute(
        'INSERT INTO open_tasks_by_user VALUES (?, ?) '
        'ON CONFLICT (user_id) DO UPDATE SET open_count = open_count + excluded.open_count',
        (user_id, delta),
    )


def project(task_id: int, event_type: str, data: dict) -> None:
    row = db.execute('SELECT assignee, is_open FROM task_view WHERE task_id = ?', (task_id,)).fetchone()
    assignee, is_open = row if row else (None, 1)
    new_assignee = data['user_id'] if event_type == 'TaskAssigned' else assignee
    new_open = {'TaskCompleted': 0, 'TaskReopened': 1}.get(event_type, is_open)
    _shift(assignee, -is_open)        # снять задачу со старого исполнителя
    _shift(new_assignee, new_open)    # и поставить новому
    db.execute('INSERT OR REPLACE INTO task_view VALUES (?, ?, ?)', (task_id, new_assignee, new_open))


def run_projector(batch: int = 100) -> int:
    """Догоняет журнал пачками; позиция сохраняется в той же транзакции, что и проекция."""
    db.execute('INSERT OR IGNORE INTO checkpoint VALUES (?, 0)', ('open_tasks',))
    total = 0
    while True:
        (position,) = db.execute('SELECT position FROM checkpoint WHERE projection = ?', ('open_tasks',)).fetchone()
        rows = db.execute(
            'SELECT position, task_id, type, data FROM events WHERE position > ? ORDER BY position LIMIT ?',
            (position, batch),
        ).fetchall()
        if not rows:
            return total
        db.execute('BEGIN')
        for position, task_id, event_type, data in rows:
            project(task_id, event_type, json.loads(data))
        db.execute('UPDATE checkpoint SET position = ? WHERE projection = ?', (position, 'open_tasks'))
        db.execute('COMMIT')
        total += len(rows)


def rebuild_projection() -> None:
    db.execute('DELETE FROM open_tasks_by_user')
    db.execute('DELETE FROM task_view')
    db.execute('DELETE FROM checkpoint')
    run_projector()


def open_tasks() -> dict[str, int]:
    rows = db.execute('SELECT user_id, open_count FROM open_tasks_by_user ORDER BY user_id').fetchall()
    return {USERS[user_id]: count for user_id, count in rows}


def lag() -> str:
    (last,) = db.execute('SELECT COALESCE(MAX(position), 0) FROM events').fetchone()
    row = db.execute('SELECT position FROM checkpoint WHERE projection = ?', ('open_tasks',)).fetchone()
    done = row[0] if row else 0
    return f'обработано {done} из {last} событий'


# ---------- сценарий ----------

print('1. Команды пишут события в журнал')
create_task(1, 'Сдать отчёт')
create_task(2, 'Купить хлеб')
create_task(3, 'Починить кран')
assign(1, 10)
assign(2, 10)
assign(3, 11)
complete(2)
print(f'   проекция до запуска: {open_tasks()}, {lag()}')
run_projector()
print(f'   проекция догнала:    {open_tasks()}, {lag()}')

print('\n2. Новые события — проекция отстаёт, пока её не обработают')
assign(1, 11)
create_task(4, 'Записаться к врачу')
assign(4, 11)
print(f'   читаем сразу:        {open_tasks()}, {lag()}')
run_projector()
print(f'   после обработки:     {open_tasks()}, {lag()}')

print('\n3. Состояние задачи 1 восстанавливается проигрыванием событий')
for version, event_type, data in db.execute('SELECT version, type, data FROM events WHERE task_id = 1'):
    print(f'   v{version} {event_type} {data}')
state, version, replayed = load(1)
print(f'   → {state} (версия {version}, проиграно {replayed})')

print('\n4. Снимок: длинную историю не нужно проигрывать целиком')
for _ in range(500):
    complete(1)
    reopen(1)
state, version, replayed = load(1)
print(f'   без снимка: версия {version}, проиграно событий: {replayed}')
save_snapshot(1)
complete(1)
state_snap, version, replayed = load(1)
state_full, _, replayed_full = load(1, use_snapshot=False)
print(f'   со снимком: версия {version}, проиграно событий: {replayed}')
print(f'   совпадает с полным проигрыванием ({replayed_full} событий): {state_snap == state_full}')

print('\n5. Два запроса изменили задачу одновременно')
_, seen_version, _ = load(3)
append(3, seen_version, 'TaskAssigned', user_id=10)        # первый успел
try:
    append(3, seen_version, 'TaskAssigned', user_id=11)    # второй видел ту же версию
except ConcurrencyError as error:
    print(f'   {error}')

print('\n6. Проекцию можно выбросить и построить заново из журнала')
run_projector()
before = open_tasks()
rebuild_projection()
after = open_tasks()
print(f'   было:      {before}')
print(f'   с нуля:    {after}, {lag()}')
print(f'   совпадает: {before == after}')
