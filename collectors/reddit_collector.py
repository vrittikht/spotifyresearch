"""
Collect Reddit posts from public sources without the official Reddit API.

Live scraping uses:
  - Reddit RSS search feeds (public, no auth)
  - old.reddit.com HTML search pages (real posts with scores)

Manual HTML import (--html-dir) remains supported as a fallback.
"""

from __future__ import annotations

import re
import time
import urllib.robotparser
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

DEFAULT_SUBREDDITS = ["spotify", "truespotify"]
DEFAULT_KEYWORDS = [
    "recommendations",
    "discover weekly",
    "music discovery",
    "same songs",
    "algorithm",
    "playlist",
]
OLD_REDDIT_BASE = "https://old.reddit.com"
REDDIT_BASE = "https://www.reddit.com"
ROBOTS_URL = "https://www.reddit.com/robots.txt"
DEFAULT_USER_AGENT = "spotify-research-collector/1.0 (PM case study; public pages only)"
LIVE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_DELAY_SECONDS = 2.0
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}


@dataclass
class RedditPost:
    post_id: str
    title: str
    body: str
    subreddit: str
    score: int | None
    url: str
    permalink: str
    keyword: str | None = None
    published_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "post_id": self.post_id,
            "title": self.title,
            "body": self.body,
            "subreddit": self.subreddit,
            "score": self.score,
            "url": self.url,
            "permalink": self.permalink,
            "keyword": self.keyword,
            "published_at": self.published_at,
        }


