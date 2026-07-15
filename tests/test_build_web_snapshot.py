import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_web_snapshot import PROJECT_ROOT, build_snapshot, write_web_snapshot


class WebSnapshotTest(unittest.TestCase):
    def test_snapshot_uses_current_project_facts(self):
        snapshot = build_snapshot()

        self.assertEqual("2026-07-15", snapshot["meta"]["article"]["date"])
        self.assertEqual("2026-07-14", snapshot["meta"]["fishDataDates"]["index"])
        self.assertEqual("2026-07-14", snapshot["meta"]["fishDataDates"]["sector"])

        groups = {group["name"]: group["directions"] for group in snapshot["groups"]}
        self.assertEqual([], groups["主攻"])
        self.assertIn("CS创新药", groups["试探"])
        self.assertIn("中证煤炭", groups["试探"])

        directions = {row["name"]: row for row in snapshot["directions"]}
        innovation_drug = directions["CS创新药"]
        self.assertEqual(1, innovation_drug["rank"])
        self.assertEqual("2026-07-13", innovation_drug["previousDataDate"])
        self.assertEqual(0, innovation_drug["rankMovement"])
        self.assertEqual(1.18, innovation_drug["volumeRatio"])
        self.assertEqual("中证A500", innovation_drug["benchmark"])
        self.assertEqual("试探", innovation_drug["group"])
        self.assertEqual("不追高", innovation_drug["action"])
        self.assertEqual(0, directions["半导体"]["rankMovement"])
        self.assertEqual("不纳入", directions["半导体"]["action"])

    def test_direction_detail_exposes_evidence_and_lifecycle(self):
        snapshot = build_snapshot()
        directions = {row["name"]: row for row in snapshot["directions"]}
        innovation_drug = directions["CS创新药"]

        self.assertEqual(
            {
                "frontRank": True,
                "aboveMa20": True,
                "strongerThanBenchmark": True,
                "continuous": True,
                "volumeConfirmed": True,
            },
            innovation_drug["conditions"],
        )
        self.assertEqual("neutral", innovation_drug["articleStance"])
        self.assertEqual("", innovation_drug["articleEvidence"])
        self.assertTrue(innovation_drug["sourceImage"].endswith("sector_85ba148e.jpg"))
        self.assertEqual("2026-06-29", innovation_drug["lifecycle"]["startDate"])
        self.assertEqual("2026-07-10", innovation_drug["lifecycle"]["mainDate"])
        self.assertEqual("open", innovation_drug["lifecycle"]["status"])
        self.assertEqual(
            [
                {"date": "2026-07-08", "rank": 1, "group": "趋势保持"},
                {"date": "2026-07-09", "rank": 2, "group": "趋势保持"},
                {"date": "2026-07-10", "rank": 1, "group": "主攻"},
                {"date": "2026-07-13", "rank": 1, "group": "试探"},
                {"date": "2026-07-14", "rank": 1, "group": "试探"},
            ],
            innovation_drug["history"],
        )

    def test_snapshot_includes_display_context_without_article_body(self):
        snapshot = build_snapshot()

        self.assertIn("超跌反弹后的局部修复", snapshot["marketSummary"])
        directions = {row["name"]: row for row in snapshot["directions"]}
        self.assertIn("偏离率降温", directions["CS创新药"]["nextValidation"])
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
