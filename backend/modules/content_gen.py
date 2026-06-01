"""
SignalFeed Content Generator
EXAONE 3.5 7.8B (Ollama) 기반 Instagram 5-slide + YouTube Shorts 스크립트 생성
"""

import os
import json
import logging
import requests
from typing import List, Dict, Optional
from collections import defaultdict
from tqdm import tqdm
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemplateFallback:
    """EXAONE/Ollama 없을 때 템플릿 기반 폴백"""

    SIGNAL_EMOJI = {
        "bullish": "🟢",
        "bearish": "🔴",
        "neutral": "⚪"
    }

    @staticmethod
    def generate_instagram_script(cluster: Dict) -> Dict:
        """템플릿 기반 Instagram 스크립트 생성 (새 구조)"""
        signal = cluster.get("signal", "neutral")
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        affected_sectors = cluster.get("affected_sectors", [])
        articles = cluster.get("articles", [])

        # Extract sources
        sources = list(set([a.get("source", "") for a in articles[:3] if a.get("source")]))[:3]
        source_text = ", ".join(sources) if sources else "Reuters, Bloomberg"

        # Hook title for cover (순한국어)
        hook_map = {
            "bullish": f"경제\n좋아진다?",
            "bearish": f"위기\n온다?",
            "neutral": f"시장\n어디로?"
        }
        hook_title = hook_map.get(signal, "경제 뉴스")

        # Signal text
        signal_text_map = {"bullish": "호재", "bearish": "악재", "neutral": "중립"}
        signal_text = signal_text_map.get(signal, "중립")

        return {
            "cluster_id": str(cluster.get("cluster_id", -1)),
            "signal": signal,
            "pexels_keyword": "financial district skyscraper aerial",
            "hook_title": hook_title,
            "slides": [
                {
                    "slide_num": 1,
                    "type": "cover",
                    "hook_title": hook_title,
                    "signal_emoji": TemplateFallback.SIGNAL_EMOJI[signal],
                    "signal_text": signal_text,
                    "one_line": cluster_label[:20]
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
                    "type": "bullish",
                    "title": "호재",
                    "sectors": [
                        {"name": "성장주", "reason": "실적 개선으로 수혜"},
                        {"name": "채권", "reason": "안전자산 선호 증가"}
                    ],
                    "fact": "경제 지표 개선으로 투자 심리 회복"
                },
                {
                    "slide_num": 4,
                    "type": "bearish",
                    "title": "악재",
                    "sectors": [
                        {"name": "금융주", "reason": "금리 인상 부담"},
                        {"name": "원자재", "reason": "수요 둔화 우려"}
                    ],
                    "fact": "인플레이션 압력으로 통화 긴축 지속"
                },
                {
                    "slide_num": 5,
                    "type": "conclusion",
                    "title": "오늘의 결론",
                    "summaries": [
                        {"signal": "bullish", "text": "성장주 중심으로 수혜 전망"},
                        {"signal": "bearish", "text": "금융주는 금리 인상 부담"},
                        {"signal": "neutral", "text": "시장 변동성 주의 필요"}
                    ],
                    "watch_point": "경제 지표와 중앙은행 발언 주목",
                    "cta": "더 궁금하다면 댓글에 '분석' 남겨주세요",
                    "cta_sub": "→ 상세 리포트 DM으로 드립니다"
                }
            ],
            "hashtags": ["#경제", "#투자", "#주식", "#ETF", "#시그널피드", "#뉴스", "#금융", "#재테크", "#자산관리", "#투자정보"],
            "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
        }

    @staticmethod
    def generate_shorts_script(cluster: Dict) -> Dict:
        """템플릿 기반 YouTube Shorts 스크립트 생성"""
        signal = cluster.get("signal", "neutral")
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        affected_sectors = cluster.get("affected_sectors", [])

        narration = f"""안녕하세요 시그널피드입니다. 오늘의 핵심 이슈입니다.

{cluster_label}이슈가 발생했습니다. 이는 {', '.join(affected_sectors[:2]) if affected_sectors else '전체 시장'}에 영향을 미칠 것으로 보입니다.

AI 분석 결과, {signal.upper()} 시그널로 분류되었습니다.

단, 이는 AI 분석이며 투자 권유가 아닙니다.

자세한 분석은 프로필 링크에서 확인하세요. 구독과 좋아요 부탁드립니다."""

        return {
            "cluster_id": str(cluster.get("cluster_id", -1)),
            "narration": narration,
            "duration_estimate": 60,
            "title": f"{cluster_label[:50]} - {signal.upper()} 시그널",
            "description": f"{cluster_label}\n\n{signal.upper()} 시그널 분석\n\n본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다.\n\n#경제 #투자 #주식 #시그널피드",
            "tags": ["경제", "투자", "주식", "ETF", "뉴스", "금융", "재테크", "시그널피드"]
        }


