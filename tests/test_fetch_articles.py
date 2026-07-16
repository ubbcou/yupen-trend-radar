import tempfile
import unittest
import json
from pathlib import Path

from scripts import fetch_maobidao_articles


class FetchArticlesTest(unittest.TestCase):
    def test_partial_fetch_never_replaces_complete_cached_article(self):
        self.assertTrue(
            hasattr(fetch_maobidao_articles, "choose_article_version"),
            "choose_article_version public behavior is missing",
        )
        cached = {
            "url": "https://mp.weixin.qq.com/s/example",
            "date": "2026-07-09",
            "title": "完整文章",
            "text": "完整正文" * 100,
        }
        fetched = {
            "url": cached["url"],
            "date": "2026-07-09",
            "title": "完整文章",
            "text": "",
        }

        selected = fetch_maobidao_articles.choose_article_version(cached, fetched)

        self.assertEqual(cached["text"], selected["text"])

    def test_redirected_article_never_replaces_known_cache_entry(self):
        cached = {
            "url": "https://mp.weixin.qq.com/s/old",
            "date": "2026-05-02",
            "title": "历史文章",
            "text": "",
        }
        fetched = {
            "url": cached["url"],
            "date": "2026-07-16",
            "title": "其他文章",
            "text": "错误正文" * 100,
        }

        selected = fetch_maobidao_articles.choose_article_version(cached, fetched)

        self.assertIs(cached, selected)

    def test_invalid_cache_stops_instead_of_replacing_history(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "articles.json"
            cache.write_text("{broken", encoding="utf-8")

            with self.assertRaises(ValueError):
                fetch_maobidao_articles.load_existing(cache)

    def test_complete_cached_article_is_not_refetched_by_default(self):
        self.assertTrue(
            hasattr(fetch_maobidao_articles, "needs_fetch"),
            "needs_fetch public behavior is missing",
        )
        cached = {"title": "文章", "text": "有效正文" * 100}

        self.assertFalse(fetch_maobidao_articles.needs_fetch(cached, refresh=False))
        self.assertTrue(fetch_maobidao_articles.needs_fetch(cached, refresh=True))

    def test_new_article_fetch_failure_is_reported_to_the_caller(self):
        self.assertTrue(
            hasattr(fetch_maobidao_articles, "update_articles"),
            "update_articles public behavior is missing",
        )

        def failing_fetch(_url):
            raise OSError("network unavailable")

        rows, failures = fetch_maobidao_articles.update_articles(
            ["https://mp.weixin.qq.com/s/new"],
            {},
            fetcher=failing_fetch,
        )

        self.assertEqual(1, failures)
        self.assertIn("network unavailable", rows[0]["error"])

    def test_json_output_is_replaced_atomically(self):
        self.assertTrue(
            hasattr(fetch_maobidao_articles, "write_json_atomic"),
            "write_json_atomic public behavior is missing",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "articles.json"
            output.write_text("[]", encoding="utf-8")

            fetch_maobidao_articles.write_json_atomic(output, [{"url": "new"}])

            self.assertEqual([{"url": "new"}], json.loads(output.read_text(encoding="utf-8")))
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
