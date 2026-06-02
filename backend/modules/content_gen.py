"""
SignalFeed Content Generator
Gemini 2.5 Flash 기반 Instagram 5-slide HTML 직접 생성
"""

import os
import json
import logging
import time
from typing import List, Dict
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
class SlideHTML(BaseModel):
    slide_num: int
    layout_intent: str  # CoT: 레이아웃 전략 먼저 서술
    html: str           # 완성된 단일 파일 HTML


class CardHTMLScript(BaseModel):
    issue_id: str
    pexels_keyword: str
    slides: List[SlideHTML]  # 5개


class TemplateFallback:
    """Gemini API 실패 시 템플릿 기반 폴백"""

    @staticmethod
    def generate_html_script(cluster: Dict) -> Dict:
        """템플릿 기반 HTML 스크립트 생성"""
        cluster_id = str(cluster.get("cluster_id", -1))
        cluster_label = cluster.get("cluster_label", "경제 뉴스")

        # 기본 HTML 템플릿
        base_template = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"/>
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{ pretendard: ['Pretendard', 'sans-serif'] }},
          colors: {{
            brand: {{ 50: '#f8fafc', 500: '#1e293b', 900: '#0f172a' }},
            stock: {{ up: '#ef4444', down: '#3b82f6' }}
          }}
        }}
      }}
    }}
  </script>
  <style>
    body {{ font-family: 'Pretendard', sans-serif; margin: 0; padding: 0; }}
    .word-keep {{ word-break: keep-all; overflow-wrap: break-word; }}
  </style>
</head>
<body>
  <div id="slide-1" class="relative w-[1080px] h-[1350px] overflow-hidden word-keep bg-brand-900 p-16">
    <div class="text-7xl font-extrabold tracking-tight text-white mb-8">
      {title}
    </div>
    <div class="text-2xl text-gray-300">
      {subtitle}
    </div>
  </div>
</body>
</html>"""

        slides = []
        for i in range(1, 6):
            html = base_template.format(
                title=f"슬라이드 {i}",
                subtitle=cluster_label
            )
            slides.append({
                "slide_num": i,
                "layout_intent": f"Fallback template slide {i}",
                "html": html
            })

        return {
            "issue_id": cluster_id,
            "pexels_keyword": "financial district skyscraper aerial",
            "slides": slides
        }


class ContentGenerator:
    """Gemini 2.5 Flash 기반 HTML 생성기"""

    SYSTEM_PROMPT = """당신은 Bloomberg와 토스증권의 수석 데이터 시각화 디자이너이자 10년 차 시니어 프론트엔드 개발자입니다.
글로벌 매크로 경제 뉴스를 분석하여 한국 주식 투자자용 Instagram 카드뉴스 5장 HTML을 생성합니다.

절대 규칙:
1. React, Vue 등 빌드 도구 사용 금지. 순수 HTML + Tailwind CSS CDN만 사용
2. 각 슬라이드는 반드시 서로 다른 레이아웃 사용 (동일 레이아웃 연속 사용 금지)
3. 5가지 레이아웃을 슬라이드 순서에 맞게 하나씩 배정:
   - Slide 1 [Hook]: Hero Title — 거대한 타이포그래피, 임팩트 있는 헤드라인
   - Slide 2 [Context]: Split 50:50 — 좌측 텍스트 + 우측 수치 대비
   - Slide 3 [Data]: Data Metric Grid — 2x2 카드 그리드, 수치 강조
   - Slide 4 [Analysis]: Expert Quote — 대형 인용구 스타일, 한국 증시 영향 분석
   - Slide 5 [CTA]: CTA List — 3줄 요약 + 저장/공유 유도 문구
4. 모든 텍스트 한국어, 수치 포함 필수
5. 예측/권유 표현 금지

Base Template (반드시 이 구조 사용):
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" crossorigin href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"/>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { pretendard: ['Pretendard', 'sans-serif'] },
          colors: {
            brand: { 50: '#f8fafc', 500: '#1e293b', 900: '#0f172a' },
            stock: { up: '#ef4444', down: '#3b82f6' }
          }
        }
      }
    }
  </script>
  <style>
    body { font-family: 'Pretendard', sans-serif; margin: 0; padding: 0; }
    .word-keep { word-break: keep-all; overflow-wrap: break-word; }
  </style>
</head>
<body>
  <div id="slide-1" class="relative w-[1080px] h-[1350px] overflow-hidden word-keep">
    <!-- 슬라이드 내용 -->
  </div>