class ContentGenerator:
    """EXAONE 3.5 7.8B (Ollama) 기반 콘텐츠 생성기"""

    SYSTEM_PROMPT = """당신은 거시경제와 한국 주식시장을 연결하는 금융 분석가입니다.

분석 방법 (반드시 이 순서로 추론):

1단계 - 이슈 파악: 무슨 일이 일어났나? (핵심 팩트 + 수치)

2단계 - 경제 메커니즘: 이 이슈가 어떤 경로로 시장에 영향을 주나?
예시 경로들:
- 금리 인상 → 달러 강세 → 수출주 환차익 / 수입 비용 상승
- 금리 인상 → 채권 수익률↑ → 성장주 밸류에이션 하락
- 유가 상승 → 에너지 비용↑ → 항공/운송/화학 악재
- 중국 경기 부양 → 원자재 수요↑ → 철강/화학 호재

3단계 - 한국 주식 영향: 구체적 한국 섹터/종목에 어떤 영향?
(반도체, 2차전지, 금융주, 방산, 바이오, 유통, 건설 등)

절대 규칙:
1. 수치 없는 팩트는 팩트가 아님 (반드시 숫자 포함)
2. 투자 권유/예측 표현 절대 금지
3. 추론 근거 없는 섹터 나열 금지
4. 반드시 JSON 형식으로만 출력
5. 한국어로만 작성
6. **내부 메모/예시 표기 절대 금지**: "(예시 필요)", "(구체적인 예시 필요)", "예상치 명시 필요", "기사 참고" 같은 내부 메모는 절대 작성하지 말 것. 모든 텍스트는 최종 사용자가 읽는 완성된 콘텐츠.

표지 훅 규칙:
- 호재/악재 표기 없음
- 이슈 자체에만 집중
- 궁금증 유발 (예: "파월이 입을 열었다", "이 숫자가 시장을 흔든다")
- 10자 이내, 강렬하게
"""

    OLLAMA_BASE_URL = "http://localhost:11434/v1"
    OLLAMA_MODEL = "exaone3.5:7.8b"

    @staticmethod
    def _get_signal_emoji(signal: str) -> str:
        """Get signal emoji"""
        return {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}.get(signal, "⚪")

    def __init__(self):
        """Initialize ContentGenerator with Ollama availability check"""
        self.use_ollama = self._check_ollama_available()

        if self.use_ollama:
            self.client = OpenAI(
                base_url=self.OLLAMA_BASE_URL,
                api_key="ollama"  # Ollama doesn't require real API key
            )
            logger.info(f"EXAONE 3.5 7.8B via Ollama: Available")
        else:
            logger.warning("Ollama not available. Using template fallback mode.")

    def _check_ollama_available(self) -> bool:
        """
        Check if Ollama is running and model is available

        Returns:
            True if Ollama is available, False otherwise
        """
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name") for m in models]
                if self.OLLAMA_MODEL in model_names:
                    return True
                else:
                    logger.warning(f"Model {self.OLLAMA_MODEL} not found in Ollama. Available: {model_names}")
                    return False
            else:
                return False
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    def _unload_model(self):
        """Unload EXAONE model from VRAM after generation"""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": self.OLLAMA_MODEL, "keep_alive": 0},
                timeout=5
            )
            if response.status_code == 200:
                logger.info("EXAONE model unloaded from VRAM")
        except Exception as e:
            logger.debug(f"Model unload failed (non-critical): {e}")

    def _call_exaone(self, user_prompt: str, response_format: str = "json") -> str:
        """
        Call EXAONE 3.5 via Ollama

        Args:
            user_prompt: User prompt
            response_format: Expected format ("json" or "text")

        Returns:
            Generated text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            generated = response.choices[0].message.content
            return generated

        except Exception as e:
            logger.error(f"EXAONE generation failed: {e}")
            return ""

    def generate_instagram_script(self, cluster: Dict) -> Dict:
        """
        Generate Instagram 5-slide script

        Args:
            cluster: Cluster dict with cluster_id, signal, affected_sectors, articles

        Returns:
            Instagram script dict with slides, hashtags, disclaimer
        """
        if not self.use_ollama:
            return TemplateFallback.generate_instagram_script(cluster)

        # Build prompt with article data
        cluster_id = cluster.get("cluster_id", "unknown")
        signal = cluster.get("signal", "neutral")
        affected_sectors = cluster.get("affected_sectors", [])
        articles = cluster.get("articles", [])[:3]  # Max 3 articles

        # Extract article summaries
        article_texts = []
        for i, article in enumerate(articles, 1):
            title = article.get("title", "")
            summary = article.get("summary", "")[:200]  # First 200 chars
            source = article.get("source", "")
            article_texts.append(f"기사 {i} ({source}):\n제목: {title}\n요약: {summary}")

        articles_str = "\n\n".join(article_texts)

        user_prompt = f"""다음 경제 뉴스 기사들을 분석하여 Instagram 5-slide 카드 뉴스 스크립트를 JSON 형식으로 생성하세요.

