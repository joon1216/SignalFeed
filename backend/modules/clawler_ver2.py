import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urljoin
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 언론사 성향별 분류 (진보/중도/보수)
MEDIA_BY_STANCE = {
    "progressive": ["한겨레", "경향신문", "오마이뉴스", "프레시안"],
    "moderate": ["한국일보", "서울신문", "세계일보"],
    "conservative": ["조선일보", "중앙일보", "동아일보", "국민일보"],
}
BALANCED_SOURCES = set(
    MEDIA_BY_STANCE["progressive"]
    + MEDIA_BY_STANCE["moderate"]
    + MEDIA_BY_STANCE["conservative"]
)

# 도메인 → 언론사 매핑 (URL 사전 필터용)
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

# 주요 언론사 화이트리스트 (전체 - all_sources 모드용)
ALLOWED_NEWS_DOMAINS = set(DOMAIN_TO_SOURCE.keys())

# 네이버 뉴스 URL 미디어 코드 → 언론사 매핑
NAVER_MEDIA_CODE_TO_SOURCE = {
    "001": "연합뉴스",
    "002": "매일경제",
    "003": "서울신문",
    "005": "국민일보",
    "020": "동아일보",
    "021": "경향신문",
    "022": "중앙일보",
    "023": "조선일보",
    "025": "한국일보",
    "028": "한겨레",
    "032": "KBS",
    "055": "SBS",
    "081": "YTN",
    "088": "JTBC",
    "094": "MBC",
    "277": "연합뉴스",
    "293": "뉴스1",
    "438": "한국경제",
    "422": "TV조선",
    "437": "채널A",
    "449": "MBN",
    "016": "세계일보",   # 일부 세부코드
}

ALLOWED_NEWS_SOURCES = set(DOMAIN_TO_SOURCE.values())

# 비정치 도메인 블랙리스트 (정치 검색에 섞여 나오는 라이프스타일/뷰티/광고 사이트)
EXCLUDED_DOMAINS = {
    "allurekorea.com",      # 뷰티/화장품 매거진
    "christiantoday.co.kr", # 종교 뉴스
    "g-enews.com",          # 지역/기타
    "netongs.com",          # 지역신문
    "woman.chosun.com",     # 여성/라이프 (조선일보 계열이지만 비정치)
    "sportsworldi.com",     # 스포츠
    "fnnews.com",           # 패션뉴스
}

# 정치 관련성 판단용 키워드 (본문에 일정 개수 이상 포함되어야 정치 기사로 간주)
POLITICS_KEYWORDS = (
    "국회", "대통령", "정부", "정당", "의원", "선거", "여야", "국정",
    "여론", "정책", "법안", "청와대", "여권", "야당", "국무", "장관",
    "국정감사", "특검", "검찰", "대법원", "헌법", "정치인", "당대표",
    "영수회담", "국정농단", "여론조사", "지지율", "민주당", "국민의힘",
)

# 언론사 정치면 직접 크롤링용 설정 (목록 URL → 기사 링크 추출)
OUTLET_POLITICS = {
    "한겨레": {
        "list_url": "https://www.hani.co.kr/arti/politics.html",
        "link_selector": "a[href*='/arti/politics/']",
        "max_articles": 25,
    },
    "조선일보": {
        "list_url": "https://www.chosun.com/politics/",
        "link_selector": "a[href*='chosun.com'][href*='/2']",
        "max_articles": 25,
    },
    "한국일보": {
        "list_url": "https://www.hankookilbo.com/News/Politics",
        "link_selector": "a[href*='/News/']",
        "max_articles": 25,
    },
}


