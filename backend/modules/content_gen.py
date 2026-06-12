"""
SignalFeed Content Generator (Session 44 — 단일 호출 + 구조화 출력 + 캐시)

클러스터당 Gemini 2.5 Flash **1회** 호출로 커버(훅/한줄요약/출처/이미지 키워드)와
내지(Slide 2~5 구조화 콘텐츠)를 한 번에 생성한다.

구조적 보장:
- 섹터명은 KoreanSector enum (response_schema) → 티커/회사명 출력 불가
- 생성 직후 content_validator로 섹터-이유 정합성/중복/출처/금지어/한국어 커버 강제
- fact_checker(규칙+yfinance)로 경제 논리 검증, failed 시 올바른 섹터로 교체
- 결과는 gen_cache에 저장 → 재실행/디자인 반복 시 API 호출 0회 (quota 보호)
- Gemini 불가 시 큐레이션 fallback (역시 validator 통과를 보장)
"""

import os
import json
import time
import logging
from collections import defaultdict
from typing import Dict, List, Optional

from dotenv import load_dotenv

from backend.modules.content_validator import (
    GeminiCardScript,
    clean_sources,
    ensure_korean_cover,
    validate_inner,
)
from backend.modules.fact_checker import FactChecker
from backend.modules.gen_cache import GenCache
from backend.modules.hook_patterns import hook_prompt_snippet

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
PROMPT_VERSION = "s44.1"  # 프롬프트/스키마 변경 시 올려서 캐시 무효화

INNER_KEYS = [
    "slide2_facts", "slide2_source", "slide3_sectors", "slide3_fact",
    "slide4_sectors", "slide4_fact", "slide5_summaries", "slide5_watch_point",
]

SYSTEM_PROMPT = """당신은 SignalFeed의 수석 에디토리얼 에디터입니다.
글로벌 매크로 경제 이슈를 분석해 한국 주식시장 영향(섹터 단위) 카드뉴스 콘텐츠를 작성합니다.

## 출력 (구조화 JSON, 스키마 강제)
- hook_title: 표지 훅 (순한국어만, 15자 이내, \\n으로 2줄 분리, 궁금증 유발 질문형 선호)
- one_line: 표지 한줄 요약 (한국어, 60자 이내, 구체적 수치 포함)
- sources: 매체명만 (예: ["Reuters", "CNBC"]) — 기사 제목/헤드라인 절대 금지
- image_keyword: 커버 배경 검색용 영어 키워드 (구체적 장면 명사)
- slide2_facts: 핵심 팩트 3개 (각 문장에 구체적 수치, 서로 다른 내용)
- slide2_source: 출처 표기 (예: "출처 · Reuters")
- slide3_sectors: 한국 수혜 섹터 2~3개 (name은 허용 업종 enum에서만, reason은 그 업종의 비즈니스와 직접 관련된 근거)
- slide3_fact: 수혜 근거 팩트 1개 — slide2_facts와 다른 각도의 문장으로
- slide4_sectors: 한국 주의 섹터 2~3개 (동일 규칙)
- slide4_fact: 주의 근거 팩트 1개 — slide2_facts와 다른 각도의 문장으로
- slide5_summaries: 3줄 요약 — 팩트를 그대로 반복하지 말고 종합/해석된 문장으로
- slide5_watch_point: 앞으로 지켜볼 포인트 1개 (수치 포함)

## 절대 규칙
1. 모든 텍스트 한국어 (image_keyword 제외)
2. 종목 티커/회사명 언급 금지 — 섹터/업종으로만
3. 예측/권유 표현 금지 (예상/전망/추천/매수/매도/오를 것 등)
4. 제공된 팩트의 수치만 사용 — 새로운 숫자를 지어내지 말 것
5. 섹터 reason은 반드시 해당 업종의 사업 내용과 일치해야 함
   (예: '보험 운용자산 수익률'은 보험 섹터의 이유이지 바이오·제약의 이유가 아님)
6. 같은 문장을 슬라이드 간 반복 금지 — 각 슬라이드는 새로운 정보/관점"""


