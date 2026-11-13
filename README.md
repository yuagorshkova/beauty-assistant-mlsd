# Beauty Assistant — ML System Design

Проект собственного диалогового бьюти-ассистента: подбор товаров
по запросу и консультации по конкретному продукту.

**Автор:** Юлия Горшкова. **Текущая работа:** HW2 — EDA и этапы решения задачи.

- [ML System Design документ](docs/ml_system_design_doc.md)
- [EDA оценочного набора: состав, качество, графики и выводы](reports/eda/report.md)

## Локальная работа

Нужны Git, Python 3.11+ и [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
uv sync --locked
uv run pre-commit install
uv run pre-commit run --all-files
```

Проверки: Ruff для Python-кода, mdformat для Markdown,
валидность YAML, пробелы и окончания файлов. Версии зависимостей закреплены
в `uv.lock`.

Отдельный запуск:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mdformat --check README.md docs
```

Для воспроизведения графиков по опубликованным агрегатам:

```bash
uv sync --locked --group eda
uv run --group eda python scripts/eda.py --summary reports/eda/summary.json
```

Полный профиль пересчитывается по локальному JSON-массиву реплик:

```bash
uv run --group eda python scripts/eda.py --input data/evaluation.json
```

Сырые обращения хранятся отдельно. Скрипт сохраняет агрегаты без текстов и исходных ID;
правила интерпретации результатов описаны в отчёте EDA.
После смены набора выводы отчёта пересматриваются по новым агрегатам.

## Состав проекта

```text
docs/ml_system_design_doc.md   — цели, требования, scope, схема и оценка
pyproject.toml / uv.lock       — инструменты и версии зависимостей
.pre-commit-config.yaml        — проверки перед коммитом
scripts/eda.py                — расчёт агрегатов и графиков
reports/eda/                  — результаты EDA
```
