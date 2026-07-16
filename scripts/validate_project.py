import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

try:
    from .build_direction_signals import build_direction_signals
    from .build_index_ranking import RANKING_NAMES, build_index_rankings
    from .build_signal_lifecycle import build_signal_episodes
    from .fetch_maobidao_articles import load_urls
except ImportError:
    from build_direction_signals import build_direction_signals
    from build_index_ranking import RANKING_NAMES, build_index_rankings
    from build_signal_lifecycle import build_signal_episodes
    from fetch_maobidao_articles import load_urls


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLE_SIZE = {"index": 20, "sector": 14}


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


def validate_index_rankings(ranking_rows, observations, required_names=RANKING_NAMES):
    errors = []
    expected = build_index_rankings(observations, required_names)
    expected_by_date = {row["数据日"]: row for row in expected}
    actual_by_date = {row.get("数据日", ""): row for row in ranking_rows}
    for data_date, expected_row in expected_by_date.items():
        actual_row = actual_by_date.get(data_date, {})
        for name in required_names:
            if actual_row.get(name, "") != expected_row.get(name, ""):
                errors.append(
                    "ranking content mismatch: "
                    f"{data_date}/{name} ranking={actual_row.get(name, '')} "
                    f"observation={expected_row.get(name, '')}"
                )
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
            for metric in ("change_pct", "deviation_pct", "range_pct"):
                try:
                    float(row.get(metric, ""))
                except (TypeError, ValueError):
                    errors.append(f"observation {index} invalid metric: {metric}")
            volume = str(row.get("volume_ratio", "")).strip()
            if volume != "-":
                try:
                    float(volume)
                except ValueError:
                    errors.append(f"observation {index} invalid metric: volume_ratio")
            rank_delta = str(row.get("rank_change", "")).strip()
            if rank_delta != "NA":
                try:
                    int(rank_delta)
                except ValueError:
                    errors.append(f"observation {index} invalid metric: rank_change")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("status_date", "")):
                errors.append(f"observation {index} invalid metric: status_date")
    tables = {}
    for row in rows:
        if str(row.get("verified", "")).lower() != "true":
            continue
        table_type = row.get("table_type")
        if table_type not in EXPECTED_TABLE_SIZE:
            continue
        key = (row.get("data_date", ""), table_type, row.get("source_image", ""))
        try:
            rank = int(row.get("rank", ""))
        except (TypeError, ValueError):
            rank = 0
        tables.setdefault(key, []).append(rank)
    for (data_date, table_type, source_image), ranks in tables.items():
        expected = list(range(1, EXPECTED_TABLE_SIZE[table_type] + 1))
        if sorted(ranks) != expected:
            errors.append(
                "observation incomplete rank sequence: "
                f"{data_date}/{table_type}/{source_image}"
            )
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


def validate_direction_signals(signals, observations, article_stances=None):
    errors = []
    for table_type in ("index", "sector"):
        observation_date = max(
            (
                row.get("data_date", "")
                for row in observations
                if row.get("table_type") == table_type
            ),
            default="",
        )
        signal_date = max(
            (row.get("data_date", "") for row in signals if row.get("table_type") == table_type),
            default="",
        )
        if observation_date != signal_date:
            errors.append(
                f"direction signals latest date mismatch: {table_type} "
                f"signals={signal_date} observations={observation_date}"
            )
    expected = build_direction_signals(observations, article_stances or {})
    key = lambda row: (row.get("data_date", ""), row.get("table_type", ""), row.get("name", ""))
    expected_by_key = {key(row): row for row in expected}
    actual_by_key = {key(row): row for row in signals}
    for signal_key in sorted(expected_by_key.keys() & actual_by_key.keys()):
        expected_row = expected_by_key[signal_key]
        actual_row = actual_by_key[signal_key]
        for field in ("rank", "benchmark", "article_stance", "group", "action"):
            if str(actual_row.get(field, "")) != str(expected_row.get(field, "")):
                errors.append(
                    "direction signals content mismatch: "
                    f"{'/'.join(signal_key)} {field}="
                    f"{actual_row.get(field, '')} expected={expected_row.get(field, '')}"
                )
    for signal_key in sorted(expected_by_key.keys() - actual_by_key.keys()):
        errors.append(f"direction signal missing: {'/'.join(signal_key)}")
    for signal_key in sorted(actual_by_key.keys() - expected_by_key.keys()):
        errors.append(f"unexpected direction signal: {'/'.join(signal_key)}")
    return errors


def validate_signal_episodes(episodes, signals):
    errors = []
    expected = build_signal_episodes(signals)
    key = lambda row: (
        row.get("table_type", ""),
        row.get("name", ""),
        row.get("start_date", ""),
    )
    expected_by_key = {key(row): row for row in expected}
    actual_by_key = {key(row): row for row in episodes}
    for episode_key in sorted(expected_by_key.keys() & actual_by_key.keys()):
        expected_row = expected_by_key[episode_key]
        actual_row = actual_by_key[episode_key]
        for field, expected_value in expected_row.items():
            if str(actual_row.get(field, "")) != str(expected_value):
                errors.append(
                    "episode content mismatch: "
                    f"{'/'.join(episode_key)} {field}="
                    f"{actual_row.get(field, '')} expected={expected_value}"
                )
    for episode_key in sorted(expected_by_key.keys() - actual_by_key.keys()):
        errors.append(f"signal episode missing: {'/'.join(episode_key)}")
    for episode_key in sorted(actual_by_key.keys() - expected_by_key.keys()):
        errors.append(f"unexpected signal episode: {'/'.join(episode_key)}")
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
    indices = [row.get("index") for row in articles if isinstance(row.get("index"), int)]
    if indices != list(range(1, len(articles) + 1)):
        errors.append("article indices are not consecutive")
    return errors


