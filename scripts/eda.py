"""Profile the evaluation corpus and rebuild its public aggregate report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

CATALOGS = ["makeup", "face_skincare", "body_skincare", "hair", "perfume", "other"]
REQUIRED = (
    "id",
    "dialog_id",
    "turn_index",
    "query",
    "sample_role",
    "category_c0",
    "catalog_0",
    "catalog_1",
    "n_subquestions",
    "personalized",
    "has_all_required_info",
    "evaluation_criteria",
)
PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s(\-]*\d{3}[\s)\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)")
EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"https?://\S+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold().replace("ё", "е")
    return re.sub(r"[^\w]+", "", text)


def quantile(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower), 1)


def summarize(rows: list[dict], digest: str) -> dict:
    if not isinstance(rows, list) or not rows or not all(isinstance(r, dict) for r in rows):
        raise ValueError("Ожидается непустой JSON-массив реплик")
    missing_keys = sum(any(key not in row for key in REQUIRED) for row in rows)
    if missing_keys:
        raise ValueError(f"В {missing_keys} строках отсутствуют обязательные столбцы")
    if any(not isinstance(r["query"], str) for r in rows):
        raise ValueError("query должен содержать строки")

    groups = defaultdict(list)
    for row in rows:
        groups[row["dialog_id"]].append(row)
    for turns in groups.values():
        turns.sort(key=lambda r: r["turn_index"])
    sequences = Counter(tuple(normalize(r["query"]) for r in v) for v in groups.values())
    all_texts = [normalize(r["query"]) for r in rows]
    checks = {
        "duplicate_ids": len(rows) - len({r["id"] for r in rows}),
        "empty_queries": sum(not r["query"].strip() for r in rows),
        "missing_annotations": sum(any(r[k] is None or r[k] == "" for k in REQUIRED) for r in rows),
        "empty_criteria": sum(not r["evaluation_criteria"] for r in rows),
        "invalid_turn_order": sum(
            [r["turn_index"] for r in v] != list(range(1, len(v) + 1)) for v in groups.values()
        ),
        "inconsistent_dialogue_length": sum(
            any(r.get("n_turns") != len(v) for r in v) for v in groups.values()
        ),
        "mixed_role_dialogues": sum(
            len({r["sample_role"] for r in v}) != 1 for v in groups.values()
        ),
        "duplicate_dialogue_sequences": sum(n - 1 for n in sequences.values()),
        "invalid_annotation_types": sum(
            type(r["personalized"]) is not bool
            or type(r["has_all_required_info"]) is not bool
            or type(r["n_subquestions"]) is not int
            or r["n_subquestions"] < 1
            or r["catalog_0"] not in CATALOGS
            or r["sample_role"] not in {"main", "hard_negative"}
            for r in rows
        ),
    }
    result = {
        "schema_version": 1,
        "input_sha256": digest,
        "rows": len(rows),
        "dialogues": len(groups),
        "checks": checks,
        "repeated_turn_text_excess": len(all_texts) - len(set(all_texts)),
        "dialogue_lengths": dict(sorted(Counter(len(v) for v in groups.values()).items())),
        "roles": {},
    }
    for role in ["main", "hard_negative"]:
        subset = [r for r in rows if r["sample_role"] == role]
        lengths = [len(r["query"]) for r in subset]
        sources = Counter(
            "Синтетические проверки"
            if r.get("transformation") == "synthetic"
            else "Обращения контакт-центра"
            if r.get("source_step") == "07"
            else "Экспертные сценарии"
            for r in subset
        )
        categories = Counter(r["category_c0"] for r in subset)
        bins = [0, 50, 100, 200, 400, 800, max(1600, max(lengths) + 1)]
        result["roles"][role] = {
            "rows": len(subset),
            "dialogues": len({r["dialog_id"] for r in subset}),
            "sources": dict(sources),
            "categories": dict(categories),
            "catalogs": dict(Counter(r["catalog_0"] for r in subset)),
            "matrix": {
                category: {
                    catalog: sum(
                        r["category_c0"] == category and r["catalog_0"] == catalog for r in subset
                    )
                    for catalog in CATALOGS
                }
                for category in categories
            },
            "personalized": sum(r["personalized"] for r in subset),
            "needs_clarification": sum(not r["has_all_required_info"] for r in subset),
            "multiturn_rows": sum(len(groups[r["dialog_id"]]) > 1 for r in subset),
            "criteria": dict(Counter(c["code"] for r in subset for c in r["evaluation_criteria"])),
            "length_quantiles": {str(p): quantile(lengths, p) for p in [0, 0.5, 0.95, 1]},
            "length_histogram": {
                "edges": bins,
                "counts": [
                    sum(low <= n < high for n in lengths)
                    for low, high in zip(bins[:-1], bins[1:], strict=True)
                ],
            },
        }
    provided = [r for r in rows if str(r.get("operator_response") or "").strip()]
    placeholders = [
        r for r in provided if str(r["operator_response"]).lstrip().startswith("[НЕТ ОТВЕТА")
    ]
    result["operator_answers"] = {
        "provided": len(provided),
        "usable_texts": len(provided) - len(placeholders),
        "placeholders": len(placeholders),
        "absent": len(rows) - len(provided),
    }
    result["privacy_signals"] = {
        field: {
            name: sum(bool(pattern.search(str(r.get(field) or ""))) for r in rows)
            for name, pattern in [("phone_like", PHONE), ("email_like", EMAIL), ("url", URL)]
        }
        for field in ["query", "operator_response"]
    }
    main_text = {normalize(r["query"]) for r in rows if r["sample_role"] == "main"}
    negative_text = {normalize(r["query"]) for r in rows if r["sample_role"] == "hard_negative"}
    result["cross_role_text_overlap"] = len(main_text & negative_text)
    excluded = {
        key
        for key, turns in groups.items()
        if any(
            r["category_c0"] == "Сравнение товаров"
            or any(c["code"] in {"R1", "R2", "R4", "R5"} for c in r["evaluation_criteria"])
            for r in turns
        )
    }
    core = [r for r in rows if r["sample_role"] == "main" and r["dialog_id"] not in excluded]
    result["scope_diagnostic"] = {
        "comparison_rows": result["roles"]["main"]["categories"].get("Сравнение товаров", 0),
        "remaining_rows": len(core),
        "remaining_dialogues": len({r["dialog_id"] for r in core}),
        "excluded_rows": result["roles"]["main"]["rows"] - len(core),
    }
    return result


def render(summary: dict, output: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    colors = ["#25877C", "#5476A5", "#C48145"]
    sources = ["Обращения контакт-центра", "Экспертные сценарии", "Синтетические проверки"]
    roles = ["main", "hard_negative"]
    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    left = [0, 0]
    for source, color in zip(sources, colors, strict=True):
        values = [summary["roles"][role]["sources"].get(source, 0) for role in roles]
        bars = ax.barh(
            ["Основной набор", "Проверки границ"], values, left=left, color=color, label=source
        )
        ax.bar_label(
            bars,
            labels=[str(v) if v else "" for v in values],
            label_type="center",
            color="white",
            fontsize=11,
        )
        left = [a + b for a, b in zip(left, values, strict=True)]
    ax.set(xlabel="Пользовательские реплики", title="Состав оценочного набора")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncols=1, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output / "composition.png", dpi=170)
    plt.close(fig)

    main = summary["roles"]["main"]
    categories = list(main["categories"])
    matrix = [
        [main["matrix"][category][catalog] for catalog in CATALOGS] for category in categories
    ]
    fig, ax = plt.subplots(figsize=(12, 5.5), layout="constrained")
    im = ax.imshow(matrix, cmap="YlGnBu", vmin=0)
    ax.set_xticks(
        range(len(CATALOGS)),
        ["Макияж", "Уход\nза лицом", "Уход\nза телом", "Волосы", "Парфюмерия", "Прочее"],
    )
    ax.set_yticks(range(len(categories)), [c.replace(", ", ",\n") for c in categories])
    for i, category in enumerate(categories):
        for j, value in enumerate(matrix[i]):
            share = 100 * value / main["categories"][category]
            ax.text(
                j,
                i,
                f"{value}\n{share:.0f}%",
                ha="center",
                va="center",
                color="white" if value >= 0.6 * max(map(max, matrix)) else "#172B35",
            )
    ax.set_title("Покрытие основного набора: количество и доля внутри строки", pad=14)
    fig.colorbar(im, ax=ax, label="Реплики", shrink=0.85)
    fig.savefig(output / "coverage.png", dpi=170)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    for index, (role, name, color) in enumerate(
        zip(roles, ["Основной", "Проверки границ"], colors[:2], strict=True)
    ):
        histogram = summary["roles"][role]["length_histogram"]
        edges = histogram["edges"]
        labels = [f"{low}–{high - 1}" for low, high in zip(edges[:-1], edges[1:], strict=True)]
        shares = [100 * n / summary["roles"][role]["rows"] for n in histogram["counts"]]
        axes[0].bar(
            [i + (index - 0.5) * 0.36 for i in range(len(labels))],
            shares,
            width=0.36,
            label=name,
            color=color,
        )
    axes[0].set_xticks(range(len(labels)), labels)
    axes[0].set(title="Длина запроса", xlabel="Символы", ylabel="% реплик своей группы")
    axes[0].tick_params(axis="x", rotation=35)
    axes[0].legend(frameon=False)
    lengths = summary["dialogue_lengths"]
    bars = axes[1].bar([str(n) for n in lengths], list(lengths.values()), color=colors[0])
    axes[1].bar_label(bars, padding=3)
    axes[1].set(title="Длина диалогов", xlabel="Пользовательские ходы", ylabel="Диалоги")
    axes[1].set_ylim(0, max(lengths.values()) * 1.15)
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(output / "dialogues.png", dpi=170)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Локальный JSON-массив реплик")
    source.add_argument("--summary", type=Path, help="Готовые агрегаты без текстов")
    parser.add_argument("--output", type=Path, default=Path("reports/eda"))
    args = parser.parse_args()
    if args.input:
        content = args.input.read_bytes()
        summary = summarize(json.loads(content), hashlib.sha256(content).hexdigest())
    else:
        summary = json.loads(args.summary.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    render(summary, args.output)
    print(
        json.dumps(
            {
                "rows": summary["rows"],
                "dialogues": summary["dialogues"],
                "checks": summary["checks"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
