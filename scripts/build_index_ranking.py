import csv
from pathlib import Path


RANKING_NAMES = (
    "科创50",
    "创业板指",
    "中证500",
    "中证1000",
    "中证A500",
    "沪深300",
    "上证50",
    "纳指100",
    "标普500",
    "日经225",
    "韩国综合",
    "恒生科技",
)


def build_index_rankings(observations, required_names=RANKING_NAMES):
    by_date = {}
    for row in observations:
        if row.get("table_type") != "index" or row.get("name") not in required_names:
            continue
        by_date.setdefault(row["data_date"], {})[row["name"]] = row["rank"]
    return [
        {"数据日": data_date, **{name: by_date[data_date].get(name, "") for name in required_names}}
        for data_date in sorted(by_date)
    ]


def update_index_ranking(observations_path, output_path):
    observations_path = Path(observations_path)
    output_path = Path(output_path)
    with observations_path.open(encoding="utf-8", newline="") as handle:
        observations = list(csv.DictReader(handle))
    rows = build_index_rankings(observations)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("数据日", *RANKING_NAMES), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(output_path)
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    rows = update_index_ranking(
        root / "data/yupen-observations.csv",
        root / "data/yupen-index-ranking.csv",
    )
    print(f"saved {len(rows)} index ranking dates")


if __name__ == "__main__":
    main()
