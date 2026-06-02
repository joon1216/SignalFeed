"""
SignalFeed Content Generator
Gemini 2.5 Flash (google-genai package) 기반 Instagram 5-slide 스크립트 생성
"""

import os
import json
import logging
import time
from typing import List, Dict, Optional
from collections import defaultdict
from tqdm import tqdm
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic Schema for Gemini structured output
class Sector(BaseModel):
    name: str
    reason: str
    example_stocks: str


class CardScript(BaseModel):
    hook_title: str
    one_line: str
    pexels_keyword: str
    context_facts: List[str]
    context_source: str
    bullish_sectors: List[Sector]
    bullish_fact: str
    bearish_sectors: List[Sector]
    bearish_fact: str
    summaries: List[str]
    watch_point: str


class TemplateFallback:
    """Gemini API 실패 시 템플릿 기반 폴백"""

    @staticmethod
    def generate_instagram_script(cluster: Dict) -> Dict:
        """템플릿 기반 Instagram 스크립트 생성"""
        cluster_id = str(cluster.get("cluster_id", -1))
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        articles = cluster.get("articles", [])

        sources = list(set([a.get("source", "") for a in articles[:3] if a.get("source")]))[:3]
        source_text = ", ".join(sources) if sources else "Reuters, Bloomberg"

        hook_title = "경제\n주목"

        return {
            "cluster_id": cluster_id,
            "macro_issue": cluster_label,
            "pexels_keyword": "financial district skyscraper aerial",
            "hook_title": hook_title,
            "reasoning_chain": "Fallback mode - no reasoning",
            "slides": [
                {
                    "slide_num": 1,
                    "type": "cover",
                    "hook_title": hook_title,
                    "one_line": cluster_label[:25],
                    "sources": sources
                },
                {
                    "slide_num": 2,
                    "type": "context",
                    "title": "무슨 일이?",
                    "facts": [
                        "주요 경제 지표 발표",
                        "시장 반응 나타남",
                        "분석가들 주목"
                    ],
                    "source": source_text
                },
                {
                    "slide_num": 3,
                    "type": "beneficiary",
                    "title": "수혜주는?",
                    "sectors": [
                        {"name": "성장주", "reason": "실적 개선으로 수혜", "example_stocks": "삼성전자, SK하이닉스"},
                        {"name": "소비재", "reason": "소비 증가 기대", "example_stocks": "LG생활건강, 아모레퍼시픽"}
                    ],
                    "fact": "경제 지표 개선으로 투자 심리 회복"
                },
                {
                    "slide_num": 4,
                    "type": "victim",
                    "title": "주의할 섹터는?",
                    "sectors": [
                        {"name": "채권", "reason": "금리 불확실성", "example_stocks": "국채 ETF, 회사채"},
                        {"name": "부동산", "reason": "금리 부담", "example_stocks": "리츠, 건설주"}
                    ],
                    "fact": "인플레이션 압력으로 통화 긴축 지속"
                },
                {
                    "slide_num": 5,
                    "type": "conclusion",
                    "title": "오늘의 핵심",
                    "summaries": [
                        {"signal": "bullish", "text": "성장주 중심 수혜 전망"},
                        {"signal": "bearish", "text": "채권은 금리 부담"},
                        {"signal": "neutral", "text": "시장 변동성 주의"}
                    ],
                    "watch_point": "경제 지표와 중앙은행 발언 주목",
                    "cta": "더 궁금하다면 댓글에 '분석' 남겨주세요",
                    "cta_sub": "→ 상세 리포트 DM으로 드립니다"
                }
            ],
            "hashtags": ["#경제", "#투자", "#주식", "#ETF", "#시그널피드", "#뉴스", "#금융", "#재테크", "#자산관리", "#투자정보"],
            "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
        }


