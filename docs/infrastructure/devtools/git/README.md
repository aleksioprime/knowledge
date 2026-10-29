# Git

Git нужен, когда папки `project_final_v2` уже не спасают: непонятно, что менялось и зачем, нельзя вернуться к рабочей версии, а два человека не могут править один файл, не затирая друг друга. Git хранит историю снимков проекта, позволяет вести параллельные ветки и сливать их, а каждый коммит отвечает на вопрос «кто, когда и что поменял».

## Содержание

> Шпаргалки и сценарии будут добавляться по мере проработки темы.

## Минимальный пример

Новый репозиторий, первый коммит, ветка с правкой и слияние её в `main`.

```bash
git init tasker && cd tasker
# Initialized empty Git repository in /home/user/tasker/.git/

echo 'tasks = []' > tasks.py
git add tasks.py
git commit -m "Список задач"
# [main (root-commit) 3f2a1c9] Список задач
#  1 file changed, 1 insertion(+)
#  create mode 100644 tasks.py

git switch -c feature/deadline
# Switched to a new branch 'feature/deadline'
echo 'deadlines = {}' >> tasks.py
git commit -am "Сроки задач"
# [feature/deadline 8b7d4e2] Сроки задач
#  1 file changed, 1 insertion(+)

git switch main
# Switched to branch 'main'
git merge feature/deadline
# Updating 3f2a1c9..8b7d4e2
# Fast-forward
#  tasks.py | 1 +
#  1 file changed, 1 insertion(+)

git log --oneline
# 8b7d4e2 (HEAD -> main, feature/deadline) Сроки задач
# 3f2a1c9 Список задач
```

Хеши коммитов у вас будут другими: они считаются от содержимого, автора и времени.

## Как это работает

Коммит — это снимок всего дерева файлов со ссылкой на родителя, а ветка — просто указатель на коммит. Поэтому создание ветки мгновенно, а история — цепочка снимков, по которой можно ходить в любую сторону.

### Модель данных Git

Файл в git проходит три состояния:

```
Working tree   →   Index (stage)   →   Repository (.git)
 (рабочие             (что попадёт         (коммиты — снимки
  файлы)               в коммит)            истории)
       ↑                  ↑                      ↑
   git checkout       git add               git commit
```

Коммит — это **снимок** всего дерева файлов, ссылающийся на родительский коммит.
Ветка — это **указатель** на конкретный коммит. `HEAD` — указатель на текущий коммит/ветку.

### Базовые команды

```sh
git init                              # создать репозиторий
git clone <url>                       # склонировать удалённый

git status                            # что изменилось
git diff                              # diff незаиндексированных изменений
git diff --staged                     # diff заиндексированных

git add <file>                        # добавить в индекс
git add -p                            # интерактивно — выбрать кусочки
git restore --staged <file>           # убрать из индекса

git commit -m "msg"
git commit --amend                    # поправить последний коммит
git commit --amend --no-edit          # просто доложить файлы

git log --oneline --graph --all       # красивый лог
git show <sha>                        # содержимое коммита
```

### Ветки

```sh
git branch                            # список локальных
git branch -a                         # включая remote-ветки
git switch -c feature/login           # создать и переключиться (новый синтаксис)
git checkout -b feature/login         # старый синтаксис, всё ещё работает

git switch main
git merge feature/login               # влить feature в main
git branch -d feature/login           # удалить локально
git branch -D feature/login           # удалить принудительно
```

### Удалённые репозитории

```sh
git remote -v                         # список remote
git remote add origin <url>
git fetch origin                      # скачать историю без слияния
git pull                              # = fetch + merge
git pull --rebase                     # = fetch + rebase (без merge-коммита)
git push -u origin feature/login      # пушнуть и связать ветку
```

### Merge vs Rebase

**Merge** — объединяет ветки, создавая merge-коммит. История остаётся «как было».
```
A---B---C---M  (main)
     \     /
      D---E    (feature)
```

**Rebase** — переносит коммиты feature на новый базис. История получается «линейной».
```
A---B---C---D'---E'  (main + feature)
```

```sh
git rebase main                       # переписать текущую ветку на main
git rebase -i HEAD~5                  # интерактивный — squash/edit/drop коммитов
```

**Правило**: не делай `rebase` на коммитах, которые уже **запушены** и используются другими.

### Stash — отложить изменения

```sh
git stash                             # отложить и очистить рабочее дерево
git stash -u                          # включая untracked файлы
git stash list
git stash pop                         # вернуть последний и удалить из стека
git stash apply stash@{2}             # применить конкретный
git stash drop stash@{0}              # удалить
```

