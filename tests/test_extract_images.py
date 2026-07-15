import tempfile
import unittest
from pathlib import Path

from scripts import extract_yupen_images as extract_images


class ExtractImagesTest(unittest.TestCase):
    def test_different_image_urls_never_share_a_local_path(self):
        self.assertTrue(
            hasattr(extract_images, "build_image_path"),
            "build_image_path public behavior is missing",
        )

        first = extract_images.build_image_path(
            article_date="2026-07-10",
            article_url="https://mp.weixin.qq.com/s/article",
            image_url="https://mmbiz.qpic.cn/first?wx_fmt=jpeg",
            kind="index",
        )
        second = extract_images.build_image_path(
            article_date="2026-07-10",
            article_url="https://mp.weixin.qq.com/s/article",
            image_url="https://mmbiz.qpic.cn/second?wx_fmt=jpeg",
            kind="index",
        )

        self.assertNotEqual(first, second)

    def test_only_images_after_explicit_fish_table_phrase_are_selected(self):
        self.assertTrue(
            hasattr(extract_images, "select_yupen_images"),
            "select_yupen_images public behavior is missing",
        )
        sequence = [
            {"type": "text", "text": "鱼盆模型早就转弱，下面聊账户收益。"},
            {"type": "img", "src": "https://example.com/account.jpg"},
            {"type": "text", "text": "贴下最新鱼盆模型回测数据，我们数据说话："},
            {"type": "img", "src": "https://example.com/index.jpg"},
            {"type": "img", "src": "https://example.com/sector.jpg"},
        ]

        selected = extract_images.select_yupen_images(sequence)

        self.assertEqual(
            ["https://example.com/index.jpg", "https://example.com/sector.jpg"],
            [item["image_url"] for item in selected],
        )
        self.assertEqual(["index", "sector"], [item["kind"] for item in selected])

    def test_seen_record_with_missing_file_is_downloaded_again(self):
        self.assertTrue(
            hasattr(extract_images, "record_needs_download"),
            "record_needs_download public behavior is missing",
        )
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.jpg"

            self.assertTrue(extract_images.record_needs_download({"path": str(missing)}))
            missing.write_bytes(b"image")
            self.assertFalse(extract_images.record_needs_download({"path": str(missing)}))

    def test_invalid_image_registry_stops_instead_of_rebuilding_silently(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "records.json"
            registry.write_text("[broken", encoding="utf-8")

            with self.assertRaises(ValueError):
                extract_images.load_existing_records(registry)

    def test_article_without_fish_table_is_a_successful_noop(self):
        self.assertTrue(
            hasattr(extract_images, "extract_article_records"),
            "extract_article_records public behavior is missing",
        )
        page = '<meta property="og:title" content="生活文章"><div id="js_content"><p>没有市场表格</p></div>'

        records, status = extract_images.extract_article_records(
            article_url="https://mp.weixin.qq.com/s/life",
            page=page,
            article_index=1,
            existing_records=[],
        )

        self.assertEqual([], records)
        self.assertEqual("no_table", status)

    def test_fish_table_records_include_type_date_and_unique_source_path(self):
        page = """
            <meta property="og:title" content="鱼盆文章">
            <script>var ct = '1783612800';</script>
            <div id="js_content">
              <p>贴下最新鱼盆模型回测数据，我们数据说话：</p>
              <img data-src="https://example.com/index.jpg?wx_fmt=jpeg">
              <img data-src="https://example.com/sector.jpg?wx_fmt=jpeg">
            </div>
        """
        with tempfile.TemporaryDirectory() as directory:
            records, status = extract_images.extract_article_records(
                article_url="https://mp.weixin.qq.com/s/fish",
                page=page,
                article_index=2,
                existing_records=[],
                out_dir=Path(directory),
            )

        self.assertEqual("found", status)
        self.assertEqual(["index", "sector"], [row["kind"] for row in records])
        self.assertEqual([False, False], [row["verified"] for row in records])
        self.assertNotEqual(records[0]["path"], records[1]["path"])
        self.assertIn("article_date", records[0])
        self.assertIn("data_date", records[0])

    def test_non_image_response_is_rejected_before_it_enters_the_registry(self):
        self.assertTrue(
            hasattr(extract_images, "write_image_atomic"),
            "write_image_atomic public behavior is missing",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "table.jpg"

            with self.assertRaises(ValueError):
                extract_images.write_image_atomic(output, b"<html>verification required</html>")

            self.assertFalse(output.exists())

    def test_registry_update_accepts_article_without_fish_table(self):
        self.assertTrue(
            hasattr(extract_images, "update_image_records"),
            "update_image_records public behavior is missing",
        )

        rows, failures, no_table = extract_images.update_image_records(
            ["https://mp.weixin.qq.com/s/life"],
            [],
            page_fetcher=lambda _url: '<div id="js_content"><p>生活随笔</p></div>',
        )

        self.assertEqual([], rows)
        self.assertEqual(0, failures)
        self.assertEqual(1, no_table)


if __name__ == "__main__":
    unittest.main()
