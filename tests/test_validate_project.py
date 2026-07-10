import importlib
import importlib.util
import tempfile
import unittest
from pathlib import Path


class ValidateProjectTest(unittest.TestCase):
    def test_duplicate_image_paths_are_rejected(self):
        spec = importlib.util.find_spec("scripts.validate_project")
        self.assertIsNotNone(spec, "scripts.validate_project public module is missing")
        validator = importlib.import_module("scripts.validate_project")
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
        validator = importlib.import_module("scripts.validate_project")
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
        validator = importlib.import_module("scripts.validate_project")
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
        validator = importlib.import_module("scripts.validate_project")
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
        validator = importlib.import_module("scripts.validate_project")
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

    def test_ranking_rows_require_unique_dates_and_integer_values(self):
        validator = importlib.import_module("scripts.validate_project")
        rows = [
            {"数据日": "2026-07-09", "科创50": "1"},
            {"数据日": "2026-07-09", "科创50": "not-a-rank"},
        ]

        errors = validator.validate_rankings(rows, required_names=("科创50", "创业板指"))

        self.assertTrue(any("duplicate ranking date" in error for error in errors))
        self.assertTrue(any("invalid ranking" in error for error in errors))
        self.assertTrue(any("missing ranking" in error for error in errors))

    def test_latest_fish_date_must_match_board_csv_and_observations(self):
        validator = importlib.import_module("scripts.validate_project")
        board = "最新指数鱼盆数据日：2026-07-09\n最新板块鱼盆数据日：2026-07-08"
        ranking_rows = [{"数据日": "2026-07-08"}]
        observations = [
            {"data_date": "2026-07-09", "table_type": "index"},
            {"data_date": "2026-07-08", "table_type": "sector"},
        ]

        errors = validator.validate_latest_dates(board, ranking_rows, observations)

        self.assertTrue(any("latest index fish date mismatch" in error for error in errors))

    def test_index_and_sector_dates_may_differ_when_each_source_matches(self):
        validator = importlib.import_module("scripts.validate_project")
        board = "最新指数鱼盆数据日：2026-07-09\n最新板块鱼盆数据日：2026-07-08"
        ranking_rows = [{"数据日": "2026-07-09"}]
        observations = [
            {"data_date": "2026-07-09", "table_type": "index"},
            {"data_date": "2026-07-08", "table_type": "sector"},
        ]

        errors = validator.validate_latest_dates(board, ranking_rows, observations)

        self.assertEqual([], errors)

    def test_article_cache_must_match_unique_link_registry(self):
        validator = importlib.import_module("scripts.validate_project")
        urls = ["a", "b"]
        articles = [{"url": "a", "index": 1}, {"url": "a", "index": 2}]

        errors = validator.validate_articles(urls, articles)

        self.assertTrue(any("article URL mismatch" in error for error in errors))
        self.assertTrue(any("duplicate article URL" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
