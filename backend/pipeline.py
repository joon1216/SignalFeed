"""
SignalFeed 전체 파이프라인
수집 → 필터 → 클러스터링 → EXAONE CoT 생성 → 카드 생성

각 단계별로 폴더를 생성하여 JSONL/JSON 파일 저장
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트를 sys.path에 추가 (backend에서 실행될 때)
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# .env 파일 로드
load_dotenv()

# 모듈 임포트
from backend.modules.collector import NewsCollector
from backend.modules.clusterer import cluster_news_articles
from backend.modules.content_gen import ContentGenerator
from backend.modules.html_card_gen import HTMLCardGenerator


def create_directories():
    """
    단계별 디렉토리 생성

    data/
    ├── 1_collected/
    ├── 2_clustered/
    ├── 3_generated/
    └── 4_cards/
    """
    folders = [
        'data/1_collected',
        'data/2_clustered',
        'data/3_generated',
        'data/4_cards',
        'data/temp'
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ {folder}")


def step1_collection():
    """
    Step 1: 뉴스 수집 (RSS + Finnhub)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("1️⃣ 뉴스 수집 단계 (RSS + Finnhub)")
    print("="*70)

    finnhub_key = os.getenv('FINNHUB_API_KEY')

    if not finnhub_key:
        raise ValueError("FINNHUB_API_KEY를 .env에 설정해주세요.")

    collector = NewsCollector()
    articles = collector.run(finnhub_key)

    print(f"\n✅ 뉴스 수집 완료! 총 {len(articles)}개 기사 → data/1_collected/news.jsonl")
    return 'data/1_collected/news.jsonl'


def step2_clustering(input_file):
    """
    Step 2: 클러스터링

    Args:
        input_file: 수집 결과 파일 (data/1_collected/news.jsonl)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("2️⃣ 클러스터링 단계")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    output_file = 'data/2_clustered/clustered.jsonl'

    # 클러스터링 실행
    cluster_news_articles(input_file, output_file)

    return output_file


def step3_content_generation(input_file):
    """
    Step 3: EXAONE CoT 콘텐츠 생성

    Args:
        input_file: 클러스터링 결과 파일 (data/2_clustered/clustered.jsonl)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("3️⃣ 콘텐츠 생성 단계 (EXAONE CoT)")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    generator = ContentGenerator()
    scripts = generator.run(input_file)

    print(f"\n✅ 콘텐츠 생성 완료! {len(scripts)}개 스크립트 → data/3_generated/scripts.json")
    return 'data/3_generated/scripts.json'


def step4_card_generation(input_file):
    """
    Step 4: HTML 카드 이미지 생성

    Args:
        input_file: 스크립트 파일 (data/3_generated/scripts.json)

    Returns:
        dict: 클러스터별 카드 경로
    """
    print("\n" + "="*70)
    print("4️⃣ 카드 생성 단계 (HTML + Playwright)")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    generator = HTMLCardGenerator()
    results = generator.run(input_file)

    print(f"\n✅ 카드 생성 완료! {len(results)}개 클러스터 → data/4_cards/")
    return results




def main():
    """메인 함수"""

    parser = argparse.ArgumentParser(description='SignalFeed 파이프라인')

    # 실행 단계 선택
    parser.add_argument(
        '--steps',
        type=str,
        default='1,2,3,4',
        help='실행할 단계 (쉼표로 구분, 예: 1,2,3,4 또는 all)'
    )

    args = parser.parse_args()

    # 디렉토리 생성
    print("\n📁 디렉토리 생성")
    create_directories()

    # 실행할 단계 파싱
    if args.steps == 'all':
        steps = ['1', '2', '3', '4']
    else:
        steps = args.steps.split(',')

    print(f"\n🚀 실행 단계: {', '.join(steps)}")

    # 파일 경로 추적
    collected_file = 'data/1_collected/news.jsonl'
    clustered_file = 'data/2_clustered/clustered.jsonl'
    generated_file = 'data/3_generated/scripts.json'
    cards_result = {}

    # 단계별 실행
    try:
        if '1' in steps:
            collected_file = step1_collection()
            print(f"\n✅ Step 1 완료: {collected_file}")

        if '2' in steps:
            clustered_file = step2_clustering(collected_file)
            print(f"\n✅ Step 2 완료: {clustered_file}")

        if '3' in steps:
            generated_file = step3_content_generation(clustered_file)
            print(f"\n✅ Step 3 완료: {generated_file}")

        if '4' in steps:
            cards_result = step4_card_generation(generated_file)
            print(f"\n✅ Step 4 완료: data/4_cards/")

        # 최종 결과
        print("\n" + "="*70)
        print("🎉 파이프라인 완료!")
        print("="*70)
        print("\n📁 생성된 파일:")
        if '1' in steps:
            print(f"   1️⃣ {collected_file}")
        if '2' in steps:
            print(f"   2️⃣ {clustered_file}")
        if '3' in steps:
            print(f"   3️⃣ {generated_file}")
        if '4' in steps:
            print(f"   4️⃣ data/4_cards/ ({len(cards_result)} clusters)")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