기사 데이터:
{articles_str}

출력 형식 (JSON):
{{
  "cluster_id": "{cluster_id}",
  "macro_issue": "이슈 한 줄 요약",
  "pexels_keyword": "Pexels 검색용 영어 키워드 (구체적으로)",
  "hook_title": "표지 훅 (10자 이내, 순한국어, 호재/악재 표기 없음)",
  "reasoning_chain": "CoT 추론 경로 (내부용, 표시 안함) - 1단계 이슈 파악 → 2단계 경제 메커니즘 → 3단계 한국 주식 영향",
  "slides": [
    {{
      "slide_num": 1,
      "type": "cover",
      "hook_title": "훅 질문 (10자 이내, 순한국어)",
      "one_line": "한 줄 요약 (25자 이내)",
      "sources": ["Reuters", "Bloomberg"]
    }},
    {{
      "slide_num": 2,
      "type": "context",
      "title": "무슨 일이?",
      "facts": [
        "핵심 팩트 1 (구체적 수치 포함)",
        "핵심 팩트 2 (수치 포함)",
        "핵심 팩트 3 (수치 포함)"
      ],
      "source": "Reuters, Bloomberg 등"
    }},
    {{
      "slide_num": 3,
      "type": "beneficiary",
      "title": "수혜주는?",
      "sectors": [
        {{
          "name": "섹터명 (예: 반도체, 2차전지)",
          "reason": "추론 근거 포함 이유 (40자 이내)",
          "example_stocks": ["삼성전자", "SK하이닉스"]
        }}
      ],
      "fact": "호재 관련 핵심 팩트 (수치 포함)"
    }},
    {{
      "slide_num": 4,
      "type": "victim",
      "title": "주의할 섹터는?",
      "sectors": [
        {{
          "name": "섹터명",
          "reason": "타격 이유 (구체적으로)",
          "example_stocks": ["종목1", "종목2"]
        }}
      ],
      "fact": "악재 관련 핵심 팩트"
    }},
    {{
      "slide_num": 5,
      "type": "conclusion",
      "title": "오늘의 핵심",
      "summaries": [
        {{"signal": "bullish", "text": "수혜 요약"}},
        {{"signal": "bearish", "text": "악재 요약"}},
        {{"signal": "neutral", "text": "주의 포인트"}}
      ],
      "watch_point": "투자자 주목 포인트 (50자 이내)",
      "cta": "더 궁금하다면 댓글에 '분석' 남겨주세요",
      "cta_sub": "→ 상세 리포트 DM으로 드립니다"
    }}
  ],
  "hashtags": ["#경제", "#투자", "#주식", "#ETF", "#시그널피드", "#뉴스", "#금융", "#재테크", "#자산관리", "#투자정보"],
  "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
}}

중요 규칙:
1. reasoning_chain에 CoT 추론 경로 명시 (1단계 이슈 → 2단계 메커니즘 → 3단계 한국 영향)
2. hook_title: 호재/악재 표기 없음, 이슈 자체에만 집중, 10자 이내
3. facts: 반드시 구체적 수치 포함
4. sectors: 추론 근거 포함, example_stocks 1-2개 명시
5. 예측 표현 절대 금지
"""

        try:
            response = self._call_exaone(user_prompt)

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()

            result = json.loads(response)

            # Validate required fields
            if "slides" in result and len(result["slides"]) == 5:
                logger.info(f"Generated Instagram script for cluster {cluster_id}")
                return result
            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            logger.error(f"EXAONE Instagram generation failed: {e}. Using fallback.")
            return TemplateFallback.generate_instagram_script(cluster)

    def generate_shorts_script(self, cluster: Dict) -> Dict:
        """
        Generate YouTube Shorts 60sec narration script

        Args:
            cluster: Cluster dict

        Returns:
            Shorts script dict with narration, duration, title, description, tags
        """
        if not self.use_ollama:
            return TemplateFallback.generate_shorts_script(cluster)

        cluster_id = cluster.get("cluster_id", "unknown")
        signal = cluster.get("signal", "neutral")
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        affected_sectors = cluster.get("affected_sectors", [])
        articles = cluster.get("articles", [])[:3]

        # Extract article summaries
        article_texts = []
        for i, article in enumerate(articles, 1):
            title = article.get("title", "")
            summary = article.get("summary", "")[:200]
            article_texts.append(f"기사 {i}: {title}\n{summary}")

        articles_str = "\n\n".join(article_texts)

        user_prompt = f"""다음 경제 뉴스 기사들을 분석하여 YouTube Shorts 60초 나레이션 스크립트를 JSON 형식으로 생성하세요.

