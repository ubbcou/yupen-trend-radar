import datetime as dt
import json
import re
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from fetch_maobidao_articles import UA, load_urls, meta


class SequenceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.grab = False
        self.skip = 0
        self.seq = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.grab:
            self.depth += 1
            if tag in {"script", "style", "svg"}:
                self.skip += 1
            if tag == "img" and not self.skip:
                src = attrs.get("data-src") or attrs.get("src")
                if src:
                    self.seq.append({"type": "img", "src": src})
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
                self.seq.append({"type": "text", "text": line})


def fetch_page(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept-Encoding": "identity",
        },
    )
    return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")


def article_date(page):
    match = re.search(r'ct\s*=\s*["\'](\d{10})["\']', page)
    if not match:
        return ""
    return dt.datetime.fromtimestamp(int(match.group(1))).strftime("%Y-%m-%d")


def normalize_image_url(src):
    if src.startswith("//"):
        return "https:" + src
    return src


def image_ext(url):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    fmt = (query.get("wx_fmt") or ["jpg"])[0].lower()
    if fmt in {"jpeg", "jpg"}:
        return "jpg"
    if fmt in {"png", "webp", "gif"}:
        return fmt
    return "jpg"


def download(url, path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    path.write_bytes(urllib.request.urlopen(req, timeout=30).read())


def main():
    out_dir = Path("outputs/maobidao-yupen-images")
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []

    # Select the image immediately after a fish-model phrase, plus one backup image
    # if it is still before the next market-section paragraph.
    trigger = re.compile(r"(鱼盆|回测模型|模型回测|数据说话|趋势回测)")
    stop = re.compile(r"^(美股|A50|中概股|消息面|闲聊区|[0-9] |1 |2 |3 )")

    for index, url in enumerate(load_urls(), 1):
        try:
            page = fetch_page(url)
            parser = SequenceParser()
            parser.feed(page)
            date = article_date(page)
            title = meta(page, "og:title")

            pending = False
            picked = 0
            last_text = ""
            for item in parser.seq:
                if item["type"] == "text":
                    last_text = item["text"]
                    if trigger.search(last_text):
                        pending = True
                        picked = 0
                    elif pending and stop.search(last_text):
                        pending = False
                elif item["type"] == "img" and pending and picked < 2:
                    img_url = normalize_image_url(item["src"])
                    ext = image_ext(img_url)
                    file_name = f"{date or 'unknown'}_{index:02d}_{picked + 1}.{ext}"
                    path = out_dir / file_name
                    if not path.exists():
                        download(img_url, path)
                    records.append(
                        {
                            "index": index,
                            "date": date,
                            "title": title,
                            "article_url": url,
                            "image_url": img_url,
                            "path": str(path),
                            "context": last_text,
                        }
                    )
                    print(f"{len(records):02d} {date} {title} -> {path}")
                    picked += 1
            time.sleep(0.15)
        except Exception as exc:
            print(f"{index:02d} ERROR {url} {type(exc).__name__}: {exc}")

    Path("work/yupen_image_records.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved {len(records)} records")


if __name__ == "__main__":
    main()
