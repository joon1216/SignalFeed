"""
SignalFeed Content Generator
Gemini 2.5 Flash (Google AI Studio) 기반 Instagram 5-slide + YouTube Shorts 스크립트 생성
"""

import os
import json
import logging
import time
from typing import List, Dict, Optional
from collections import defaultdict
from tqdm import tqdm
from pydantic import BaseModel, Field
from typing import Literal

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


class Slide(BaseModel):
    slide_num: int
    type: Literal["cover", "context", "beneficiary", "victim", "conclusion"]
    hook_title: Optional[str] = None
    one_line: Optional[str] = None
    sources: Optional[List[str]] = None
    title: Optional[str] = None
    facts: Optional[List[str]] = None
    source: Optional[str] = None
    sectors: Optional[List[Sector]] = None
    fact: Optional[str] = None
    summaries: Optional[List[Dict[str, str]]] = None
    watch_point: Optional[str] = None
    cta: Optional[str] = None
    cta_sub: Optional[str] = None


class CardScript(BaseModel):
    cluster_id: str
    macro_issue: str
    pexels_keyword: str
    hook_title: str
    reasoning_chain: str
    slides: List[Slide]
    hashtags: List[str]
    disclaimer: str


class TemplateFallback:
    """Gemini API 실패 시 템플릿 기반 폴백"""

    @staticmethod
    def generate_instagram_script(cluster: Dict) -> Dict:
        """템플릿 기반 Instagram 스크립트 생성"""
        signal = cluster.get("signal", "neutral")
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        articles = cluster.get("articles", [])

        sources = list(set([a.get("source", "") for a in articles[:3] if a.get("source")]))[:3]
        source_text = ", ".join(sources) if sources else "Reuters, Bloomberg"

        hook_title = "경제\n주목"

        return {
            "cluster_id": str(cluster.get("cluster_id", -1)),
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
3. facts: 반드시 구체적 수치 포함 ("3.2% 상승", "0.25%p 인하", "2050억 달러")
4. sectors: beneficiary/victim 각각 반드시 2-3개
5. 예측/권유 표현 절대 금지 ("예상", "전망", "추천", "매수", "매도")
6. 내부 메모/예시 표기 절대 금지 ("(예시 필요)", "(구체적인 예시 필요)")
7. 면책조항: 모든 콘텐츠는 AI 분석이며 투자 권유 아님

추론 순서 (Chain of Thought):
Step 1: 기사에서 핵심 팩트 + 수치 추출
Step 2: 매크로 경제 메커니즘 추론 (금리→달러→수출주 등 인과관계)
  - 금리 인상 → 달러 강세 → 수출주 환차익 / 수입 비용 상승
  - 금리 인상 → 채권 수익률↑ → 성장주 밸류에이션 하락
  - 유가 상승 → 에너지 비용↑ → 항공/운송/화학 악재
  - 중국 경기 부양 → 원자재 수요↑ → 철강/화학 호재
Step 3: 한국 주식시장 섹터별 영향 분석 (반도체/2차전지/금융주/방산/바이오/소비재 등)

[CRITICAL]:
- slides[2].sectors 배열: 반드시 2-3개 항목
- slides[3].sectors 배열: 반드시 2-3개 항목
- 1개만 있으면 무조건 틀린 답임
- 두 번째 섹터를 못 찾겠으면 관련 있는 다른 섹터를 발굴할 것

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
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=CardScript
                )
            )
            self.use_gemini = True
            logger.info("Gemini 2.5 Flash: Available")
        except Exception as e:
            logger.warning(f"Gemini initialization failed: {e}. Using fallback.")
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
            return TemplateFallback.generate_instagram_script(cluster)

        cluster_id = cluster.get("cluster_id", "unknown")
        articles = cluster.get("articles", [])[:3]  # Max 3 articles

        # Build article summaries
        article_texts = []
        for i, article in enumerate(articles, 1):
            title = article.get("title", "")
            summary = article.get("summary", "")[:500]  # First 500 chars
            source = article.get("source", "")
            article_texts.append(f"기사 {i} ({source}):\n제목: {title}\n요약: {summary}")

        articles_str = "\n\n".join(article_texts)

        user_prompt = f"""{self.SYSTEM_PROMPT}

다음 경제 뉴스 기사들을 분석하여 Instagram 5-slide 카드뉴스 스크립트를 생성하세요.

기사 데이터:
{articles_str}

출력 JSON 스키마:
- cluster_id: "{cluster_id}"
- macro_issue: 이슈 한 줄 요약
- pexels_keyword: Pexels 검색용 영어 키워드 (구체적으로)
- hook_title: 표지 훅 (15자 이내, 순한국어, 호재/악재 표기 없음)
- reasoning_chain: CoT 추론 경로 (1단계→2단계→3단계)
- slides: 5개 슬라이드 배열
  - slide 1 (cover): hook_title, one_line, sources
  - slide 2 (context): title="무슨 일이?", facts=[3개, 수치 포함], source
  - slide 3 (beneficiary): title="수혜주는?", sectors=[2-3개], fact
  - slide 4 (victim): title="주의할 섹터는?", sectors=[2-3개], fact
  - slide 5 (conclusion): title="오늘의 핵심", summaries=[3개], watch_point, cta, cta_sub
- hashtags: 10개
- disclaimer: "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"

중요 규칙:
1. hook_title은 반드시 순한국어만 (영어 절대 금지)
2. facts는 반드시 구체적 수치 포함 ("3.2% 상승", "250억 달러")
3. sectors는 반드시 2-3개 (1개면 오류)
4. 예측 표현 절대 금지
5. 내부 메모 절대 금지
"""

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(user_prompt)
                result = json.loads(response.text)

                # Validate
                if "slides" in result and len(result["slides"]) == 5:
                    logger.info(f"Generated Instagram script for cluster {cluster_id}")
                    return result
                else:
                    raise ValueError("Invalid response: missing slides or wrong count")

            except Exception as e:
                logger.warning(f"Gemini attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Backoff before retry
                continue

        # All retries failed, use fallback
        logger.error(f"Gemini failed for cluster {cluster_id}. Using fallback.")
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
