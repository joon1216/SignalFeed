"""
SignalFeed 전체 파이프라인
수집 → 자동 레이블링 → 클러스터링 → 신호 분류

각 단계별로 폴더를 생성하여 JSONL 파일 저장
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
from backend.modules.auto_labeler import AutoLabeler
from backend.modules.clusterer import cluster_news_articles
from backend.modules.classifier import SignalClassifier


def create_directories():
    """
    단계별 디렉토리 생성

    data/
    ├── 1_collected/
    ├── 2_labeled/
    ├── 3_clustered/
    └── 4_classified/
    """
    folders = [
        'data/1_collected',
        'data/2_labeled',
        'data/3_clustered',
        'data/4_classified',
    ]

    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ {folder}")


def step1_collection():
    """
    Step 1: 뉴스 수집 (Polygon.io + Finnhub)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("1️⃣ 뉴스 수집 단계 (Polygon.io + Finnhub)")
    print("="*70)

    polygon_key = os.getenv('POLYGON_API_KEY')
    finnhub_key = os.getenv('FINNHUB_API_KEY')

    if not polygon_key or not finnhub_key:
        raise ValueError("POLYGON_API_KEY, FINNHUB_API_KEY를 .env에 설정해주세요.")

    collector = NewsCollector(polygon_key, finnhub_key)
    articles = collector.run()

    print(f"\n✅ 뉴스 수집 완료! 총 {len(articles)}개 기사 → data/1_collected/news.jsonl")
    return 'data/1_collected/news.jsonl'


def step2_auto_labeling(input_file):
    """
    Step 2: GPT-4o-mini 자동 레이블링

    Args:
        input_file: 수집 결과 파일 (data/1_collected/news.jsonl)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("2️⃣ 자동 레이블링 단계 (GPT-4o-mini)")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY를 .env에 설정해주세요.")

    labeler = AutoLabeler()
    articles = labeler.run(input_file, api_key)

    print(f"\n✅ 자동 레이블링 완료! {len(articles)}개 기사 → data/2_labeled/labeled.jsonl")
    return 'data/2_labeled/labeled.jsonl'


def step3_clustering(input_file):
    """
    Step 3: 클러스터링

    Args:
        input_file: 레이블링 결과 파일 (data/2_labeled/labeled.jsonl)

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("3️⃣ 클러스터링 단계")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    output_file = 'data/3_clustered/clustered.jsonl'

    # 클러스터링 실행
    cluster_news_articles(input_file, output_file)

    return output_file


def step4_classification(input_file, model_path=None, batch_size=32):
    """
    Step 4: FinBERT 신호 분류

    Args:
        input_file: 레이블링 결과 파일 (data/2_labeled/labeled.jsonl)
        model_path: 로컬 모델 경로 (None이면 ProsusAI/finbert 사용)
        batch_size: 배치 크기

    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("4️⃣ 신호 분류 단계 (FinBERT)")
    print("="*70)

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_file}")

    classifier = SignalClassifier(model_path=model_path)
    articles = classifier.run(input_file)

    print(f"\n✅ 신호 분류 완료! {len(articles)}개 기사 → data/4_classified/classified.jsonl")
    return 'data/4_classified/classified.jsonl'




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

    # 분류 옵션
    parser.add_argument(
        '--model-path',
        type=str,
        default=None,
        help='FinBERT 로컬 모델 경로 (기본값: ProsusAI/finbert)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='분류 배치 크기'
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
    labeled_file = 'data/2_labeled/labeled.jsonl'
    clustered_file = 'data/3_clustered/clustered.jsonl'
    classified_file = 'data/4_classified/classified.jsonl'

    # 단계별 실행
    try:
        if '1' in steps:
            collected_file = step1_collection()
            print(f"\n✅ Step 1 완료: {collected_file}")

        if '2' in steps:
            labeled_file = step2_auto_labeling(collected_file)
            print(f"\n✅ Step 2 완료: {labeled_file}")

        if '3' in steps:
            clustered_file = step3_clustering(labeled_file)
            print(f"\n✅ Step 3 완료: {clustered_file}")

        if '4' in steps:
            classified_file = step4_classification(labeled_file, args.model_path, args.batch_size)
            print(f"\n✅ Step 4 완료: {classified_file}")

        # 최종 결과
        print("\n" + "="*70)
        print("🎉 파이프라인 완료!")
        print("="*70)
        print("\n📁 생성된 파일:")
        if '1' in steps:
            print(f"   1️⃣ {collected_file}")
        if '2' in steps:
            print(f"   2️⃣ {labeled_file}")
        if '3' in steps:
            print(f"   3️⃣ {clustered_file}")
        if '4' in steps:
            print(f"   4️⃣ {classified_file}")

    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
