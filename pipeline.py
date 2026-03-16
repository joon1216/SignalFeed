"""
IssueFit 전체 파이프라인
크롤링 → 클러스터링 → 분류 → 요약

각 단계별로 폴더를 생성하여 JSON 파일 저장
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 모듈 임포트
from modules.clawler_ver2 import PoliticsNewsCrawler
from modules.classifier import PoliticalClassifier
from modules.summarizer import PoliticalNewsSummarizer
from modules.clusterer import cluster_news_articles


def create_directories():
    """
    단계별 디렉토리 생성
    
    data/
    ├── 1_crawled/
    ├── 2_clustered/
    ├── 3_classified/
    └── 4_summarized/
    """
    folders = [
        'data/1_crawled',
        'data/2_clustered',
        'data/3_classified',
        'data/4_summarized',
    ]
    
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ {folder}")


def step1_crawling(keywords, max_per_keyword=100, all_sources=False, balanced_crawl=True):
    """
    Step 1: 크롤링 (clawler_ver2 - 진보/중도/보수 11곳 균형 수집)
    
    Args:
        keywords: 검색 키워드 리스트
        max_per_keyword: 키워드당 최대 기사 수
        balanced_crawl: True면 한겨레·경향·오마이·프레시안·한국일보·서울·세계·조선·중앙·동아·국민일보에서 균형 수집
    """
    print("\n" + "="*70)
    mode = "균형(진보/중도/보수 11곳)" if balanced_crawl else ("전체 언론사" if all_sources else "주요 언론사")
    print("1️⃣ 크롤링 단계 (clawler_ver2) - " + mode)
    print("="*70)
    
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise ValueError("NAVER_CLIENT_ID, NAVER_CLIENT_SECRET을 .env에 설정해주세요.")
    
    crawler = PoliticsNewsCrawler(client_id, client_secret)
    all_articles = []
    seen_urls = set()
    use_balanced = balanced_crawl and not all_sources
    
    for keyword in keywords:
        print(f"\n🔍 '{keyword}' 크롤링 중...")
        articles = crawler.crawl_politics_news(
            keyword=keyword,
            max_articles=max_per_keyword,
            allowed_sources_only=not all_sources,
            balanced_crawl=use_balanced,
        )
        for a in articles:
            if a.get("url") and a["url"] not in seen_urls:
                seen_urls.add(a["url"])
                all_articles.append({
                    "title": a.get("title") or "",
                    "content": a.get("content") or "",
                    "url": a.get("url") or "",
                    "published_at": a.get("pubDate") or a.get("published_at", ""),
                    "thumbnail": None,
                    "source": a.get("source"),
                    "media_stance": a.get("media_stance"),
                })
        print(f"   '{keyword}': {len(articles)}개 (중복 제외 후 누적: {len(all_articles)}개)")
    
    # 균형 크롤링에서 0개 또는 100개 미만일 때 폴백: 전체 언론사(all_sources)로 확대
    target_total = 100
    if use_balanced and len(all_articles) == 0:
        print("\n⚠️ 균형 크롤링(11개 언론사)에서 기사 0건 → 전체 언론사 방식으로 폴백")
        seen_urls.clear()
        all_articles.clear()
        use_balanced = False
        all_sources = True
    elif len(all_articles) < target_total and not all_sources:
        print(f"\n⚠️ 수집량 {len(all_articles)}개 < 목표 {target_total}개 → 전체 언론사로 보완 크롤링")
        all_sources = True

    if (use_balanced and len(all_articles) == 0) or (len(all_articles) < target_total and all_sources):
        # 단일 키워드로 검색 폭 확대해 수집량 증대
        fallback_keywords = ['정치', '국회', '대통령', '여야', '정당', '선거', '정책', '법안', '국정감사', '여론조사', '지지율', '국정']
        use_balanced = False
        for keyword in fallback_keywords:
            if len(all_articles) >= target_total:
                break
            remain = target_total - len(all_articles)
            print(f"\n🔍 '{keyword}' 크롤링 (전체 언론사, 목표 {min(max_per_keyword, remain)}개)...")
            articles = crawler.crawl_politics_news(
                keyword=keyword,
                max_articles=min(max_per_keyword, max(remain, 50)),
                allowed_sources_only=False,
                balanced_crawl=False,
            )
            for a in articles:
                if a.get("url") and a["url"] not in seen_urls:
                    seen_urls.add(a["url"])
                    all_articles.append({
                        "title": a.get("title") or "",
                        "content": a.get("content") or "",
                        "url": a.get("url") or "",
                        "published_at": a.get("pubDate") or a.get("published_at", ""),
                        "thumbnail": None,
                        "source": a.get("source"),
                        "media_stance": a.get("media_stance"),
                    })
            print(f"   '{keyword}': {len(articles)}개 (누적: {len(all_articles)}개)")
    
    output_file = 'data/1_crawled/news.jsonl'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        for article in all_articles:
            f.write(json.dumps(article, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 크롤링 완료! 총 {len(all_articles)}개 기사 → {output_file}")
    return output_file


def step2_clustering(input_file):
    """
    Step 2: 클러스터링
    
    Args:
        input_file: 크롤링 결과 파일
    
    Returns:
        str: 출력 파일 경로
    """
    # 입력 파일 확인
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")
    
    output_file = 'data/2_clustered/clustered.jsonl'
    
    # 클러스터링 실행
    cluster_news_articles(input_file, output_file)
    
    return output_file


def step3_classification(input_file, model_dir, device='cuda', batch_size=32, mock=False):
    """
    Step 3: 정치 성향 분류
    
    Args:
        input_file: 클러스터링 결과 파일
        model_dir: 모델 디렉토리
        device: 디바이스 ('cuda' 또는 'cpu')
        batch_size: 배치 크기
        mock: True면 모델 없이 neutral로 통과 (테스트용)
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("3️⃣ 정치 성향 분류 단계" + (" [Mock]" if mock else ""))
    print("="*70)
    
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")
    
    output_file = 'data/3_classified/classified.jsonl'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    if mock:
        articles = []
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    articles.append(json.loads(line))
        with open(output_file, 'w', encoding='utf-8') as f:
            for a in articles:
                a['political_stance'] = 'neutral'
                a['stance_confidence'] = 0.5
                f.write(json.dumps(a, ensure_ascii=False) + '\n')
        print(f"📰 {len(articles)}개 기사 Mock 분류 (neutral) 완료")
        return output_file
    
    classifier = PoliticalClassifier(model_dir=model_dir, device=device)
    classifier.classify_jsonl(input_file, output_file, batch_size=batch_size)
    return output_file


