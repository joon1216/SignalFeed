"""
이슈별 클러스터링 모듈
TF-IDF + UMAP + HDBSCAN을 사용한 뉴스 클러스터링
"""

import pandas as pd
import json
import numpy as np
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
import umap
import hdbscan
from scipy.sparse import hstack


def cluster_news_articles(input_jsonl: str, output_jsonl: str):
    """
    뉴스 기사를 이슈별로 클러스터링
    
    Args:
        input_jsonl: 크롤링된 기사 JSONL 파일
        output_jsonl: 클러스터링 결과 JSONL 파일
    
    Returns:
        str: 출력 파일 경로
    """
    print("\n" + "="*70)
    print("2️⃣ 이슈별 클러스터링 단계")
    print("="*70)
    
    # 1. 데이터 로드
    print(f"\n📄 JSONL 로드: {input_jsonl}")
    articles = []
    with open(input_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                articles.append(json.loads(line))
    
    if not articles:
        print("❌ 기사가 없습니다.")
        return output_jsonl
    
    df = pd.DataFrame(articles)
    print(f"✅ {len(df)}개 기사 로드")
    
    # 2. 텍스트 전처리 및 벡터화
    print(f"\n>>> 텍스트 전처리 및 벡터화 중...")
    print(f"  → {len(df)}개 기사 처리 중...")
    
    # 제목 및 본문 전처리
    df['title'] = df['title'].fillna('').astype(str)
    df['content'] = df['content'].fillna('').astype(str)
    
    # 제목과 본문을 결합 (제목에 더 높은 가중치, 본문은 핵심 부분만)
    combined_text = (df['title'] + ' ' + df['title'] + ' ' + 
                     df['content'].str[:2000])
    
    # TF-IDF 벡터화 (단어 단위)
    tfidf_word = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 3),
        max_features=5000,
        min_df=2,
        max_df=0.9,
        sublinear_tf=True
    )
    word_vectors = tfidf_word.fit_transform(combined_text)
    
    # TF-IDF 벡터화 (글자 단위)
    tfidf_char = TfidfVectorizer(
        analyzer='char',
        ngram_range=(2, 4),
        max_features=1500,
        min_df=3,
        max_df=0.95
    )
    char_vectors = tfidf_char.fit_transform(combined_text)
    
    # 두 벡터 결합 (단어 벡터에 더 높은 가중치)
    combined_vectors = hstack([word_vectors, word_vectors, char_vectors])
    
    print(f"✅ 벡터화 완료. 차원: {combined_vectors.shape}")
    
    # 3. UMAP 차원 축소
    print(f"\n>>> UMAP 차원 축소 중...")
    
    n_samples = combined_vectors.shape[0]
    n_neighbors = min(15, n_samples - 1)
    n_components = min(50, n_samples - 1)
    
    # 희소 행렬을 밀집 행렬로 변환
    if hasattr(combined_vectors, 'toarray'):
        dense_vectors = combined_vectors.toarray()
    else:
        dense_vectors = combined_vectors
    
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=0.0,
        metric='cosine',
        random_state=42,
        low_memory=False,
        spread=1.0
    )
    
    reduced_vectors = reducer.fit_transform(dense_vectors)
    print(f"✅ 차원 축소 완료. 차원: {reduced_vectors.shape}")
    
    # 4. HDBSCAN 클러스터링
    print(f"\n>>> HDBSCAN 클러스터링 중...")
    
    min_cluster_size = max(3, int(n_samples * 0.05))  # 최소 3개 또는 전체의 5%
    min_samples = max(2, min_cluster_size // 3)
    
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_method='eom',
        cluster_selection_epsilon=0.0,
        prediction_data=True
    )
    
    cluster_labels = clusterer.fit_predict(reduced_vectors)
    df['cluster_id'] = cluster_labels
    
    # 노이즈 포인트(-1) 제외하고 클러스터 개수 확인
    unique_clusters = [c for c in np.unique(cluster_labels) if c != -1]
    num_issues = len(unique_clusters)
    noise_count = np.sum(cluster_labels == -1)
    
    print(f"✅ 클러스터링 완료!")
    print(f"   - 발견된 이슈 클러스터: {num_issues}개")
    print(f"   - 노이즈 포인트 (클러스터 없음): {noise_count}개 ({noise_count/len(df)*100:.1f}%)")
    print(f"   - 최소 클러스터 크기: {min_cluster_size}개")
    
    # 5. 클러스터 품질 검증 및 레이블 생성
    print(f"\n>>> 클러스터 품질 검증 및 레이블 생성 중...")
    
    clustered_df = df[df['cluster_id'] != -1].copy()
    clustered_clusters = sorted([c for c in clustered_df['cluster_id'].unique()])
    
    # 일관성 낮은 클러스터를 노이즈로 재분류
    low_quality_clusters = []
    for cluster_id in clustered_clusters:
        cluster_data = clustered_df[clustered_df['cluster_id'] == cluster_id]
        if not _check_cluster_consistency(cluster_data, threshold=0.3):
            low_quality_clusters.append(cluster_id)
            clustered_df.loc[clustered_df['cluster_id'] == cluster_id, 'cluster_id'] = -1
    
    if low_quality_clusters:
        print(f"  ⚠️ 일관성 낮은 클러스터 {len(low_quality_clusters)}개를 노이즈로 재분류했습니다.")
    
    # 재분류 후 클러스터 목록 업데이트
    clustered_df = clustered_df[clustered_df['cluster_id'] != -1]
    clustered_clusters = sorted([c for c in clustered_df['cluster_id'].unique()])
    num_issues = len(clustered_clusters)
    
    print(f"✅ 최종 클러스터 수: {num_issues}개")
    
    # 각 클러스터에 레이블 부여 (대표 제목 또는 주요 키워드)
    cluster_labels_dict = {}
    for cluster_id in clustered_clusters:
        cluster_data = clustered_df[clustered_df['cluster_id'] == cluster_id]
        keywords = _get_cluster_keywords(cluster_data, top_n=3)
        # 가장 긴 제목을 레이블로 사용
        representative_title = max(cluster_data['title'], key=len)
        if len(representative_title) > 50:
            representative_title = representative_title[:50] + "..."
        cluster_labels_dict[cluster_id] = representative_title
    
    # 모든 데이터프레임에 cluster_label 추가
    df['cluster_label'] = df['cluster_id'].map(cluster_labels_dict)
    df['cluster_label'] = df['cluster_label'].fillna('노이즈')
    
    # 6. 결과 저장
    print(f"\n💾 결과 저장: {output_jsonl}")
    with open(output_jsonl, 'w', encoding='utf-8') as f:
        for _, row in df.iterrows():
            article_dict = row.to_dict()
            # NaN 값을 None으로 변환
            for key, value in article_dict.items():
                if pd.isna(value):
                    article_dict[key] = None
            f.write(json.dumps(article_dict, ensure_ascii=False) + '\n')
    
    print("\n" + "="*70)
    print(f"✅ 클러스터링 완료! 총 {num_issues}개 이슈 클러스터 생성")
    print("="*70)
    
    return output_jsonl