### Отмена изменений

```sh
git restore <file>                    # откатить файл к версии из индекса
git restore --source=HEAD~1 <file>    # к версии из коммита

git reset --soft HEAD~1               # отменить коммит, оставить изменения staged
git reset --mixed HEAD~1              # (по умолчанию) оставить изменения unstaged
git reset --hard HEAD~1               # ⚠️  снести всё, включая рабочее дерево

git revert <sha>                      # сделать «обратный» коммит — безопасно для shared веток
```

### Cherry-pick

Взять отдельный коммит из другой ветки:
```sh
git cherry-pick <sha>
```

### Reflog — спасение после `reset --hard`

`git reflog` хранит **все движения HEAD** локально, даже после reset.
```sh
git reflog                            # увидеть, где HEAD был
git reset --hard HEAD@{2}             # вернуться к нужной позиции
```

### Полезные алиасы

В `~/.gitconfig`:
```ini
[alias]
    st = status -sb
    co = checkout
    br = branch
    lg = log --oneline --graph --all --decorate
    last = log -1 HEAD
    unstage = restore --staged
```

### .gitignore

```
# Python
__pycache__/
*.pyc
.venv/
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Сборки
dist/
build/
*.egg-info/
```

## Частые ошибки

- `git add .` без `.gitignore` → в репозиторий попали `.venv/`, `__pycache__/` и `.env` с паролями; удаление из истории требует переписывания всех коммитов → завести `.gitignore` до первого коммита, секреты в репозитории считать скомпрометированными и перевыпустить.
- `git rebase` или `commit --amend` на уже запушенной ветке → `git push` отклонён, а коллеги получают конфликты на каждом `pull` → на общих ветках менять историю только `git revert`; свою ветку после rebase пушить через `git push --force-with-lease`.
- `git reset --hard` вместо `git stash` → незакоммиченные правки стёрты без возможности вернуть → откладывать работу через `git stash`; коммиты после `reset` возвращаются через `git reflog`, а вот незакоммиченные файлы — нет.
- `git pull` на ветке с локальными коммитами → лишние merge-коммиты «Merge branch 'main' of ...» в истории → `git pull --rebase` или `git config pull.rebase true`.
- `git checkout <sha>` для просмотра старого коммита, потом новые коммиты → они сделаны в detached HEAD и «пропадают» при переключении → перед правками создать ветку: `git switch -c fix-from-old`.
- Конфликт при слиянии решён, но маркеры `<<<<<<<` остались в файле → код не запускается, маркеры уходят в коммит → после правки искать маркеры (`git diff --check`) и только потом `git add`.
- Один коммит «fix» на двадцать файлов и три задачи → ревью затягивается, откатить одну правку нельзя → коммитить частями, выбирая куски через `git add -p`.

## Когда не использовать

Git не предназначен для больших двоичных файлов: видео, датасеты и дампы базы раздувают историю навсегда, даже после удаления из рабочего дерева. Для них берут Git LFS, облачное хранилище или DVC, а в репозитории оставляют ссылку.

Секреты и настройки конкретной машины (`.env`, ключи, токены) в репозитории не хранят, даже в приватном: история копируется в каждый клон. Для них — переменные окружения, [direnv или mise](../env_management/README.md) и хранилище секретов.

Для черновиков и личных заметок без истории git тоже лишний. Он окупается, когда есть что возвращать и с кем делиться.

## Что спрашивают на собеседовании

- В чём разница между **merge** и **rebase**? Когда что использовать?
- В чём разница между **`reset`** и **`revert`**?
- Что такое **detached HEAD** и как из него выйти?
- Как **отменить коммит**, который уже **запушен**? *(`git revert` — создаст обратный коммит; `reset` + force push только если ты один работаешь с веткой.)*
- Как разрешать **merge-конфликты**?
- Что такое **`HEAD`**, **`HEAD~1`**, **`HEAD^`**? *(HEAD — текущий коммит, ~ и ^ — двигаются по родителям.)*
- Что делает **`git rebase -i`**? *(Интерактивный rebase: squash, reword, drop коммитов.)*
- Что такое **fast-forward merge**?

## Связанные темы

- [Docker](../docker/README.md)
- [Линтеры и форматтеры](../linter/README.md) — pre-commit: проверки перед каждым коммитом
- [Управление окружением](../env_management/README.md)
- [Код-ревью](../../../practice/teamwork/code_review.md)
- [GitHub Actions](../../cicd/github/README.md)
