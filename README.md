# Beauty Assistant — ML System Design

Учебный проект собственного диалогового бьюти-ассистента: подбор товаров
по запросу и консультации по конкретному продукту.

**Автор:** Юлия Горшкова. **Текущая работа:** HW1 — дизайн системы и сетап репозитория.
Реализация и результаты экспериментов появятся в следующих итерациях.
Описание обезличено; корпоративные данные и исходный код сюда не включены.

- [ML System Design документ](docs/ml_system_design_doc.md)
- [Порядок сдачи домашних работ](CONTRIBUTING.md)

## Локальная работа

Нужны Git, Python 3.11+ и [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync --locked
uv run pre-commit install
uv run pre-commit run --all-files
```

Проверки: Ruff для будущего Python-кода, mdformat для Markdown,
валидность YAML, пробелы и окончания файлов. Версии зависимостей закреплены
в `uv.lock`; те же проверки запускаются в GitHub Actions на push и PR.
Ruff пропускает файлы, пока в проекте нет Python-кода.

Отдельный запуск:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mdformat --check README.md CONTRIBUTING.md docs
```

## Состав проекта

```text
docs/ml_system_design_doc.md   — цели, требования, scope, схема и оценка
pyproject.toml / uv.lock       — инструменты и версии зависимостей
.pre-commit-config.yaml        — проверки перед коммитом
.github/workflows/checks.yml   — проверки в GitHub Actions
```

## Основа документа

Структура адаптирована из [шаблона Reliable ML](https://github.com/IrinaGoloshchapova/ml_system_design_doc_ru/blob/main/ML_System_Design_Doc_Template.md).
Учебные материалы: [MLOps](https://mlops.ml-devs.com/).
Предлагаемые решения и неизвестные параметры отмечены в документе;
измеренных результатов пока нет.
