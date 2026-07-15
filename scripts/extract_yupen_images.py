import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from .fetch_maobidao_articles import (
        ContentParser,
        UA,
        article_date,
        fetch_page,
        load_urls,
        meta,
        write_json_atomic,
    )
except ImportError:
    from fetch_maobidao_articles import (
        ContentParser,
        UA,
        article_date,
        fetch_page,
        load_urls,
        meta,
        write_json_atomic,
    )

RECORDS_JSON = Path("data/yupen_image_records.json")


def normalize_image_url(src):
    if src.startswith("//"):
        return "https:" + src
    return src


YUPEN_TABLE_TRIGGER = re.compile(
    r"((贴下|附上|技术层面).{0,20}鱼盆.{0,20}(回测|数据说话)|鱼盆.{0,12}回测数据.{0,12}数据说话)"
)


def select_yupen_images(sequence):
    selected = []
    pending = False
    context = ""
    for item in sequence:
        if item["type"] == "text":
            text = item["text"]
            if YUPEN_TABLE_TRIGGER.search(text):
                pending = True
                context = text
                selected = []
            elif pending and not selected:
                pending = False
        elif item["type"] == "img" and pending:
            position = len(selected)
            if position >= 2:
                pending = False
                continue
            selected.append(
                {
                    "image_url": normalize_image_url(item["src"]),
                    "kind": "index" if position == 0 else "sector",
                    "context": context,
                }
            )
            if len(selected) == 2:
                pending = False
    return selected


def image_ext(url):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    fmt = (query.get("wx_fmt") or ["jpg"])[0].lower()
    if fmt in {"jpeg", "jpg"}:
        return "jpg"
    if fmt in {"png", "webp", "gif"}:
        return fmt
    return "jpg"


def build_image_path(*, article_date, article_url, image_url, kind, out_dir=Path("data/yupen-images")):
    article_id = hashlib.sha256(article_url.encode("utf-8")).hexdigest()[:8]
    image_id = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:8]
    extension = image_ext(image_url)
    return out_dir / f"{article_date or 'unknown'}_{article_id}_{kind}_{image_id}.{extension}"


def write_image_atomic(path, content):
    is_image = (
        content.startswith(b"\xff\xd8\xff")
        or content.startswith(b"\x89PNG\r\n\x1a\n")
        or content.startswith((b"GIF87a", b"GIF89a"))
        or (content.startswith(b"RIFF") and content[8:12] == b"WEBP")
    )
    if not is_image:
        raise ValueError("downloaded content is not a supported image")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def download(url, path):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Referer": "https://mp.weixin.qq.com/",
        },
    )
    write_image_atomic(path, urllib.request.urlopen(req, timeout=30).read())


def record_needs_download(record):
    path = Path(record["path"])
    return not path.is_file() or path.stat().st_size == 0


def load_existing_records(path=RECORDS_JSON):
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid image registry: {path}") from exc


def extract_article_records(
    *,
    article_url,
    page,
    article_index,
    existing_records,
    out_dir=Path("data/yupen-images"),
):
    parser = ContentParser()
    parser.feed(page)
    selected = select_yupen_images(parser.seq)
    if not selected:
        return [], "no_table"
    date = article_date(page)
    title = meta(page, "og:title")
    existing_by_url = {row.get("image_url"): row for row in existing_records if row.get("image_url")}
    records = []
    for item in selected:
        previous = existing_by_url.get(item["image_url"], {})
        path = build_image_path(
            article_date=date,
            article_url=article_url,
            image_url=item["image_url"],
            kind=item["kind"],
            out_dir=out_dir,
        )
        records.append(
            {
                "article_index": article_index,
                "article_date": date,
                "data_date": previous.get("data_date", ""),
                "title": title,
                "article_url": article_url,
                "image_url": item["image_url"],
                "kind": item["kind"],
                "path": str(path),
                "context": item["context"],
                "verified": bool(previous.get("verified", False)),
            }
        )
    return records, "found"


def update_image_records(
    urls,
    existing_records,
    *,
    page_fetcher=fetch_page,
    image_downloader=download,
    out_dir=Path("data/yupen-images"),
    refresh=False,
):
    records_by_article = {}
    for row in existing_records:
        records_by_article.setdefault(row.get("article_url"), []).append(row)

    updated = []
    failures = 0
    no_table = 0
    for article_index, url in enumerate(urls, 1):
        cached = records_by_article.get(url, [])
        complete = (
            {row.get("kind") for row in cached} == {"index", "sector"}
            and all(row.get("verified") and not record_needs_download(row) for row in cached)
        )
        if complete and not refresh:
            updated.extend(cached)
            continue
        try:
            page = page_fetcher(url)
            article_records, status = extract_article_records(
                article_url=url,
                page=page,
                article_index=article_index,
                existing_records=cached,
                out_dir=out_dir,
            )
            if status == "no_table":
                if cached:
                    failures += 1
                    updated.extend(cached)
                else:
                    no_table += 1
                continue
            for row in article_records:
                if record_needs_download(row):
                    image_downloader(row["image_url"], Path(row["path"]))
            updated.extend(article_records)
        except Exception as exc:
            failures += 1
            updated.extend(cached)
            print(f"{article_index:02d} ERROR {url} {type(exc).__name__}: {exc}")

    updated.sort(
        key=lambda row: (
            row.get("article_date") or row.get("date") or "9999-99-99",
            row.get("article_index") or row.get("index") or 0,
            0 if row.get("kind") == "index" else 1,
        )
    )
    return updated, failures, no_table


def main(argv=None):
    parser = argparse.ArgumentParser(description="Extract verified fish-table candidates from new articles.")
    parser.add_argument("--refresh", action="store_true", help="Refetch articles with complete verified records.")
    args = parser.parse_args(argv)

    out_dir = Path("data/yupen-images")
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = load_existing_records()
    records, failures, no_table = update_image_records(
        load_urls(),
        existing,
        out_dir=out_dir,
        refresh=args.refresh,
    )
    write_json_atomic(RECORDS_JSON, records)
    pending = sum(row.get("verified") is not True for row in records)
    print(
        f"saved {len(records)} records; pending_verification={pending}; "
        f"no_table={no_table}; failures={failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
