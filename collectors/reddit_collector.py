"""
Collect Reddit posts from publicly accessible content without the Reddit API.

Important: https://www.reddit.com/robots.txt disallows automated fetching for all
user-agents (`Disallow: /`). This module therefore defaults to **offline mode**:
parse HTML files you save manually while browsing public Reddit pages in a browser.

Optional live fetch exists for local experimentation but will be blocked when
robots.txt disallows the URL (expected for Reddit).
"""

from __future__ import annotations

import re
import time
import urllib.robotparser
from dataclasses import dataclass, field
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
ROBOTS_URL = "https://www.reddit.com/robots.txt"
DEFAULT_USER_AGENT = "spotify-research-collector/1.0 (PM case study; public pages only)"
REQUEST_DELAY_SECONDS = 2.0


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

    def collect_from_html_dir(
        self,
        directory: str | Path,
        keyword: str | None = None,
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
            subreddit = html_file.stem.split("_")[0] if "_" in html_file.stem else "spotify"
            parsed = self.parse_listing_html(html, default_subreddit=subreddit, keyword=keyword)
            fetched += len(parsed)
            for post in parsed:
                if post.post_id not in seen:
                    seen.add(post.post_id)
                    posts.append(post)

        return CollectResult(fetched=fetched, unique=len(posts), posts=posts)

    def build_search_url(self, subreddit: str, keyword: str) -> str:
        query = quote_plus(keyword)
        return f"{OLD_REDDIT_BASE}/r/{subreddit}/search?q={query}&restrict_sr=on&sort=relevance"

    def search_subreddit_live(
        self,
        subreddit: str,
        keyword: str,
        limit: int = 25,
    ) -> list[RedditPost]:
        url = self.build_search_url(subreddit, keyword)
        html = self.fetch_html(url)
        posts = self.parse_listing_html(html, default_subreddit=subreddit, keyword=keyword)
        return posts[:limit]

    def collect(
        self,
        subreddits: list[str] | None = None,
        keywords: list[str] | None = None,
        limit_per_search: int = 15,
        html_dir: str | Path | None = None,
        live: bool = False,
    ) -> CollectResult:
        """
        Collect Reddit posts.

        Default (recommended): import from `html_dir` of manually saved pages.
        Optional `live=True`: automated fetch (blocked by Reddit robots.txt).
        """
        warnings: list[str] = []
        if html_dir:
            result = self.collect_from_html_dir(html_dir)
            result.warnings = warnings
            return result

        if not live:
            urls = []
            for sub in subreddits or DEFAULT_SUBREDDITS:
                for kw in keywords or DEFAULT_KEYWORDS:
                    urls.append(self.build_search_url(sub, kw))
            warnings.append(self.robots_status_message())
            warnings.append("Manual workflow:")
            warnings.append("  1. Open each search URL in your browser")
            warnings.append("  2. Save page as HTML → data/reddit_html/{subreddit}_{keyword}.html")
            warnings.append("  3. Re-run: python scripts/collect_reddit.py --html-dir data/reddit_html")
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
    user_agent: str = DEFAULT_USER_AGENT,
) -> CollectResult:
    collector = RedditPublicCollector(user_agent=user_agent)
    return collector.collect(
        subreddits=subreddits,
        keywords=keywords,
        limit_per_search=limit_per_search,
        html_dir=html_dir,
        live=live,
    )


def test_public_access(user_agent: str = DEFAULT_USER_AGENT) -> tuple[bool, str]:
    """Check robots policy and whether manual collection workflow is ready."""
    collector = RedditPublicCollector(user_agent=user_agent)
    html_dir = Path("data/reddit_html")
    if html_dir.exists() and list(html_dir.glob("*.html")):
        result = collector.collect_from_html_dir(html_dir)
        return True, f"Found {result.unique} posts in {html_dir} (manual HTML import)"

    if not collector.robots_allows(f"{OLD_REDDIT_BASE}/r/spotify/"):
        return True, collector.robots_status_message()

    try:
        collector.fetch_html(f"{OLD_REDDIT_BASE}/r/spotify/")
        return True, "Public Reddit pages reachable for automated fetch"
    except Exception as exc:
        return False, f"Could not reach public Reddit pages: {exc}"
