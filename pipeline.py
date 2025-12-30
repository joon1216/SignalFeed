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
from modules.crawler import crawl_political_news
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


def step1_crawling(keywords, max_per_keyword=100):
    """
    Step 1: 크롤링
    
    Args:
        keywords: 검색 키워드 리스트
        max_per_keyword: 키워드당 최대 기사 수
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("1️⃣ 크롤링 단계")
    print("="*70)
    
    # 환경 변수에서 API 키 읽기
    client_id = os.getenv('NAVER_CLIENT_ID')
    client_secret = os.getenv('NAVER_CLIENT_SECRET')
    
    output_file = 'data/1_crawled/news.jsonl'
    crawl_political_news(keywords, max_per_keyword, output_file, client_id, client_secret)
    
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


def step3_classification(input_file, model_dir, device='cuda', batch_size=32):
    """
    Step 3: 정치 성향 분류
    
    Args:
        input_file: 클러스터링 결과 파일
        model_dir: 모델 디렉토리
        device: 디바이스 ('cuda' 또는 'cpu')
        batch_size: 배치 크기
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("3️⃣ 정치 성향 분류 단계")
    print("="*70)
    
    # 입력 파일 확인
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")
    
    # 분류기 초기화
    classifier = PoliticalClassifier(
        model_dir=model_dir,
        device=device
    )
    
    # JSONL 로드
    articles = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            articles.append(json.loads(line))
    
    print(f"📰 {len(articles)}개 기사 로드")
    
    # 분류 실행
    output_file = 'data/3_classified/classified.jsonl'
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
        default=['국회 정치', '대통령 정책', '여야 협상'],
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
            crawled_file = step1_crawling(args.keywords, args.max_articles)
            print(f"\\n✅ Step 1 완료: {crawled_file}")
        
        if '2' in steps:
            clustered_file = step2_clustering(crawled_file)
            print(f"\\n✅ Step 2 완료: {clustered_file}")
        
        if '3' in steps:
            classified_file = step3_classification(
                clustered_file,
                args.model_dir,
                args.device,
                args.batch_size
            )
            print(f"\\n✅ Step 3 완료: {classified_file}")
        
        if '4' in steps:
            summarized_file = step4_summarization(
                classified_file,
                args.ollama_model
            )
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
