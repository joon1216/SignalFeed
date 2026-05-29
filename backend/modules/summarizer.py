"""
다관점 요약 모듈
Ollama LLM을 사용하여 이슈별로 진보/보수/중립/전체 관점의 요약 생성
"""

import json
import pandas as pd
from typing import Dict, List
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from tqdm.auto import tqdm


class PoliticalNewsSummarizer:
    """정치 뉴스 다관점 요약 생성기"""
    
    def __init__(self, model_name='gemma2:2b', base_url='http://localhost:11434'):
        """
        Args:
            model_name: Ollama 모델 이름
            base_url: Ollama 서버 URL
        """
        print(f"\n🤖 LLM 모델 초기화: {model_name}")
        self.llm = Ollama(model=model_name, base_url=base_url)
        self.model_name = model_name
        
        # 성향 매핑
        self.stance_mapping = {
            'progressive': '진보',
            'conservative': '보수',
            'neutral': '중립'
        }
        
        # 요약 길이 (문장 수)
        self.summary_length = 3
        
        # 프롬프트 설정
        self._setup_prompts()
    
    def _setup_prompts(self):
        """프롬프트 템플릿 설정"""
        
        # 관점별 요약 프롬프트
        self.perspective_prompt = PromptTemplate(
            input_variables=["perspective", "articles", "num_sentences"],
            template="""당신은 정치 뉴스 전문 분석가입니다.

다음은 하나의 정치 이슈에 대한 {perspective} 관점의 기사들입니다:

{articles}

위 기사들을 분석하여 {perspective} 관점에서 이 이슈를 {num_sentences}문장으로 요약해주세요.
요약은 반드시 {num_sentences}문장이어야 하며, 각 문장은 명확하고 구체적이어야 합니다.

요약:"""
        )
        
        # 전체 요약 프롬프트
        self.overall_prompt = PromptTemplate(
            input_variables=["all_articles", "num_sentences"],
            template="""당신은 정치 뉴스 전문 분석가입니다.

다음은 하나의 정치 이슈에 대한 모든 관점의 기사들입니다:

{all_articles}

위 기사들을 종합적으로 분석하여 이 이슈의 핵심 내용을 {num_sentences}문장으로 요약해주세요.
진보/보수/중립 관점을 모두 고려한 균형잡힌 요약을 제공해주세요.

요약:"""
        )
    
    def _group_by_cluster(self, df: pd.DataFrame) -> Dict:
        """클러스터 및 정치성향별로 그룹화"""
        grouped = {}
        
        for cluster_id in df['cluster_id'].unique():
            cluster_df = df[df['cluster_id'] == cluster_id]
            
            cluster_info = {
                'cluster_id': int(cluster_id),
                'cluster_label': cluster_df.iloc[0]['cluster_label'],
                'articles_by_stance': {},
                'all_articles': []
            }
            
            # 성향별 그룹화 (신뢰도 높은 순으로)
            for stance in ['progressive', 'conservative', 'neutral']:
                stance_articles = cluster_df[cluster_df['political_stance'] == stance]
                
                if len(stance_articles) > 0:
                    # 신뢰도 높은 순으로 정렬 (최대 10개)
                    stance_articles = stance_articles.nlargest(10, 'stance_confidence')
                    
                    cluster_info['articles_by_stance'][stance] = [
                        {
                            'title': row['title'],
                            'content': row['content'][:500]  # 첫 500자만
                        }
                        for _, row in stance_articles.iterrows()
                    ]
            
            # 전체 기사 (모든 기사 포함, 최대 50개)
            all_articles = cluster_df.copy()
            # 신뢰도가 없는 경우(unknown) 0으로 설정
            if 'stance_confidence' not in all_articles.columns:
                all_articles['stance_confidence'] = 0.0
            all_articles['stance_confidence'] = all_articles['stance_confidence'].fillna(0.0)
            # 최대 50개 선택 (전체 클러스터가 작으면 모두 포함)
            max_articles = min(50, len(all_articles))
            all_articles = all_articles.nlargest(max_articles, 'stance_confidence')
            
            cluster_info['all_articles'] = [
                {
                    'title': row['title'],
                    'content': row['content'][:500],
                    'stance': row['political_stance']
                }
                for _, row in all_articles.iterrows()
            ]
            
            grouped[cluster_id] = cluster_info
        
        return grouped
    
    def _format_articles(self, articles: List[Dict]) -> str:
        """기사 리스트를 프롬프트용 텍스트로 변환"""
        formatted = []
        for i, article in enumerate(articles, 1):
            formatted.append(f"[기사 {i}]")
            formatted.append(f"제목: {article['title']}")
            formatted.append(f"내용: {article['content']}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _summarize_perspective(self, perspective: str, articles: List[Dict]) -> str:
        """특정 관점의 요약 생성"""
        if not articles:
            return None
        
        articles_text = self._format_articles(articles)
        perspective_kr = self.stance_mapping[perspective]
        
        try:
            prompt = self.perspective_prompt.format(
                perspective=perspective_kr,
                articles=articles_text,
                num_sentences=self.summary_length
            )
            summary = self.llm.invoke(prompt)
            return summary.strip() if isinstance(summary, str) else summary.content.strip()
        except Exception as e:
            print(f"⚠️ {perspective} 요약 생성 실패: {str(e)}")
            return None
    
    def _summarize_overall(self, all_articles: List[Dict]) -> str:
        """전체 관점 요약 생성"""
        if not all_articles:
            return None
        
        articles_text = self._format_articles(all_articles)
        
        try:
            prompt = self.overall_prompt.format(
                all_articles=articles_text,
                num_sentences=self.summary_length
            )
            summary = self.llm.invoke(prompt)
            return summary.strip() if isinstance(summary, str) else summary.content.strip()
        except Exception as e:
            print(f"⚠️ 전체 요약 생성 실패: {str(e)}")
            return None
    
    def _summarize_cluster(self, cluster_info: Dict) -> Dict:
        """단일 클러스터 요약"""
        summaries = {
            'cluster_id': cluster_info['cluster_id'],
            'cluster_label': cluster_info['cluster_label'],
            'article_count': len(cluster_info['all_articles']),
            'summaries': {}
        }
        
        # 각 관점별 요약
        for stance in ['progressive', 'conservative', 'neutral']:
            if stance in cluster_info['articles_by_stance']:
                print(f"  - {self.stance_mapping[stance]} 관점 요약...")
                summary = self._summarize_perspective(
                    stance,
                    cluster_info['articles_by_stance'][stance]
                )
                summaries['summaries'][stance] = summary
            else:
                summaries['summaries'][stance] = None
        
        # 전체 요약
        print(f"  - 전체 요약...")
        summaries['summaries']['overall'] = self._summarize_overall(
            cluster_info['all_articles']
        )
        
        return summaries
    
    def summarize_all(self, input_jsonl: str, output_json: str):
        """
        전체 요약 파이프라인 실행
        
        Args:
            input_jsonl: 분류된 JSONL 파일
            output_json: 요약 결과 JSON 파일
        """
        print("\n" + "="*70)
        print("🚀 다관점 요약 시작")
        print("="*70)
        
        # 1. 데이터 로드
        print(f"\n📄 JSONL 로드: {input_jsonl}")
        articles = []
        with open(input_jsonl, 'r', encoding='utf-8') as f:
            for line in f:
                articles.append(json.loads(line))
        
        df = pd.DataFrame(articles)
        print(f"✅ {len(df)}개 기사 로드")
        
        # 2. 클러스터별 그룹화
        print(f"\n🔄 클러스터별 그룹화...")
        grouped = self._group_by_cluster(df)
        print(f"✅ {len(grouped)}개 클러스터")
        
        # 3. 각 클러스터 요약
        print(f"\n📝 클러스터별 요약 생성 중...\n")
        all_summaries = {}
        
        for i, (cluster_id, cluster_info) in enumerate(grouped.items(), 1):
            print(f"[{i}/{len(grouped)}] 클러스터 {cluster_id}: {cluster_info['cluster_label']}")
            summary = self._summarize_cluster(cluster_info)
            all_summaries[str(cluster_id)] = summary
        
        # 4. 결과 저장
        print(f"\n💾 결과 저장: {output_json}")
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(all_summaries, f, ensure_ascii=False, indent=2)
        
        print("\n" + "="*70)
        print(f"✅ 요약 완료! 총 {len(all_summaries)}개 이슈")
        print("="*70)
        
        return all_summaries


if __name__ == "__main__":
    # 테스트 코드
    import argparse
    
    parser = argparse.ArgumentParser(description='정치 뉴스 다관점 요약')
    parser.add_argument('--input', '-i', required=True, help='입력 JSONL 파일')
    parser.add_argument('--output', '-o', required=True, help='출력 JSON 파일')
    parser.add_argument('--model', default='gemma2:2b', help='Ollama 모델')
    parser.add_argument('--url', default='http://localhost:11434', help='Ollama URL')
    
    args = parser.parse_args()
    
    summarizer = PoliticalNewsSummarizer(
        model_name=args.model,
        base_url=args.url
    )
    
    summarizer.summarize_all(args.input, args.output)
