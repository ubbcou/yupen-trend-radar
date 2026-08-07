import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode

try:
    from .build_web_snapshot import build_snapshot
    from .validate_project import main as validate_project
except ImportError:
    from build_web_snapshot import build_snapshot
    from validate_project import main as validate_project


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SITE_URL = "https://yupen.ifnet.top/data/project-snapshot.json"
DEFAULT_WORKFLOW = "deploy-pages.yml"


@dataclass(frozen=True)
class ReleaseStatus:
    state: str
    details: dict


class ReleaseCheckError(RuntimeError):
    pass


def _release_facts(meta):
    meta = meta or {}
    fish_dates = meta.get("fishDataDates", {})
    return {
        "article": meta.get("article", {}).get("date", ""),
        "index": fish_dates.get("index", ""),
        "sector": fish_dates.get("sector", ""),
    }


def determine_release_status(
    *,
    project_valid,
    worktree_clean,
    head_sha,
    remote_sha,
    deployment,
    local_meta,
    online_meta,
):
    details = {
        "head": head_sha,
        "remote": remote_sha,
        "local": _release_facts(local_meta),
    }
    if not project_valid:
        return ReleaseStatus("INVALID", details)
    if not worktree_clean:
        return ReleaseStatus("UNCOMMITTED", details)
    if head_sha != remote_sha:
        return ReleaseStatus("NOT_PUSHED", details)
    if not deployment or deployment.get("status") != "completed":
        if deployment:
            details["deployment"] = deployment
        return ReleaseStatus("DEPLOYING", details)
    details["deployment"] = deployment
    if deployment.get("conclusion") != "success":
        return ReleaseStatus("DEPLOY_FAILED", details)

    online_facts = _release_facts(online_meta)
    online_commit = (online_meta or {}).get("release", {}).get("commit", "")
    details["online"] = online_facts
    details["onlineCommit"] = online_commit
    if online_commit != head_sha or online_facts != details["local"]:
        return ReleaseStatus("ONLINE_STALE", details)
    return ReleaseStatus("PUBLISHED", details)


def _run(args, *, root=PROJECT_ROOT):
    try:
        result = subprocess.run(
            args,
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        raise ReleaseCheckError(f"cannot run {' '.join(args)}: {error}") from error
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        raise ReleaseCheckError(f"command failed: {' '.join(args)}: {message}")
    return result.stdout.strip()


def _deployment_for_commit(head_sha, *, root=PROJECT_ROOT, workflow=DEFAULT_WORKFLOW):
    output = _run(
        [
            "gh",
            "run",
            "list",
            "--workflow",
            workflow,
            "--commit",
            head_sha,
            "--limit",
            "1",
            "--json",
            "status,conclusion,headSha,url",
        ],
        root=root,
    )
    try:
        runs = json.loads(output)
    except json.JSONDecodeError as error:
        raise ReleaseCheckError("GitHub Actions returned invalid JSON") from error
    if not isinstance(runs, list):
        raise ReleaseCheckError("GitHub Actions returned an unexpected response")
    return runs[0] if runs else None


def _online_meta(head_sha, *, root=PROJECT_ROOT, site_url=DEFAULT_SITE_URL):
    separator = "&" if "?" in site_url else "?"
    url = f"{site_url}{separator}{urlencode({'commit': head_sha})}"
    output = _run(
        ["curl", "-fsSL", "--max-time", "20", url],
        root=root,
    )
    try:
        meta = json.loads(output)["meta"]
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ReleaseCheckError("online snapshot returned invalid metadata") from error
    if not isinstance(meta, dict):
        raise ReleaseCheckError("online snapshot returned invalid metadata")
    return meta


def collect_release_status(
    *,
    root=PROJECT_ROOT,
    site_url=DEFAULT_SITE_URL,
    workflow=DEFAULT_WORKFLOW,
):
    root = Path(root)
    project_valid = validate_project([]) == 0
    if not project_valid:
        return determine_release_status(
            project_valid=False,
            worktree_clean=False,
            head_sha="",
            remote_sha="",
            deployment=None,
            local_meta=None,
            online_meta=None,
        )

    local_meta = build_snapshot(root)["meta"]
    head_sha = _run(["git", "rev-parse", "HEAD"], root=root)
    worktree_clean = not _run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        root=root,
    )
    if not worktree_clean:
        return determine_release_status(
            project_valid=True,
            worktree_clean=False,
            head_sha=head_sha,
            remote_sha="",
            deployment=None,
            local_meta=local_meta,
            online_meta=None,
        )

    _run(["git", "fetch", "--quiet", "origin", "main"], root=root)
    remote_sha = _run(["git", "rev-parse", "origin/main"], root=root)
    if head_sha != remote_sha:
        return determine_release_status(
            project_valid=True,
            worktree_clean=True,
            head_sha=head_sha,
            remote_sha=remote_sha,
            deployment=None,
            local_meta=local_meta,
            online_meta=None,
        )

    deployment = _deployment_for_commit(head_sha, root=root, workflow=workflow)
    online_meta = None
    if deployment and deployment.get("status") == "completed":
        if deployment.get("conclusion") == "success":
            online_meta = _online_meta(head_sha, root=root, site_url=site_url)
    return determine_release_status(
        project_valid=True,
        worktree_clean=True,
        head_sha=head_sha,
        remote_sha=remote_sha,
        deployment=deployment,
        local_meta=local_meta,
        online_meta=online_meta,
    )


def _print_status(result):
    print(result.state)
    details = result.details
    local = details.get("local", {})
    if local:
        print(
            "local "
            f"article={local.get('article', '')} "
            f"index={local.get('index', '')} "
            f"sector={local.get('sector', '')}"
        )
    if details.get("head"):
        print(f"head={details['head']}")
    if details.get("remote"):
        print(f"origin/main={details['remote']}")
    deployment = details.get("deployment", {})
    if deployment.get("url"):
        print(f"deployment={deployment['url']}")
    if "online" in details:
        online = details["online"]
        print(
            "online "
            f"article={online.get('article', '')} "
            f"index={online.get('index', '')} "
            f"sector={online.get('sector', '')} "
            f"commit={details.get('onlineCommit', '')}"
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check whether the latest radar is published.")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    args = parser.parse_args(argv)
    try:
        result = collect_release_status(
            site_url=args.site_url,
            workflow=args.workflow,
        )
    except ReleaseCheckError as error:
        print(f"CHECK_FAILED {error}")
        return 2
    _print_status(result)
    return 0 if result.state == "PUBLISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
