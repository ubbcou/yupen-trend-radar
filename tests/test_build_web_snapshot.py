import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_web_snapshot import PROJECT_ROOT, build_snapshot, write_web_snapshot


class WebSnapshotTest(unittest.TestCase):
    def test_snapshot_uses_current_project_facts(self):
        snapshot = build_snapshot()

        self.assertEqual("2026-08-07", snapshot["meta"]["article"]["date"])
        self.assertEqual("2026-08-06", snapshot["meta"]["fishDataDates"]["index"])
        self.assertEqual("2026-08-06", snapshot["meta"]["fishDataDates"]["sector"])

        groups = {group["name"]: group["directions"] for group in snapshot["groups"]}
        self.assertEqual(
            [],
            groups["主攻"],
        )
        self.assertEqual(
            ["微盘股", "有色金属", "细分化工"],
            groups["试探"],
        )
        self.assertEqual(["电网设备"], groups["趋势保持"])
        self.assertEqual(
            [
                "中证2000",
                "商业航天",
                "中证煤炭",
                "北证50",
                "中证1000",
                "光伏设备",
                "房地产",
                "机器人",
                "纳指100",
                "中证红利",
                "国企指数",
                "新能源",
                "中证消费",
                "恒生科技",
                "中证500",
            ],
            groups["等待"],
        )

        directions = {row["name"]: row for row in snapshot["directions"]}
        innovation_drug = directions["CS创新药"]
        self.assertEqual(12, innovation_drug["rank"])
        self.assertEqual("2026-08-05", innovation_drug["previousDataDate"])
        self.assertEqual(-1, innovation_drug["rankMovement"])
        self.assertEqual(1.04, innovation_drug["volumeRatio"])
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
                "strongerThanBenchmark": False,
                "continuous": False,
                "volumeConfirmed": True,
            },
            innovation_drug["conditions"],
        )
        self.assertEqual("neutral", innovation_drug["articleStance"])
        self.assertEqual("", innovation_drug["articleEvidence"])
        self.assertTrue(innovation_drug["sourceImage"].endswith("sector_9efb2ed1.jpg"))
        self.assertEqual("2026-06-29", innovation_drug["lifecycle"]["startDate"])
        self.assertEqual("2026-07-10", innovation_drug["lifecycle"]["mainDate"])
        self.assertEqual("2026-07-23", innovation_drug["lifecycle"]["endDate"])
        self.assertEqual("closed", innovation_drug["lifecycle"]["status"])
        self.assertEqual(
            [
                {"date": "2026-07-31", "rank": 9, "group": "回避"},
                {"date": "2026-08-03", "rank": 11, "group": "回避"},
                {"date": "2026-08-04", "rank": 10, "group": "回避"},
                {"date": "2026-08-05", "rank": 11, "group": "等待"},
                {"date": "2026-08-06", "rank": 12, "group": "回避"},
            ],
            innovation_drug["history"],
        )

    def test_snapshot_includes_display_context_without_article_body(self):
        snapshot = build_snapshot()

        self.assertIn("当前主攻仍为空", snapshot["marketSummary"])
        directions = {row["name"]: row for row in snapshot["directions"]}
        self.assertIn("下一次鱼盆数据", directions["CS创新药"]["nextValidation"])
        self.assertEqual("neutral", directions["半导体"]["articleStance"])
        self.assertEqual("回避", directions["半导体"]["group"])
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
                release_commit="22860fd",
            )

            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual("passed", written["meta"]["validationStatus"])
            self.assertEqual("22860fd", written["meta"]["release"]["commit"])
            self.assertEqual(snapshot, written)
            for direction in written["directions"]:
                self.assertTrue(direction["sourceImage"].startswith("/yupen-images/"))
                self.assertTrue((image_dir / Path(direction["sourceImage"]).name).is_file())


if __name__ == "__main__":
    unittest.main()
