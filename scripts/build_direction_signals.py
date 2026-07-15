import csv
from pathlib import Path

try:
    from .trend_rules import evaluate_direction
except ImportError:
    from trend_rules import evaluate_direction


INDEX_BENCHMARKS = {
    "科创50": "中证A500",
    "创业板指": "中证A500",
    "中证500": "中证A500",
    "中证1000": "中证A500",
    "沪深300": "中证A500",
    "上证50": "中证A500",
    "微盘股": "中证A500",
    "北证50": "中证A500",
    "中证2000": "中证A500",
    "恒生科技": "恒生指数",
    "国企指数": "恒生指数",
    "纳指100": "标普500",
}
SIGNAL_FIELDS = (
    "data_date",
    "table_type",
    "name",
    "rank",
    "change_pct",
    "deviation_pct",
    "volume_ratio",
    "benchmark",
    "benchmark_change_pct",
    "previous_rank",
    "continuous",
    "article_stance",
    "article_evidence",
    "group",
    "action",
    "source_image",
)


def build_direction_signals(observations, article_stances):
    benchmark_changes = {
        (row["data_date"], row["name"]): float(row["change_pct"])
        for row in observations
        if row.get("table_type") == "index"
    }
    history = {}
    signals = []
    for row in sorted(
        observations,
        key=lambda item: (
            item.get("data_date", ""),
            item.get("table_type", ""),
            int(item.get("rank") or 999),
        ),
    ):
        table_type = row.get("table_type")
        if table_type == "sector":
            benchmark = "中证A500"
        elif table_type == "index":
            benchmark = INDEX_BENCHMARKS.get(row.get("name"))
        else:
            benchmark = None
        if not benchmark:
            continue
        data_date = row["data_date"]
        benchmark_change = benchmark_changes.get((data_date, benchmark))
        if benchmark_change is None:
            continue
        name = row["name"]
        ranks = history.setdefault((table_type, name), [])
        ranks.append(int(row["rank"]))
        stance = article_stances.get((data_date, table_type, name), "neutral")
        result = evaluate_direction(
            rank=ranks[-1],
            deviation_pct=float(row["deviation_pct"]),
            change_pct=float(row["change_pct"]),
            benchmark_change_pct=benchmark_change,
            volume_ratio=float(row["volume_ratio"]),
            recent_ranks=ranks,
            article_stance=stance,
        )
        signals.append(
            {
                "data_date": data_date,
                "table_type": table_type,
                "name": name,
                "rank": ranks[-1],
                "change_pct": float(row["change_pct"]),
                "deviation_pct": float(row["deviation_pct"]),
                "volume_ratio": float(row["volume_ratio"]),
                "benchmark": benchmark,
                "benchmark_change_pct": benchmark_change,
                "recent_ranks": ranks[-2:],
                "previous_rank": ranks[-2] if len(ranks) >= 2 else "",
                "continuous": result.continuous,
                "article_stance": stance,
                "article_evidence": "",
                "group": result.group,
                "action": result.action,
                "source_image": row.get("source_image", ""),
            }
        )
    return signals


def update_direction_signals(observations_path, stances_path, output_path):
    observations_path = Path(observations_path)
    stances_path = Path(stances_path)
    output_path = Path(output_path)
    with observations_path.open(encoding="utf-8", newline="") as handle:
        observations = list(csv.DictReader(handle))
    stance_rows = []
    if stances_path.is_file():
        with stances_path.open(encoding="utf-8", newline="") as handle:
            stance_rows = list(csv.DictReader(handle))
    stances = {
        (row["data_date"], row["table_type"], row["name"]): row["stance"]
        for row in stance_rows
    }
    evidence = {
        (row["data_date"], row["table_type"], row["name"]): row.get("evidence", "")
        for row in stance_rows
    }
    signals = build_direction_signals(observations, stances)
    for signal in signals:
        key = (signal["data_date"], signal["table_type"], signal["name"])
        signal["article_evidence"] = evidence.get(key, "")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SIGNAL_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(signals)
    temporary.replace(output_path)
    return signals


def main():
    root = Path(__file__).resolve().parents[1]
    signals = update_direction_signals(
        root / "data/yupen-observations.csv",
        root / "data/article-direction-stances.csv",
        root / "data/direction-signals.csv",
    )
    print(f"saved {len(signals)} direction signals")


if __name__ == "__main__":
    main()
