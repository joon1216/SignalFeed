"""
SignalFeed Auto Labeler
GPT-4o-mini 기반 bullish/bearish/neutral 자동 레이블링
"""

import os
import json
import time
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoLabeler:
    """GPT-4o-mini 기반 자동 레이블러"""

    SYSTEM_PROMPT = """You are a financial news signal classifier.
Classify the news article as EXACTLY one of: bullish, bearish, neutral.

Rules:
- bullish: news that is positive for markets/economy/specific sectors
- bearish: news that is negative for markets/economy/specific sectors
- neutral: factual announcements with no clear directional impact

STRICT RULES:
1. Output ONLY a JSON object: {"signal": "bullish|bearish|neutral", "confidence": 0.0-1.0, "affected_sectors": ["sector1", "sector2"], "reason": "one sentence fact-based reason"}
2. NEVER predict future prices
3. NEVER recommend buy/sell
4. Base judgment ONLY on facts in the article
5. reason must be under 20 words"""

    def __init__(self):
        """Initialize AutoLabeler"""
        self.model = "gpt-4o-mini"

    def label_single(self, article: Dict, api_key: str) -> Dict:
        """
        단일 기사 레이블링

        Args:
            article: Article dict with title + summary
            api_key: OpenAI API key

        Returns:
            Enriched article dict with signal, confidence, affected_sectors, label_reason
        """
        try:
            client = OpenAI(api_key=api_key)

            # Extract title and summary (first 200 chars to minimize tokens)
            title = article.get("title", "")
            summary = article.get("summary", "")[:200]

            user_message = f"Title: {title}\n\nSummary: {summary}"

            # Call GPT-4o-mini
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=150
            )

            # Parse response
            response_text = response.choices[0].message.content.strip()

            # Try to parse JSON
            try:
                result = json.loads(response_text)

                # Validate required fields
                if "signal" not in result or result["signal"] not in ["bullish", "bearish", "neutral"]:
                    raise ValueError("Invalid signal value")

                # Add fields to article
                article["signal"] = result.get("signal", "neutral")
                article["confidence"] = float(result.get("confidence", 0.0))
                article["affected_sectors"] = result.get("affected_sectors", [])
                article["label_reason"] = result.get("reason", "")

            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse GPT response: {e}")
                # Fallback to neutral
                article["signal"] = "neutral"
                article["confidence"] = 0.0
                article["affected_sectors"] = []
                article["label_reason"] = "Failed to parse response"

        except Exception as e:
            logger.error(f"Error labeling article: {e}")
            # Fallback to neutral on any error
            article["signal"] = "neutral"
            article["confidence"] = 0.0
            article["affected_sectors"] = []
            article["label_reason"] = f"Error: {str(e)}"

        return article

    def label_batch(
        self,
        articles: List[Dict],
        api_key: str,
        batch_size: int = 20
    ) -> List[Dict]:
        """
        배치 레이블링

        Args:
            articles: List of articles
            api_key: OpenAI API key
            batch_size: Number of articles per batch

        Returns:
            Labeled articles
        """
        logger.info(f"Labeling {len(articles)} articles in batches of {batch_size}...")

        labeled = []

        # Process in batches with progress bar
        for i in tqdm(range(0, len(articles), batch_size), desc="Labeling batches"):
            batch = articles[i:i + batch_size]

            for article in batch:
                labeled_article = self.label_single(article, api_key)
                labeled.append(labeled_article)

            # Rate limiting: sleep 1s between batches
            if i + batch_size < len(articles):
                time.sleep(1)

        logger.info(f"Labeled {len(labeled)} articles")
        return labeled

    def validate_labels(self, articles: List[Dict]) -> Dict:
        """
        레이블 검증 및 통계

        Args:
            articles: Labeled articles

        Returns:
            Validation stats dict
        """
        logger.info("Validating labels...")

        # Calculate label distribution
        distribution = {"bullish": 0, "bearish": 0, "neutral": 0}
        confidence_by_label = {"bullish": [], "bearish": [], "neutral": []}
        low_confidence_count = 0

        for article in articles:
            signal = article.get("signal", "neutral")
            confidence = article.get("confidence", 0.0)

            # Update distribution
            if signal in distribution:
                distribution[signal] += 1

            # Track confidence
            if signal in confidence_by_label:
                confidence_by_label[signal].append(confidence)

            # Flag low confidence articles
            if confidence < 0.6:
                article["needs_review"] = True
                low_confidence_count += 1
            else:
                article["needs_review"] = False

        # Calculate average confidence per label
        avg_confidence = {}
        for label, confidences in confidence_by_label.items():
            if confidences:
                avg_confidence[label] = sum(confidences) / len(confidences)
            else:
                avg_confidence[label] = 0.0

        stats = {
            "total": len(articles),
            "distribution": distribution,
            "avg_confidence": avg_confidence,
            "low_confidence_count": low_confidence_count
        }

        logger.info(f"Label distribution: {distribution}")
        logger.info(f"Average confidence: {avg_confidence}")
        logger.warning(f"Low confidence articles (< 0.6): {low_confidence_count}")

        return stats

    def save(self, articles: List[Dict], output_path: str = "data/2_labeled/labeled.jsonl") -> None:
        """
        레이블된 기사 저장

        Args:
            articles: Labeled articles
            output_path: Output file path
        """
        # Create directory if not exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save as JSONL
        with open(output_path, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')

        logger.info(f"Saved {len(articles)} labeled articles to {output_path}")

    def run(
        self,
        input_path: str = "data/1_collected/news.jsonl",
        api_key: Optional[str] = None
    ) -> List[Dict]:
        """
        전체 파이프라인 실행: load → label_batch → validate → save → return

        Args:
            input_path: Input file path
            api_key: OpenAI API key (if None, tries to load from env)

        Returns:
            Labeled articles
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Auto Labeler Started")
        logger.info("=" * 70)

        # Load API key from env if not provided
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")

        # Load articles
        logger.info(f"Loading articles from {input_path}...")
        articles = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    articles.append(json.loads(line))

        logger.info(f"Loaded {len(articles)} articles")

        # Label batch
        labeled_articles = self.label_batch(articles, api_key)

        # Validate
        stats = self.validate_labels(labeled_articles)

        # Save
        self.save(labeled_articles)

        logger.info("=" * 70)
        logger.info(f"Auto Labeling Complete: {len(labeled_articles)} articles")
        logger.info(f"Distribution: {stats['distribution']}")
        logger.info("=" * 70)

        return labeled_articles


if __name__ == "__main__":
    # Test run (requires .env file with OPENAI_API_KEY)
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error("Missing OPENAI_API_KEY. Please set in .env")
    else:
        labeler = AutoLabeler()

        # Use sample data if exists, otherwise skip
        sample_path = "data/1_collected/sample_news.jsonl"
        if os.path.exists(sample_path):
            articles = labeler.run(sample_path, api_key)
            logger.info(f"Labeled {len(articles)} sample articles")
        else:
            logger.warning(f"Sample data not found at {sample_path}")
