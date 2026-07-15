import csv
import json
import re
import shutil
from pathlib import Path

try:
    from .validate_project import main as validate_project
except ImportError:
    from validate_project import main as validate_project


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GROUP_ORDER = ("主攻", "试探", "趋势保持", "等待", "回避")
NAME_ALIASES = {"证券": "证券公司", "创业板": "创业板指", "A500": "中证A500"}


def _read_csv(path):
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_action_board(text):
    summary_match = re.search(
        r"## 一句话状态\s*```text\s*(.*?)\s*```",
        text,
        re.DOTALL,
    )
    summary = " ".join(summary_match.group(1).split()) if summary_match else ""
    details = {}
    section_match = re.search(r"## 操作明细(.*?)(?=\n## )", text, re.DOTALL)
    if section_match:
        rows = [line for line in section_match.group(1).splitlines() if line.startswith("|")]
        for line in rows[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != 6:
                continue
            names, _, _, operation, _, next_validation = cells
            detail = {
                "operation": operation,
                "nextValidation": next_validation,
            }
            for name in (part.strip() for part in names.split("/")):
                details[NAME_ALIASES.get(name, name)] = detail
    return summary, details


def build_snapshot(root=PROJECT_ROOT):
    root = Path(root)
    data_dir = root / "data"
    action_board = (root / "docs/action-board.md").read_text(encoding="utf-8")
    market_summary, board_details = _parse_action_board(action_board)
    articles = json.loads((data_dir / "maobidao_articles.json").read_text(encoding="utf-8"))
    latest_article = max(articles, key=lambda row: (row["date"], row["index"]))
    signals = _read_csv(data_dir / "direction-signals.csv")
    episodes = _read_csv(data_dir / "signal-episodes.csv")
    signal_history = {}
    for signal in signals:
        signal_history.setdefault(
            (signal["table_type"], signal["name"]), []
        ).append(signal)
    episodes_by_direction = {}
    for episode in episodes:
        episodes_by_direction.setdefault(
            (episode["table_type"], episode["name"]), []
        ).append(episode)
    latest_dates = {
        table_type: max(
            row["data_date"] for row in signals if row["table_type"] == table_type
        )
        for table_type in ("index", "sector")
    }
    previous_dates = {}
    for table_type, latest_date in latest_dates.items():
        dates = sorted(
            {
                row["data_date"]
                for row in signals
                if row["table_type"] == table_type and row["data_date"] < latest_date
            }
        )
        previous_dates[table_type] = dates[-1] if dates else None
    current_signals = [
        row
        for row in signals
        if row["data_date"] == latest_dates[row["table_type"]]
    ]
    directions = []
    for row in current_signals:
        direction_episodes = episodes_by_direction.get((row["table_type"], row["name"]), [])
        lifecycle = max(direction_episodes, key=lambda item: item["start_date"], default=None)
        previous_rank = int(row["previous_rank"]) if row["previous_rank"] else None
        current_rank = int(row["rank"])
        recent_history = sorted(
            signal_history[(row["table_type"], row["name"])],
            key=lambda item: item["data_date"],
        )[-5:]
        direction = {
            "id": f'{row["table_type"]}:{row["name"]}',
            "name": row["name"],
            "type": row["table_type"],
            "dataDate": row["data_date"],
            "rank": current_rank,
            "changePct": float(row["change_pct"]),
            "deviationPct": float(row["deviation_pct"]),
            "volumeRatio": float(row["volume_ratio"]),
            "benchmark": row["benchmark"],
            "benchmarkChangePct": float(row["benchmark_change_pct"]),
            "previousDataDate": previous_dates[row["table_type"]],
            "rankMovement": previous_rank - current_rank if previous_rank else None,
            "history": [
                {
                    "date": item["data_date"],
                    "rank": int(item["rank"]),
                    "group": item["group"],
                }
                for item in recent_history
            ],
            "conditions": {
                "frontRank": int(row["rank"]) <= 3,
                "aboveMa20": float(row["deviation_pct"]) > 0,
                "strongerThanBenchmark": (
                    float(row["change_pct"]) > float(row["benchmark_change_pct"])
                ),
                "continuous": row["continuous"].lower() == "true",
                "volumeConfirmed": float(row["volume_ratio"]) >= 1,
            },
            "articleStance": row["article_stance"],
            "articleEvidence": row["article_evidence"],
            "group": row["group"],
            "action": row["action"],
            "sourceImage": row["source_image"],
            "lifecycle": (
                {
                    "startDate": lifecycle["start_date"],
                    "startGroup": lifecycle["start_group"],
                    "mainDate": lifecycle["main_date"],
                    "endDate": lifecycle["end_date"],
                    "endGroup": lifecycle["end_group"],
                    "observations": int(lifecycle["signal_observations"]),
                    "falseBreakout": lifecycle["false_breakout"].lower() == "true",
                    "status": lifecycle["status"],
                }
                if lifecycle
                else None
            ),
        }
        board_detail = board_details.get(row["name"], {})
        operation = board_detail.get("operation", "")
        operation_parts = [part.strip() for part in operation.split("/")]
        if len(operation_parts) > 1 and operation_parts[0] == row["group"]:
            direction["action"] = operation_parts[-1]
        elif operation and operation != row["group"]:
            direction["action"] = operation
        direction["nextValidation"] = board_detail.get(
            "nextValidation", "等待下一次鱼盆数据确认"
        )
        directions.append(direction)
    directions.sort(key=lambda row: (GROUP_ORDER.index(row["group"]), row["rank"], row["name"]))
    groups = [
        {
            "name": group,
            "directions": [row["name"] for row in directions if row["group"] == group],
        }
        for group in GROUP_ORDER
    ]
    return {
        "schemaVersion": 1,
        "meta": {
            "article": {
                "date": latest_article["date"],
                "title": latest_article["title"],
                "url": latest_article["url"],
            },
            "fishDataDates": latest_dates,
        },
        "marketSummary": market_summary,
        "groups": groups,
        "directions": directions,
    }


def write_web_snapshot(
    root=PROJECT_ROOT,
    output_path=None,
    image_dir=None,
):
    root = Path(root)
    output_path = Path(output_path or root / "web/public/data/project-snapshot.json")
    image_dir = Path(image_dir or root / "web/public/yupen-images")
    if validate_project([]) != 0:
        raise RuntimeError("project validation failed; web snapshot was not written")

    snapshot = build_snapshot(root)
    snapshot["meta"]["validationStatus"] = "passed"
    image_dir.mkdir(parents=True, exist_ok=True)
    for direction in snapshot["directions"]:
        source = root / direction["sourceImage"]
        if not source.is_file():
            raise FileNotFoundError(f"missing web evidence image: {source}")
        destination = image_dir / source.name
        shutil.copy2(source, destination)
        direction["sourceImage"] = f"/yupen-images/{source.name}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return snapshot


if __name__ == "__main__":
    result = write_web_snapshot()
    print(
        "saved web snapshot: "
        f"directions={len(result['directions'])} "
        f"article={result['meta']['article']['date']}"
    )