class ContentGenerator:
    """Gemini 2.5 Flash 기반 콘텐츠 생성기"""

    SYSTEM_PROMPT = """당신은 글로벌 매크로 경제 뉴스를 분석하여 한국 주식 투자자를 위한 Instagram 카드뉴스 스크립트를 생성하는 전문 금융 애널리스트입니다.

타겟: 한국 MZ세대 투자자 (20-35세), 고등학교 수준 언어로 간결하게 설명

절대 규칙:
1. 모든 출력은 반드시 한국어
2. hook_title: 순한국어만 (영어 단어 절대 금지), 15자 이내, 궁금증 유발
3. context_facts: 반드시 구체적 수치 포함 ("3.2% 상승", "0.25%p 인하", "2050억 달러")
4. bullish_sectors, bearish_sectors: 각각 반드시 2개 이상
5. 예측/권유 표현 절대 금지 ("예상", "전망", "추천", "매수", "매도")
6. 내부 메모/예시 표기 절대 금지 ("(예시 필요)", "(구체적인 예시 필요)")

추론 순서 (Chain of Thought):
Step 1: 기사에서 핵심 팩트 + 수치 추출
Step 2: 매크로 경제 메커니즘 추론
  - 금리 인상 → 달러 강세 → 수출주 환차익 / 수입 비용 상승
  - 금리 인상 → 채권 수익률↑ → 성장주 밸류에이션 하락
  - 유가 상승 → 에너지 비용↑ → 항공/운송/화학 악재
  - 중국 경기 부양 → 원자재 수요↑ → 철강/화학 호재
Step 3: 한국 주식시장 섹터별 영향 분석

[CRITICAL]:
- bullish_sectors: 반드시 2개 이상 (1개면 오류)
- bearish_sectors: 반드시 2개 이상 (1개면 오류)
- 금리 인상이면: 금융주 호재 + 달러 자산 호재 (최소 2개)
- 금리 인하면: 성장주 호재 + 부동산 호재 (최소 2개)

표지 훅 규칙:
- 호재/악재 표기 없음, 이슈 자체에만 집중
- 궁금증 유발 (예: "연준이\n입을 열었다", "이 숫자가\n시장을 흔든다")
- 15자 이내, 강렬하게, \n으로 2줄 구분
"""

    def __init__(self):
        """Initialize ContentGenerator with Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. Using template fallback mode.")
            self.use_gemini = False
            return

        try:
            from google import genai
            from google.genai import types

            self.client = genai.Client(api_key=api_key)
            self.use_gemini = True
            logger.info("✅ Gemini 2.5 Flash: Available")
        except Exception as e:
            logger.warning(f"❌ Gemini initialization failed: {e}. Using fallback.")
            self.use_gemini = False

    def generate_instagram_script(self, cluster: Dict, max_retries: int = 3) -> Dict:
        """
        Generate Instagram 5-slide script with Gemini

        Args:
            cluster: Cluster dict with cluster_id, articles
            max_retries: Maximum retry attempts

        Returns:
            Instagram script dict
        """
        if not self.use_gemini:
            logger.warning("⚠️ Fallback mode (no Gemini API key)")
            return TemplateFallback.generate_instagram_script(cluster)

        cluster_id = cluster.get("cluster_id", "unknown")
        articles = cluster.get("articles", [])[:5]  # Max 5 articles

        # Build article summaries
        article_texts = []
        for i, article in enumerate(articles, 1):
            title = article.get("title", "")
            summary = article.get("summary", "")[:400]  # First 400 chars
            source = article.get("source", "")
            article_texts.append(f"기사 {i} ({source}):\n제목: {title}\n요약: {summary}")

        articles_str = "\n\n".join(article_texts)

        # Extract sources for slide 1
        sources = list(set([a.get("source", "") for a in articles[:3] if a.get("source")]))[:3]

        user_prompt = f"""{self.SYSTEM_PROMPT}

다음 경제 뉴스 기사들을 분석하여 Instagram 5-slide 카드뉴스 스크립트를 생성하세요.

기사 데이터:
{articles_str}

