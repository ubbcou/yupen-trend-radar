import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_web_snapshot import PROJECT_ROOT, build_snapshot, write_web_snapshot


class WebSnapshotTest(unittest.TestCase):
    def test_snapshot_uses_current_project_facts(self):
        snapshot = build_snapshot()

        self.assertEqual("2026-07-30", snapshot["meta"]["article"]["date"])
        self.assertEqual("2026-07-29", snapshot["meta"]["fishDataDates"]["index"])
        self.assertEqual("2026-07-29", snapshot["meta"]["fishDataDates"]["sector"])

        groups = {group["name"]: group["directions"] for group in snapshot["groups"]}
        self.assertEqual(
            ["中证消费", "国企指数", "中证红利", "恒生科技"],
            groups["主攻"],
        )
        self.assertEqual(
            ["中证煤炭"],
            groups["试探"],
        )
        self.assertEqual([], groups["趋势保持"])
        self.assertEqual(
            ["微盘股", "电网设备", "有色金属", "房地产"],
            groups["等待"],
        )

        directions = {row["name"]: row for row in snapshot["directions"]}
        innovation_drug = directions["CS创新药"]
        self.assertEqual(9, innovation_drug["rank"])
        self.assertEqual("2026-07-28", innovation_drug["previousDataDate"])
        self.assertEqual(-2, innovation_drug["rankMovement"])
        self.assertEqual(0.91, innovation_drug["volumeRatio"])
        self.assertEqual("中证A500", innovation_drug["benchmark"])
        self.assertEqual("回避", innovation_drug["group"])
        self.assertEqual("不纳入", innovation_drug["action"])
        self.assertEqual(0, directions["半导体"]["rankMovement"])
        self.assertEqual("不纳入", directions["半导体"]["action"])

    def test_direction_detail_exposes_evidence_and_lifecycle(self):
        snapshot = build_snapshot()
        directions = {row["name"]: row for row in snapshot["directions"]}
        innovation_drug = directions["CS创新药"]

        self.assertEqual(
            {
                "frontRank": False,
                "aboveMa20": False,
                "strongerThanBenchmark": True,
                "continuous": False,
                "volumeConfirmed": False,
            },
            innovation_drug["conditions"],
        )
        self.assertEqual("neutral", innovation_drug["articleStance"])
        self.assertEqual("", innovation_drug["articleEvidence"])
        self.assertTrue(innovation_drug["sourceImage"].endswith("sector_4f7e7c04.jpg"))
        self.assertEqual("2026-06-29", innovation_drug["lifecycle"]["startDate"])
        self.assertEqual("2026-07-10", innovation_drug["lifecycle"]["mainDate"])
        self.assertEqual("2026-07-23", innovation_drug["lifecycle"]["endDate"])
        self.assertEqual("closed", innovation_drug["lifecycle"]["status"])
        self.assertEqual(
            [
                {"date": "2026-07-23", "rank": 4, "group": "等待"},
                {"date": "2026-07-24", "rank": 4, "group": "回避"},
                {"date": "2026-07-27", "rank": 5, "group": "等待"},
                {"date": "2026-07-28", "rank": 7, "group": "回避"},
                {"date": "2026-07-29", "rank": 9, "group": "回避"},
            ],
            innovation_drug["history"],
        )

    def test_snapshot_includes_display_context_without_article_body(self):
        snapshot = build_snapshot()

        self.assertIn("主攻方向扩展为国企指数", snapshot["marketSummary"])
        directions = {row["name"]: row for row in snapshot["directions"]}
        self.assertIn("下一次鱼盆数据", directions["CS创新药"]["nextValidation"])
        self.assertNotIn("text", snapshot["meta"]["article"])

    def test_writer_validates_and_publishes_snapshot_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            output_path = output_dir / "data/project-snapshot.json"
            image_dir = output_dir / "yupen-images"

            snapshot = write_web_snapshot(
                root=PROJECT_ROOT,
                output_path=output_path,
                image_dir=image_dir,
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("passed", written["meta"]["validationStatus"])
            self.assertEqual(snapshot, written)
            for direction in written["directions"]:
                self.assertTrue(direction["sourceImage"].startswith("/yupen-images/"))
                self.assertTrue((image_dir / Path(direction["sourceImage"]).name).is_file())


if __name__ == "__main__":
    unittest.main()
