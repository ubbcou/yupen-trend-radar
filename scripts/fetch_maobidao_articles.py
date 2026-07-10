import argparse
import datetime as dt
import html
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

LINK_LOG = Path("data/maobidao-link-log.md")
ARTICLE_JSON = Path("data/maobidao_articles.json")
MIN_COMPLETE_TEXT_CHARS = 80

UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.50 NetType/WIFI Language/zh_CN"
)


def load_urls(path=LINK_LOG):
    text = path.read_text(encoding="utf-8")
    urls = re.findall(r"https://mp\.weixin\.qq\.com/s/[A-Za-z0-9_-]+", text)
    return list(dict.fromkeys(urls))


class ContentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.grab = False
        self.skip = 0
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.grab:
            self.depth += 1
            if tag in {"script", "style", "svg"}:
                self.skip += 1
        elif attrs.get("id") == "js_content":
            self.grab = True
            self.depth = 1

    def handle_endtag(self, tag):
        if not self.grab:
            return
        if self.skip and tag in {"script", "style", "svg"}:
            self.skip -= 1
        self.depth -= 1
        if self.depth <= 0:
            self.grab = False

    def handle_data(self, data):
        if self.grab and not self.skip:
            line = " ".join(data.split())
            if line:
                self.text.append(line)


def meta(page, prop):
    match = re.search(r'<meta property="' + re.escape(prop) + r'" content="(.*?)"', page)
    return html.unescape(match.group(1)) if match else ""


def fetch(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Encoding": "identity",
        },
    )
    page = urllib.request.urlopen(request, timeout=25).read().decode("utf-8", "ignore")
    parser = ContentParser()
    parser.feed(page)
    match = re.search(r'ct\s*=\s*["\'](\d{10})["\']', page)
    ts = int(match.group(1)) if match else 0
    date = dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d") if ts else ""
    return {
        "url": url,
        "date": date,
        "title": meta(page, "og:title"),
        "author": meta(page, "og:article:author"),
        "description": meta(page, "og:description"),
        "text": "\n".join(parser.text),
    }


def useful(row):
    return bool(row.get("date") or row.get("title") or row.get("text"))


def choose_article_version(cached, fetched):
    if not cached:
        return fetched
    if len((fetched.get("text") or "").strip()) < len((cached.get("text") or "").strip()):
        return cached
    return fetched


def needs_fetch(cached, *, refresh=False):
    if refresh or not cached:
        return True
    return len((cached.get("text") or "").strip()) < MIN_COMPLETE_TEXT_CHARS


def load_existing(path=ARTICLE_JSON):
    if not path.exists():
        return {}
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid article cache: {path}") from exc
    return {row["url"]: row for row in rows if row.get("url") and useful(row)}


def update_articles(urls, existing, *, fetcher=fetch, refresh=False):
    rows = []
    failures = 0
    for index, url in enumerate(urls, 1):
        cached = existing.get(url)
        if not needs_fetch(cached, refresh=refresh):
            rows.append({**cached, "index": index})
            continue
        try:
            fetched = {**fetcher(url), "index": index}
            selected = choose_article_version(cached, fetched)
            if selected is cached:
                failures += 1
            rows.append({**selected, "index": index})
        except Exception as exc:
            failures += 1
            if cached:
                rows.append({**cached, "index": index})
            else:
                rows.append(
                    {
                        "index": index,
                        "url": url,
                        "date": "",
                        "title": "",
                        "author": "",
                        "description": "",
                        "text": "",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    rows.sort(key=lambda row: (row.get("date") or "9999-99-99", row["index"]))
    return rows, failures


def write_json_atomic(path, rows):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Fetch new WeChat articles without downgrading the cache.")
    parser.add_argument("--refresh", action="store_true", help="Refetch all URLs and keep the better version.")
    args = parser.parse_args(argv)

    urls = load_urls()
    existing = load_existing()
    if not urls:
        raise SystemExit(f"no urls found in {LINK_LOG}")

    rows, failures = update_articles(urls, existing, refresh=args.refresh)
    for row in sorted(rows, key=lambda item: item["index"]):
        status = "ERROR" if row.get("error") else "OK"
        print(
            f"{row['index']:02d} {status} {row.get('date', '')} "
            f"{row.get('title', '')} {len(row.get('text', ''))}"
        )
    write_json_atomic(ARTICLE_JSON, rows)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