@dataclass
class CollectResult:
    fetched: int
    unique: int
    posts: list[RedditPost] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class RedditPublicCollector:
    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        request_delay: float = REQUEST_DELAY_SECONDS,
        respect_robots: bool = True,
    ) -> None:
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.respect_robots = respect_robots
        self._last_request_at = 0.0
        self._robots = urllib.robotparser.RobotFileParser()
        self._robots_loaded = False

    def _load_robots(self) -> None:
        if self._robots_loaded:
            return
        try:
            self._robots.set_url(ROBOTS_URL)
            self._robots.read()
        except Exception:
            pass
        self._robots_loaded = True

    def robots_allows(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        self._load_robots()
        try:
            return self._robots.can_fetch(self.user_agent, url)
        except Exception:
            return False

    def robots_status_message(self) -> str:
        sample = f"{OLD_REDDIT_BASE}/r/spotify/"
        if self.robots_allows(sample):
            return "robots.txt allows automated fetch for sample Reddit URL"
        return (
            "robots.txt disallows automated Reddit fetching. "
            "Save public pages manually in your browser, then import HTML from data/reddit_html/"
        )

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self._last_request_at = time.monotonic()

    def _get_with_retry(self, url: str, headers: dict[str, str], max_attempts: int = 4) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(max_attempts):
            self._throttle()
            try:
                with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
                    response = client.get(url)
                    if response.status_code == 429 and attempt < max_attempts - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    return response
            except Exception as exc:
                last_exc = exc
                if attempt < max_attempts - 1:
                    time.sleep(3 * (attempt + 1))
        raise last_exc or RuntimeError(f"Failed to fetch {url}")

    def fetch_live_html(self, url: str) -> str:
        """Fetch public Reddit HTML (RSS companion / old.reddit search)."""
        headers = {
            "User-Agent": LIVE_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        return self._get_with_retry(url, headers).text

    def fetch_rss(self, url: str) -> str:
        """Fetch a Reddit RSS feed."""
        headers = {"User-Agent": LIVE_USER_AGENT, "Accept": "application/atom+xml,text/xml,*/*"}
        return self._get_with_retry(url, headers).text

    def fetch_html(self, url: str) -> str:
        if not self.robots_allows(url):
            raise PermissionError(
                f"robots.txt disallows automated fetch: {url}. "
                "Save the page manually and use collect_from_html_dir()."
            )

        self._throttle()
        headers = {"User-Agent": self.user_agent, "Accept": "text/html"}
        with httpx.Client(headers=headers, timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return response.text

    def _parse_score(self, thing: BeautifulSoup) -> int | None:
        score_el = thing.select_one("div.score.unvoted, div.score.likes, div.score")
        if not score_el:
            return None
        text = score_el.get_text(strip=True)
        if text in ("•", "·", ""):
            return None
        match = re.search(r"-?\d+", text.replace(",", ""))
        return int(match.group()) if match else None

    def _parse_post_id(self, thing: BeautifulSoup) -> str:
        thing_id = thing.get("data-fullname") or thing.get("id") or ""
        if thing_id.startswith("t3_"):
            return thing_id[3:]
        match = re.search(r"t3_(\w+)", thing_id)
        if match:
            return match.group(1)
        link = thing.select_one("a.title")
        if link and link.get("href"):
            match = re.search(r"/comments/(\w+)/", link["href"])
            if match:
                return match.group(1)
        return thing_id or "unknown"

    def _parse_body(self, thing: BeautifulSoup) -> str:
        body_el = thing.select_one("div.usertext-body div.md")
        if body_el:
            return body_el.get_text("\n", strip=True)
        return ""

    def _infer_subreddit(self, thing: BeautifulSoup, fallback: str) -> str:
        tagline = thing.select_one("p.tagline")
        if tagline:
            sub_link = tagline.select_one("a.subreddit")
            if sub_link:
                href = sub_link.get("href", "")
                match = re.search(r"/r/(\w+)", href)
                if match:
                    return match.group(1)
        return fallback

    def parse_listing_html(
        self,
        html: str,
        default_subreddit: str = "spotify",
        keyword: str | None = None,
    ) -> list[RedditPost]:
        soup = BeautifulSoup(html, "html.parser")
        posts: list[RedditPost] = []

        for thing in soup.select("div.thing.link"):
            title_el = thing.select_one("a.title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            permalink = urljoin(OLD_REDDIT_BASE, title_el.get("href", ""))
            post_id = self._parse_post_id(thing)
            body = self._parse_body(thing)
            score = self._parse_score(thing)
            subreddit = self._infer_subreddit(thing, default_subreddit)

            posts.append(
                RedditPost(
                    post_id=post_id,
                    title=title,
                    body=body or title,
                    subreddit=subreddit,
                    score=score,
                    url=permalink,
                    permalink=permalink,
                    keyword=keyword,
                )
            )

        return posts

    def _parse_search_score(self, result: BeautifulSoup) -> int | None:
        score_el = result.select_one("span.search-score")
        if not score_el:
            return None
        match = re.search(r"-?\d+", score_el.get_text(strip=True).replace(",", ""))
        return int(match.group()) if match else None

    def _parse_search_post_id(self, result: BeautifulSoup, link: str) -> str:
        fullname = result.get("data-fullname") or ""
        if fullname.startswith("t3_"):
            return fullname[3:]
        match = re.search(r"/comments/(\w+)/", link)
        return match.group(1) if match else fullname or "unknown"

    def parse_search_html(
        self,
        html: str,
        default_subreddit: str = "spotify",
        keyword: str | None = None,
    ) -> list[RedditPost]:
        """Parse old.reddit.com search results (div.search-result)."""
        soup = BeautifulSoup(html, "html.parser")
        posts: list[RedditPost] = []

        for result in soup.select("div.search-result"):
            title_el = result.select_one("a.search-title")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            permalink = urljoin(OLD_REDDIT_BASE, title_el.get("href", ""))
            post_id = self._parse_search_post_id(result, permalink)
            body_el = result.select_one("div.search-result-body")
            body = body_el.get_text("\n", strip=True) if body_el else ""
            score = self._parse_search_score(result)

            subreddit = default_subreddit
            sub_link = result.select_one("a.search-subreddit-link")
            if sub_link:
                match = re.search(r"/r/(\w+)", sub_link.get("href", ""))
                if match:
                    subreddit = match.group(1)

            published_at = None
            time_el = result.select_one("time")
            if time_el and time_el.get("datetime"):
                published_at = time_el["datetime"]

            posts.append(
                RedditPost(
                    post_id=post_id,
                    title=title,
                    body=body or title,
                    subreddit=subreddit,
                    score=score,
                    url=permalink,
                    permalink=permalink,
                    keyword=keyword,
                    published_at=published_at,
                )
            )

        return posts

    def parse_rss_feed(
        self,
        xml_text: str,
        default_subreddit: str = "spotify",
        keyword: str | None = None,
    ) -> list[RedditPost]:
        """Parse Reddit Atom RSS search/browse feed."""
        posts: list[RedditPost] = []
        root = ET.fromstring(xml_text)

        for entry in root.findall("a:entry", ATOM_NS):
            title_el = entry.find("a:title", ATOM_NS)
            link_el = entry.find("a:link", ATOM_NS)
            content_el = entry.find("a:content", ATOM_NS)
            id_el = entry.find("a:id", ATOM_NS)
            published_el = entry.find("a:published", ATOM_NS) or entry.find("a:updated", ATOM_NS)

            if title_el is None or link_el is None:
                continue

            title = unescape(title_el.text or "").strip()
            permalink = link_el.attrib.get("href", "")
            post_id = ""
            if id_el is not None and id_el.text:
                post_id = id_el.text.replace("t3_", "", 1)
            if not post_id:
                match = re.search(r"/comments/(\w+)/", permalink)
                post_id = match.group(1) if match else "unknown"

            body = ""
            if content_el is not None and content_el.text:
                body = BeautifulSoup(unescape(content_el.text), "html.parser").get_text("\n", strip=True)

            subreddit = default_subreddit
            category = entry.find("a:category", ATOM_NS)
            if category is not None and category.attrib.get("term"):
                subreddit = category.attrib["term"]

            published_at = published_el.text if published_el is not None else None

            posts.append(
                RedditPost(
                    post_id=post_id,
                    title=title,
                    body=body or title,
                    subreddit=subreddit,
                    score=None,
                    url=permalink,
                    permalink=permalink,
                    keyword=keyword,
                    published_at=published_at,
                )
            )

        return posts

    def build_rss_search_url(self, subreddit: str, keyword: str) -> str:
        query = quote_plus(keyword)
        return f"{REDDIT_BASE}/r/{subreddit}/search.rss?q={query}&restrict_sr=on&sort=relevance"

    def search_subreddit_rss(
        self,
        subreddit: str,
        keyword: str,
        limit: int = 25,
    ) -> list[RedditPost]:
        url = self.build_rss_search_url(subreddit, keyword)
        xml_text = self.fetch_rss(url)
        return self.parse_rss_feed(xml_text, default_subreddit=subreddit, keyword=keyword)[:limit]

    def search_subreddit_live(
        self,
        subreddit: str,
        keyword: str,
        limit: int = 25,
    ) -> list[RedditPost]:
        url = self.build_search_url(subreddit, keyword)
        html = self.fetch_live_html(url)
        posts = self.parse_search_html(html, default_subreddit=subreddit, keyword=keyword)
        if not posts:
            posts = self.parse_listing_html(html, default_subreddit=subreddit, keyword=keyword)
        return posts[:limit]

    def collect_scrape(
        self,
        subreddits: list[str] | None = None,
        keywords: list[str] | None = None,
        limit: int = 150,
        use_rss: bool = True,
        use_html: bool = True,
    ) -> CollectResult:
        """Fetch real Reddit posts via RSS + old.reddit HTML search."""
        subreddits = subreddits or DEFAULT_SUBREDDITS
        keywords = keywords or DEFAULT_KEYWORDS
        seen: set[str] = set()
        posts: list[RedditPost] = []
        errors: list[str] = []
        fetched = 0
        warnings = [
            "Live scrape mode: fetching real public Reddit data via RSS and old.reddit HTML.",
            "Respect rate limits — do not run repeatedly in short intervals.",
        ]

        for subreddit in subreddits:
            for keyword in keywords:
                if len(posts) >= limit:
                    break
                batch: list[RedditPost] = []
                if use_rss:
                    try:
                        batch.extend(self.search_subreddit_rss(subreddit, keyword))
                    except Exception as exc:
                        errors.append(f"RSS r/{subreddit} '{keyword}': {exc}")
                if use_html:
                    try:
                        batch.extend(self.search_subreddit_live(subreddit, keyword))
                    except Exception as exc:
                        errors.append(f"HTML r/{subreddit} '{keyword}': {exc}")

                fetched += len(batch)
                for post in batch:
                    if post.post_id not in seen:
                        seen.add(post.post_id)
                        posts.append(post)
                        if len(posts) >= limit:
                            break
            if len(posts) >= limit:
                break

        return CollectResult(
            fetched=fetched,
            unique=len(posts),
            posts=posts[:limit],
            errors=errors,
            warnings=warnings,
        )

    def collect_from_html_dir(
        self,
        directory: str | Path,
        keyword: str | None = None,
        limit: int | None = None,
    ) -> CollectResult:
        """Parse one or more HTML files saved from public Reddit pages."""
        path = Path(directory)
        if not path.exists():
            return CollectResult(
                fetched=0,
                unique=0,
                errors=[f"Directory not found: {path}"],
            )

        html_files = sorted(path.glob("*.html"))
        if not html_files:
            return CollectResult(
                fetched=0,
                unique=0,
                errors=[f"No .html files in {path}"],
            )

        seen: set[str] = set()
        posts: list[RedditPost] = []
        fetched = 0

        for html_file in html_files:
            html = html_file.read_text(encoding="utf-8", errors="replace")
            stem_parts = html_file.stem.split("_", 1)
            subreddit = stem_parts[0] if stem_parts else "spotify"
            file_keyword = stem_parts[1].replace("-", " ") if len(stem_parts) > 1 else keyword
            parsed = self.parse_listing_html(
                html, default_subreddit=subreddit, keyword=file_keyword or keyword
            )
            fetched += len(parsed)
            for post in parsed:
                if post.post_id not in seen:
                    seen.add(post.post_id)
                    posts.append(post)
                    if limit and len(posts) >= limit:
                        break
            if limit and len(posts) >= limit:
                break

        return CollectResult(fetched=fetched, unique=len(posts), posts=posts)

    def build_search_url(self, subreddit: str, keyword: str) -> str:
        query = quote_plus(keyword)
        return f"{OLD_REDDIT_BASE}/r/{subreddit}/search?q={query}&restrict_sr=on&sort=relevance"

    def collect(
        self,
        subreddits: list[str] | None = None,
        keywords: list[str] | None = None,
        limit_per_search: int = 15,
        html_dir: str | Path | None = None,
        live: bool = False,
        scrape: bool = False,
        limit: int | None = None,
    ) -> CollectResult:
        """
        Collect Reddit posts.

        Modes (first match wins):
          scrape=True  — live RSS + old.reddit HTML (real data)
          html_dir     — parse manually saved HTML files
          live=True    — legacy HTML fetch (prefer scrape=True)
          default      — print manual workflow hints
        """
        warnings: list[str] = []
        if scrape:
            return self.collect_scrape(
                subreddits=subreddits,
                keywords=keywords,
                limit=limit or 150,
            )

        if html_dir:
            result = self.collect_from_html_dir(html_dir, limit=limit)
            result.warnings = warnings
            return result

        if not live:
            urls = []
            for sub in subreddits or DEFAULT_SUBREDDITS:
                for kw in keywords or DEFAULT_KEYWORDS:
                    urls.append(self.build_search_url(sub, kw))
            warnings.append("No scrape mode enabled. Use --scrape for live real data collection.")
            warnings.append("Manual workflow:")
            warnings.append("  1. Open each search URL in your browser")
            warnings.append("  2. Save page as HTML → data/reddit_html/{subreddit}_{keyword}.html")
            warnings.append("  3. Re-run: python scripts/collect_reddit.py --html-dir data/reddit_html")
            warnings.append("Or run: python scripts/collect_reddit.py --scrape")
            warnings.append("Search URLs to save:")
            warnings.extend(f"  - {u}" for u in urls[:6])
            return CollectResult(
                fetched=0,
                unique=0,
                posts=[],
                errors=[],
                warnings=warnings,
            )

        subreddits = subreddits or DEFAULT_SUBREDDITS
        keywords = keywords or DEFAULT_KEYWORDS
        seen: set[str] = set()
        posts: list[RedditPost] = []
        errors: list[str] = []
        fetched = 0

        for subreddit in subreddits:
            for keyword in keywords:
                try:
                    search_posts = self.search_subreddit_live(
                        subreddit, keyword, limit=limit_per_search
                    )
                    fetched += len(search_posts)
                    for post in search_posts:
                        if post.post_id not in seen:
                            seen.add(post.post_id)
                            posts.append(post)
                except Exception as exc:
                    errors.append(f"r/{subreddit} search '{keyword}': {exc}")

        return CollectResult(
            fetched=fetched,
            unique=len(posts),
            posts=posts,
            errors=errors,
            warnings=warnings,
        )


def collect_reddit(
    subreddits: list[str] | None = None,
    keywords: list[str] | None = None,
    limit_per_search: int = 15,
    html_dir: str | Path | None = None,
    live: bool = False,
    scrape: bool = False,
    user_agent: str = DEFAULT_USER_AGENT,
    limit: int | None = None,
) -> CollectResult:
    collector = RedditPublicCollector(user_agent=user_agent)
    effective_limit = limit if (html_dir or scrape) else None
    if live and limit:
        limit_per_search = limit
    return collector.collect(
        subreddits=subreddits,
        keywords=keywords,
        limit_per_search=limit_per_search,
        html_dir=html_dir,
        live=live,
        scrape=scrape,
        limit=effective_limit,
    )


def test_public_access(user_agent: str = DEFAULT_USER_AGENT) -> tuple[bool, str]:
    """Check whether live Reddit scraping is reachable."""
    collector = RedditPublicCollector(user_agent=user_agent)
    try:
        posts = collector.search_subreddit_rss("spotify", "discover weekly", limit=3)
        if posts:
            return True, f"Reddit RSS live — fetched {len(posts)} real posts (sample scrape OK)"
    except Exception as exc:
        return False, f"Reddit RSS unreachable: {exc}"

    html_dir = Path("data/reddit_html")
    if html_dir.exists() and list(html_dir.glob("*.html")):
        result = collector.collect_from_html_dir(html_dir)
        return True, f"Found {result.unique} posts in {html_dir} (manual HTML import)"

    return False, "Could not reach Reddit RSS or local HTML files"