def step4_summarization(input_file, model_name=None):
    """
    Step 4: 다관점 요약
    
    Args:
        input_file: 분류 결과 파일
        model_name: Ollama 모델 이름
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("4️⃣ 다관점 요약 단계")
    print("="*70)
    
    # 입력 파일 확인
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")
    
    # 모델 이름 설정 (기본값 또는 환경 변수)
    if model_name is None:
        model_name = os.getenv('OLLAMA_MODEL', 'gemma2:2b')
    
    # 요약 생성기 초기화
    summarizer = PoliticalNewsSummarizer(model_name=model_name)
    
    # 요약 실행
    output_file = 'data/4_summarized/summaries.json'
    summarizer.summarize_all(input_file, output_file)
    
    return output_file


def main():
    """메인 함수"""
    
    parser = argparse.ArgumentParser(description='IssueFit 파이프라인')
    
    # 실행 단계 선택
    parser.add_argument(
        '--steps',
        type=str,
        default='1,2,3,4',
        help='실행할 단계 (쉼표로 구분, 예: 1,2,3,4 또는 all)'
    )
    
    # 크롤링 옵션
    parser.add_argument(
        '--keywords',
        nargs='+',
        default=['정치', '국회', '대통령', '여야', '정당', '선거', '정책', '법안', '국정감사', '여론조사'],
        help='크롤링 키워드'
    )
    parser.add_argument(
        '--max-articles',
        type=int,
        default=100,
        help='키워드당 최대 기사 수'
    )
    
    # 분류 옵션
    parser.add_argument(
        '--model-dir',
        type=str,
        default='models/political_classifier',
        help='분류 모델 디렉토리'
    )
    parser.add_argument(
        '--device',
        type=str,
        default='cuda',
        help='디바이스 (cuda 또는 cpu)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='분류 배치 크기'
    )
    
    # 요약 옵션
    parser.add_argument(
        '--ollama-model',
        type=str,
        default=None,
        help='Ollama 모델 이름 (기본값: .env 파일 또는 gemma2:2b)'
    )
    parser.add_argument(
        '--mock-classify',
        action='store_true',
        help='분류 모델 없이 neutral로 통과 (테스트용)'
    )
    parser.add_argument(
        '--skip-summarize',
        action='store_true',
        help='요약 단계 건너뛰기 (Ollama 없을 때)'
    )
    parser.add_argument(
        '--all-sources',
        action='store_true',
        help='주요 언론사 필터 없이 전체 수집 (균형 크롤링 비활성화)'
    )
    parser.add_argument(
        '--no-balanced',
        action='store_true',
        help='균형 크롤링 비활성화 (기존 주요 언론사 방식)'
    )
    
    args = parser.parse_args()
    
    # 디렉토리 생성
    print("\\n📁 디렉토리 생성")
    create_directories()
    
    # 실행할 단계 파싱
    if args.steps == 'all':
        steps = ['1', '2', '3', '4']
    else:
        steps = args.steps.split(',')
    
    print(f"\\n🚀 실행 단계: {', '.join(steps)}")
    
    # 파일 경로 추적
    crawled_file = 'data/1_crawled/news.jsonl'
    clustered_file = 'data/2_clustered/clustered.jsonl'
    classified_file = 'data/3_classified/classified.jsonl'
    summarized_file = 'data/4_summarized/summaries.json'
    
    # 단계별 실행
    try:
        if '1' in steps:
            crawled_file = step1_crawling(
                args.keywords, args.max_articles,
                all_sources=args.all_sources,
                balanced_crawl=not args.all_sources and not args.no_balanced
            )
            print(f"\\n✅ Step 1 완료: {crawled_file}")
        
        if '2' in steps:
            clustered_file = step2_clustering(crawled_file)
            print(f"\\n✅ Step 2 완료: {clustered_file}")
        
        if '3' in steps:
            classified_file = step3_classification(
                clustered_file,
                args.model_dir,
                args.device,
                args.batch_size,
                mock=args.mock_classify
            )
            print(f"\\n✅ Step 3 완료: {classified_file}")
        
        if '4' in steps:
            if args.skip_summarize:
                # 요약 건너뛰기: 플레이스홀더 summaries.json 생성
                from collections import defaultdict
                clusters = defaultdict(lambda: {'article_count': 0, 'cluster_label': ''})
                with open(classified_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            a = json.loads(line)
                            cid = a.get('cluster_id', -1)
                            if cid >= 0:
                                clusters[cid]['article_count'] += 1
                                clusters[cid]['cluster_label'] = a.get('cluster_label', '')
                summaries = {str(cid): {'cluster_label': info['cluster_label'], 'article_count': info['article_count'], 'summaries': {'progressive': None, 'conservative': None, 'neutral': '(요약 생략)', 'overall': None}} for cid, info in clusters.items()}
                os.makedirs(os.path.dirname(summarized_file), exist_ok=True)
                with open(summarized_file, 'w', encoding='utf-8') as f:
                    json.dump(summaries, f, ensure_ascii=False, indent=2)
                print(f"\\n✅ Step 4 건너뜀 (플레이스홀더 생성): {summarized_file}")
            else:
                summarized_file = step4_summarization(classified_file, args.ollama_model)
                print(f"\\n✅ Step 4 완료: {summarized_file}")
        
        # 최종 결과
        print("\\n" + "="*70)
        print("🎉 파이프라인 완료!")
        print("="*70)
        print("\\n📁 생성된 파일:")
        if '1' in steps:
            print(f"   1️⃣ {crawled_file}")
        if '2' in steps:
            print(f"   2️⃣ {clustered_file}")
        if '3' in steps:
            print(f"   3️⃣ {classified_file}")
        if '4' in steps:
            print(f"   4️⃣ {summarized_file}")
        
        print("\\n🎨 UI 실행:")
        print("   streamlit run app.py")
        
    except Exception as e:
        print(f"\\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
