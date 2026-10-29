# Beauty Assistant — ML System Design

Проект собственного диалогового бьюти-ассистента: подбор товаров
по запросу и консультации по конкретному продукту.

**Автор:** Юлия Горшкова. **Текущая работа:** HW1 — дизайн системы и сетап репозитория.
Реализация и результаты экспериментов появятся в следующих итерациях.

- [ML System Design документ](docs/ml_system_design_doc.md)

## Локальная работа

Нужны Git, Python 3.11+ и [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync --locked
uv run pre-commit install
uv run pre-commit run --all-files
```

Проверки: Ruff для будущего Python-кода, mdformat для Markdown,
валидность YAML, пробелы и окончания файлов. Версии зависимостей закреплены
в `uv.lock`.
Ruff пропускает файлы, пока в проекте нет Python-кода.

Отдельный запуск:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mdformat --check README.md docs
```

## Состав проекта

```text
docs/ml_system_design_doc.md   — цели, требования, scope, схема и оценка
pyproject.toml / uv.lock       — инструменты и версии зависимостей
.pre-commit-config.yaml        — проверки перед коммитом
```
