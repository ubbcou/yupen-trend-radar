import csv
import tempfile
import unittest
from pathlib import Path

from scripts import build_direction_signals as builder


class DirectionSignalsTest(unittest.TestCase):
    def test_observations_build_a_confirmed_sector_signal(self):
        observations = [
            {
                "data_date": "2026-07-09",
                "table_type": "index",
                "name": "中证A500",
                "change_pct": "1.0",
            },
            {
                "data_date": "2026-07-09",
                "table_type": "sector",
                "name": "半导体",
                "rank": "2",
                "change_pct": "2.0",
                "deviation_pct": "3.0",
                "volume_ratio": "1.1",
            },
            {
                "data_date": "2026-07-10",
                "table_type": "index",
                "name": "中证A500",
                "change_pct": "0.5",
            },
            {
                "data_date": "2026-07-10",
                "table_type": "sector",
                "name": "半导体",
                "rank": "1",
                "change_pct": "2.5",
                "deviation_pct": "4.0",
                "volume_ratio": "1.2",
            },
        ]
        stances = {("2026-07-10", "sector", "半导体"): "support"}

        signals = builder.build_direction_signals(observations, stances)

        latest = signals[-1]
        self.assertEqual("2026-07-10", latest["data_date"])
        self.assertEqual("中证A500", latest["benchmark"])
        self.assertEqual([2, 1], latest["recent_ranks"])
        self.assertEqual("主攻", latest["group"])

    def test_hong_kong_index_uses_hang_seng_as_benchmark(self):
        observations = []
        for data_date, benchmark_change, rank in (
            ("2026-07-09", "0.5", "2"),
            ("2026-07-10", "0.8", "1"),
        ):
            observations.extend(
                (
                    {
                        "data_date": data_date,
                        "table_type": "index",
                        "name": "恒生指数",
                        "change_pct": benchmark_change,
                    },
                    {
                        "data_date": data_date,
                        "table_type": "index",
                        "name": "恒生科技",
                        "rank": rank,
                        "change_pct": "1.2",
                        "deviation_pct": "2.0",
                        "volume_ratio": "1.1",
                    },
                )
            )

        signals = builder.build_direction_signals(observations, {})

        self.assertTrue(signals, "Hong Kong index signal was not generated")
        latest = signals[-1]
        self.assertEqual("恒生科技", latest["name"])
        self.assertEqual("恒生指数", latest["benchmark"])
        self.assertEqual("试探", latest["group"])

    def test_a_share_index_uses_a500_as_benchmark(self):
        observations = [
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": "中证A500",
                "change_pct": "-2.56",
            },
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": "科创50",
                "rank": "5",
                "change_pct": "-3.42",
                "deviation_pct": "-0.10",
                "volume_ratio": "1.04",
            },
        ]

        signals = builder.build_direction_signals(observations, {})

        self.assertTrue(signals, "A-share index signal was not generated")
        self.assertEqual("中证A500", signals[0]["benchmark"])
        self.assertEqual("回避", signals[0]["group"])

    def test_nasdaq_uses_sp500_as_benchmark(self):
        observations = [
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": "标普500",
                "change_pct": "-0.78",
            },
            {
                "data_date": "2026-07-13",
                "table_type": "index",
                "name": "纳指100",
                "rank": "8",
                "change_pct": "-1.90",
                "deviation_pct": "-1.52",
                "volume_ratio": "1.08",
            },
        ]

        signals = builder.build_direction_signals(observations, {})

        self.assertTrue(signals, "US index signal was not generated")
        self.assertEqual("标普500", signals[0]["benchmark"])

    def test_update_direction_signals_writes_a_reproducible_csv(self):
        if not hasattr(builder, "update_direction_signals"):
            self.fail("direction signal CSV writer is missing")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observations_path = root / "observations.csv"
            stances_path = root / "stances.csv"
            output_path = root / "signals.csv"
            with observations_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=(
                        "data_date",
                        "table_type",
                        "name",
                        "rank",
                        "change_pct",
                        "deviation_pct",
                        "volume_ratio",
                        "source_image",
                    ),
                )
                writer.writeheader()
                writer.writerows(
                    (
                        {
                            "data_date": "2026-07-13",
                            "table_type": "index",
                            "name": "中证A500",
                            "change_pct": "-2.56",
                        },
                        {
                            "data_date": "2026-07-13",
                            "table_type": "sector",
                            "name": "CS创新药",
                            "rank": "1",
                            "change_pct": "-0.70",
                            "deviation_pct": "6.58",
                            "volume_ratio": "0.99",
                            "source_image": "sector.jpg",
                        },
                    )
                )
            with stances_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=("data_date", "table_type", "name", "stance", "evidence"),
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "data_date": "2026-07-13",
                        "table_type": "sector",
                        "name": "CS创新药",
                        "stance": "support",
                        "evidence": "文章弱支持",
                    }
                )

            builder.update_direction_signals(observations_path, stances_path, output_path)

            self.assertNotIn(b"\r\n", output_path.read_bytes())
            with output_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(1, len(rows))
        self.assertEqual("support", rows[0]["article_stance"])
        self.assertEqual("试探", rows[0]["group"])

    def test_signals_are_sorted_by_numeric_rank(self):
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
                "name": "后排",
                "rank": "10",
                "change_pct": "-1",
                "deviation_pct": "-1",
                "volume_ratio": "1",
            },
            {
                "data_date": "2026-07-13",
                "table_type": "sector",
                "name": "前排",
                "rank": "2",
                "change_pct": "1",
                "deviation_pct": "1",
                "volume_ratio": "1",
            },
        ]

        signals = builder.build_direction_signals(observations, {})

        self.assertEqual(["前排", "后排"], [row["name"] for row in signals])


if __name__ == "__main__":
    unittest.main()
