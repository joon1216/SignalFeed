"""
SignalFeed Content Generator
EXAONE 3.5 기반 Instagram 5-slide + YouTube Shorts 스크립트 생성
"""

import os
import json
import logging
import requests
from typing import List, Dict, Optional
from collections import defaultdict
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TemplateFallback:
    """EXAONE API 없을 때 템플릿 기반 폴백"""

    SIGNAL_EMOJI = {
        "bullish": "🟢",
        "bearish": "🔴",
        "neutral": "⚪"
    }

    @staticmethod
    def generate_instagram_script(cluster: Dict) -> Dict:
        """템플릿 기반 Instagram 스크립트 생성"""
        signal = cluster.get("signal", "neutral")
        cluster_label = cluster.get("cluster_label", "경제 뉴스")
        affected_sectors = cluster.get("affected_sectors", [])
        articles = cluster.get("articles", [])

        # Slide 1: Cover
        slide1 = {
            "slide_num": 1,
            "title": cluster_label[:20],
            "body": f"{signal.upper()} 시그널 발생\n\n관련 섹터: {', '.join(affected_sectors[:3]) if affected_sectors else '전체 시장'}",
            "signal_emoji": TemplateFallback.SIGNAL_EMOJI[signal]
        }

        # Slide 2: Bullish
        slide2 = {
            "slide_num": 2,
            "title": "호재 요인",
            "body": "• 경제 성장 지표 개선\n• 기업 실적 증가\n• 정책 지원 확대",
            "sectors": affected_sectors[:3] if signal == "bullish" else []
        }

        # Slide 3: Bearish
        slide3 = {
            "slide_num": 3,
            "title": "악재 요인",
            "body": "• 인플레이션 우려\n• 금리 인상 압력\n• 글로벌 불확실성",
            "sectors": affected_sectors[:3] if signal == "bearish" else []
        }

        # Slide 4: Neutral/Caution
        slide4 = {
            "slide_num": 4,
            "title": "중립 요인",
            "body": "• 시장 관망세 지속\n• 혼조세 나타남\n• 변동성 확대 가능",
            "caution": "AI 분석 결과이며, 실제 시장 상황과 다를 수 있습니다."
        }

        # Slide 5: Conclusion
        slide5 = {
            "slide_num": 5,
            "title": "요약",
            "body": f"{cluster_label}\n\n{signal.upper()} 시그널\n\n모든 투자 판단은 본인 책임입니다.",
            "cta": "자세한 분석은 프로필 링크"
        }

        return {
            "cluster_id": str(cluster.get("cluster_id", -1)),
            "signal": signal,
            "slides": [slide1, slide2, slide3, slide4, slide5],
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
    """EXAONE 3.5 기반 콘텐츠 생성기"""

    SYSTEM_PROMPT = """You are a Korean financial news content writer for SignalFeed.
Your job is to explain global economic news to Korean MZ generation investors (20-35).
STRICT RULES:

1. Write ONLY in Korean
2. NEVER predict stock prices or future market direction
3. NEVER recommend buy/sell/hold
4. ONLY use facts from the provided news data
5. Keep language simple and clear (high school level)
6. Always end with: "모든 투자 판단은 본인 책임입니다"
"""

    BANNED_WORDS = ["예상", "전망", "오를", "떨어질", "추천", "매수", "매도"]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ContentGenerator

        Args:
            api_key: EXAONE API key (if None, uses template fallback)
        """
        self.api_key = api_key
        self.use_llm = api_key is not None

        if not self.use_llm:
            logger.warning("EXAONE API key not provided. Using template fallback mode.")

    def _call_exaone(self, prompt: str) -> str:
        """
        Call EXAONE 3.5 API

        Args:
            prompt: User prompt

        Returns:
            Generated text
        """
        # NOTE: EXAONE API endpoint is placeholder - LG AI API details not public yet
        # Using template fallback for now
        logger.warning("EXAONE API not yet available. Using template fallback.")
        return ""

    def generate_instagram_script(self, cluster: Dict) -> Dict:
        """
        Generate Instagram 5-slide script

        Args:
            cluster: Cluster dict with cluster_label, signal, affected_sectors, articles

        Returns:
            Instagram script dict with slides, hashtags, disclaimer
        """
        # Use template fallback (EXAONE API not public yet)
        return TemplateFallback.generate_instagram_script(cluster)

    def generate_shorts_script(self, cluster: Dict) -> Dict:
        """
        Generate YouTube Shorts script

        Args:
            cluster: Cluster dict

        Returns:
            Shorts script dict with narration, duration, title, description, tags
        """
        # Use template fallback (EXAONE API not public yet)
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
        logger.info("=" * 70)
        logger.info("SignalFeed Content Generator Started")
        logger.info("=" * 70)

        # Load classified articles
        logger.info(f"Loading classified articles from {input_path}...")
        articles = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    articles.append(json.loads(line))

        logger.info(f"Loaded {len(articles)} articles")

        # Group by cluster_id
        clusters_dict = defaultdict(lambda: {
            "cluster_id": -1,
            "cluster_label": "",
            "signal": "neutral",
            "affected_sectors": [],
            "articles": []
        })

        for article in articles:
            cluster_id = article.get("cluster_id", -1)
            if cluster_id >= 0:
                clusters_dict[cluster_id]["cluster_id"] = cluster_id
                clusters_dict[cluster_id]["cluster_label"] = article.get("cluster_label", "")
                clusters_dict[cluster_id]["signal"] = article.get("signal", "neutral")

                # Aggregate affected_sectors
                sectors = article.get("affected_sectors", [])
                for sector in sectors:
                    if sector not in clusters_dict[cluster_id]["affected_sectors"]:
                        clusters_dict[cluster_id]["affected_sectors"].append(sector)

                clusters_dict[cluster_id]["articles"].append(article)

        clusters = list(clusters_dict.values())
        logger.info(f"Grouped into {len(clusters)} clusters")

        # Generate scripts
        scripts = self.generate_all(clusters)

        # Save
        output_path = "data/5_generated/scripts.json"
        self.save(scripts, output_path)

        logger.info("=" * 70)
        logger.info(f"Content Generation Complete: {len(scripts)} scripts")
        logger.info("=" * 70)

        return scripts


if __name__ == "__main__":
    # Test run
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("EXAONE_API_KEY")

    generator = ContentGenerator(api_key=api_key)

    # Use sample data if exists
    sample_path = "data/4_classified/sample_classified.jsonl"
    if os.path.exists(sample_path):
        scripts = generator.run(sample_path)
        logger.info(f"Generated {len(scripts)} sample scripts")
    else:
        logger.warning(f"Sample data not found at {sample_path}")