출력 JSON 스키마:
{{
  "hook_title": "표지 훅 (15자 이내, 순한국어, \\n으로 2줄)",
  "one_line": "이슈 한 줄 요약 (40자 이내)",
  "pexels_keyword": "Pexels 검색용 영어 키워드 (구체적으로)",
  "context_facts": ["팩트1 (수치 포함)", "팩트2 (수치 포함)", "팩트3 (수치 포함)"],
  "context_source": "출처 표기 (예: Reuters, Bloomberg)",
  "bullish_sectors": [
    {{"name": "섹터명", "reason": "이유 (40자 이내)", "example_stocks": "종목1, 종목2"}},
    {{"name": "섹터명2", "reason": "이유", "example_stocks": "종목3, 종목4"}}
  ],
  "bullish_fact": "호재 팩트 요약 (50자 이내)",
  "bearish_sectors": [
    {{"name": "섹터명", "reason": "이유 (40자 이내)", "example_stocks": "종목5, 종목6"}},
    {{"name": "섹터명2", "reason": "이유", "example_stocks": "종목7, 종목8"}}
  ],
  "bearish_fact": "악재 팩트 요약 (50자 이내)",
  "summaries": ["호재 요약 (30자)", "악재 요약 (30자)", "중립 요약 (30자)"],
  "watch_point": "주목 포인트 (50자 이내)"
}}

