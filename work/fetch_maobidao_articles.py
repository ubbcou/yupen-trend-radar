import datetime as dt
import html
import json
import re
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

LINK_LOG = Path("outputs/maobidao-link-log.md")

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


def main():
    rows = []
    urls = load_urls()
    if not urls:
        raise SystemExit(f"no urls found in {LINK_LOG}")

    for i, url in enumerate(urls, 1):
        try:
            row = fetch(url)
            row["index"] = i
            print(f"{i:02d} {row['date']} {row['title']} {len(row['text'])}")
        except Exception as exc:
            row = {
                "index": i,
                "url": url,
                "date": "",
                "title": "",
                "author": "",
                "description": "",
                "text": "",
                "error": f"{type(exc).__name__}: {exc}",
            }
            print(f"{i:02d} ERROR {url} {row['error']}")
        rows.append(row)
        time.sleep(0.15)

    rows.sort(key=lambda row: (row["date"] or "9999-99-99", row["index"]))
    Path("work/maobidao_articles.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
