# Git

**Git** — распределённая система контроля версий. Стандарт де-факто для разработки ПО.

## Модель данных Git

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

## Базовые команды

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

## Ветки

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

## Удалённые репозитории

```sh
git remote -v                         # список remote
git remote add origin <url>
git fetch origin                      # скачать историю без слияния
git pull                              # = fetch + merge
git pull --rebase                     # = fetch + rebase (без merge-коммита)
git push -u origin feature/login      # пушнуть и связать ветку
```

## Merge vs Rebase

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

## Stash — отложить изменения

```sh
git stash                             # отложить и очистить рабочее дерево
git stash -u                          # включая untracked файлы
git stash list
git stash pop                         # вернуть последний и удалить из стека
git stash apply stash@{2}             # применить конкретный
git stash drop stash@{0}              # удалить
```

## Отмена изменений

```sh
git restore <file>                    # откатить файл к версии из индекса
git restore --source=HEAD~1 <file>    # к версии из коммита

git reset --soft HEAD~1               # отменить коммит, оставить изменения staged
git reset --mixed HEAD~1              # (по умолчанию) оставить изменения unstaged
git reset --hard HEAD~1               # ⚠️  снести всё, включая рабочее дерево

git revert <sha>                      # сделать «обратный» коммит — безопасно для shared веток
```

## Cherry-pick

Взять отдельный коммит из другой ветки:
```sh
git cherry-pick <sha>
```

## Reflog — спасение после `reset --hard`

`git reflog` хранит **все движения HEAD** локально, даже после reset.
```sh
git reflog                            # увидеть, где HEAD был
git reset --hard HEAD@{2}             # вернуться к нужной позиции
```

## Полезные алиасы

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

## .gitignore

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

## Что спрашивают на собеседовании

- В чём разница между **merge** и **rebase**? Когда что использовать?
- В чём разница между **`reset`** и **`revert`**?
- Что такое **detached HEAD** и как из него выйти?
- Как **отменить коммит**, который уже **запушен**? *(`git revert` — создаст обратный коммит; `reset` + force push только если ты один работаешь с веткой.)*
- Как разрешать **merge-конфликты**?
- Что такое **`HEAD`**, **`HEAD~1`**, **`HEAD^`**? *(HEAD — текущий коммит, ~ и ^ — двигаются по родителям.)*
- Что делает **`git rebase -i`**? *(Интерактивный rebase: squash, reword, drop коммитов.)*
- Что такое **fast-forward merge**?

## Содержание

> Шпаргалки и сценарии будут добавляться по мере проработки темы.
