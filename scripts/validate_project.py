import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

try:
    from .fetch_maobidao_articles import load_urls
except ImportError:
    from fetch_maobidao_articles import load_urls


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


def validate_image_records(records, *, root=PROJECT_ROOT):
    errors = []
    paths = [row.get("path", "") for row in records]
    for path, count in Counter(paths).items():
        if path and count > 1:
            errors.append(f"duplicate image path: {path}")
    keys = [(row.get("article_url"), row.get("image_url")) for row in records]
    for key, count in Counter(keys).items():
        if all(key) and count > 1:
            errors.append(f"duplicate article/image key: {key[0]} {key[1]}")
    article_kinds = {}
    for row in records:
        article_kinds.setdefault(row.get("article_url", ""), []).append(row.get("kind"))
    for article_url, kinds in article_kinds.items():
        if not article_url or len(kinds) != 2 or set(kinds) != {"index", "sector"}:
            errors.append(f"incomplete fish-table pair: {article_url}")
    for index, row in enumerate(records, 1):
        path = row.get("path", "")
        if not path or not (root / path).is_file():
            errors.append(f"record {index} missing image file: {path}")
        if row.get("kind") not in {"index", "sector"}:
            errors.append(f"record {index} invalid table kind: {row.get('kind', '')}")
        if row.get("verified") is not True:
            errors.append(f"record {index} unverified fish-table record")
        if row.get("verified") and not row.get("data_date"):
            errors.append(f"record {index} verified record missing data_date")
    return errors


def validate_rankings(rows, *, required_names=RANKING_NAMES):
    errors = []
    dates = [row.get("数据日", "") for row in rows]
    for date, count in Counter(dates).items():
        if date and count > 1:
            errors.append(f"duplicate ranking date: {date}")
    for index, row in enumerate(rows, 1):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("数据日", "")):
            errors.append(f"ranking {index} invalid data date")
        for name in required_names:
            value = str(row.get(name, "")).strip()
            if not value:
                errors.append(f"ranking {index} missing ranking: {name}")
                continue
            try:
                rank = int(value)
            except ValueError:
                errors.append(f"ranking {index} invalid ranking: {name}={value}")
                continue
            if rank < 1 or rank > 20:
                errors.append(f"ranking {index} invalid ranking: {name}={value}")
    return errors


def validate_observations(rows):
    errors = []
    keys = [(row.get("data_date"), row.get("table_type"), row.get("name")) for row in rows]
    for key, count in Counter(keys).items():
        if all(key) and count > 1:
            errors.append(f"duplicate observation: {'/'.join(key)}")
    metrics = (
        "rank",
        "change_pct",
        "deviation_pct",
        "volume_ratio",
        "status_date",
        "range_pct",
        "rank_change",
        "source_image",
    )
    for index, row in enumerate(rows, 1):
        if row.get("table_type") not in {"index", "sector"}:
            errors.append(f"observation {index} invalid table_type")
        if str(row.get("verified", "")).lower() == "true":
            for metric in metrics:
                if str(row.get(metric, "")).strip() == "":
                    errors.append(f"observation {index} missing metric: {metric}")
    return errors


def validate_latest_dates(action_board, ranking_rows, observations):
    errors = []
    index_match = re.search(r"最新指数鱼盆数据日：(\d{4}-\d{2}-\d{2})", action_board)
    sector_match = re.search(r"最新板块鱼盆数据日：(\d{4}-\d{2}-\d{2})", action_board)
    board_index_date = index_match.group(1) if index_match else ""
    board_sector_date = sector_match.group(1) if sector_match else ""
    ranking_date = max((row.get("数据日", "") for row in ranking_rows), default="")
    index_observation_date = max(
        (row.get("data_date", "") for row in observations if row.get("table_type") == "index"),
        default="",
    )
    sector_observation_date = max(
        (row.get("data_date", "") for row in observations if row.get("table_type") == "sector"),
        default="",
    )
    if not board_index_date or len({board_index_date, ranking_date, index_observation_date}) != 1:
        errors.append(
            "latest index fish date mismatch: "
            f"board={board_index_date} ranking={ranking_date} observations={index_observation_date}"
        )
    if not board_sector_date or board_sector_date != sector_observation_date:
        errors.append(
            "latest sector fish date mismatch: "
            f"board={board_sector_date} observations={sector_observation_date}"
        )
    return errors


def validate_articles(urls, articles):
    errors = []
    article_urls = [row.get("url", "") for row in articles]
    if len(article_urls) != len(set(article_urls)):
        errors.append("duplicate article URL in cache")
    if len(urls) != len(set(urls)):
        errors.append("duplicate article URL in link registry")
    if set(urls) != set(article_urls):
        errors.append("article URL mismatch between registry and cache")
    indices = sorted(row.get("index") for row in articles if isinstance(row.get("index"), int))
    if indices != list(range(1, len(articles) + 1)):
        errors.append("article indices are not consecutive")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate project data invariants.")
    parser.parse_args(argv)
    data_dir = PROJECT_ROOT / "data"
    records = json.loads((data_dir / "yupen_image_records.json").read_text(encoding="utf-8"))
    articles = json.loads((data_dir / "maobidao_articles.json").read_text(encoding="utf-8"))
    with (data_dir / "yupen-index-ranking.csv").open(encoding="utf-8", newline="") as handle:
        ranking_rows = list(csv.DictReader(handle))
    with (data_dir / "yupen-observations.csv").open(encoding="utf-8", newline="") as handle:
        observations = list(csv.DictReader(handle))
    action_board = (PROJECT_ROOT / "docs/action-board.md").read_text(encoding="utf-8")

    errors = []
    errors.extend(validate_articles(load_urls(data_dir / "maobidao-link-log.md"), articles))
    errors.extend(validate_image_records(records))
    errors.extend(validate_rankings(ranking_rows))
    errors.extend(validate_observations(observations))
    errors.extend(validate_latest_dates(action_board, ranking_rows, observations))
    for row in observations:
        source = PROJECT_ROOT / row.get("source_image", "")
        if not source.is_file():
            errors.append(f"observation missing source image: {row.get('source_image', '')}")
    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1
    print(
        "project validation passed: "
        f"articles={len(articles)} images={len(records)} observations={len(observations)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