# ──────────────────────────────────────────────────────────────
# 큐레이션 fallback 콘텐츠 (Gemini 불가 시 — validator 통과 보장)
# ──────────────────────────────────────────────────────────────
CURATED_FALLBACK: Dict[str, Dict] = {
    "6": {
        "hook_title": "물가 다시\n오를까?",
        "one_line": "미국 연준 위원 다수, 물가 상승 위험에 금리 인상 가능성 언급하며 긴축 기조 재확인.",
        "sources": ["Reuters"],
        "image_keyword": "federal reserve building washington",
        "slide2_facts": [
            "미국 연준 위원 다수가 물가 상승 위험을 이유로 현재 금리 5.50% 수준에서 추가 인상 가능성을 언급하며 긴축 기조를 재확인했다.",
            "유로존 5월 소비자물가 상승률은 2.8%로 전월 2.6%에서 반등했다.",
            "미국 셰일 유정 완결 대기 물량은 약 4,150개로 사상 최저 수준까지 줄었다.",
        ],
        "slide2_source": "출처 · Reuters",
        "slide3_sectors": [
            {"name": "은행·금융", "reason": "금리 인상 기조가 이어지며 예대마진이 0.2%p 개선됐다."},
            {"name": "보험", "reason": "시장 금리가 5.50%로 오르며 신규 운용자산 수익률이 높아졌다."},
        ],
        "slide3_fact": "유로존 물가가 2.8%로 반등하면서 고금리 환경이 길어질 가능성이 커졌다.",
        "slide4_sectors": [
            {"name": "건설업종", "reason": "조달 금리가 5.50%까지 오르며 프로젝트 이자 부담이 커졌다."},
            {"name": "유통·소비재", "reason": "고금리 장기화로 가계 이자 부담이 늘며 소비 여력이 줄었다."},
        ],
        "slide4_fact": "셰일 완결 대기 유정이 4,150개로 줄어 공급 측 유가 부담이 이어졌다.",
        "slide5_summaries": [
            "연준의 긴축 재확인과 유로존 물가 반등이 겹치며 고금리 국면이 길어질 조건이 쌓였다.",
            "금리 수혜 업종(은행·보험)과 부담 업종(건설·소비재)의 온도 차가 뚜렷해졌다.",
            "셰일 공급 여력 축소는 유가를 떠받쳐 물가 부담을 더하는 요인으로 꼽혔다.",
        ],
        "slide5_watch_point": "다음 FOMC 금리 결정과 유로존 물가 2.8% 흐름의 지속 여부.",
    },
}

GENERIC_FALLBACK: Dict = {
    "hook_title": "오늘의 글로벌\n경제 시그널",
    "one_line": "주요 외신이 보도한 글로벌 매크로 이슈를 시그널로 정리했습니다.",
    "sources": ["Reuters"],
    "image_keyword": "global economy finance business city",
    "slide2_facts": [
        "주요 외신이 글로벌 매크로 이슈를 일제히 보도하며 시장의 관심이 집중됐다.",
        "관련 지표와 시장 가격이 함께 움직이며 변동성이 커졌다.",
    ],
    "slide2_source": "출처 · Reuters",
    "slide3_sectors": [
        {"name": "은행·금융", "reason": "거래 변동성이 커질 때 중개·운용 수익 기반이 넓어졌다."},
    ],
    "slide3_fact": "",
    "slide4_sectors": [
        {"name": "유통·소비재", "reason": "대외 불확실성이 커지면 소비 심리가 위축되는 흐름이 나타났다."},
    ],
    "slide4_fact": "",
    "slide5_summaries": [
        "글로벌 매크로 이슈가 시장 변동성을 키웠다.",
        "업종별로 영향의 방향이 갈리는 모습이 관찰됐다.",
    ],
    "slide5_watch_point": "후속 보도와 주요 지표 발표 일정.",
}


def build_material(cluster: Dict) -> str:
    """클러스터 기사들 → Gemini 입력 자료 텍스트 (캐시 키의 입력이기도 함)"""
    lines = [f"[클러스터 라벨] {cluster.get('cluster_label', '')}", "", "[기사 목록]"]
    for i, a in enumerate(cluster.get("articles", [])[:5], 1):
        title = a.get("title", "")
        summary = (a.get("summary", "") or "")[:400]
        source = a.get("source", "")
        lines.append(f"{i}. ({source}) {title}\n   {summary}")
    return "\n".join(lines)