중요 규칙:
1. hook_title: 반드시 순한국어만 (영어 절대 금지)
2. context_facts: 반드시 구체적 수치 포함 ("3.2% 상승", "250억 달러")
3. bullish_sectors, bearish_sectors: 각각 반드시 2개 이상
4. 예측 표현 절대 금지
5. 내부 메모 절대 금지
"""

        from google.genai import types

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CardScript,
                        temperature=0.7,
                    )
                )

                result = json.loads(response.text)

                # Validate sectors
                bullish_count = len(result.get("bullish_sectors", []))
                bearish_count = len(result.get("bearish_sectors", []))

                if bullish_count < 2 or bearish_count < 2:
                    raise ValueError(f"Insufficient sectors: bullish={bullish_count}, bearish={bearish_count}")

                # Convert to old format for compatibility
                instagram_script = {
                    "cluster_id": str(cluster_id),
                    "macro_issue": result["one_line"],
                    "pexels_keyword": result["pexels_keyword"],
                    "hook_title": result["hook_title"],
                    "reasoning_chain": "Gemini 2.5 Flash CoT",
                    "slides": [
                        {
                            "slide_num": 1,
                            "type": "cover",
                            "hook_title": result["hook_title"],
                            "one_line": result["one_line"],
                            "sources": sources
                        },
                        {
                            "slide_num": 2,
                            "type": "context",
                            "title": "무슨 일이?",
                            "facts": result["context_facts"],
                            "source": result["context_source"]
                        },
                        {
                            "slide_num": 3,
                            "type": "beneficiary",
                            "title": "수혜주는?",
                            "sectors": [
                                {
                                    "name": s["name"] if isinstance(s, dict) else s.name,
                                    "reason": s["reason"] if isinstance(s, dict) else s.reason,
                                    "example_stocks": s["example_stocks"] if isinstance(s, dict) else s.example_stocks
                                } for s in result["bullish_sectors"]
                            ],
                            "fact": result["bullish_fact"]
                        },
                        {
                            "slide_num": 4,
                            "type": "victim",
                            "title": "주의할 섹터는?",
                            "sectors": [
                                {
                                    "name": s["name"] if isinstance(s, dict) else s.name,
                                    "reason": s["reason"] if isinstance(s, dict) else s.reason,
                                    "example_stocks": s["example_stocks"] if isinstance(s, dict) else s.example_stocks
                                } for s in result["bearish_sectors"]
                            ],
                            "fact": result["bearish_fact"]
                        },
                        {
                            "slide_num": 5,
                            "type": "conclusion",
                            "title": "오늘의 핵심",
                            "summaries": [
                                {"signal": "bullish", "text": result["summaries"][0]},
                                {"signal": "bearish", "text": result["summaries"][1]},
                                {"signal": "neutral", "text": result["summaries"][2]}
                            ],
                            "watch_point": result["watch_point"],
                            "cta": "더 궁금하다면 댓글에 '분석' 남겨주세요",
                            "cta_sub": "→ 상세 리포트 DM으로 드립니다"
                        }
                    ],
                    "hashtags": ["#경제", "#투자", "#주식", "#ETF", "#시그널피드", "#뉴스", "#금융", "#재테크", "#자산관리", "#투자정보"],
                    "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
                }

                logger.info(f"✅ Generated Instagram script for cluster {cluster_id}")
                return instagram_script

            except Exception as e:
                logger.warning(f"⚠️ Gemini attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Backoff before retry
                continue

        # All retries failed, use fallback
        logger.error(f"❌ Gemini failed for cluster {cluster_id}. Using fallback.")
        return TemplateFallback.generate_instagram_script(cluster)

    def generate_all(self, clusters: List[Dict]) -> List[Dict]:
        """
        Generate scripts for all clusters

        Args:
            clusters: List of cluster dicts

        Returns:
            List of generated scripts
        """
        logger.info(f"Generating content for {len(clusters)} clusters...")

        scripts = []

        for cluster in tqdm(clusters, desc="Generating scripts"):
            try:
                instagram = self.generate_instagram_script(cluster)

                script = {
                    "cluster_id": cluster.get("cluster_id"),
                    "cluster_label": cluster.get("cluster_label"),
                    "instagram": instagram
                }

                scripts.append(script)
                logger.info(f"Generated script for cluster {cluster.get('cluster_id')}")

            except Exception as e:
                logger.error(f"Error generating script for cluster {cluster.get('cluster_id')}: {e}")
                continue

        logger.info(f"Generated {len(scripts)} scripts")
        return scripts

    def save(self, scripts: List[Dict], output_path: str = "data/3_generated/scripts.json") -> None:
        """Save scripts to JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(scripts)} scripts to {output_path}")

    def run(self, input_path: str = "data/2_clustered/clustered.jsonl") -> List[Dict]:
        """
        Full pipeline: load → group by cluster → generate → save → return

        Args:
            input_path: Input file path (clustered articles)

        Returns:
            Generated scripts
        """
        import jsonlines

        logger.info("=" * 70)
        logger.info("SignalFeed Content Generation Started (Gemini 2.5 Flash)")
        logger.info("=" * 70)

        # Load clustered articles
        articles = []
        with jsonlines.open(input_path) as reader:
            for obj in reader:
                articles.append(obj)

        logger.info(f"Loaded {len(articles)} articles")

        # Group by cluster_id
        clusters = defaultdict(list)
        for article in articles:
            cluster_id = article.get("cluster_id", -1)
            if cluster_id >= 0:  # Skip noise
                clusters[cluster_id].append(article)

        logger.info(f"Found {len(clusters)} clusters")

        # Prepare cluster data
        cluster_list = []
        for cluster_id, cluster_articles in clusters.items():
            cluster_data = {
                "cluster_id": cluster_id,
                "cluster_label": cluster_articles[0].get("cluster_label", ""),
                "articles": cluster_articles
            }
            cluster_list.append(cluster_data)

        # Generate scripts
        scripts = self.generate_all(cluster_list)

        # Save
        self.save(scripts)

        logger.info("=" * 70)
        logger.info(f"Content Generation Complete: {len(scripts)} scripts")
        logger.info("=" * 70)

        return scripts


if __name__ == "__main__":
    generator = ContentGenerator()

    if os.path.exists("data/2_clustered/clustered.jsonl"):
        scripts = generator.run()
        logger.info(f"Generated {len(scripts)} scripts")
    else:
        logger.warning("No clustered data found. Run clusterer first.")
