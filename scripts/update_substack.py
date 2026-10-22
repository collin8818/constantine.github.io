#!/usr/bin/env python3
"""Build a local three-post JSON feed for a GitHub Pages Substack carousel."""

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEED = "https://collinconstantine.substack.com/feed"
OUT = Path(__file__).resolve().parent.parent / "substack-posts.json"


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self.ignored:
            self.ignored -= 1

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def plain_text(html):
    parser = TextOnly()
    parser.feed(html or "")
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def normalize_date(raw):
    if not raw:
        return "1970-01-01T00:00:00+00:00"
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def valid_link(link):
    return link.startswith("https://collinconstantine.substack.com/p/")


def from_rss():
    request = Request(FEED, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SiteSubstackFeed/1.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    })
    with urlopen(request, timeout=25) as response:
        rss = response.read()

    root = ET.fromstring(rss)
    items = root.findall("./channel/item")
    if not items:
        raise ValueError("No RSS <item> elements received")

    posts = []
    for item in items:
        link = (item.findtext("link") or "").strip()
        if not valid_link(link):
            continue
        posts.append({
            "title": (item.findtext("title") or "").strip(),
            "link": link,
            "pubDate": normalize_date(item.findtext("pubDate")),
            "description": plain_text(item.findtext("description")),
        })
    return posts


def from_rss2json():
    # Fallback only in the GitHub job. Visitors never query this service.
    url = "https://api.rss2json.com/v1/api.json?rss_url=" + quote(FEED, safe="")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=25) as response:
        data = json.load(response)
    if data.get("status") != "ok":
        raise ValueError(f"RSS2JSON error: {data.get('message', data.get('status'))}")
    posts = []
    for item in data.get("items", []):
        link = (item.get("link") or "").strip()
        if not valid_link(link):
            continue
        posts.append({
            "title": item.get("title", ""),
            "link": link,
            "pubDate": normalize_date(item.get("pubDate")),
            "description": plain_text(item.get("description", "")),
        })
    return posts


def main():
    try:
        try:
            posts = from_rss()
            print("Fetched RSS directly from Substack")
        except Exception as first_error:
            print(f"Direct RSS unavailable: {first_error}. Trying backup service.")
            posts = from_rss2json()

        # Ensure newest posts first, even if the upstream order changes.
        posts.sort(key=lambda p: p["pubDate"], reverse=True)
        posts = posts[:3]
        if not posts:
            raise ValueError("Feed has no usable public posts")
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "posts": posts,
        }
        OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"Wrote {len(posts)} latest posts to {OUT.name}")
        print("Posts currently returned by the Substack feed:")
        for post in posts:
            print(f"  {post['pubDate'][:10]} | {post['title']}")
    except Exception as error:
        # Never silently deploy an old JSON snapshot as a successful refresh.
        # A failed GitHub Actions run tells the site owner the feed needs attention.
        raise RuntimeError(
            f"Substack refresh FAILED; existing {OUT.name} has not been updated. "
            f"Reason: {error}"
        ) from error


if __name__ == "__main__":
    main()
