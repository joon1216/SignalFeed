"""
IssueFit Streamlit 웹 UI (DB 없는 버전)
JSONL 파일을 직접 읽어서 표시
"""

import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter


# 페이지 설정
st.set_page_config(
    page_title="IssueFit - 정치 뉴스 이슈 분석",
    page_icon="🗞️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS - 다크 테마
st.markdown("""
<style>
    /* 전체 배경 및 기본 스타일 */
    .main {
        background-color: #0e1117;
    }
    
    .stApp {
        background-color: #0e1117;
    }
    
    /* 모든 텍스트 기본 색상 */
    body, p, h1, h2, h3, h4, h5, h6, div, span, label {
        color: #ffffff !important;
    }
    
    /* Streamlit 기본 요소들 */
    .stMarkdown, .stMarkdown p, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff !important;
    }
    
    .stHeader {
        color: #ffffff !important;
    }
    
    .stSubheader {
        color: #ffffff !important;
    }
    
    /* 메인 헤더 */
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* 서브타이틀 */
    .subtitle-text {
        color: #cccccc !important;
    }
    
    /* 성향 배지 */
    .stance-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.875rem;
        font-weight: 600;
        margin: 0.25rem;
    }
    
    .badge-progressive {
        background-color: #FF6B6B;
        color: white;
    }
    
    .badge-conservative {
        background-color: #45B7D1;
        color: white;
    }
    
    .badge-neutral {
        background-color: #4ECDC4;
        color: white;
    }
    
    /* 요약 박스 - 다크 테마 */
    .summary-box {
        padding: 1rem;
        border-radius: 8px;
        background-color: #1e2130 !important;
        margin: 0.5rem 0;
        border-left: 4px solid;
        color: #ffffff !important;
    }
    
    .summary-box strong {
        color: #ffffff !important;
    }
    
    .summary-box p, .summary-box div {
        color: #ffffff !important;
    }
    
    .summary-progressive {
        border-left-color: #FF6B6B;
    }
    
    .summary-conservative {
        border-left-color: #45B7D1;
    }
    
    .summary-neutral {
        border-left-color: #4ECDC4;
    }
    
    .summary-overall {
        border-left-color: #764ba2;
    }
    
    /* 기사 카드 스타일 - 다크 테마 */
    .article-card {
        display: flex;
        gap: 1rem;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #2d3441;
        margin-bottom: 1rem;
        background-color: #1e2130 !important;
        transition: all 0.3s;
        cursor: pointer;
    }
    
    .article-card:hover {
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        border-color: #667eea;
        background-color: #262940 !important;
    }
    
    .article-thumbnail {
        width: 150px;
        height: 100px;
        object-fit: cover;
        border-radius: 8px;
        flex-shrink: 0;
    }
    
    .article-thumbnail-placeholder {
        width: 150px;
        height: 100px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 2rem;
        flex-shrink: 0;
    }
    
    .article-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    
    .article-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #ffffff !important;
        margin: 0;
        line-height: 1.4;
    }
    
    .article-preview {
        font-size: 0.9rem;
        color: #cccccc !important;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .article-meta {
        display: flex;
        gap: 1rem;
        align-items: center;
        font-size: 0.85rem;
        color: #aaaaaa !important;
    }
    
    .article-link {
        color: #667eea !important;
        text-decoration: none;
        font-weight: 500;
    }
    
    .article-link:hover {
        text-decoration: underline;
        color: #8a9eff !important;
    }
    
    /* Streamlit 컨테이너 및 블록 */
    .stContainer, .block-container {
        background-color: #0e1117;
    }
    
    /* 구분선 */
    hr {
        border-color: #2d3441 !important;
    }
    
    /* Info, Warning, Error 메시지 */
    .stInfo, .stWarning, .stError, .stSuccess {
        background-color: #1e2130 !important;
        color: #ffffff !important;
    }
    
    /* 사이드바 */
    .css-1d391kg, .css-1lcbmhc {
        background-color: #0e1117;
    }
    
    /* 메트릭 */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #ffffff !important;
    }
    
    /* 입력 필드 */
    .stTextInput > div > div > input {
        background-color: #1e2130 !important;
        color: #ffffff !important;
        border-color: #2d3441 !important;
    }
    
    /* 버튼 */
    .stButton > button {
        background-color: #667eea !important;
        color: #ffffff !important;
        border: none;
    }
    
    .stButton > button:hover {
        background-color: #5568d3 !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1e2130 !important;
        color: #ffffff !important;
    }
    
    .streamlit-expanderContent {
        background-color: #0e1117 !important;
        color: #ffffff !important;
    }
    
    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #0e1117;
    }
    
    .stTabs [data-baseweb="tab"] {
        color: #ffffff !important;
    }
    
    /* 차트 컨테이너 */
    .js-plotly-plot {
        background-color: #1e2130 !important;
    }
</style>
""", unsafe_allow_html=True)


def load_classified_articles(file_path):
    """분류된 기사 JSONL 로드"""
    import os
    articles = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:  # 빈 줄 제외
                    articles.append(json.loads(line))
        return pd.DataFrame(articles)
    except FileNotFoundError:
        st.error(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ 파일 로드 실패: {str(e)}")
        return pd.DataFrame()


def load_summaries(file_path):
    """요약 JSON 로드"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.warning(f"⚠️ 요약 파일을 찾을 수 없습니다: {file_path}")
        return {}
    except Exception as e:
        st.error(f"❌ 요약 로드 실패: {str(e)}")
        return {}


def get_statistics(df):
    """전체 통계 계산"""
    stats = {
        'total_issues': df['cluster_id'].nunique() if 'cluster_id' in df.columns else 0,
        'total_articles': len(df),
        'progressive': len(df[df['political_stance'] == 'progressive']),
        'conservative': len(df[df['political_stance'] == 'conservative']),
        'neutral': len(df[df['political_stance'] == 'neutral'])
    }
    return stats


def main():
    """메인 앱"""
    
    # 헤더
    st.markdown('<h1 class="main-header">🗞️ IssueFit</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle-text" style="text-align: center; font-size: 1.2rem; margin-bottom: 2rem;">정치 뉴스 이슈 분석 및 다관점 요약 시스템 (DB 없는 버전)</p>', unsafe_allow_html=True)
    
    # 사이드바 - 파일 경로
    st.sidebar.title("⚙️ 설정")
    
    data_preset = st.sidebar.selectbox(
        "데이터 선택",
        ["기본 (classified.jsonl)", "테스트 데이터 (test_classified.jsonl)"],
        help="클러스터링된 이슈가 없다면 '테스트 데이터'를 선택해 보세요."
    )
    
    if "테스트 데이터" in data_preset:
        classified_path = "data/3_classified/test_classified.jsonl"
        summary_path = "data/4_summarized/summaries.json"
    else:
        classified_path = "data/3_classified/classified.jsonl"
        summary_path = "data/4_summarized/summaries.json"
    
    st.sidebar.text(f"분류: {classified_path}")
    
    # 데이터 로드
    df = load_classified_articles(classified_path)
    summaries = load_summaries(summary_path)
    
    if df.empty:
        st.warning("⚠️ 데이터를 로드할 수 없습니다. 파일 경로를 확인하세요.")
        st.stop()
    
    st.sidebar.success("✅ 데이터 로드 성공")
    
    # 통계
    stats = get_statistics(df)
    
    st.sidebar.markdown("---")
    if stats['total_articles'] < 20:
        st.sidebar.caption("💡 기사가 적을 땐: 터미널에서 `python pipeline.py --all-sources` 실행")
    # 언론사별 기사 수
    if 'source' in df.columns and not df['source'].isna().all():
        src_counts = df['source'].value_counts()
        with st.sidebar.expander("📰 언론사별 기사 수"):
            for src, cnt in src_counts.items():
                sub = df[df['source']==src]
                stance = sub['media_stance'].iloc[0] if 'media_stance' in df.columns and len(sub) and pd.notna(sub['media_stance'].iloc[0]) else ''
                badge = {'progressive':'🔴', 'moderate':'⚪', 'conservative':'🔵'}.get(stance, '')
                st.caption(f"{badge} {str(src)}: {cnt}개")
    st.sidebar.markdown("### 📊 전체 통계")
    st.sidebar.metric("총 이슈", f"{stats['total_issues']}개")
    st.sidebar.metric("총 기사", f"{stats['total_articles']:,}개")
    
    st.sidebar.markdown("**성향별 분포:**")
    col1, col2, col3 = st.sidebar.columns(3)
    col1.metric("진보", stats['progressive'])
    col2.metric("보수", stats['conservative'])
    col3.metric("중립", stats['neutral'])
    
    # 메인 탭
    tab1, tab2, tab3 = st.tabs(["🏠 이슈 목록", "📊 대시보드", "ℹ️ 정보"])
    
    with tab1:
        show_issue_list(df, summaries)
    
    with tab2:
        show_dashboard(df, stats)
    
    with tab3:
        show_info()


def show_issue_list(df, summaries):
    """이슈 목록 페이지"""
    
    st.header("📰 최신 정치 이슈")
    
    # 선택된 이슈 상세 - 먼저 표시 (스크롤 없이 바로 보이도록)
    if 'selected_issue' in st.session_state:
        show_issue_detail(df, summaries, st.session_state.selected_issue)
        st.markdown("---")
        st.markdown("### 📋 다른 이슈")
    
    # 이슈별 집계 (노이즈 제외)
    df_valid = df[df['cluster_id'] >= 0]
    issue_stats = df_valid.groupby(['cluster_id', 'cluster_label']).agg({
        'title': 'count',
        'political_stance': lambda x: (
            (x == 'progressive').sum(),
            (x == 'conservative').sum(),
            (x == 'neutral').sum()
        )
    }).reset_index()
    
    if len(issue_stats) == 0:
        st.info("""클러스터링된 이슈가 없습니다.
        
**원인:** 모든 기사가 노이즈로 분류되었거나 데이터가 너무 적을 수 있습니다.

**해결 방법:**
1. **테스트 데이터 사용**: 왼쪽 사이드바에서 "데이터 선택" → **테스트 데이터** 를 선택하세요.
2. **파이프라인 재실행**: 더 많은 기사를 크롤링한 뒤 `python pipeline.py`를 실행하세요.
3. **기사 수 확보**: 현재 기사 수가 적으면(예: 9개) 유사 주제가 2~3개 이상 있어야 클러스터가 형성됩니다.""")
        return
    
    issue_stats.columns = ['cluster_id', 'cluster_label', 'article_count', 'stance_counts']
    issue_stats[['progressive_count', 'conservative_count', 'neutral_count']] = pd.DataFrame(
        issue_stats['stance_counts'].tolist(), index=issue_stats.index
    )
    
    # 검색 및 필터
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 이슈 검색", placeholder="키워드를 입력하세요...")
    with col2:
        sort_by = st.selectbox("정렬", ["기사 수", "이슈 번호"])
    
    # 필터링
    if search:
        issue_stats = issue_stats[issue_stats['cluster_label'].str.contains(search, case=False, na=False)]
    
    # 정렬
    if sort_by == "기사 수":
        issue_stats = issue_stats.sort_values('article_count', ascending=False)
    else:
        issue_stats = issue_stats.sort_values('cluster_id')
    
    # 이슈 카드 표시
    if len(issue_stats) == 0:
        st.info("검색 결과가 없습니다.")
    else:
        for _, issue in issue_stats.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"### {issue['cluster_label']}")
                    
                    # 성향 배지
                    badges = []
                    if issue['progressive_count'] > 0:
                        badges.append(f'<span class="stance-badge badge-progressive">진보 {issue["progressive_count"]}</span>')
                    if issue['conservative_count'] > 0:
                        badges.append(f'<span class="stance-badge badge-conservative">보수 {issue["conservative_count"]}</span>')
                    if issue['neutral_count'] > 0:
                        badges.append(f'<span class="stance-badge badge-neutral">중립 {issue["neutral_count"]}</span>')
                    
                    st.markdown(" ".join(badges), unsafe_allow_html=True)
                
                with col2:
                    st.metric("총 기사", f"{issue['article_count']}개")
                    
                    # 이미 선택된 이슈는 "선택됨" 표시, 아니면 상세보기
                    is_selected = st.session_state.get('selected_issue') == int(issue['cluster_id'])
                    btn_label = "✓ 선택됨" if is_selected else "상세보기"
                    if st.button(btn_label, key=f"btn_{issue['cluster_id']}"):
                        if is_selected:
                            del st.session_state.selected_issue
                        else:
                            st.session_state.selected_issue = int(issue['cluster_id'])
                        st.rerun()
                
                st.markdown("---")


def show_issue_detail(df, summaries, cluster_id):
    """이슈 상세 페이지"""
    
    # 이슈 기사 필터링
    issue_articles = df[df['cluster_id'] == cluster_id]
    
    if len(issue_articles) == 0:
        st.error("이슈 정보를 찾을 수 없습니다.")
        return
    
    cluster_label = issue_articles.iloc[0]['cluster_label']
    
    # 요약 정보
    summary = summaries.get(str(cluster_id), {})
    
    # 상세 정보 모달
    with st.expander(f"📋 {cluster_label} - 상세 정보", expanded=True):
        
        # 닫기 버튼
        if st.button("❌ 닫기", key=f"close_{cluster_id}"):
            del st.session_state.selected_issue
            st.rerun()
        
        st.markdown(f"**총 기사:** {len(issue_articles)}개")
        
        # 관점별 요약
        if summary:
            st.markdown("### 📝 다관점 요약")
            
            summaries_dict = summary.get('summaries', {})
            
            # 전체 요약
            if summaries_dict.get('overall'):
                st.markdown(f'<div class="summary-box summary-overall"><strong>🌐 전체 요약</strong><br>{summaries_dict["overall"]}</div>', unsafe_allow_html=True)
            
            # 3단 레이아웃
            col1, col2, col3 = st.columns(3)
            
            with col1:
                progressive_summary = summaries_dict.get('progressive')
                if progressive_summary and progressive_summary is not None:
                    st.markdown(f'<div class="summary-box summary-progressive"><strong>🔴 진보 관점</strong><br>{progressive_summary}</div>', unsafe_allow_html=True)
                else:
                    st.info("진보 관점 요약 없음")
            
            with col2:
                conservative_summary = summaries_dict.get('conservative')
                if conservative_summary and conservative_summary is not None:
                    st.markdown(f'<div class="summary-box summary-conservative"><strong>🔵 보수 관점</strong><br>{conservative_summary}</div>', unsafe_allow_html=True)
                else:
                    st.info("보수 관점 요약 없음")
            
            with col3:
                neutral_summary = summaries_dict.get('neutral')
                if neutral_summary and neutral_summary is not None:
                    st.markdown(f'<div class="summary-box summary-neutral"><strong>⚪ 중립 관점</strong><br>{neutral_summary}</div>', unsafe_allow_html=True)
                else:
                    st.info("중립 관점 요약 없음")
        
        # 기사 목록
        st.markdown("### 📰 관련 기사")
        
        # 성향 필터
        stance_filter = st.multiselect(
            "성향 필터",
            ["progressive", "conservative", "neutral"],
            default=["progressive", "conservative", "neutral"],
            format_func=lambda x: {"progressive": "진보", "conservative": "보수", "neutral": "중립"}[x]
        )
        
        filtered_articles = issue_articles[issue_articles['political_stance'].isin(stance_filter)]
        filtered_articles = filtered_articles.sort_values('stance_confidence', ascending=False)
        
        if len(filtered_articles) > 0:
            for idx, article in filtered_articles.iterrows():
                stance_color = {
                    'progressive': '#FF6B6B',
                    'conservative': '#45B7D1',
                    'neutral': '#4ECDC4'
                }.get(article['political_stance'], '#999')
                
                stance_text = {
                    'progressive': '진보',
                    'conservative': '보수',
                    'neutral': '중립'
                }.get(article['political_stance'], '알 수 없음')
                
                # 썸네일 HTML
                thumbnail_html = ""
                if pd.notna(article.get('thumbnail')) and article['thumbnail']:
                    thumbnail_html = f'<img src="{article["thumbnail"]}" class="article-thumbnail" />'
                else:
                    thumbnail_html = '<div class="article-thumbnail-placeholder">🗞️</div>'
                
                # URL 처리
                article_url = article.get('url', '')
                url_link = f'<a href="{article_url}" target="_blank" class="article-link">원문 보기 →</a>' if article_url else ''
                
                # 발행일 처리 (published_at 또는 pubDate)
                published_date = article.get('published_at') or article.get('pubDate', '')
                if published_date:
                    date_display = f'<span style="color: #aaaaaa;">📅 {published_date}</span>'
                else:
                    date_display = ''
                
                # 내용 미리보기
                preview = article.get('content', '')[:150] if article.get('content') else ''
                
                # 카드 HTML
                card_html = f"""
                <div class="article-card" onclick="window.open('{article_url}', '_blank')">
                    {thumbnail_html}
                    <div class="article-content">
                        <h4 class="article-title">{article['title']}</h4>
                        <p class="article-preview">{preview}...</p>
                        <div class="article-meta">
                            <span style="color: {stance_color}; font-weight: 600;">● {stance_text}</span>
                            <span style="color: #aaaaaa;">신뢰도: {article['stance_confidence']:.1%}</span>
                            {date_display}
                            {url_link}
                        </div>
                    </div>
                </div>
                """
                
                st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info("선택한 성향의 기사가 없습니다.")


def show_dashboard(df, stats):
    """대시보드 페이지"""
    
    st.header("📊 통계 대시보드")
    
    # KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 이슈", f"{stats['total_issues']}개")
    col2.metric("총 기사", f"{stats['total_articles']:,}개")
    col3.metric("평균 기사/이슈", f"{stats['total_articles'] / max(stats['total_issues'], 1):.1f}개")
    col4.metric("분류 정확도", f"{df['stance_confidence'].mean():.1%}")
    
    st.markdown("---")
    
    # 차트 영역
    col1, col2 = st.columns(2)
    
    with col1:
        # 성향별 분포 파이 차트
        st.subheader("🎯 성향별 기사 분포")
        
        stance_data = pd.DataFrame({
            '성향': ['진보', '보수', '중립'],
            '기사 수': [stats['progressive'], stats['conservative'], stats['neutral']],
        })
        
        fig_pie = px.pie(
            stance_data, 
            values='기사 수', 
            names='성향',
            color='성향',
            color_discrete_map={'진보': '#FF6B6B', '보수': '#45B7D1', '중립': '#4ECDC4'},
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # 이슈별 기사 수 막대 차트
        st.subheader("📈 이슈별 기사 수")
        
        issue_counts = df.groupby('cluster_label').size().reset_index(name='count')
        top_issues = issue_counts.nlargest(10, 'count')
        
        fig_bar = px.bar(
            top_issues,
            x='count',
            y='cluster_label',
            orientation='h',
            color='count',
            color_continuous_scale='Viridis',
            labels={'count': '기사 수', 'cluster_label': '이슈'}
        )
        fig_bar.update_layout(showlegend=False, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)


def show_info():
    """정보 페이지"""
    
    st.header("ℹ️ IssueFit 소개")
    
    st.markdown("""
    ### 📋 프로젝트 개요
    
    **IssueFit**은 대량의 정치 뉴스를 자동으로 분석하여 이슈별로 분류하고, 
    각 이슈에 대한 다관점 요약을 제공하는 AI 기반 뉴스 분석 시스템입니다.
    
    ### 🎯 주요 기능
    
    1. **이슈 클러스터링**: 유사한 주제의 뉴스를 자동으로 그룹화
    2. **정치 성향 분류**: BERT + TextCNN으로 진보/보수/중립 분류
    3. **다관점 요약**: Ollama LLM으로 각 성향별 + 전체 요약
    
    ### 💾 DB 없는 버전
    
    이 버전은 **SQLite DB 없이 JSONL 파일을 직접 읽어서 표시**합니다.
    
    - ✅ 간단한 구조
    - ✅ 빠른 시작
    - ✅ 파일 하나만 관리
    
    ### 📁 필요한 파일
    
    - `data/classified.jsonl` - 분류된 기사
    - `data/summaries.json` - 요약 결과
    
    ---
    
    **IssueFit v1.0 (DB 없는 버전)** | Made with ❤️
    """)


if __name__ == "__main__":
    main()
