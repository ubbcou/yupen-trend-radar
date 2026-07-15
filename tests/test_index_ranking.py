import unittest

from scripts import build_index_ranking as builder


class IndexRankingTest(unittest.TestCase):
    def test_index_rankings_are_derived_from_observations(self):
        observations = [
            {"data_date": "2026-07-10", "table_type": "index", "name": "科创50", "rank": "1"},
            {"data_date": "2026-07-10", "table_type": "index", "name": "创业板指", "rank": "19"},
            {"data_date": "2026-07-13", "table_type": "index", "name": "科创50", "rank": "5"},
            {"data_date": "2026-07-13", "table_type": "index", "name": "创业板指", "rank": "17"},
        ]

        rows = builder.build_index_rankings(observations, ("科创50", "创业板指"))

        self.assertEqual(
            [
                {"数据日": "2026-07-10", "科创50": "1", "创业板指": "19"},
                {"数据日": "2026-07-13", "科创50": "5", "创业板指": "17"},
            ],
            rows,
        )


if __name__ == "__main__":
    unittest.main()