def validate_article_metadata(link_log, articles):
    errors = []
    articles_by_url = {row.get("url", ""): row for row in articles}
    entries = re.findall(
        r"^- \[[ x]\] (\d{4}-\d{2}-\d{2})｜(.+?)｜"
        r"(https://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+)$",
        link_log,
        re.MULTILINE,
    )
    def normalize_title(title):
        return re.sub(r"\.{3,}", "…", title.strip())

    for date, title, url in entries:
        article = articles_by_url.get(url)
        if not article:
            continue
        if article.get("date", "") != date:
            errors.append(
                f"article date mismatch: {url} registry={date} cache={article.get('date', '')}"
            )
        if normalize_title(article.get("title", "")) != normalize_title(title):
            errors.append(f"article title mismatch: {url}")
    return errors


def validate_reading_report(report, articles, ranking_rows):
    errors = []
    dates = sorted(row.get("date", "") for row in articles if row.get("date"))
    expected_count = len(articles)
    expected_start = dates[0] if dates else ""
    expected_end = dates[-1] if dates else ""

    count_match = re.search(r"文章数量：(\d+) 篇", report)
    start_end_match = re.search(
        r"覆盖范围：(\d{4}-\d{2}-\d{2}) 至 (\d{4}-\d{2}-\d{2})", report
    )
    generated_match = re.search(r"生成时间：(\d{4}-\d{2}-\d{2})", report)
    report_count = int(count_match.group(1)) if count_match else None
    report_start = start_end_match.group(1) if start_end_match else ""
    report_end = start_end_match.group(2) if start_end_match else ""
    generated_date = generated_match.group(1) if generated_match else ""

    if report_count != expected_count:
        errors.append(f"reading report article count mismatch: report={report_count} cache={expected_count}")
    if report_start != expected_start:
        errors.append(f"reading report coverage start mismatch: report={report_start} cache={expected_start}")
    if report_end != expected_end:
        errors.append(f"reading report coverage end mismatch: report={report_end} cache={expected_end}")
    if generated_date != expected_end:
        errors.append(f"reading report generated date mismatch: report={generated_date} cache={expected_end}")

    latest_ranking_date = max((row.get("数据日", "") for row in ranking_rows), default="")
    ranking_section = re.search(r"### 指数横向跟踪(.*?)(?=\n### )", report, re.DOTALL)
    if latest_ranking_date and (
        not ranking_section or f"| {latest_ranking_date} |" not in ranking_section.group(1)
    ):
        errors.append(f"reading report latest ranking date missing: {latest_ranking_date}")
    if ranking_section:
        table_lines = [
            line.strip()
            for line in ranking_section.group(1).splitlines()
            if line.strip().startswith("|")
        ]
        headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")] if table_lines else []
        report_rankings = {}
        for line in table_lines[2:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if cells and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cells[0]):
                report_rankings[cells[0]] = dict(zip(headers, cells))
        for ranking_row in ranking_rows:
            data_date = ranking_row.get("数据日", "")
            report_row = report_rankings.get(data_date, {})
            for name, value in ranking_row.items():
                if name == "数据日" or name not in headers:
                    continue
                if report_row.get(name, "") != value:
                    errors.append(
                        "reading report ranking value mismatch: "
                        f"{data_date}/{name} report={report_row.get(name, '')} ranking={value}"
                    )
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
    with (data_dir / "direction-signals.csv").open(encoding="utf-8", newline="") as handle:
        direction_signals = list(csv.DictReader(handle))
    with (data_dir / "signal-episodes.csv").open(encoding="utf-8", newline="") as handle:
        signal_episodes = list(csv.DictReader(handle))
    with (data_dir / "article-direction-stances.csv").open(encoding="utf-8", newline="") as handle:
        stance_rows = list(csv.DictReader(handle))
    article_stances = {
        (row["data_date"], row["table_type"], row["name"]): row["stance"]
        for row in stance_rows
    }
    action_board = (PROJECT_ROOT / "docs/action-board.md").read_text(encoding="utf-8")
    reading_report = (PROJECT_ROOT / "docs/reading-report.md").read_text(encoding="utf-8")
    link_log = (data_dir / "maobidao-link-log.md").read_text(encoding="utf-8")

    errors = []
    errors.extend(validate_articles(load_urls(data_dir / "maobidao-link-log.md"), articles))
    errors.extend(validate_article_metadata(link_log, articles))
    errors.extend(validate_reading_report(reading_report, articles, ranking_rows))
    errors.extend(validate_image_records(records))
    errors.extend(validate_rankings(ranking_rows))
    errors.extend(validate_index_rankings(ranking_rows, observations))
    errors.extend(validate_observations(observations))
    errors.extend(validate_direction_signals(direction_signals, observations, article_stances))
    errors.extend(validate_signal_episodes(signal_episodes, direction_signals))
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
