"""
Crawler v3: Outlet-specific politics section crawler.

Each outlet has its own list_url, link_selector, and optional article page
selectors (title_selector, content_selector). Tune these per outlet without
changing the core logic.
"""

import os
import re
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Media stance classification (progressive / moderate / conservative)
MEDIA_BY_STANCE = {
    "progressive": ["한겨레", "경향신문", "오마이뉴스", "프레시안"],
    "moderate": ["한국일보", "서울신문", "세계일보"],
    "conservative": ["조선일보", "중앙일보", "동아일보", "국민일보"],
}

# Domain -> outlet name (for source extraction)
DOMAIN_TO_SOURCE = {
    "hani.co.kr": "한겨레",
    "khan.co.kr": "경향신문",
    "ohmynews.com": "오마이뉴스",
    "pressian.com": "프레시안",
    "hankookilbo.com": "한국일보",
    "seoul.co.kr": "서울신문",
    "segye.com": "세계일보",
    "chosun.com": "조선일보",
    "joongang.co.kr": "중앙일보",
    "donga.com": "동아일보",
    "kmib.co.kr": "국민일보",
    "mk.co.kr": "매일경제",
    "hankyung.com": "한국경제",
    "yonhapnews.co.kr": "연합뉴스",
    "yna.co.kr": "연합뉴스",
    "news1.kr": "뉴스1",
    "sbs.co.kr": "SBS",
    "kbs.co.kr": "KBS",
    "mbc.co.kr": "MBC",
    "ytn.co.kr": "YTN",
    "jtbc.co.kr": "JTBC",
    "channeltva.com": "채널A",
    "tvchosun.com": "TV조선",
    "mbn.co.kr": "MBN",
}

# Keywords used to filter political articles
POLITICS_KEYWORDS = (
    "국회", "대통령", "정부", "정당", "의원", "선거", "여야", "국정",
    "여론", "정책", "법안", "청와대", "여권", "야당", "국무", "장관",
    "국정감사", "특검", "검찰", "대법원", "헌법", "정치인", "당대표",
    "영수회담", "국정농단", "여론조사", "지지율", "민주당", "국민의힘",
)

# ---------------------------------------------------------------------------
# Outlet config: adjust list_url, link_selector (and optionally title_selector,
# content_selector) per outlet. Other code does not need to change.
# ---------------------------------------------------------------------------
OUTLET_CONFIG = {
    "한겨레": {
        "list_url": "https://www.hani.co.kr/arti/politics",
        # li.ArticleList_item___OGQO 안에 기사 링크가 2개(제목+썸네일) → seen으로 중복 제거됨. .html로 끝나는 것만 골라 섹션 링크(/arti/politics/politics_general) 제외.
        "link_selector": "a.BaseArticleCard_link__Q3YFK[href*='/arti/politics/'][href$='.html']",
        "max_articles": 25,
        "title_selector": "h3.ArticleDetailView_title__9kRU_",
        "content_selector": "div.article-text",
    },
    "조선일보": {
        "list_url": "https://www.chosun.com/politics/",
        # 기사 링크는 상대경로(/politics/assembly/2026/02/20/ID/). 헤드라인 링크만 선택해 한 기사당 하나만 수집
        "link_selector": "a[class*='story-card__headline'][href^='/politics/']",
        "max_articles": 25,
        "title_selector": "h1.article-header__headline",
        "content_selector": "section.article-body",
    },
    "한국일보": {
        "list_url": "https://www.hankookilbo.com/news/politics",
        "link_selector": "a[href*='/news/article/']",
        "max_articles": 25,
        "title_selector": "p[class*='font-extrabold'][class*='text-24']",
        "content_selector": "div.article-view",
    },
}


