import unittest

from scripts.check_release_status import determine_release_status


LOCAL_META = {
    "article": {"date": "2026-08-07"},
    "fishDataDates": {"index": "2026-08-06", "sector": "2026-08-06"},
}
HEAD_SHA = "22860fdbffa8b0bab55e8feb2062cb1607f0c873"


def successful_deployment():
    return {
        "status": "completed",
        "conclusion": "success",
        "headSha": HEAD_SHA,
        "url": "https://github.com/ubbcou/yupen-trend-radar/actions/runs/1",
    }


def current_online_meta():
    return {
        **LOCAL_META,
        "release": {"commit": HEAD_SHA},
    }


class ReleaseStatusTest(unittest.TestCase):
    def determine(self, **overrides):
        inputs = {
            "project_valid": True,
            "worktree_clean": True,
            "head_sha": HEAD_SHA,
            "remote_sha": HEAD_SHA,
            "deployment": successful_deployment(),
            "local_meta": LOCAL_META,
            "online_meta": current_online_meta(),
        }
        inputs.update(overrides)
        return determine_release_status(**inputs)

    def test_invalid_project_stops_before_release_checks(self):
        result = self.determine(project_valid=False, worktree_clean=False)

        self.assertEqual("INVALID", result.state)

    def test_uncommitted_changes_are_reported(self):
        result = self.determine(worktree_clean=False)

        self.assertEqual("UNCOMMITTED", result.state)

    def test_local_commit_not_on_main_is_not_pushed(self):
        result = self.determine(remote_sha="e88d624")

        self.assertEqual("NOT_PUSHED", result.state)

    def test_missing_or_running_deployment_is_deploying(self):
        self.assertEqual("DEPLOYING", self.determine(deployment=None).state)
        self.assertEqual(
            "DEPLOYING",
            self.determine(deployment={"status": "in_progress", "conclusion": ""}).state,
        )

    def test_failed_deployment_is_reported(self):
        result = self.determine(
            deployment={"status": "completed", "conclusion": "failure"}
        )

        self.assertEqual("DEPLOY_FAILED", result.state)

    def test_online_commit_must_match_head(self):
        online_meta = current_online_meta()
        online_meta["release"] = {"commit": "e88d624"}

        result = self.determine(online_meta=online_meta)

        self.assertEqual("ONLINE_STALE", result.state)

    def test_online_dates_must_match_local_facts(self):
        online_meta = current_online_meta()
        online_meta["article"] = {"date": "2026-07-31"}

        result = self.determine(online_meta=online_meta)

        self.assertEqual("ONLINE_STALE", result.state)

    def test_matching_commit_and_dates_are_published(self):
        result = self.determine()

        self.assertEqual("PUBLISHED", result.state)


if __name__ == "__main__":
    unittest.main()
