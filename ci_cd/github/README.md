# GitHub Actions

**GitHub Actions** — встроенная в GitHub платформа CI/CD. Позволяет автоматизировать сборку, тестирование и деплой прямо из репозитория через YAML-файлы в `.github/workflows/`.

Основные сущности:
- **Workflow** — описание pipeline в YAML
- **Event** — триггер (push, pull_request, schedule, workflow_dispatch)
- **Job** — набор шагов на одном runner-е
- **Step** — отдельная команда или action
- **Action** — переиспользуемая единица (есть Marketplace)
- **Runner** — VM, где выполняется job (GitHub-hosted или self-hosted)

Типичные сценарии:
- Прогон тестов и линтеров на каждый PR
- Сборка и публикация Docker-образа
- Деплой на сервер по push в main
- Релизы и публикация артефактов

## Содержание

> Заметки и примеры будут добавляться по мере проработки темы.