class ContentGenerator:
    """Gemini 단일 호출 + 검증 + 캐시 콘텐츠 생성기"""

    def __init__(self, use_cache: bool = True, allow_api: bool = True,
                 cache_dir: str = "data/cache/gen"):
        self.fact_checker = FactChecker()
        self.cache = GenCache(cache_dir) if use_cache else None
        self.allow_api = allow_api and bool(os.getenv("GEMINI_API_KEY"))
        if not self.allow_api:
            logger.warning("Gemini 비활성 (키 없음 또는 allow_api=False) → 캐시/fallback만 사용")

    # ── Gemini 호출 ───────────────────────────────────────────
    def _call_gemini(self, material: str, max_retries: int = 3) -> Optional[Dict]:
        if not self.allow_api:
            return None
        try:
            from google import genai
            from google.genai import types
        except Exception as e:
            logger.warning(f"google-genai import 실패: {e}")
            return None

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        hook_snippet = hook_prompt_snippet()
        user_prompt = "아래 이슈 자료로 카드뉴스 콘텐츠 전체를 구조화 JSON으로 작성하라.\n\n"
        if hook_snippet:
            user_prompt += hook_snippet + "\n\n"
        user_prompt += material

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Gemini({GEMINI_MODEL}) 호출 {attempt}/{max_retries}")
                resp = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        temperature=0.8,
                        response_mime_type="application/json",
                        response_schema=GeminiCardScript,
                    ),
                )
                return json.loads(resp.text or "{}")
            except Exception as e:
                logger.warning(f"Gemini 실패 ({attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(5)
        return None

    # ── fallback ──────────────────────────────────────────────
    @staticmethod
    def _fallback_raw(cluster: Dict) -> Dict:
        issue_id = str(cluster.get("cluster_id", "0"))
        if issue_id in CURATED_FALLBACK:
            return json.loads(json.dumps(CURATED_FALLBACK[issue_id]))  # deep copy
        fb = json.loads(json.dumps(GENERIC_FALLBACK))
        sources = list({a.get("source", "") for a in cluster.get("articles", []) if a.get("source")})
        if sources:
            fb["sources"] = sources[:3]
            fb["slide2_source"] = "출처 · " + " · ".join(clean_sources(sources))
        return fb

    # ── 스크립트 빌드 (검증 포함) ─────────────────────────────
    def _build_script(self, issue_id: str, raw: Dict, from_fallback: bool) -> Optional[Dict]:
        """raw(Gemini 출력 또는 fallback) → 검증 완료된 최종 스크립트. 비생존 시 None"""
        inner = {k: raw.get(k) for k in INNER_KEYS}
        inner, viable, issues = validate_inner(inner)
        if not viable:
            return None

        hook, one_line, cover_issues = ensure_korean_cover(
            raw.get("hook_title", ""), raw.get("one_line", ""))
        issues.extend(cover_issues)

        return {
            "issue_id": issue_id,
            "hook_title": hook,
            "one_line": one_line,
            "sources": clean_sources(raw.get("sources")),
            "image_keyword": raw.get("image_keyword", "") or "global economy finance business city",
            "inner": inner,
            "from_fallback": from_fallback,
            "validation_issues": issues,
        }

    def generate_script(self, cluster: Dict, check_market: bool = True) -> Dict:
        """클러스터 1개 → 검증 완료 스크립트 (캐시 우선, API는 마지막 수단)"""
        issue_id = str(cluster.get("cluster_id", "0"))
        material = build_material(cluster)
        cache_key = GenCache.make_key(GEMINI_MODEL, PROMPT_VERSION, material)

        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                cached["from_cache"] = True
                return cached

        raw = self._call_gemini(material)
        script = self._build_script(issue_id, raw, from_fallback=False) if raw else None
        if script is None:
            if raw is not None:
                logger.warning(f"Cluster {issue_id}: Gemini 출력이 검증 탈락 → fallback")
            script = self._build_script(issue_id, self._fallback_raw(cluster), from_fallback=True)
            if script is None:  # fallback은 설계상 통과해야 함 — 방어선
                raise RuntimeError(f"Cluster {issue_id}: fallback 콘텐츠가 검증 탈락 (데이터 버그)")

        # 팩트 검증 (경제 논리 → 시장 추세)
        macro_text = " ".join([
            cluster.get("cluster_label", ""),
            script["hook_title"].replace("\n", " "),
            script["one_line"],
        ])
        fc = self.fact_checker.validate(
            macro_text,
            [s["name"] for s in script["inner"]["slide3_sectors"]],
            [s["name"] for s in script["inner"]["slide4_sectors"]],
            check_market=check_market,
        )
        script["fact_check"] = fc
        script["extra_disclaimer"] = ""
        if fc.get("status") == "failed":
            logger.warning(f"⚠️ Cluster {issue_id} 팩트 검증 실패: {fc.get('message')}")
            self._apply_correct_sectors(script["inner"], fc)
        elif fc.get("status") == "warning":
            logger.warning(f"⚠️ Cluster {issue_id} 팩트 경고: {fc.get('message')}")
            script["extra_disclaimer"] = "※ 현재 시장 지표가 엇갈리고 있어 실제 반응은 다를 수 있습니다."

        script["from_cache"] = False
        if self.cache:
            self.cache.set(cache_key, script)
        return script

    @staticmethod
    def _apply_correct_sectors(inner: Dict, fc: Dict) -> None:
        """팩트 검증 실패 시 룰 테이블의 올바른 enum 섹터로 교체"""
        from backend.modules.content_validator import VALID_SECTOR_NAMES

        def rebuild(correct: List[str], old: List[Dict]) -> List[Dict]:
            names = [n for n in correct if n in VALID_SECTOR_NAMES][:2]
            out = []
            for i, n in enumerate(names):
                reason = old[i]["reason"] if i < len(old) else ""
                out.append({"name": n, "reason": reason or "이번 이슈의 직접 영향권에 있는 업종이다."})
            return out or old

        if fc.get("correct_pos"):
            inner["slide3_sectors"] = rebuild(fc["correct_pos"], inner["slide3_sectors"])
        if fc.get("correct_neg"):
            inner["slide4_sectors"] = rebuild(fc["correct_neg"], inner["slide4_sectors"])

    # ── 전체 실행 ─────────────────────────────────────────────
    def run(self, input_path: str = "data/2_clustered/clustered.jsonl",
            output_path: str = "data/3_generated/scripts.json") -> List[Dict]:
        """clustered.jsonl → 클러스터별 스크립트 생성 → scripts.json 저장"""
        import jsonlines

        articles = []
        with jsonlines.open(input_path) as reader:
            for obj in reader:
                articles.append(obj)
        logger.info(f"{len(articles)}개 기사 로드")

        clusters = defaultdict(list)
        for a in articles:
            cid = a.get("cluster_id", -1)
            if cid >= 0:
                clusters[cid].append(a)
        logger.info(f"{len(clusters)}개 클러스터")

        scripts = []
        for cid, arts in clusters.items():
            cluster = {
                "cluster_id": cid,
                "cluster_label": arts[0].get("cluster_label", ""),
                "articles": arts,
            }
            try:
                script = self.generate_script(cluster)
                scripts.append(script)
                logger.info(f"Cluster {cid} hook: {script['hook_title']!r} "
                            f"(fallback={script['from_fallback']}, cache={script.get('from_cache')})")
            except Exception as e:
                logger.error(f"Cluster {cid} 생성 실패: {e}")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scripts, f, ensure_ascii=False, indent=2)
        logger.info(f"{len(scripts)}개 스크립트 저장 → {output_path}")
        return scripts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    generator = ContentGenerator()
    if os.path.exists("data/2_clustered/clustered.jsonl"):
        generator.run()
    else:
        logger.warning("clustered.jsonl 없음 — clusterer를 먼저 실행하세요.")