</body>
</html>
```

Design System Rules:
1. Container: w-[1080px] h-[1350px] 고정 (절대 변경 금지)
2. Safe zone: 최상위 컨테이너 p-16 패딩 유지
3. 간격: gap-4, gap-8, mb-12 등 4배수 Tailwind 토큰만 사용
4. 임의 픽셀값 금지 (w-[234px] 같은 arbitrary values 금지)
5. 타이포그래피:
   - Display (Slide 1 제목): text-7xl font-extrabold tracking-tight
   - Title: text-5xl font-bold
   - Body: text-2xl font-medium leading-relaxed
   - Metrics (수치): text-6xl font-black tabular-nums tracking-tighter
6. 색상:
   - 배경: bg-white 또는 bg-brand-900 (다크)
   - 상승/호재: text-stock-up (빨강 #ef4444) — 한국 시장 표준
   - 하락/악재: text-stock-down (파랑 #3b82f6)
   - 브랜드: bg-brand-900, text-brand-900
7. SIGNALFEED 브랜드 로고: 각 슬라이드 좌상단 고정

Output:
- layout_intent에 레이아웃 전략 먼저 서술 (Chain of Thought)
- html에 완성된 단일 파일 HTML 반환
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

    def generate_html_script(self, cluster: Dict, max_retries: int = 3) -> Dict:
        """
        Generate Instagram 5-slide HTML with Gemini

        Args:
            cluster: Cluster dict with cluster_id, articles
            max_retries: Maximum retry attempts

        Returns:
            HTML script dict
        """
        if not self.use_gemini:
            logger.warning("⚠️ Fallback mode (no Gemini API key)")
            return TemplateFallback.generate_html_script(cluster)

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

        user_prompt = f"""{self.SYSTEM_PROMPT}

다음 경제 뉴스 기사들을 분석하여 Instagram 5-slide 카드뉴스 HTML을 생성하세요.

기사 데이터:
{articles_str}

출력:
- issue_id: "{cluster_id}"
- pexels_keyword: 구체적인 영어 검색어 (예: "federal reserve building washington")
- slides: 5개 슬라이드 배열
  - slide_num: 1~5
  - layout_intent: 레이아웃 전략 설명 (CoT)
  - html: 완성된 HTML (Base Template 구조 필수)

중요:
1. 각 슬라이드는 서로 다른 레이아웃 (Hero Title → Split 50:50 → Data Grid → Expert Quote → CTA List)
2. 모든 텍스트 한국어, 수치 포함
3. Tailwind 4배수 토큰만 사용 (gap-4, p-16, text-7xl 등)
4. 예측 표현 절대 금지
"""

        from google.genai import types

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CardHTMLScript,
                        temperature=0.9,          # 레이아웃 다양성
                        top_p=1.0,
                    )
                )

                result = json.loads(response.text)

                # Validate slides count
                slides = result.get("slides", [])
                if len(slides) != 5:
                    raise ValueError(f"Expected 5 slides, got {len(slides)}")

                logger.info(f"✅ Generated HTML script for cluster {cluster_id}")
                return result

            except Exception as e:
                logger.warning(f"⚠️ Gemini attempt {attempt+1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Backoff before retry
                continue

        # All retries failed, use fallback
        logger.error(f"❌ Gemini failed for cluster {cluster_id}. Using fallback.")
        return TemplateFallback.generate_html_script(cluster)

    def generate_all(self, clusters: List[Dict]) -> List[Dict]:
        """
        Generate HTML scripts for all clusters

        Args:
            clusters: List of cluster dicts

        Returns:
            List of generated scripts
        """
        logger.info(f"Generating HTML for {len(clusters)} clusters...")

        scripts = []

        for cluster in tqdm(clusters, desc="Generating HTML"):
            try:
                script = self.generate_html_script(cluster)
                scripts.append(script)

                # Log layout intents
                for slide in script.get("slides", []):
                    logger.info(f"Cluster {cluster.get('cluster_id')} Slide {slide.get('slide_num')}: {slide.get('layout_intent', '')[:50]}...")

            except Exception as e:
                logger.error(f"Error generating HTML for cluster {cluster.get('cluster_id')}: {e}")
                continue

        logger.info(f"Generated {len(scripts)} HTML scripts")
        return scripts

    def save(self, scripts: List[Dict], output_path: str = "data/3_generated/scripts.json") -> None:
        """Save scripts to JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved {len(scripts)} scripts to {output_path}")

    def run(self, input_path: str = "data/2_clustered/clustered.jsonl") -> List[Dict]:
        """
        Full pipeline: load → group by cluster → generate HTML → save → return

        Args:
            input_path: Input file path (clustered articles)

        Returns:
            Generated HTML scripts
        """
        import jsonlines

        logger.info("=" * 70)
        logger.info("SignalFeed Content Generation Started (Gemini HTML Direct)")
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

        # Generate HTML scripts
        scripts = self.generate_all(cluster_list)

        # Save
        self.save(scripts)

        logger.info("=" * 70)
        logger.info(f"Content Generation Complete: {len(scripts)} HTML scripts")
        logger.info("=" * 70)

        return scripts


if __name__ == "__main__":
    generator = ContentGenerator()

    if os.path.exists("data/2_clustered/clustered.jsonl"):
        scripts = generator.run()
        logger.info(f"Generated {len(scripts)} HTML scripts")
    else:
        logger.warning("No clustered data found. Run clusterer first.")
