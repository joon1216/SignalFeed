"""
SignalFeed Fake News Filter
5-layer defense system
"""

import logging
import re
from typing import List, Dict
from collections import defaultdict
from difflib import SequenceMatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FakeNewsFilter:
    """5계층 가짜뉴스 방어 시스템"""

    # Layer 1: Source whitelist
    SOURCE_WHITELIST = {
        "Reuters",
        "Bloomberg",
        "Financial Times",
        "The Wall Street Journal",
        "CNBC",
        "MarketWatch",
        "Associated Press",
        "AP News"
    }

    def __init__(self):
        """Initialize FakeNewsFilter"""
        pass

    def layer1_whitelist(self, articles: List[Dict]) -> List[Dict]:
        """
        Layer 1: Source whitelist filtering

        Args:
            articles: List of articles

        Returns:
            Filtered articles (whitelist only)
        """
        logger.info("Layer 1: Source whitelist filtering...")
        initial_count = len(articles)

        filtered = [
            article for article in articles
            if article.get("source", "") in self.SOURCE_WHITELIST
        ]

        filtered_count = initial_count - len(filtered)
        logger.info(f"Layer 1: Filtered {filtered_count} articles (non-whitelisted sources)")
        logger.info(f"Layer 1: Remaining {len(filtered)} articles")

        return filtered

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity (0-1)"""
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()

    def layer2_cross_validate(
        self,
        articles: List[Dict],
        min_sources: int = 3
    ) -> List[Dict]:
        """
        Layer 2: Cross-validation (minimum 3 sources per issue)

        Args:
            articles: List of articles
            min_sources: Minimum number of sources required

        Returns:
            Articles with 'confirmed' field added
        """
        logger.info(f"Layer 2: Cross-validation (min {min_sources} sources)...")

        # Group articles by similar titles
        groups = []
        remaining = list(articles)

        while remaining:
            current = remaining.pop(0)
            current_title = current.get("title", "")
            if not current_title:
                continue

            # Find similar articles
            group = [current]
            to_remove = []

            for i, article in enumerate(remaining):
                title = article.get("title", "")
                if self._title_similarity(current_title, title) > 0.7:
                    group.append(article)
                    to_remove.append(i)

            # Remove grouped articles from remaining
            for i in reversed(to_remove):
                remaining.pop(i)

            groups.append(group)

        # Mark confirmed/unconfirmed based on unique sources
        result = []
        for group in groups:
            unique_sources = set(article.get("source", "") for article in group)
            is_confirmed = len(unique_sources) >= min_sources

            for article in group:
                article["confirmed"] = is_confirmed
                result.append(article)

        confirmed_count = sum(1 for a in result if a.get("confirmed", False))
        unconfirmed_count = len(result) - confirmed_count

        logger.info(f"Layer 2: {confirmed_count} confirmed, {unconfirmed_count} unconfirmed")
        return result

    def layer3_llm_screen(self, articles: List[Dict], openai_key: str) -> List[Dict]:
        """
        Layer 3: LLM screening for contradictions/anomalies

        Args:
            articles: List of articles
            openai_key: OpenAI API key

        Returns:
            Articles with 'llm_verified' field added
        """
        logger.info("Layer 3: LLM screening (GPT-4o-mini)...")

        # TODO: Implement GPT-4o-mini verification in future phase
        # For now, mark all as verified (placeholder)
        for article in articles:
            article["llm_verified"] = True

        logger.info(f"Layer 3: Verified {len(articles)} articles (placeholder)")
        return articles

    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text"""
        # Match patterns like: +500%, -30.5%, 1000%, etc.
        pattern = r'[-+]?\d+\.?\d*%?'
        matches = re.findall(pattern, text)

        numbers = []
        for match in matches:
            try:
                # Remove % sign if present
                num_str = match.replace('%', '')
                numbers.append(float(num_str))
            except ValueError:
                continue

        return numbers

    def layer4_anomaly_detect(self, articles: List[Dict]) -> List[Dict]:
        """
        Layer 4: Statistical anomaly detection

        Args:
            articles: List of articles

        Returns:
            Articles with 'anomaly_flagged' field added
        """
        logger.info("Layer 4: Anomaly detection...")

        # Define anomaly thresholds
        EXTREME_PERCENT_CHANGE = 100.0  # ±100% in one day
        EXTREME_VALUE = 10000.0  # Very large numbers

        flagged_count = 0

        for article in articles:
            title = article.get("title", "")
            summary = article.get("summary", "")
            combined_text = f"{title} {summary}"

            # Extract numbers
            numbers = self._extract_numbers(combined_text)

            # Check for extreme values
            is_anomaly = False
            for num in numbers:
                if abs(num) > EXTREME_PERCENT_CHANGE or abs(num) > EXTREME_VALUE:
                    is_anomaly = True
                    break

            article["anomaly_flagged"] = is_anomaly

            if is_anomaly:
                flagged_count += 1

        logger.info(f"Layer 4: Flagged {flagged_count} anomalies")
        return articles

    def layer5_disclaimer(self, articles: List[Dict]) -> List[Dict]:
        """
        Layer 5: Add disclaimer to all articles

        Args:
            articles: List of articles

        Returns:
            Articles with 'disclaimer' field added
        """
        logger.info("Layer 5: Adding disclaimers...")

        disclaimer_text = "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다"

        for article in articles:
            article["disclaimer"] = disclaimer_text

        logger.info(f"Layer 5: Added disclaimer to {len(articles)} articles")
        return articles

    def run(self, articles: List[Dict], openai_key: str = None) -> List[Dict]:
        """
        Run all 5 layers sequentially

        Args:
            articles: List of articles
            openai_key: OpenAI API key (optional, for Layer 3)

        Returns:
            Filtered and validated articles
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Fake News Filter Started")
        logger.info(f"Input: {len(articles)} articles")
        logger.info("=" * 70)

        # Layer 1: Whitelist
        articles = self.layer1_whitelist(articles)

        # Layer 2: Cross-validation
        articles = self.layer2_cross_validate(articles)

        # Layer 3: LLM screening (optional)
        if openai_key:
            articles = self.layer3_llm_screen(articles, openai_key)
        else:
            logger.warning("Layer 3: Skipped (no OpenAI key provided)")

        # Layer 4: Anomaly detection
        articles = self.layer4_anomaly_detect(articles)

        # Layer 5: Disclaimer
        articles = self.layer5_disclaimer(articles)

        logger.info("=" * 70)
        logger.info(f"Fake News Filter Complete: {len(articles)} articles")
        logger.info("=" * 70)

        return articles


if __name__ == "__main__":
    # Test run
    test_articles = [
        {
            "id": "1",
            "title": "Apple stock rises 2% on strong earnings",
            "summary": "Apple Inc. reported better-than-expected quarterly earnings.",
            "source": "Reuters",
            "url": "https://example.com/1"
        },
        {
            "id": "2",
            "title": "Apple shares up 2.5% after earnings beat",
            "summary": "Apple's Q4 results exceeded analyst expectations.",
            "source": "Bloomberg",
            "url": "https://example.com/2"
        },
        {
            "id": "3",
            "title": "Tesla stock jumps 500% in one day",
            "summary": "Tesla shares skyrocket amid anomaly.",
            "source": "Unknown Blog",
            "url": "https://example.com/3"
        },
        {
            "id": "4",
            "title": "Fed raises interest rates by 0.25%",
            "summary": "Federal Reserve announces rate hike.",
            "source": "CNBC",
            "url": "https://example.com/4"
        }
    ]

    filter_system = FakeNewsFilter()
    filtered = filter_system.run(test_articles)

    logger.info(f"\nFinal result: {len(filtered)} articles")
    for article in filtered:
        logger.info(f"- {article['title']} (confirmed: {article.get('confirmed')}, anomaly: {article.get('anomaly_flagged')})")