def _get_cluster_keywords(cluster_data, top_n=5):
    """클러스터 내 가장 빈도 높은 키워드 추출"""
    # 모든 제목을 합쳐서 키워드 추출
    all_titles = ' '.join(cluster_data['title'].astype(str))
    # 한글 단어만 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}', all_titles)
    word_counts = Counter(words)
    
    # 너무 흔한 단어 제외
    common_words = {'의원', '기자', '대통령', '정부', '국회', '당', '시', '군', '도', '구', '면', '동', '위원', '위원장', '의회', '의장'}
    filtered_words = {word: count for word, count in word_counts.items() if word not in common_words}
    
    top_words = sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [word for word, count in top_words]


def _check_cluster_consistency(cluster_data, threshold=0.3):
    """클러스터 내 일관성 검사"""
    if len(cluster_data) < 3:
        return True  # 작은 클러스터는 검증 스킵
    
    keywords = _get_cluster_keywords(cluster_data, top_n=3)
    if len(keywords) < 2:
        return False  # 공통 키워드가 너무 적으면 일관성 낮음
    
    # 각 제목에서 주요 키워드가 나타나는 비율 확인
    keyword_in_title_count = 0
    for _, row in cluster_data.iterrows():
        title = str(row['title'])
        if any(keyword in title for keyword in keywords[:2]):  # 상위 2개 키워드 중 하나라도 있으면
            keyword_in_title_count += 1
    
    consistency_ratio = keyword_in_title_count / len(cluster_data)
    return consistency_ratio >= threshold

