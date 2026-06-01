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

    SYSTEM_PROMPT = """당신은 SignalFeed의 한국어 경제 뉴스 카드뉴스 작성자입니다.
5장의 카드뉴스가 하나의 완결된 스토리를 형성해야 합니다.
독자가 1→2→3→4→5장을 보면서 자연스럽게 이해하고 행동할 수 있어야 합니다.

스토리 구조:
1장 (표지): 독자의 호기심을 자극하는 짧고 강렬한 질문 (순한국어만 사용)
2장 (맥락): 무슨 일이 있었는지 핵심 팩트 3가지 (구체적 수치 포함)
3장 (호재): 이 이슈로 수혜받는 섹터와 구체적 이유
4장 (악재): 이 이슈로 타격받는 섹터와 구체적 이유
5장 (결론): 핵심 요약 3줄 + 투자자가 주목할 포인트

절대 규칙:
1. 훅 타이틀은 반드시 순한국어만 사용 (영어 단어 절대 금지)
2. 팩트는 구체적 수치 포함 (예: "3.2% 상승", "0.25%p 인하")
3. 예측/권유 표현 절대 금지 ("오를 것", "떨어질 것", "기대됩니다", "추천" 등)
4. 각 슬라이드는 이전 슬라이드와 자연스럽게 연결되어야 함
5. 반드시 JSON 형식으로만 출력
6. 모든 내용은 한국어로 작성
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

이슈 시그널: {signal}
관련 섹터: {', '.join(affected_sectors) if affected_sectors else '없음'}

기사 데이터:
{articles_str}

출력 형식 (JSON):
{{
  "cluster_id": "{cluster_id}",
  "signal": "{signal}",
  "pexels_keyword": "Pexels 검색용 영어 키워드 (구체적으로, 예: 'federal reserve building', 'dollar bills money close up')",
  "hook_title": "순한국어 훅 질문 (15자 이내, 2줄, \\n으로 구분)",
  "slides": [
    {{
      "slide_num": 1,
      "type": "cover",
      "hook_title": "훅 질문 (순한국어)",
      "signal_emoji": "{self._get_signal_emoji(signal)}",
      "signal_text": "호재|악재|중립",
      "one_line": "한 줄 요약 (20자 이내)"
    }},
    {{
      "slide_num": 2,
      "type": "context",
      "title": "무슨 일이?",
      "facts": [
        "핵심 팩트 1 (구체적 수치 포함)",
        "핵심 팩트 2",
        "핵심 팩트 3"
      ],
      "source": "Reuters, Bloomberg 등"
    }},
    {{
      "slide_num": 3,
      "type": "bullish",
      "title": "호재",
      "sectors": [
        {{"name": "섹터명", "reason": "수혜 이유 (구체적으로, 40자 이내)"}},
        {{"name": "섹터명", "reason": "이유"}}
      ],
      "fact": "호재 관련 핵심 팩트 (수치 포함)"
    }},
    {{
      "slide_num": 4,
      "type": "bearish",
      "title": "악재",
      "sectors": [
        {{"name": "섹터명", "reason": "타격 이유 (구체적으로)"}},
        {{"name": "섹터명", "reason": "이유"}}
      ],
      "fact": "악재 관련 핵심 팩트"
    }},
    {{
      "slide_num": 5,
      "type": "conclusion",
      "title": "오늘의 결론",
      "summaries": [
        {{"signal": "bullish", "text": "호재 요약 (40자)"}},
        {{"signal": "bearish", "text": "악재 요약 (40자)"}},
        {{"signal": "neutral", "text": "주의 포인트 (40자)"}}
      ],
      "watch_point": "투자자가 주목할 포인트 (50자 이내)",
      "cta": "더 궁금하다면 댓글에 '분석' 남겨주세요",
      "cta_sub": "→ 상세 리포트 DM으로 드립니다"
    }}
  ],
  "hashtags": ["#경제", "#투자", "#주식", "#ETF", "#시그널피드", "#뉴스", "#금융", "#재테크", "#자산관리", "#투자정보"],
  "disclaimer": "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"
}}

중요 규칙:
1. pexels_keyword: 이슈와 가장 관련된 구체적인 영어 키워드 (예: "inflation" → "dollar bills money close up")
2. hook_title: 반드시 순한국어만 사용 (영어 단어 절대 금지)
3. facts: 반드시 구체적 수치 포함 (예: "3.2% 상승", "0.25%p 인하", "1조 달러")
4. sectors: 각 슬라이드마다 2~3개 섹터명 필수, reason은 구체적으로 (40자 이내)
5. 예측 표현 절대 금지 ("오를 것", "떨어질 것", "기대됩니다", "예상됩니다")
6. 각 슬라이드는 스토리로 자연스럽게 연결되어야 함
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

    def save(self, scripts: List[Dict], output_path: str = "data/5_generated/scripts.json") -> None:
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