이슈: {cluster_label}
시그널: {signal}
관련 섹터: {', '.join(affected_sectors) if affected_sectors else '없음'}

기사 데이터:
{articles_str}

출력 형식 (JSON):
{{
  "cluster_id": "{cluster_id}",
  "narration": "약 150 단어의 한국어 나레이션 (60초 분량)",
  "duration_estimate": 60,
  "title": "60자 이내",
  "description": "설명",
  "tags": ["경제", "투자", ...]
}}

나레이션 구조:
1. 인사 (안녕하세요 시그널피드입니다)
2. 핵심 이슈 설명 (팩트만)
3. 시그널 분석 결과
4. 면책조항 (본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다)
5. 구독 요청

주의: 예측 표현 사용 금지. 팩트만 작성.
"""

        try:
            response = self._call_exaone(user_prompt)

            # Parse JSON
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()

            result = json.loads(response)

            if "narration" in result:
                logger.info(f"Generated Shorts script for cluster {cluster_id}")
                return result
            else:
                raise ValueError("Invalid response format")

        except Exception as e:
            logger.error(f"EXAONE Shorts generation failed: {e}. Using fallback.")
            return TemplateFallback.generate_shorts_script(cluster)

    def generate_all(self, clusters: List[Dict]) -> List[Dict]:
        """
        Generate scripts for all clusters

        Args:
            clusters: List of cluster dicts

        Returns:
            List of generated scripts (instagram + shorts combined)
        """
        logger.info(f"Generating content for {len(clusters)} clusters...")

        scripts = []

        for cluster in tqdm(clusters, desc="Generating scripts"):
            try:
                # Generate Instagram script
                instagram = self.generate_instagram_script(cluster)

                # Generate Shorts script
                shorts = self.generate_shorts_script(cluster)

                # Combine
                script = {
                    "cluster_id": cluster.get("cluster_id"),
                    "cluster_label": cluster.get("cluster_label"),
                    "signal": cluster.get("signal"),
                    "instagram": instagram,
                    "shorts": shorts
                }

                scripts.append(script)

                logger.info(f"Generated script for cluster {cluster.get('cluster_id')}: {cluster.get('cluster_label')}")

            except Exception as e:
                logger.error(f"Error generating script for cluster {cluster.get('cluster_id')}: {e}")
                continue

        # Unload model from VRAM after all generations
        if self.use_ollama:
            self._unload_model()

        logger.info(f"Generated {len(scripts)} scripts")
        return scripts

    def save(self, scripts: List[Dict], output_path: str = "data/3_generated/scripts.json") -> None:
        """
        Save scripts to JSON

        Args:
            scripts: List of script dicts
            output_path: Output file path
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(scripts)} scripts to {output_path}")

    def run(self, input_path: str = "data/4_classified/classified.jsonl") -> List[Dict]:
        """
        Full pipeline: load → group by cluster → generate → save → return

        Args:
            input_path: Input file path (classified articles)

        Returns:
            Generated scripts
        """
        import jsonlines

        logger.info("=" * 70)
        logger.info("SignalFeed Content Generation Started")
        logger.info("=" * 70)

        # Load classified articles
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
            # Get dominant signal and affected sectors from first article
            first_article = cluster_articles[0]

            cluster_data = {
                "cluster_id": cluster_id,
                "cluster_label": first_article.get("cluster_label", ""),
                "signal": first_article.get("signal", "neutral"),
                "affected_sectors": first_article.get("affected_sectors", []),
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
    # Test run
    generator = ContentGenerator()

    if os.path.exists("data/4_classified/classified.jsonl"):
        scripts = generator.run()
        logger.info(f"Generated {len(scripts)} scripts")
    else:
        logger.warning("No classified data found. Run classifier first.")