class PoliticsNewsCrawler:
    def __init__(self, naver_client_id: str, naver_client_secret: str):
        """
        네이버 API와 뉴스 크롤링을 위한 크롤러 초기화
        
        Args:
            naver_client_id: 네이버 API Client ID
            naver_client_secret: 네이버 API Client Secret
        """
        self.client_id = naver_client_id
        self.client_secret = naver_client_secret
        
        # 네이버 API 헤더
        self.naver_headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        # 웹 크롤링 헤더
        self.web_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.web_headers)
    
    def search_naver_news(self, keyword: str, display: int = 100, sort: str = "date", start: int = 1) -> List[Dict]:
        """
        네이버 뉴스 API를 통해 기사 검색
        
        Args:
            keyword: 검색어
            display: 결과 개수 (1~100)
            sort: 정렬 (date: 날짜순, sim: 정확도순)
            start: 시작 위치 (1부터 시작, 최대 1000)
        
        Returns:
            검색 결과 리스트
        """
        url = "https://openapi.naver.com/v1/search/news.json"
        
        params = {
            "query": quote(keyword),
            "display": min(display, 100),
            "start": max(1, min(start, 1000)),  # 1~1000 범위 제한
            "sort": sort
        }
        
        try:
            response = requests.get(url, headers=self.naver_headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("items", [])
            total = data.get("total", 0)
            
            logger.info(f"'{keyword}' 검색 결과: {len(items)}개 (전체: {total}개)")
            return items
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("네이버 API 인증 실패: Client ID 또는 Secret이 잘못되었습니다.")
            elif e.response.status_code == 429:
                logger.error("네이버 API 호출 한도 초과: 잠시 후 다시 시도해주세요.")
            else:
                logger.error(f"네이버 API HTTP 오류 ({e.response.status_code}): {e}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"네이버 API 요청 실패: {e}")
            return []
        except Exception as e:
            logger.error(f"네이버 API 검색 실패: {e}")
            return []
    
    def extract_article_content(self, url: str, max_retries: int = 2) -> Dict[str, Optional[str]]:
        """
        개별 뉴스 기사에서 제목, 본문, 언론사, 날짜 추출
        
        Args:
            url: 기사 URL
            max_retries: 최대 재시도 횟수
        
        Returns:
            제목, 본문, 언론사, 날짜가 포함된 딕셔너리
        """
        for attempt in range(max_retries + 1):
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                response.encoding = 'utf-8'
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 제목 추출
                title = self._extract_title(soup)
                
                # 본문 추출
                content = self._extract_content(soup)
                
                # 제목 없을 때 본문 첫줄을 제목으로 사용
                if (not title or not title.strip()) and content:
                    first_line = content.split('\n')[0].strip()
                    if first_line and len(first_line) > 10:
                        title = first_line[:80] + ('...' if len(first_line) > 80 else '')
                
                # 언론사 추출
                source = self._extract_source(soup, url)
                
                # 날짜 추출
                pub_date = self._extract_date(soup)
                
                return {
                    "title": title,
                    "content": content,
                    "source": source,
                    "url": url,
                    "pubDate": pub_date
                }
                
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    logger.warning(f"타임아웃 발생, 재시도 중... ({attempt + 1}/{max_retries})")
                    time.sleep(1)
                    continue
                logger.error(f"기사 크롤링 타임아웃 ({url})")
            except requests.exceptions.RequestException as e:
                logger.error(f"기사 크롤링 실패 ({url}): {e}")
            except Exception as e:
                logger.error(f"기사 크롤링 중 예상치 못한 오류 ({url}): {e}")
        
        return {
            "title": None,
            "content": None,
            "source": None,
            "url": url,
            "pubDate": None
        }
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """제목 추출 (og:title → DOM 셀렉터 → 본문 첫줄 fallback)"""
        # 1) og:title 메타 태그 (네이버 뉴스 등에서 보통 포함)
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title and og_title.get('content'):
            t = og_title.get('content', '').strip()
            if t and len(t) > 3:
                return t
        
        # 2) DOM 셀렉터
        title_selectors = [
            '#title_area h2',
            '.media_end_head_headline h2',
            '#articleTitle',
            '.newsct_article h2',
            'h1.title',
            'h1'
        ]
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) > 5:
                    return title
        
        return None
    
    def _extract_content(self, soup: BeautifulSoup) -> Optional[str]:
        """본문 추출 (여러 선택자로 시도)"""
        content_selectors = [
            '#dic_area',                    # 네이버 뉴스 최신
            '#articleBodyContents',         # 일반 네이버 뉴스
            '.newsct_article ._article_body_contents',
            '._article_body_contents',
            '#newsEndContents',             # 스포츠 뉴스
            '#articeBody',                  # 기타 형식
            '.se_component_wrap',
            '.article_body',
            '#article_body',
            'article',
            '.article_view'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # 불필요한 요소 제거
                for unwanted in element.select('script, style, .ad, .advertisement, .related, .comment, .byline, .reporter_area, .copyright, figure, figcaption'):
                    unwanted.decompose()
                
                # 본문 텍스트 추출
                text = element.get_text(separator='\n', strip=True)
                
                # 텍스트 정리
                text = '\n'.join(line.strip() for line in text.split('\n') if line.strip())
                
                if text and len(text) > 100:  # 최소 100자
                    return text
        
        return None
    
    def _extract_source(self, soup: BeautifulSoup, url: str) -> Optional[str]:
        """언론사명 추출"""
        # 메타 태그에서 추출 시도
        source_selectors = [
            ('meta[property="og:site_name"]', 'content'),
            ('meta[name="publisher"]', 'content'),
            ('meta[property="article:author"]', 'content'),
        ]
        
        for selector, attr in source_selectors:
            element = soup.select_one(selector)
            if element and element.get(attr):
                return element.get(attr)
        
        # URL에서 도메인 기반 추출
        for domain, name in {**DOMAIN_TO_SOURCE, "segyebac.com": "세계일보", "kmib.co.kr": "국민일보"}.items():
            if domain in url:
                return name
        
        # 네이버 뉴스 URL에서 미디어 코드로 언론사 추출
        if "n.news.naver.com" in url or "news.naver.com" in url:
            match = re.search(r"/article/(\d{3})/", url)
            if match:
                code = match.group(1)
                return NAVER_MEDIA_CODE_TO_SOURCE.get(code)
        
        return None
    
    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        """발행일 추출"""
        date_selectors = [
            ('meta[property="article:published_time"]', 'content'),
            ('meta[name="publish_date"]', 'content'),
            ('meta[property="og:published_time"]', 'content'),
            ('.media_end_head_info_datestamp em', None),
            ('.times', None),
        ]
        
        for selector, attr in date_selectors:
            if attr:
                element = soup.select_one(selector)
                if element and element.get(attr):
                    date_str = element.get(attr)
                    # ISO 형식에서 날짜만 추출 (예: 2024-01-01T12:00:00 -> 2024-01-01)
                    if 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    return date_str
            else:
                element = soup.select_one(selector)
                if element and element.get_text():
                    return element.get_text().strip()
        
        # 날짜를 찾지 못한 경우 None 반환 (현재 날짜로 대체하는 것은 부정확)
        return None
    
    def _get_source_from_url(self, url: str) -> Optional[str]:
        """URL만으로 소스 추정 (크롤링 전 사전 판단용)"""
        url_lower = url.lower()
        for domain, name in DOMAIN_TO_SOURCE.items():
            if domain in url_lower:
                return name
        if "n.news.naver.com" in url_lower or "news.naver.com" in url_lower:
            match = re.search(r"/article/(\d{3})/", url)
            if match:
                return NAVER_MEDIA_CODE_TO_SOURCE.get(match.group(1))
        return None
    
    def _is_allowed_source(self, url: str, source: Optional[str] = None) -> bool:
        """
        주요 언론사인지 확인
        - URL 도메인으로 판단 (직접 링크인 경우)
        - source(언론사명)로 판단 (네이버 뉴스 등 집계 사이트에서 가져온 경우)
        """
        url_lower = url.lower()
        # 1) URL 도메인 체크
        for domain in ALLOWED_NEWS_DOMAINS:
            if domain in url_lower:
                return True
        # 2) 네이버 뉴스(n.news.naver.com)는 크롤링 후 source로 판단
        if "n.news.naver.com" in url_lower or "news.naver.com" in url_lower:
            if source and any(s in source for s in ALLOWED_NEWS_SOURCES):
                return True
            return False  # source 없거나 허용 목록에 없으면 제외
        # 3) 언론사명으로 체크 (다른 집계 사이트 등)
        if source and any(s in source for s in ALLOWED_NEWS_SOURCES):
            return True
        return False
    
    def _is_excluded_domain(self, url: str) -> bool:
        """블랙리스트 도메인 여부 (뷰티, 광고 등 비정치 사이트)"""
        url_lower = url.lower()
        return any(excl in url_lower for excl in EXCLUDED_DOMAINS)

    def _is_political_content(self, title: str, content: str, min_keywords: int = 2) -> bool:
        """제목+본문에 정치 관련 키워드가 최소 N개 이상 있는지"""
        text = (title or "") + " " + (content or "")
        count = sum(1 for kw in POLITICS_KEYWORDS if kw in text)
        return count >= min_keywords

    def _should_crawl_url(self, url: str) -> bool:
        """크롤링할 URL인지 사전 필터 (불필요한 요청 절약)"""
        if self._is_excluded_domain(url):
            return False
        url_lower = url.lower()
        for domain in ALLOWED_NEWS_DOMAINS:
            if domain in url_lower:
                return True
        if "n.news.naver.com" in url_lower or "news.naver.com" in url_lower:
            return True  # 네이버 뉴스는 source로 나중에 필터
        return False
    
    def crawl_politics_news(
        self,
        keyword: str = "정치",
        max_articles: int = 50,
        allowed_sources_only: bool = True,
        filter_political_content: bool = True,
        balanced_crawl: bool = False,
    ) -> List[Dict]:
        """
        정치 뉴스 크롤링 (제목, 본문, 언론사, 주소, 날짜)
        
        Args:
            keyword: 검색 키워드
            max_articles: 최대 크롤링 기사 수
            allowed_sources_only: True면 주요 언론사만 수집
            balanced_crawl: True면 진보/중도/보수 언론사 11곳에서 균형 수집
        """
        target_sources = BALANCED_SOURCES if balanced_crawl else ALLOWED_NEWS_SOURCES
        if balanced_crawl:
            logger.info(f"'{keyword}' 균형 크롤링 시작... (최대 {max_articles}개, 언론사 {len(BALANCED_SOURCES)}곳)")
        else:
            logger.info(f"'{keyword}' 정치 뉴스 크롤링 시작... (최대 {max_articles}개, 주요 언론사만: {allowed_sources_only})")
        
        # 전체 언론사(all_sources) 모드: 언론사별 쿼터로 다양한 소스 확보하려면 더 많은 API 결과 필요
        search_limit = (
            max_articles * 8 if balanced_crawl
            else (max_articles * 10 if not allowed_sources_only else max_articles * 6)
        )
        # 전체 언론사 모드: 언론사별 쿼터 부여해 SBS/KBS 편중 방지 (이슈당 각 언론사 1~2개씩 수집)
        if balanced_crawl:
            max_per_source = max(2, (max_articles + len(BALANCED_SOURCES) - 1) // len(BALANCED_SOURCES))
        elif not allowed_sources_only:
            max_per_source = 2  # 이슈당 언론사별 최대 2개 → 다양한 언론사 확보
        else:
            max_per_source = 9999
        
        all_search_results = []
        display = min(100, search_limit)
        start = 1
        
        while len(all_search_results) < search_limit:
            remaining = search_limit - len(all_search_results)
            current_display = min(display, remaining, 100)
            search_results = self.search_naver_news(keyword=keyword, display=current_display, start=start)
            if not search_results:
                break
            all_search_results.extend(search_results)
            if len(search_results) < current_display or len(all_search_results) >= search_limit:
                break
            start += current_display
            if start > 1000:
                break
        
        articles = []
        seen_urls = set()
        source_count = {}
        failed_count = 0
        skipped_source = 0
        processed = 0
        
        for i, item in enumerate(all_search_results):
            if len(articles) >= max_articles:
                break
            url = item.get("link")
            if not url or url in seen_urls:
                continue
            if self._is_excluded_domain(url):
                skipped_source += 1
                continue
            
            # 균형/언론사다양화: URL로 소스 추정 후 허용·쿼터 확인
            estimated_source = self._get_source_from_url(url)
            if balanced_crawl:
                if not estimated_source or estimated_source not in BALANCED_SOURCES:
                    skipped_source += 1
                    continue
                if source_count.get(estimated_source, 0) >= max_per_source:
                    skipped_source += 1
                    continue
            elif not allowed_sources_only:
                # 전체 언론사 모드: 언론사별 쿼터로 SBS/KBS 편중 방지 (미인증 소스는 5개까지)
                cap = max_per_source if estimated_source in ALLOWED_NEWS_SOURCES else 5
                if estimated_source and source_count.get(estimated_source, 0) >= cap:
                    skipped_source += 1
                    continue
            elif allowed_sources_only and not self._should_crawl_url(url):
                skipped_source += 1
                continue
            
            seen_urls.add(url)
            processed += 1
            
            logger.info(f"크롤링 중... ({len(articles)+1}/{max_articles}) [{estimated_source or '?'}] {url[:50]}...")
            article_data = self.extract_article_content(url)
            
            if not article_data.get("content"):
                failed_count += 1
                continue
            if not article_data.get("title") or not str(article_data.get("title", "")).strip():
                api_title = item.get("title")
                if api_title and len(api_title.strip()) > 3:
                    article_data["title"] = api_title.replace("<b>", "").replace("</b>", "").strip()
            
            actual_source = article_data.get("source") or estimated_source
            if balanced_crawl:
                if actual_source not in BALANCED_SOURCES:
                    skipped_source += 1
                    continue
                if source_count.get(actual_source, 0) >= max_per_source:
                    skipped_source += 1
                    continue
            elif not allowed_sources_only:
                # 전체 언론사 모드: 크롤링 후에도 쿼터 확인 (소스 불일치 대비)
                cap = max_per_source if actual_source in ALLOWED_NEWS_SOURCES else 5
                if actual_source and source_count.get(actual_source, 0) >= cap:
                    skipped_source += 1
                    continue
            elif allowed_sources_only and actual_source not in ALLOWED_NEWS_SOURCES:
                skipped_source += 1
                continue
            
            if filter_political_content and not self._is_political_content(
                article_data.get("title") or "", article_data.get("content") or ""
            ):
                skipped_source += 1
                continue
            
            articles.append(article_data)
            source_count[actual_source] = source_count.get(actual_source, 0) + 1
            article_data["media_stance"] = next(
                (s for s, names in MEDIA_BY_STANCE.items() if actual_source in names),
                None
            )
            time.sleep(0.5)
        
        if source_count:
            logger.info(f"언론사별: " + ", ".join(f"{s} {c}개" for s, c in sorted(source_count.items(), key=lambda x: -x[1])))
        logger.info(f"크롤링 완료: {len(articles)}개 (실패: {failed_count}, 제외: {skipped_source})")
        return articles

    def fetch_article_links_from_outlet(
        self, outlet_name: str, max_articles: Optional[int] = None
    ) -> List[str]:
        """
        언론사 정치면 목록 페이지에서 기사 URL 목록만 추출 (본문 크롤링 없음).
        
        Args:
            outlet_name: OUTLET_POLITICS 키 (예: "한겨레", "조선일보", "한국일보")
            max_articles: 최대 URL 개수 (None이면 설정값 사용)
        
        Returns:
            기사 URL 리스트 (절대 URL, 중복 제거, max_articles 이하)
        """
        if outlet_name not in OUTLET_POLITICS:
            logger.warning(f"미등록 언론사: {outlet_name}")
            return []
        conf = OUTLET_POLITICS[outlet_name]
        list_url = conf["list_url"]
        link_selector = conf["link_selector"]
        limit = max_articles if max_articles is not None else conf.get("max_articles", 25)
        try:
            resp = self.session.get(list_url, timeout=15)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
        except Exception as e:
            logger.error(f"목록 페이지 요청 실패 [{outlet_name}] {list_url}: {e}")
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
        logger.info(f"[{outlet_name}] 목록에서 기사 URL {len(urls)}개 추출")
        return urls

    def crawl_politics_from_outlets(
        self,
        outlet_names: List[str],
        max_per_outlet: int = 25,
        filter_political_content: bool = True,
    ) -> List[Dict]:
        """
        지정한 언론사 정치면에서 직접 기사 수집 (목록 → 본문).
        
        Args:
            outlet_names: 언론사 이름 리스트 (예: ["한겨레", "조선일보", "한국일보"])
            max_per_outlet: 언론사당 최대 기사 수
            filter_political_content: True면 정치 관련성 필터 적용
        
        Returns:
            기사 딕셔너리 리스트 (crawl_politics_news와 동일 형식)
        """
        all_articles = []
        seen_urls = set()
        for outlet in outlet_names:
            if outlet not in OUTLET_POLITICS:
                logger.warning(f"건너뜀(미등록): {outlet}")
                continue
            urls = self.fetch_article_links_from_outlet(outlet, max_articles=max_per_outlet)
            for url in urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                logger.info(f"크롤링 중... [{outlet}] {url[:60]}...")
                data = self.extract_article_content(url)
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
        logger.info(f"언론사 정치면 크롤링 완료: 총 {len(all_articles)}개")
        return all_articles

    def save_to_json(self, articles: List[Dict], filename: str = "politics_news.json"):
        """크롤링 결과를 JSON 파일로 저장"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            logger.info(f"결과 저장 완료: {filename}")
        except Exception as e:
            logger.error(f"JSON 저장 실패 ({filename}): {e}")
            raise
    
    def save_to_jsonl(self, articles: List[Dict], filename: str = "politics_news.jsonl"):
        """크롤링 결과를 JSONL 파일로 저장 (각 줄에 하나의 JSON 객체)"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for article in articles:
                    # 각 기사를 한 줄의 JSON으로 저장
                    json_line = json.dumps(article, ensure_ascii=False)
                    f.write(json_line + '\n')
            logger.info(f"결과 저장 완료: {filename} ({len(articles)}개 기사)")
        except Exception as e:
            logger.error(f"JSONL 저장 실패 ({filename}): {e}")
            raise


# 사용 예제
if __name__ == "__main__":
    # .env 또는 환경 변수에서 API 키 로드
    NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "your_client_id")
    NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "your_client_secret")
    
    if NAVER_CLIENT_ID == "your_client_id" or not NAVER_CLIENT_ID:
        print("❌ .env 파일에 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET을 설정해주세요.")
        exit(1)
    
    # 크롤러 초기화
    crawler = PoliticsNewsCrawler(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)
    
    # (선택) 언론사 정치면 직접 크롤링: 아래 두 줄 사용 시 3개 언론사에서 수집
    # articles = crawler.crawl_politics_from_outlets(["한겨레", "조선일보", "한국일보"], max_per_outlet=15)
    # crawler.save_to_jsonl(articles, "data/1_crawled/outlet_news.jsonl")
    
    # 정치 뉴스 크롤링 (네이버 API, 주요 언론사만 수집)
    articles = crawler.crawl_politics_news(keyword="정치", max_articles=50, allowed_sources_only=True)
    
    # 결과 저장
    crawler.save_to_json(articles, "politics_news.json")
    crawler.save_to_jsonl(articles, "politics_news.jsonl")
    
    # 결과 출력
    if articles:
        print(f"\n총 {len(articles)}개 기사 수집 완료\n")
        for i, article in enumerate(articles[:3], 1):
            print(f"\n{'='*80}")
            print(f"[{i}] 제목: {article.get('title', 'N/A')}")
            print(f"언론사: {article.get('source', 'N/A')}")
            print(f"날짜: {article.get('pubDate', 'N/A')}")
            print(f"주소: {article.get('url', 'N/A')}")
            content = article.get('content', '')
            if content:
                print(f"본문: {content[:200]}...")
            else:
                print("본문: 없음")
    else:
        print("수집된 기사가 없습니다.")