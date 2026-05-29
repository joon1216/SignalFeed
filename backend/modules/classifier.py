"""
SignalFeed Signal Classifier
FinBERT (ProsusAI/finbert) 기반 bullish/bearish/neutral 분류
"""

import os
import json
import logging
from typing import List, Dict, Optional
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm
from sklearn.metrics import precision_recall_fscore_support, accuracy_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalClassifier:
    """FinBERT 기반 신호 분류기 (bullish/bearish/neutral)"""

    # Label mapping: FinBERT outputs → SignalFeed signals
    LABEL_MAPPING = {
        "positive": "bullish",
        "negative": "bearish",
        "neutral": "neutral"
    }

    # Reverse mapping for evaluation
    REVERSE_MAPPING = {
        "bullish": "positive",
        "bearish": "negative",
        "neutral": "neutral"
    }

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize SignalClassifier

        Args:
            model_path: Path to local fine-tuned model (if None, loads ProsusAI/finbert from HF)
        """
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading local model from {model_path}...")
            self.model_name = model_path
        else:
            logger.info("Loading ProsusAI/finbert from Hugging Face...")
            self.model_name = "ProsusAI/finbert"

        # Load tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)

        # Set device (cuda if available, else cpu)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()

        logger.info(f"Model loaded on device: {self.device}")

    def classify_single(self, text: str) -> Dict:
        """
        단일 텍스트 분류

        Args:
            text: Article title + summary (concatenated)

        Returns:
            {"signal": "bullish|bearish|neutral", "confidence": float, "raw_scores": {...}}
        """
        # Tokenize (max 512 tokens)
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=True
        ).to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits

        # Softmax to get probabilities
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        # Get predicted class
        pred_idx = torch.argmax(probs).item()

        # Map FinBERT labels (0=positive, 1=negative, 2=neutral) to signals
        finbert_labels = ["positive", "negative", "neutral"]
        predicted_label = finbert_labels[pred_idx]
        signal = self.LABEL_MAPPING[predicted_label]
        confidence = probs[pred_idx].item()

        # Raw scores for all classes
        raw_scores = {
            "bullish": probs[0].item(),
            "bearish": probs[1].item(),
            "neutral": probs[2].item()
        }

        return {
            "signal": signal,
            "confidence": confidence,
            "raw_scores": raw_scores
        }

    def classify_batch(
        self,
        articles: List[Dict],
        batch_size: int = 32
    ) -> List[Dict]:
        """
        배치 분류

        Args:
            articles: List of articles with "title" and "summary" fields
            batch_size: Batch size for processing

        Returns:
            Enriched articles with signal, confidence, raw_scores
        """
        logger.info(f"Classifying {len(articles)} articles in batches of {batch_size}...")

        for i in tqdm(range(0, len(articles), batch_size), desc="Classifying batches"):
            batch = articles[i:i + batch_size]

            for article in batch:
                try:
                    # Concatenate title + summary
                    title = article.get("title", "")
                    summary = article.get("summary", "")
                    text = f"{title} {summary}"

                    # Classify
                    result = self.classify_single(text)

                    # Add fields to article
                    article["signal"] = result["signal"]
                    article["confidence"] = result["confidence"]
                    article["raw_scores"] = result["raw_scores"]

                    # Warn if low confidence
                    if result["confidence"] < 0.5:
                        logger.warning(f"Low confidence ({result['confidence']:.2f}) for: {title[:50]}...")

                except Exception as e:
                    logger.error(f"Error classifying article {article.get('id', 'unknown')}: {e}")
                    # Skip article on error
                    article["signal"] = "neutral"
                    article["confidence"] = 0.0
                    article["raw_scores"] = {"bullish": 0.0, "bearish": 0.0, "neutral": 1.0}

        logger.info(f"Classified {len(articles)} articles")
        return articles

    def evaluate(self, labeled_articles: List[Dict]) -> Dict:
        """
        평가: FinBERT vs GPT-4o-mini labels

        Args:
            labeled_articles: Articles with both "signal" (FinBERT) and GPT labels

        Returns:
            Evaluation dict with precision, recall, F1, accuracy
        """
        logger.info("Evaluating classifier against labeled data...")

        # Extract predictions and ground truth
        y_true = []
        y_pred = []

        for article in labeled_articles:
            # GPT label (ground truth) - may be in "signal" or "label" field
            gpt_label = article.get("label") or article.get("signal")
            # FinBERT prediction
            finbert_signal = article.get("signal")

            if gpt_label and finbert_signal:
                y_true.append(gpt_label)
                y_pred.append(finbert_signal)

        if not y_true:
            logger.warning("No labeled data found for evaluation")
            return {}

        # Calculate metrics
        labels = ["bullish", "bearish", "neutral"]
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=labels, average=None, zero_division=0
        )

        accuracy = accuracy_score(y_true, y_pred)

        # Build evaluation dict
        eval_dict = {
            "accuracy": accuracy,
            "precision": {label: precision[i] for i, label in enumerate(labels)},
            "recall": {label: recall[i] for i, label in enumerate(labels)},
            "f1": {label: f1[i] for i, label in enumerate(labels)},
            "support": {label: int(support[i]) for i, label in enumerate(labels)}
        }

        logger.info(f"Accuracy: {accuracy:.3f}")
        logger.info(f"F1 scores: {eval_dict['f1']}")

        return eval_dict

    def save_local(self, output_dir: str = "models/signal_classifier") -> None:
        """
        모델을 로컬에 저장

        Args:
            output_dir: Output directory
        """
        logger.info(f"Saving model to {output_dir}...")

        os.makedirs(output_dir, exist_ok=True)

        # Save model and tokenizer
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        logger.info(f"Model saved to {output_dir}")

    def run(self, input_path: str = "data/2_labeled/labeled.jsonl") -> List[Dict]:
        """
        전체 파이프라인: load → classify → save → return

        Args:
            input_path: Input file path

        Returns:
            Classified articles
        """
        logger.info("=" * 70)
        logger.info("SignalFeed Signal Classifier Started")
        logger.info("=" * 70)

        # Load articles
        logger.info(f"Loading articles from {input_path}...")
        articles = []
        with open(input_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    articles.append(json.loads(line))

        logger.info(f"Loaded {len(articles)} articles")

        # Classify
        classified_articles = self.classify_batch(articles)

        # Save
        output_path = "data/4_classified/classified.jsonl"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for article in classified_articles:
                f.write(json.dumps(article, ensure_ascii=False) + '\n')

        logger.info(f"Saved {len(classified_articles)} classified articles to {output_path}")

        logger.info("=" * 70)
        logger.info(f"Signal Classification Complete: {len(classified_articles)} articles")
        logger.info("=" * 70)

        return classified_articles


if __name__ == "__main__":
    # Test run
    classifier = SignalClassifier()

    # Use sample labeled data if exists
    sample_path = "data/2_labeled/labeled.jsonl"
    if os.path.exists(sample_path):
        articles = classifier.run(sample_path)
        logger.info(f"Classified {len(articles)} sample articles")
    else:
        logger.warning(f"Sample data not found at {sample_path}")
