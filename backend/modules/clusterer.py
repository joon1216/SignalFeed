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
    n_samples = len(df)
    print(f"✅ {n_samples}개 기사 로드")
    
    # 2. 텍스트 전처리 및 벡터화
    print(f"\n>>> 텍스트 전처리 및 벡터화 중...")
    print(f"  → {len(df)}개 기사 처리 중...")
    
    # 제목 및 본문 전처리
    df['title'] = df['title'].fillna('').astype(str)

    # Use 'summary' field if 'content' doesn't exist (SignalFeed uses summary instead of content)
    # Increase title weight to 10x for English news (titles more discriminative)
    if 'content' in df.columns:
        df['content'] = df['content'].fillna('').astype(str)
        combined_text = (df['title'] + ' ') * 10 + df['content'].str[:600]
    elif 'summary' in df.columns:
        df['summary'] = df['summary'].fillna('').astype(str)
        combined_text = (df['title'] + ' ') * 10 + df['summary'].str[:600]
    else:
        # Title only if no content/summary
        combined_text = (df['title'] + ' ') * 10
    
    # 소규모 데이터(n<15)에서는 min_df 완화
    min_df_word = 1 if n_samples < 15 else 2
    min_df_char = 2 if n_samples < 15 else 3
    
    # TF-IDF 벡터화 (단어 단위, English stopwords 추가)
    tfidf_word = TfidfVectorizer(
        analyzer='word',
        ngram_range=(1, 2),
        max_features=5000,
        min_df=min_df_word,
        max_df=0.85,
        sublinear_tf=True,
        stop_words='english'  # Add English stopwords
    )
    word_vectors = tfidf_word.fit_transform(combined_text)
    
    # TF-IDF 벡터화 (글자 단위)
    tfidf_char = TfidfVectorizer(
        analyzer='char',
        ngram_range=(2, 4),
        max_features=1500,
        min_df=min_df_char,
        max_df=0.95
    )
    char_vectors = tfidf_char.fit_transform(combined_text)
    
    # 두 벡터 결합 (단어 벡터에 더 높은 가중치)
    combined_vectors = hstack([word_vectors, word_vectors, char_vectors])
    
    print(f"✅ 벡터화 완료. 차원: {combined_vectors.shape}")
    
    # 3. UMAP 차원 축소
    print(f"\n>>> UMAP 차원 축소 중...")
    
    # n_components가 n_samples에 가까우면 UMAP spectral layout에서 eigsh 오류 발생
    n_neighbors = max(2, min(15, n_samples - 1))
    n_components = 2 if n_samples < 60 else min(50, n_samples // 2)
    
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

    # 클러스터 품질: 매크로 경제 뉴스는 작은 클러스터도 유의미할 수 있음 (min_cluster_size 완화)
    if n_samples < 8:
        min_cluster_size = 2
        min_samples = 1
    else:
        min_cluster_size = max(2, int(n_samples * 0.05))  # 10% → 5%로 완화
        min_samples = max(1, min_cluster_size // 2)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',
        cluster_selection_method='eom',
        cluster_selection_epsilon=0.3,  # 유사도 임계값 완화 (0.0 → 0.3)
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
    
    # Post-processing: merge clusters with high similarity
    clustered_df = _merge_similar_clusters(clustered_df, df, threshold=0.85)
    clustered_clusters = sorted([c for c in clustered_df['cluster_id'].unique() if c != -1])

    # Filter: keep only clusters with 2+ articles from 2+ sources
    low_quality_clusters = []
    for cluster_id in clustered_clusters:
        cluster_data = clustered_df[clustered_df['cluster_id'] == cluster_id]
        unique_sources = cluster_data['source'].nunique()
        if len(cluster_data) < 2 or unique_sources < 2:
            low_quality_clusters.append(cluster_id)
            clustered_df.loc[clustered_df['cluster_id'] == cluster_id, 'cluster_id'] = -1
            df.loc[df['cluster_id'] == cluster_id, 'cluster_id'] = -1
    
    if low_quality_clusters:
        print(f"  ⚠️ 품질 낮은 클러스터 {len(low_quality_clusters)}개를 노이즈로 재분류했습니다. (단일 소스 또는 1개 기사)")
    
    # 재분류 후 클러스터 목록 업데이트
    clustered_df = clustered_df[clustered_df['cluster_id'] != -1]
    clustered_clusters = sorted([c for c in clustered_df['cluster_id'].unique()])
    num_issues = len(clustered_clusters)
    
    print(f"✅ 최종 클러스터 수: {num_issues}개")
    
    # 각 클러스터에 레이블 부여 (대표 제목 또는 본문 기반 키워드)
    cluster_labels_dict = {}
    for cluster_id in clustered_clusters:
        cluster_data = clustered_df[clustered_df['cluster_id'] == cluster_id]
        # 제목이 비어있으면 본문에서 키워드 추출해서 레이블로 사용
        representative_title = max(cluster_data['title'].astype(str), key=len)
        if not representative_title or len(representative_title.strip()) < 5:
            keywords = _get_cluster_keywords(cluster_data, top_n=3)
            representative_title = ' '.join(keywords) if keywords else f"이슈 {cluster_id}"
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
            # NaN 값을 None으로 변환 (handle arrays and scalars)
            for key, value in article_dict.items():
                # Check if value is array-like (list, numpy array)
                if isinstance(value, (list, np.ndarray)):
                    article_dict[key] = [None if pd.isna(v) else v for v in value] if isinstance(value, list) else value.tolist()
                elif pd.isna(value):
                    article_dict[key] = None
            f.write(json.dumps(article_dict, ensure_ascii=False) + '\n')
    
    print("\n" + "="*70)
    print(f"✅ 클러스터링 완료! 총 {num_issues}개 이슈 클러스터 생성")
    print("="*70)
    
    return output_jsonl


def _get_cluster_keywords(cluster_data, top_n=5, use_content=True):
    """클러스터 내 가장 빈도 높은 키워드 추출 (영문 뉴스 지원)"""
    all_titles = ' '.join(cluster_data['title'].fillna('').astype(str))
    text_for_keywords = all_titles
    # 제목이 비어있으면 본문 앞부분(각 500자) 사용
    if (not all_titles.strip() or len(all_titles.strip()) < 20):
        if 'content' in cluster_data.columns:
            content_previews = cluster_data['content'].fillna('').astype(str).str[:500].fillna('')
            text_for_keywords = ' '.join(content_previews)
        elif 'summary' in cluster_data.columns:
            summary_previews = cluster_data['summary'].fillna('').astype(str).str[:500].fillna('')
            text_for_keywords = ' '.join(summary_previews)

    # Extract English words (3+ letters) or Korean words (2+ chars)
    words = re.findall(r'\b[A-Za-z]{3,}\b|[가-힣]{2,}', text_for_keywords.lower())
    word_counts = Counter(words)

    # Filter out common English stopwords, source names, and Korean political terms
    common_words = {
        # English stopwords
        'the', 'and', 'for', 'are', 'from', 'with', 'that', 'this', 'said', 'says',
        'will', 'has', 'have', 'been', 'about', 'after', 'could', 'would', 'should',
        'news', 'reuters', 'bloomberg', 'cnbc', 'report', 'reports', 'reported',
        # Korean political terms (legacy)
        '의원', '기자', '대통령', '정부', '국회', '당', '시', '군', '도', '구', '면', '동',
        '위원', '위원장', '의회', '의장', '정치', '뉴스', '오늘', '사실', '관련', '발표',
        '대표', '청와대', '여야', '야당', '여당', '국민', '우리', '조사'
    }
    filtered_words = {word: count for word, count in word_counts.items() if word not in common_words}

    top_words = sorted(filtered_words.items(), key=lambda x: x[1], reverse=True)[:top_n]
    return [word for word, count in top_words]


def _merge_similar_clusters(clustered_df, df, threshold=0.85):
    """Merge clusters with cosine similarity > threshold"""
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer

    cluster_ids = sorted([c for c in clustered_df['cluster_id'].unique() if c != -1])
    if len(cluster_ids) < 2:
        return clustered_df

    # Build cluster centroids
    cluster_texts = {}
    for cid in cluster_ids:
        cluster_articles = clustered_df[clustered_df['cluster_id'] == cid]
        titles = ' '.join(cluster_articles['title'].fillna('').astype(str))
        cluster_texts[cid] = titles

    # Compute similarity matrix
    vectorizer = TfidfVectorizer(stop_words='english')
    vectors = vectorizer.fit_transform([cluster_texts[cid] for cid in cluster_ids])
    sim_matrix = cosine_similarity(vectors)

    # Merge similar clusters
    merged = {}
    for i, cid1 in enumerate(cluster_ids):
        if cid1 in merged:
            continue
        merged[cid1] = cid1
        for j, cid2 in enumerate(cluster_ids):
            if i >= j or cid2 in merged:
                continue
            if sim_matrix[i, j] > threshold:
                merged[cid2] = cid1  # Merge cid2 into cid1

    # Apply merging
    for old_cid, new_cid in merged.items():
        if old_cid != new_cid:
            clustered_df.loc[clustered_df['cluster_id'] == old_cid, 'cluster_id'] = new_cid
            df.loc[df['cluster_id'] == old_cid, 'cluster_id'] = new_cid

    return clustered_df


