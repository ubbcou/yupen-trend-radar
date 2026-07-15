import unittest

from scripts import build_signal_lifecycle as builder


class SignalLifecycleTest(unittest.TestCase):
    def test_active_signal_is_closed_when_it_becomes_avoid(self):
        signals = [
            {"data_date": "2026-07-09", "table_type": "sector", "name": "半导体", "group": "试探"},
            {"data_date": "2026-07-10", "table_type": "sector", "name": "半导体", "group": "主攻"},
            {"data_date": "2026-07-13", "table_type": "sector", "name": "半导体", "group": "回避"},
        ]

        episodes = builder.build_signal_episodes(signals)

        self.assertEqual(1, len(episodes))
        self.assertEqual("2026-07-09", episodes[0]["start_date"])
        self.assertEqual("2026-07-10", episodes[0]["main_date"])
        self.assertEqual("2026-07-13", episodes[0]["end_date"])
        self.assertEqual(2, episodes[0]["signal_observations"])
        self.assertTrue(episodes[0]["false_breakout"])


if __name__ == "__main__":
    unittest.main()
