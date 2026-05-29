"""
네이버 뉴스 크롤러
URL과 썸네일을 포함한 뉴스 데이터 수집
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from urllib.parse import quote
from tqdm.auto import tqdm


class NaverNewsCrawler:
    """네이버 뉴스 크롤러"""
    
    def __init__(self, client_id=None, client_secret=None):
        """
        Args:
            client_id: 네이버 API Client ID (선택)
            client_secret: 네이버 API Client Secret (선택)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.use_api = client_id and client_secret
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        if self.use_api:
            self.api_headers = {
                'X-Naver-Client-Id': client_id,
                'X-Naver-Client-Secret': client_secret
            }
    
    def search_news_api(self, query, display=100, start=1, sort='date'):
        """
        네이버 검색 API를 사용한 뉴스 검색
        
        Args:
            query: 검색 키워드
            display: 한 번에 가져올 뉴스 수 (최대 100)
            start: 검색 시작 위치
            sort: 정렬 방식 ('date' or 'sim')
        
        Returns:
            list: 뉴스 목록
        """
        if not self.use_api:
            print("⚠️ API 키가 설정되지 않았습니다. 웹 크롤링을 사용하세요.")
            return []
        
        url = "https://openapi.naver.com/v1/search/news.json"
        params = {
            'query': query,
            'display': display,
            'start': start,
            'sort': sort
        }
        
        try:
            response = requests.get(url, headers=self.api_headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for item in data.get('items', []):
                article = {
                    'title': self._clean_html(item['title']),
                    'content': self._clean_html(item['description']),
                    'url': item['link'],
                    'published_at': item['pubDate'],
                    'thumbnail': None  # API는 썸네일 제공 안 함
                }
                articles.append(article)
            
            return articles
            
        except Exception as e:
            print(f"❌ API 검색 실패: {str(e)}")
            return []
    
    def search_news_web(self, query, max_articles=100):
        """
        웹 크롤링을 통한 뉴스 검색 (URL + 썸네일 포함)
        
        Args:
            query: 검색 키워드
            max_articles: 최대 수집 기사 수
        
        Returns:
            list: 뉴스 목록 (url, thumbnail 포함)
        """
        print(f"\n🔍 '{query}' 검색 중...")
        
        articles = []
        page = 1
        
        while len(articles) < max_articles:
            # 네이버 뉴스 검색 URL
            start = (page - 1) * 10 + 1
            search_url = f"https://search.naver.com/search.naver?where=news&query={quote(query)}&start={start}"
            
            try:
                response = requests.get(search_url, headers=self.headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 뉴스 목록 추출
                news_items = soup.select('div.news_area')
                
                if not news_items:
                    print(f"   페이지 {page}: 더 이상 뉴스가 없습니다.")
                    break
                
                for item in news_items:
                    if len(articles) >= max_articles:
                        break
                    
                    try:
                        # 제목 및 링크
                        title_elem = item.select_one('a.news_tit')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        url = title_elem['href']
                        
                        # 내용
                        content_elem = item.select_one('div.news_dsc')
                        content = content_elem.get_text(strip=True) if content_elem else ""
                        
                        # 썸네일
                        thumbnail = None
                        img_elem = item.select_one('a.dsc_thumb img')
                        if img_elem and img_elem.get('src'):
                            thumbnail = img_elem['src']
                        
                        # 날짜
                        date_elem = item.select_one('span.info')
                        published_at = date_elem.get_text(strip=True) if date_elem else ""
                        
                        article = {
                            'title': title,
                            'content': content,
                            'url': url,
                            'thumbnail': thumbnail,
                            'published_at': published_at
                        }
                        
                        articles.append(article)
                        
                    except Exception as e:
                        continue
                
                print(f"   페이지 {page}: {len(news_items)}개 수집 (총 {len(articles)}개)")
                page += 1
                time.sleep(0.5)  # 요청 간격
                
            except Exception as e:
                print(f"❌ 페이지 {page} 크롤링 실패: {str(e)}")
                break
        
        print(f"✅ 총 {len(articles)}개 기사 수집 완료\n")
        return articles
    
    def get_article_detail(self, url):
        """
        특정 기사의 상세 정보 가져오기 (본문 전체 + 썸네일)
        
        Args:
            url: 기사 URL
        
        Returns:
            dict: 상세 기사 정보
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 본문 추출 (네이버 뉴스)
            article_body = soup.select_one('article#dic_area') or soup.select_one('div#articleBodyContents')
            
            if article_body:
                # 불필요한 태그 제거
                for tag in article_body.select('script, style, iframe'):
                    tag.decompose()
                
                content = article_body.get_text(strip=True)
            else:
                content = None
            
            # 썸네일 추출
            thumbnail = None
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image and og_image.get('content'):
                thumbnail = og_image['content']
            
            return {
                'content': content,
                'thumbnail': thumbnail
            }
            
        except Exception as e:
            print(f"⚠️ 기사 상세 가져오기 실패: {str(e)}")
            return None
    
    def _clean_html(self, text):
        """HTML 태그 제거"""
        if not text:
            return ""
        text = text.replace('<b>', '').replace('</b>', '')
        text = text.replace('&quot;', '"').replace('&apos;', "'")
        text = text.replace('&lt;', '<').replace('&gt;', '>')
        return text
    
    def save_to_jsonl(self, articles, output_file):
        """
        기사 목록을 JSONL 파일로 저장
        
        Args:
            articles: 기사 목록
            output_file: 출력 파일 경로
        """
        print(f"\n💾 {output_file}에 저장 중...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')
        
        print(f"✅ {len(articles)}개 기사 저장 완료!")


def crawl_political_news(keywords, max_per_keyword=100, output_file='data/crawled_news.jsonl', client_id=None, client_secret=None):
    """
    정치 뉴스 크롤링 (URL + 썸네일 포함)
    
    Args:
        keywords: 검색 키워드 리스트
        max_per_keyword: 키워드당 최대 수집 기사 수
        output_file: 출력 파일 경로
        client_id: 네이버 API Client ID (선택)
        client_secret: 네이버 API Client Secret (선택)
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("🗞️ 정치 뉴스 크롤링 시작")
    print("="*70)
    
    crawler = NaverNewsCrawler(client_id=client_id, client_secret=client_secret)
    all_articles = []
    
    # API 사용 가능 여부 확인
    use_api = crawler.use_api
    if use_api:
        print("✅ 네이버 검색 API 사용")
    else:
        print("⚠️ API 키가 없어 웹 크롤링을 시도합니다 (네이버 페이지 구조 변경으로 실패할 수 있음)")
        print("💡 안정적인 크롤링을 위해 네이버 검색 API 키 사용을 권장합니다")
    
    for keyword in tqdm(keywords, desc="키워드 처리"):
        if use_api:
            # API 사용
            articles = []
            start = 1
            while len(articles) < max_per_keyword:
                api_articles = crawler.search_news_api(keyword, display=100, start=start, sort='date')
                if not api_articles:
                    break
                articles.extend(api_articles)
                if len(api_articles) < 100:
                    break
                start += 100
                time.sleep(0.1)  # API 호출 제한 고려
            articles = articles[:max_per_keyword]
        else:
            # 웹 크롤링 사용
            articles = crawler.search_news_web(keyword, max_articles=max_per_keyword)
        
        # 중복 제거 (URL 기준)
        existing_urls = {a['url'] for a in all_articles}
        new_articles = [a for a in articles if a['url'] not in existing_urls]
        
        all_articles.extend(new_articles)
        print(f"   '{keyword}': {len(new_articles)}개 (중복 제외)")
    
    # 저장
    crawler.save_to_jsonl(all_articles, output_file)
    
    print("\n" + "="*70)
    print(f"✅ 크롤링 완료! 총 {len(all_articles)}개 기사")
    print("="*70)
    
    return output_file


if __name__ == "__main__":
    # 테스트용
    keywords = [
        "국회 정치",
        "대통령 정책",
        "여야 협상",
        "법안 처리",
        "정당 갈등"
    ]
    
    output = crawl_political_news(
        keywords=keywords,
        max_per_keyword=50,
        output_file='data/crawled_news.jsonl'
    )
    
    print(f"\n출력 파일: {output}")