class OutletPoliticsCrawler:
    """
    Crawler that fetches articles from each outlet's politics section.
    Per-outlet list URL and CSS selectors are defined in OUTLET_CONFIG.
    """

    def __init__(
        self,
        naver_client_id: Optional[str] = None,
        naver_client_secret: Optional[str] = None,
    ):
        """
        Args:
            naver_client_id: Optional (unused in v3; for API compatibility).
            naver_client_secret: Optional (unused in v3; for API compatibility).
        """
        self.web_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.session = requests.Session()
        self.session.headers.update(self.web_headers)

    def fetch_article_links_from_outlet(
        self,
        outlet_name: str,
        max_articles: Optional[int] = None,
    ) -> List[str]:
        """
        Fetch article URLs from an outlet's politics list page.

        Args:
            outlet_name: Key in OUTLET_CONFIG (e.g. "한겨레", "조선일보", "한국일보").
            max_articles: Max number of URLs to return; uses config default if None.

        Returns:
            List of absolute article URLs (deduplicated, up to max_articles).
        """
        if outlet_name not in OUTLET_CONFIG:
            logger.warning("Outlet not in config: %s", outlet_name)
            return []
        conf = OUTLET_CONFIG[outlet_name]
        list_url = conf["list_url"]
        link_selector = conf["link_selector"]
        limit = max_articles if max_articles is not None else conf.get("max_articles", 25)
        try:
            resp = self.session.get(list_url, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception as e:
            logger.error("List page request failed [%s] %s: %s", outlet_name, list_url, e)
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        links = soup.select(link_selector)
        seen = set()
        urls = []
        for a in links:
            href = (a.get("href") or "").strip()
            if not href:
                continue
            full = urljoin(list_url, href)
            if full in seen:
                continue
            if full == list_url or full.rstrip("/") == list_url.rstrip("/"):
                continue
            seen.add(full)
            urls.append(full)
            if len(urls) >= limit:
                break
        logger.info("[%s] Fetched %d article URLs from list", outlet_name, len(urls))
        return urls

    def extract_article_content(
        self,
        url: str,
        outlet_name: Optional[str] = None,
        max_retries: int = 2,
    ) -> Dict[str, Optional[str]]:
        """
        Extract title, body, source, and date from a single article URL.
        If outlet_name is set and that outlet has title_selector/content_selector
        in OUTLET_CONFIG, those are used first; otherwise generic selectors are used.

        Args:
            url: Article URL.
            outlet_name: Optional outlet key for outlet-specific selectors.
            max_retries: Number of retries on failure.

        Returns:
            Dict with keys: title, content, source, url, pubDate.
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                response.encoding = "utf-8"
                soup = BeautifulSoup(response.text, "html.parser")

                title = self._extract_title(soup, outlet_name)
                content = self._extract_content(soup, outlet_name)

                if (not title or not title.strip()) and content:
                    first_line = content.split("\n")[0].strip()
                    if first_line and len(first_line) > 10:
                        title = first_line[:80] + ("..." if len(first_line) > 80 else "")

                source = self._extract_source(soup, url)
                pub_date = self._extract_date(soup)

                return {
                    "title": title,
                    "content": content,
                    "source": source,
                    "url": url,
                    "pubDate": pub_date,
                }
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    logger.warning("Timeout, retrying (%s/%s)", attempt + 1, max_retries)
                    time.sleep(1)
                    continue
                logger.error("Article fetch timeout: %s", url)
            except requests.exceptions.RequestException as e:
                logger.error("Article fetch failed %s: %s", url, e)
            except Exception as e:
                logger.error("Unexpected error fetching %s: %s", url, e)

        return {
            "title": None,
            "content": None,
            "source": None,
            "url": url,
            "pubDate": None,
        }

    def _extract_title(self, soup: BeautifulSoup, outlet_name: Optional[str] = None) -> Optional[str]:
        """Extract title: outlet-specific selector first, then og:title, then generic DOM."""
        if outlet_name and outlet_name in OUTLET_CONFIG:
            conf = OUTLET_CONFIG[outlet_name]
            sel = conf.get("title_selector")
            if sel:
                el = soup.select_one(sel)
                if el:
                    t = el.get_text().strip()
                    if t and len(t) > 3:
                        return t

        og = soup.select_one('meta[property="og:title"]')
        if og and og.get("content"):
            t = og.get("content", "").strip()
            if t and len(t) > 3:
                return t

        for selector in (
            "#title_area h2",
            ".media_end_head_headline h2",
            "#articleTitle",
            ".newsct_article h2",
            "h1.title",
            "h1",
        ):
            el = soup.select_one(selector)
            if el:
                title = el.get_text().strip()
                if title and len(title) > 5:
                    return title
        return None

    def _extract_content(self, soup: BeautifulSoup, outlet_name: Optional[str] = None) -> Optional[str]:
        """Extract body: outlet-specific selector first, then generic selectors."""
        if outlet_name and outlet_name in OUTLET_CONFIG:
            conf = OUTLET_CONFIG[outlet_name]
            sel = conf.get("content_selector")
            if sel:
                el = soup.select_one(sel)
                if el:
                    text = self._text_from_element(el)
                    if text and len(text) > 100:
                        return text

        for selector in (
            "#dic_area",
            "#articleBodyContents",
            ".newsct_article ._article_body_contents",
            "._article_body_contents",
            "#newsEndContents",
            "#articeBody",
            ".se_component_wrap",
            ".article_body",
            "#article_body",
            "article",
            ".article_view",
        ):
            el = soup.select_one(selector)
            if el:
                text = self._text_from_element(el)
                if text and len(text) > 100:
                    return text
        return None

    def _text_from_element(self, element) -> str:
        """Get cleaned text from a BeautifulSoup element."""
        for unwanted in element.select(
            "script, style, .ad, .advertisement, .related, .comment, .byline, .reporter_area, .copyright, figure, figcaption"
        ):
            unwanted.decompose()
        text = element.get_text(separator="\n", strip=True)
        return "\n".join(line.strip() for line in text.split("\n") if line.strip())

    def _extract_source(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """Extract outlet name from meta or URL."""
        for selector, attr in (
            ('meta[property="og:site_name"]', "content"),
            ('meta[name="publisher"]', "content"),
            ('meta[property="article:author"]', "content"),
        ):
            el = soup.select_one(selector)
            if el and el.get(attr):
                return el.get(attr)
        for domain, name in DOMAIN_TO_SOURCE.items():
            if domain in url:
                return name
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publish date."""
        for selector, attr in (
            ('meta[property="article:published_time"]', "content"),
            ('meta[name="publish_date"]', "content"),
            ('meta[property="og:published_time"]', "content"),
            (".media_end_head_info_datestamp em", None),
            (".times", None),
        ):
            if attr:
                el = soup.select_one(selector)
                if el and el.get(attr):
                    date_str = el.get(attr)
                    if "T" in date_str:
                        date_str = date_str.split("T")[0]
                    return date_str
            else:
                el = soup.select_one(selector)
                if el and el.get_text():
                    return el.get_text().strip()
        return None

    def _get_source_from_url(self, url: str) -> Optional[str]:
        """Guess outlet name from URL."""
        url_lower = url.lower()
        for domain, name in DOMAIN_TO_SOURCE.items():
            if domain in url_lower:
                return name
        return None

    def _is_political_content(self, title: str, content: str, min_keywords: int = 2) -> bool:
        """Whether title+content contain enough politics keywords."""
        text = (title or "") + " " + (content or "")
        return sum(1 for kw in POLITICS_KEYWORDS if kw in text) >= min_keywords

    def crawl_politics_from_outlets(
        self,
        outlet_names: List[str],
        max_per_outlet: int = 25,
        filter_political_content: bool = True,
    ) -> List[Dict]:
        """
        Crawl politics sections of the given outlets: list page -> article URLs -> full text.

        Args:
            outlet_names: List of outlet keys (e.g. ["한겨레", "조선일보", "한국일보"]).
            max_per_outlet: Max articles per outlet.
            filter_political_content: If True, drop articles that fail politics keyword check.

        Returns:
            List of article dicts (title, content, source, url, pubDate, media_stance).
        """
        all_articles = []
        seen_urls = set()
        for outlet in outlet_names:
            if outlet not in OUTLET_CONFIG:
                logger.warning("Skipping unknown outlet: %s", outlet)
                continue
            urls = self.fetch_article_links_from_outlet(outlet, max_articles=max_per_outlet)
            for url in urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                logger.info("Crawling [%s] %s...", outlet, url[:60])
                data = self.extract_article_content(url, outlet_name=outlet)
                if not data.get("content"):
                    continue
                if filter_political_content and not self._is_political_content(
                    data.get("title") or "", data.get("content") or ""
                ):
                    continue
                source = data.get("source") or self._get_source_from_url(url)
                data["source"] = source
                data["media_stance"] = next(
                    (s for s, names in MEDIA_BY_STANCE.items() if source in names),
                    None,
                )
                all_articles.append(data)
                time.sleep(0.5)
        logger.info("Outlet politics crawl done: %d articles", len(all_articles))
        return all_articles

    def save_to_json(self, articles: List[Dict], filename: str = "politics_news.json") -> None:
        """Save articles to a JSON file."""
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        logger.info("Saved: %s", filename)

    def save_to_jsonl(self, articles: List[Dict], filename: str = "politics_news.jsonl") -> None:
        """Save articles to a JSONL file (one JSON object per line)."""
        with open(filename, "w", encoding="utf-8") as f:
            for article in articles:
                f.write(json.dumps(article, ensure_ascii=False) + "\n")
        logger.info("Saved: %s (%d articles)", filename, len(articles))


# Backward-compatible alias
PoliticsNewsCrawler = OutletPoliticsCrawler


if __name__ == "__main__":
    # No Naver API needed for outlet-only crawl
    crawler = OutletPoliticsCrawler(
        os.getenv("NAVER_CLIENT_ID"),
        os.getenv("NAVER_CLIENT_SECRET"),
    )
    # List URLs only (test)
    # urls = crawler.fetch_article_links_from_outlet("조선일보", max_articles=10)
    # print(urls)
    # Full crawl and save
    articles = crawler.crawl_politics_from_outlets(
        ["한겨레", "조선일보", "한국일보"],
        max_per_outlet=15,
    )
    crawler.save_to_jsonl(articles, "data/1_crawled/outlet_news.jsonl")
    print("Done:", len(articles), "articles")
