import unittest

from scripts import trend_rules


class TrendRulesTest(unittest.TestCase):
    def test_article_stance_cannot_be_omitted(self):

        with self.assertRaises(ValueError):
            trend_rules.evaluate_direction(
                rank=1,
                deviation_pct=3.0,
                change_pct=2.0,
                benchmark_change_pct=1.0,
                volume_ratio=1.1,
                recent_ranks=[1, 1],
            )

    def test_confirmed_overheated_leader_is_main_attack_without_chasing(self):

        result = trend_rules.evaluate_direction(
            rank=1,
            deviation_pct=9.23,
            change_pct=6.52,
            benchmark_change_pct=2.83,
            volume_ratio=1.11,
            recent_ranks=[2, 1],
            article_stance="support",
        )

        self.assertEqual("主攻", result.group)
        self.assertEqual("不追高", result.action)
        self.assertTrue(result.core_trend)

    def test_front_above_line_but_weaker_than_benchmark_is_hold_without_chasing(self):

        result = trend_rules.evaluate_direction(
            rank=2,
            deviation_pct=5.66,
            change_pct=1.84,
            benchmark_change_pct=2.83,
            volume_ratio=0.79,
            recent_ranks=[1, 2],
            article_stance="support",
        )

        self.assertEqual("趋势保持", result.group)
        self.assertEqual("不新增", result.action)
        self.assertFalse(result.core_trend)

    def test_new_core_trend_without_confirmation_is_trial(self):

        result = trend_rules.evaluate_direction(
            rank=2,
            deviation_pct=2.5,
            change_pct=3.2,
            benchmark_change_pct=1.0,
            volume_ratio=0.9,
            recent_ranks=[6, 2],
            article_stance="support",
        )

        self.assertEqual("试探", result.group)
        self.assertEqual("等待确认", result.action)
        self.assertTrue(result.core_trend)

    def test_below_twenty_day_and_outside_front_is_avoid(self):

        result = trend_rules.evaluate_direction(
            rank=12,
            deviation_pct=-3.0,
            change_pct=-1.0,
            benchmark_change_pct=0.5,
            volume_ratio=0.8,
            recent_ranks=[10, 12],
            article_stance="support",
        )

        self.assertEqual("回避", result.group)
        self.assertEqual("不纳入", result.action)

    def test_confirmed_trend_with_neutral_article_stays_trial(self):

        result = trend_rules.evaluate_direction(
            rank=2,
            deviation_pct=3.75,
            change_pct=0.01,
            benchmark_change_pct=-0.70,
            volume_ratio=1.07,
            recent_ranks=[2, 2],
            article_stance="neutral",
        )

        self.assertEqual("试探", result.group)
        self.assertEqual("等待文章确认", result.action)

    def test_confirmed_overheated_trend_with_neutral_article_is_not_chased(self):

        result = trend_rules.evaluate_direction(
            rank=1,
            deviation_pct=9.12,
            change_pct=3.31,
            benchmark_change_pct=2.27,
            volume_ratio=1.18,
            recent_ranks=[1, 1],
            article_stance="neutral",
        )

        self.assertEqual("试探", result.group)
        self.assertEqual("不追高", result.action)

    def test_opposing_article_blocks_core_trend(self):

        result = trend_rules.evaluate_direction(
            rank=1,
            deviation_pct=3.75,
            change_pct=2.0,
            benchmark_change_pct=1.0,
            volume_ratio=1.07,
            recent_ranks=[1, 1],
            article_stance="oppose",
        )

        self.assertEqual("等待", result.group)
        self.assertEqual("文章冲突", result.action)


if __name__ == "__main__":
    unittest.main()
