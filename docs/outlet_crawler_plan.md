# 언론사 정치면 직접 크롤러 계획

## 목적

- **최신 기사 확보**: 각 언론사 정치 섹션 목록에서 수집해 키워드 검색 의존을 줄인다.
- **이슈당 기사 수 자연 제한**: 한 이슈에 대해 언론사당 1~2편 수준으로 수집된다.
- **타깃만 수집**: 지정한 언론사 목록만 돌리므로 마이너 언론사 요청이 없다.

## 1단계: 3개 언론사 시범 (현재 구현 대상)

| 구분 | 언론사 | 정치 섹션 URL |
|------|--------|----------------|
| 진보 | 한겨레 | `https://www.hani.co.kr/arti/politics.html` |
| 중도 | 한국일보 | `https://www.hankookilbo.com/News/Politics` (실제 URL은 사이트 확인) |
| 보수 | 조선일보 | `https://www.chosun.com/politics/` |

- 목록 페이지에서 **기사 링크만 추출** → 기존 `extract_article_content(url)`로 본문 수집.
- 사이트당 **최신 N개** 상한 (예: 20~30개).

## 구현 구성

1. **설정**  
   - 언론사별 `list_url`, 목록에서 기사 링크를 찾는 **CSS 선택자** (또는 `href` 패턴), `max_articles`.

2. **목록 수집**  
   - `fetch_article_links_from_outlet(outlet_name)`  
   - 목록 URL 요청 → 선택자로 `<a href="...">` 수집 → 절대 URL 정규화, 중복 제거, `max_articles`만 반환.

3. **본문 수집**  
   - `crawl_politics_from_outlets(outlet_names, max_per_outlet)`  
   - 각 언론사에 대해 `fetch_article_links_from_outlet` 호출 후, URL마다 기존 `extract_article_content(url)` 호출.  
   - 반환 형식은 기존 `crawl_politics_news`와 동일 (제목, 본문, url, source, pubDate 등).

4. **본문 추출 실패 시**  
   - 해당 언론사 직링크용 제목/본문 선택자를 `_extract_title`, `_extract_content`에 언론사별 분기 또는 추가 선택자로 보강.

## 파일 배치

- **설정·목록·진입점**: `modules/clawler_ver2.py`에 상수 `OUTLET_POLITICS`와 메서드 `fetch_article_links_from_outlet`, `crawl_politics_from_outlets` 추가.
- 본문 추출은 기존 `PoliticsNewsCrawler.extract_article_content` 재사용.

## 테스트 순서

1. 한 곳(예: 조선일보)만 설정하고 `fetch_article_links_from_outlet`으로 URL 10개 정도 나오는지 확인.
2. 해당 URL로 `extract_article_content` 호출 시 제목·본문 추출 여부 확인.
3. 나머지 두 곳 설정 추가 후 동일 확인.
4. `crawl_politics_from_outlets(["한겨레","조선일보","한국일보"], max_per_outlet=15)` 실행 후 JSONL 저장으로 파이프라인 연동 확인.

## 사용 예시

```python
from modules.clawler_ver2 import PoliticsNewsCrawler, OUTLET_POLITICS
import os
from dotenv import load_dotenv
load_dotenv()

crawler = PoliticsNewsCrawler(
    os.getenv("NAVER_CLIENT_ID"),
    os.getenv("NAVER_CLIENT_SECRET"),
)
articles = crawler.crawl_politics_from_outlets(
    ["한겨레", "조선일보", "한국일보"],
    max_per_outlet=15,
)
crawler.save_to_jsonl(articles, "data/1_crawled/outlet_news.jsonl")
```

목록만 확인: `urls = crawler.fetch_article_links_from_outlet("조선일보", max_articles=10)`

## 추후 확장 (11곳)

- `OUTLET_POLITICS`에 진보·중도·보수 11곳의 `list_url`·선택자·`max_articles` 추가.
- 파이프라인에 “정치면 크롤링 모드” 옵션 추가 시, 이 경로로 URL 수집 후 동일 본문/클러스터 파이프라인 사용.
