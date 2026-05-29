"""
SQLite 데이터베이스 저장 모듈
분류 및 요약 결과를 SQLite DB에 저장 (웹 서비스용)
"""

import sqlite3
import json
from datetime import datetime


def load_to_database(classified_jsonl: str, summary_json: str, db_path: str):
    """
    분류 및 요약 결과를 SQLite DB에 저장
    
    Args:
        classified_jsonl: 분류된 기사 JSONL 파일
        summary_json: 요약 결과 JSON 파일
        db_path: SQLite DB 파일 경로
    """
    print("\n" + "="*70)
    print("💾 데이터베이스 저장 시작")
    print("="*70)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 테이블 생성
    print("\n📋 테이블 생성 중...")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            url TEXT,
            thumbnail TEXT,
            published_at TEXT,
            cluster_id INTEGER,
            cluster_label TEXT,
            cluster_keywords TEXT,
            political_stance TEXT,
            stance_confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS summaries (
            cluster_id INTEGER PRIMARY KEY,
            cluster_label TEXT,
            progressive_summary TEXT,
            conservative_summary TEXT,
            neutral_summary TEXT,
            overall_summary TEXT,
            article_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_cluster_id ON articles(cluster_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_political_stance ON articles(political_stance)
    ''')
    
    # 기존 데이터 삭제
    cursor.execute('DELETE FROM articles')
    cursor.execute('DELETE FROM summaries')
    
    # 기사 데이터 삽입
    print("\n📰 기사 데이터 삽입 중...")
    article_count = 0
    
    with open(classified_jsonl, 'r', encoding='utf-8') as f:
        for line in f:
            article = json.loads(line)
            
            # cluster_keywords를 JSON 문자열로 변환
            keywords = article.get('cluster_keywords', [])
            keywords_str = json.dumps(keywords, ensure_ascii=False) if keywords else None
            
            cursor.execute('''
                INSERT INTO articles 
                (title, content, url, thumbnail, published_at,
                 cluster_id, cluster_label, cluster_keywords,
                 political_stance, stance_confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('title', ''),
                article.get('content', ''),
                article.get('url', ''),
                article.get('thumbnail', ''),
                article.get('published_at') or article.get('pubDate', ''),
                article.get('cluster_id'),
                article.get('cluster_label'),
                keywords_str,
                article.get('political_stance'),
                article.get('stance_confidence')
            ))
            
            article_count += 1
    
    print(f"✅ {article_count}개 기사 삽입 완료")
    
    # 요약 데이터 삽입
    print("\n📝 요약 데이터 삽입 중...")
    summary_count = 0
    
    with open(summary_json, 'r', encoding='utf-8') as f:
        summaries = json.load(f)
        
        for cluster_id, data in summaries.items():
            cursor.execute('''
                INSERT INTO summaries 
                (cluster_id, cluster_label, progressive_summary, 
                 conservative_summary, neutral_summary, overall_summary, article_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(cluster_id),
                data.get('cluster_label'),
                data.get('summaries', {}).get('progressive'),
                data.get('summaries', {}).get('conservative'),
                data.get('summaries', {}).get('neutral'),
                data.get('summaries', {}).get('overall'),
                data.get('article_count', 0)
            ))
            
            summary_count += 1
    
    print(f"✅ {summary_count}개 이슈 요약 삽입 완료")
    
    # 커밋 및 닫기
    conn.commit()
    
    # 통계 출력
    print("\n📊 데이터베이스 통계:")
    
    # 성향별 기사 수
    cursor.execute('''
        SELECT political_stance, COUNT(*) 
        FROM articles 
        WHERE political_stance IS NOT NULL
        GROUP BY political_stance
    ''')
    
    for stance, count in cursor.fetchall():
        print(f"   {stance}: {count}개")
    
    # 클러스터 수
    cursor.execute('SELECT COUNT(*) FROM summaries')
    cluster_count = cursor.fetchone()[0]
    print(f"\n   총 이슈(클러스터): {cluster_count}개")
    
    conn.close()
    
    print("\n" + "="*70)
    print(f"✅ 데이터베이스 저장 완료: {db_path}")
    print("="*70)
    
    return db_path


if __name__ == "__main__":
    # 테스트 코드
    import argparse
    
    parser = argparse.ArgumentParser(description='SQLite DB 저장')
    parser.add_argument('--classified', required=True, help='분류 JSONL')
    parser.add_argument('--summary', required=True, help='요약 JSON')
    parser.add_argument('--db', required=True, help='DB 파일 경로')
    
    args = parser.parse_args()
    
    load_to_database(args.classified, args.summary, args.db)
