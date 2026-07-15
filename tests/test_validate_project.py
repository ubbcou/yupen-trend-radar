import tempfile
import unittest
from pathlib import Path

from scripts import validate_project as validator


class ValidateProjectTest(unittest.TestCase):
    def test_duplicate_image_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "same.jpg"
            image.write_bytes(b"image")
            records = [
                {"article_url": "a", "image_url": "1", "path": "same.jpg"},
                {"article_url": "a", "image_url": "2", "path": "same.jpg"},
            ]

            errors = validator.validate_image_records(records, root=root)

        self.assertTrue(any("duplicate image path" in error for error in errors))

    def test_verified_record_requires_data_date_type_and_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = [
                {
                    "article_url": "a",
                    "image_url": "1",
                    "path": "missing.jpg",
                    "verified": True,
                    "data_date": "",
                    "kind": "",
                }
            ]

            errors = validator.validate_image_records(records, root=root)

        self.assertTrue(any("missing image file" in error for error in errors))
        self.assertTrue(any("verified record missing data_date" in error for error in errors))
        self.assertTrue(any("invalid table kind" in error for error in errors))

    def test_unverified_fish_record_blocks_project_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "candidate.jpg"
            image.write_bytes(b"image")
            records = [
                {
                    "article_url": "a",
                    "image_url": "1",
                    "path": "candidate.jpg",
                    "verified": False,
                    "data_date": "",
                    "kind": "index",
                }
            ]

            errors = validator.validate_image_records(records, root=root)

        self.assertTrue(any("unverified fish-table record" in error for error in errors))

    def test_fish_article_requires_index_and_sector_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "index.jpg"
            image.write_bytes(b"image")
            records = [
                {
                    "article_url": "a",
                    "image_url": "1",
                    "path": "index.jpg",
                    "verified": True,
                    "data_date": "2026-07-09",
                    "kind": "index",
                }
            ]

            errors = validator.validate_image_records(records, root=root)

        self.assertTrue(any("incomplete fish-table pair" in error for error in errors))

    def test_observation_rows_require_unique_complete_metrics(self):
        rows = [
            {
                "data_date": "2026-07-09",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "change_pct": "6.52",
                "deviation_pct": "9.23",
                "volume_ratio": "1.11",
                "status_date": "2026-06-15",
                "range_pct": "23.01",
                "rank_change": "1",
                "source_image": "image.jpg",
                "verified": "true",
            },
            {
                "data_date": "2026-07-09",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "change_pct": "",
                "deviation_pct": "",
                "volume_ratio": "",
                "status_date": "",
                "range_pct": "",
                "rank_change": "",
                "source_image": "image.jpg",
                "verified": "true",
            },
        ]

        errors = validator.validate_observations(rows)

        self.assertTrue(any("duplicate observation" in error for error in errors))
        self.assertTrue(any("missing metric" in error for error in errors))

    def test_verified_observation_table_requires_complete_rank_sequence(self):
        rows = [
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": f"指数{rank}",
                "rank": str(rank),
                "change_pct": "0",
                "deviation_pct": "0",
                "volume_ratio": "1",
                "status_date": "2026-07-13",
                "range_pct": "0",
                "rank_change": "0",
                "source_image": "index.jpg",
                "verified": "true",
            }
            for rank in range(1, 20)
        ]

        errors = validator.validate_observations(rows)

        self.assertTrue(any("incomplete rank sequence" in error for error in errors))

    def test_verified_observation_rejects_invalid_numeric_metrics(self):
        rows = [
            {
                "data_date": "2026-07-13",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "change_pct": "not-a-number",
                "deviation_pct": "1.0",
                "volume_ratio": "1.1",
                "status_date": "2026-07-13",
                "range_pct": "2.0",
                "rank_change": "NA",
                "source_image": "sector.jpg",
                "verified": "true",
            }
        ]

        errors = validator.validate_observations(rows)

        self.assertTrue(any("invalid metric: change_pct" in error for error in errors))
        self.assertFalse(any("invalid metric: rank_change" in error for error in errors))

    def test_ranking_rows_require_unique_dates_and_integer_values(self):
        rows = [
            {"数据日": "2026-07-09", "科创50": "1"},
            {"数据日": "2026-07-09", "科创50": "not-a-rank"},
        ]

        errors = validator.validate_rankings(rows, required_names=("科创50", "创业板指"))

        self.assertTrue(any("duplicate ranking date" in error for error in errors))
        self.assertTrue(any("invalid ranking" in error for error in errors))
        self.assertTrue(any("missing ranking" in error for error in errors))

    def test_index_rankings_must_match_observations(self):
        if not hasattr(validator, "validate_index_rankings"):
            self.fail("derived index ranking validation is missing")
        ranking_rows = [{"数据日": "2026-06-03", "科创50": "14"}]
        observations = [
            {
                "data_date": "2026-06-03",
                "table_type": "index",
                "name": "科创50",
                "rank": "13",
            }
        ]

        errors = validator.validate_index_rankings(
            ranking_rows,
            observations,
            required_names=("科创50",),
        )

        self.assertTrue(any("ranking content mismatch" in error for error in errors))

    def test_latest_fish_date_must_match_board_csv_and_observations(self):
        board = "最新指数鱼盆数据日：2026-07-09\n最新板块鱼盆数据日：2026-07-08"
        ranking_rows = [{"数据日": "2026-07-08"}]
        observations = [
            {"data_date": "2026-07-09", "table_type": "index"},
            {"data_date": "2026-07-08", "table_type": "sector"},
        ]

        errors = validator.validate_latest_dates(board, ranking_rows, observations)

        self.assertTrue(any("latest index fish date mismatch" in error for error in errors))

    def test_direction_signals_must_cover_latest_observation_date(self):
        if not hasattr(validator, "validate_direction_signals"):
            self.fail("direction signal validation is missing")
        observations = [
            {"data_date": "2026-07-13", "table_type": "sector", "name": "半导体"}
        ]
        signals = [
            {"data_date": "2026-07-10", "table_type": "sector", "name": "半导体"}
        ]

        errors = validator.validate_direction_signals(signals, observations)

        self.assertTrue(any("latest date mismatch" in error for error in errors))

    def test_direction_signals_must_match_recomputed_rules(self):
        observations = [
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": "中证A500",
                "change_pct": "0",
            },
            {
                "data_date": "2026-07-13",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "change_pct": "1",
                "deviation_pct": "1",
                "volume_ratio": "1.1",
            },
        ]
        signals = [
            {
                "data_date": "2026-07-13",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "benchmark": "中证A500",
                "article_stance": "neutral",
                "group": "主攻",
                "action": "可关注",
            }
        ]

        errors = validator.validate_direction_signals(signals, observations)

        self.assertTrue(any("content mismatch" in error for error in errors))

    def test_signal_episodes_must_match_direction_signals(self):
        if not hasattr(validator, "validate_signal_episodes"):
            self.fail("signal episode validation is missing")
        signals = [
            {"data_date": "2026-07-09", "table_type": "sector", "name": "半导体", "group": "试探"},
            {"data_date": "2026-07-10", "table_type": "sector", "name": "半导体", "group": "回避"},
        ]
        episodes = [
            {
                "table_type": "sector",
                "name": "半导体",
                "start_date": "2026-07-09",
                "start_group": "试探",
                "main_date": "",
                "end_date": "",
                "end_group": "",
                "signal_observations": "1",
                "false_breakout": "False",
                "status": "open",
            }
        ]

        errors = validator.validate_signal_episodes(episodes, signals)

        self.assertTrue(any("episode content mismatch" in error for error in errors))

    def test_index_and_sector_dates_may_differ_when_each_source_matches(self):
        board = "最新指数鱼盆数据日：2026-07-09\n最新板块鱼盆数据日：2026-07-08"
        ranking_rows = [{"数据日": "2026-07-09"}]
        observations = [
            {"data_date": "2026-07-09", "table_type": "index"},
            {"data_date": "2026-07-08", "table_type": "sector"},
        ]

        errors = validator.validate_latest_dates(board, ranking_rows, observations)

        self.assertEqual([], errors)

    def test_article_cache_must_match_unique_link_registry(self):
        urls = ["a", "b"]
        articles = [{"url": "a", "index": 1}, {"url": "a", "index": 2}]

        errors = validator.validate_articles(urls, articles)

        self.assertTrue(any("article URL mismatch" in error for error in errors))
        self.assertTrue(any("duplicate article URL" in error for error in errors))

    def test_reading_report_metadata_must_match_article_cache(self):
        if not hasattr(validator, "validate_reading_report"):
            self.fail("reading report validation is missing")
        report = "\n".join(
            (
                "- 生成时间：2026-07-13",
                "- 覆盖范围：2026-01-01 至 2026-07-13",
                "- 文章数量：55 篇",
            )
        )
        articles = [
            {"date": "2026-01-01"},
            {"date": "2026-07-14"},
        ]

        errors = validator.validate_reading_report(report, articles, [])

        self.assertTrue(any("article count mismatch" in error for error in errors))
        self.assertTrue(any("coverage end mismatch" in error for error in errors))
        self.assertTrue(any("generated date mismatch" in error for error in errors))

    def test_reading_report_index_table_must_include_latest_ranking_date(self):
        report = "\n".join(
            (
                "### 指数横向跟踪",
                "| 数据日 | 科创50 |",
                "|---|---:|",
                "| 2026-07-10 | 1 |",
                "### 指数强弱迁移",
            )
        )
        ranking_rows = [{"数据日": "2026-07-10"}, {"数据日": "2026-07-13"}]

        errors = validator.validate_reading_report(report, [], ranking_rows)

        self.assertTrue(any("latest ranking date missing" in error for error in errors))

    def test_reading_report_index_values_must_match_ranking_data(self):
        report = "\n".join(
            (
                "### 指数横向跟踪",
                "| 数据日 | 科创50 |",
                "|---|---:|",
                "| 2026-06-03 | 14 |",
                "### 指数强弱迁移",
            )
        )
        ranking_rows = [{"数据日": "2026-06-03", "科创50": "13"}]

        errors = validator.validate_reading_report(report, [], ranking_rows)

        self.assertTrue(any("ranking value mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
