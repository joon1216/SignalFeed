"""
SignalFeed 콘텐츠 구조 검증기 (Session 44)

LLM 출력을 신뢰하지 않고 렌더링 전에 코드로 강제하는 레이어:
1. 섹터명 enum 검증 (티커/회사명 구조 차단)
2. 섹터-이유 정합성 (시그니처 키워드 소유권 — 예: '예대마진'은 은행·금융만)
3. 슬라이드 간 콘텐츠 중복 제거 (토큰 Jaccard 유사도)
4. 출처 화이트리스트 정제 (헤드라인 문자열 → 매체명만)
5. 예측/권유 금지어 차단
6. 커버 훅/한줄요약 한국어 강제
"""

import re
import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# 스키마 — 섹터명은 enum으로만 (Gemini response_schema에 그대로 사용)
# ──────────────────────────────────────────────────────────────
class KoreanSector(str, Enum):
    정유업종 = "정유업종"
    항공사들 = "항공사들"
    해운업체 = "해운업체"
    반도체기업 = "반도체 기업"
    방산업체 = "방산업체"
    화학업종 = "화학업종"
    자동차제조 = "자동차 제조사"
    은행금융 = "은행·금융"
    보험 = "보험"
    바이오제약 = "바이오·제약"
    건설업종 = "건설업종"
    유통소비재 = "유통·소비재"
    전력설비 = "전력·설비"
    철강소재 = "철강·소재"
    엔터미디어 = "엔터·미디어"
    IT플랫폼 = "IT·플랫폼"
    여행레저 = "여행·레저"


VALID_SECTOR_NAMES = {s.value for s in KoreanSector}


class Sector(BaseModel):
    name: KoreanSector
    reason: str


class InnerSlides(BaseModel):
    """Slide 2~5 구조화 콘텐츠 (Gemini 출력 스키마)"""
    slide2_facts: List[str]
    slide2_source: str
    slide3_sectors: List[Sector]
    slide3_fact: str
    slide4_sectors: List[Sector]
    slide4_fact: str
    slide5_summaries: List[str]
    slide5_watch_point: str


class GeminiCardScript(BaseModel):
    """클러스터당 Gemini 1회 호출의 전체 출력 스키마 (커버 + 내지)"""
    hook_title: str        # 순한국어, 15자 이내, \n 줄바꿈
    one_line: str          # 한줄 요약 (수치 포함)
    sources: List[str]     # 매체명만 (Reuters 등)
    image_keyword: str     # 커버 배경 검색용 영어 키워드
    slide2_facts: List[str]
    slide2_source: str
    slide3_sectors: List[Sector]
    slide3_fact: str
    slide4_sectors: List[Sector]
    slide4_fact: str
    slide5_summaries: List[str]
    slide5_watch_point: str


# ──────────────────────────────────────────────────────────────
# 1) 출처 정제 — 매체명 화이트리스트
# ──────────────────────────────────────────────────────────────
OUTLET_WHITELIST = [
    "Reuters", "Bloomberg", "CNBC", "Financial Times", "Wall Street Journal",
    "MarketWatch", "AP", "New York Times", "NYT", "WSJ", "FT",
]

# 정규화: 소문자 변형 → 표준 표기
_OUTLET_CANON = {o.lower(): o for o in OUTLET_WHITELIST}
_OUTLET_CANON.update({"nyt": "NYT", "wsj": "WSJ", "ft": "FT"})

DEFAULT_SOURCES = ["Reuters"]


def clean_sources(sources: Optional[List[str]], max_n: int = 3) -> List[str]:
    """출처 배열 정제 — 헤드라인/임의 문자열에서 매체명만 추출.

    "Reuters: Record-low U.S. shale well backlog ..." → "Reuters"
    화이트리스트에 매칭되지 않는 항목은 버린다 (커버 영문 헤드라인 노출 방지).
    """
    cleaned: List[str] = []
    for raw in sources or []:
        if not isinstance(raw, str):
            continue
        low = raw.lower()
        matched = None
        for key, canon in _OUTLET_CANON.items():
            if key in low:
                matched = canon
                break
        if matched and matched not in cleaned:
            cleaned.append(matched)
        if len(cleaned) >= max_n:
            break
    return cleaned or list(DEFAULT_SOURCES)


# ──────────────────────────────────────────────────────────────
# 2) 예측/권유 금지어
# ──────────────────────────────────────────────────────────────
BANNED_PATTERNS = [
    "예상된다", "예상됩니다", "전망이다", "전망입니다", "전망된다",
    "오를 것", "떨어질 것", "상승할 것", "하락할 것",
    "추천", "매수", "매도", "사야", "팔아야", "유망하다",
]


def find_banned(text: str) -> List[str]:
    """예측/권유 금지어 검출"""
    return [p for p in BANNED_PATTERNS if p in (text or "")]


# ──────────────────────────────────────────────────────────────
# 3) 섹터-이유 정합성 — 시그니처 키워드 소유권
# ──────────────────────────────────────────────────────────────
# 각 섹터의 '시그니처 키워드': 이 단어가 이유(reason)에 등장하면
# 해당 섹터(또는 공동 소유 섹터)의 이유여야만 한다.
REASON_SIGNATURES: Dict[str, List[str]] = {
    "은행·금융": ["예대마진", "순이자마진", "대출금리", "수신금리", "예대 마진"],
    "보험": ["보험", "운용자산", "보험금", "역마진", "공시이율"],
    "바이오·제약": ["임상", "신약", "제약", "바이오"],
    "정유업종": ["정제마진", "정제 마진", "정유"],
    "항공사들": ["항공유", "여객", "항공권", "항공"],
    "해운업체": ["운임", "해운", "선사", "해상운송", "해상 운송"],
    "방산업체": ["방산", "국방예산", "국방 예산", "무기"],
    "반도체 기업": ["파운드리", "메모리", "반도체"],
    "건설업종": ["분양", "시공", "수주잔고", "건설"],
    "자동차 제조사": ["완성차", "자동차"],
    "화학업종": ["납사", "석유화학"],
    "철강·소재": ["철강", "철광석"],
    "전력·설비": ["송전", "변압기", "전력망"],
    "엔터·미디어": ["콘텐츠", "엔터"],
    "IT·플랫폼": ["플랫폼", "클라우드", "소프트웨어"],
    "여행·레저": ["여행", "관광", "레저"],
}


def check_sector_reason(name: str, reason: str) -> Tuple[bool, Optional[str]]:
    """섹터명과 이유 텍스트의 정합성 검사.

    Returns:
        (ok, suggested_owner) — 불일치 시 이유가 실제로 가리키는 섹터명 제안
    """
    reason = reason or ""
    owners = [
        sector for sector, keys in REASON_SIGNATURES.items()
        if any(k in reason for k in keys)
    ]
    if not owners:
        return True, None  # 시그니처 없음 → 일반 이유로 허용
    if name in owners:
        return True, None
    return False, owners[0]


def repair_sectors(sectors: List[Dict], side: str = "") -> Tuple[List[Dict], List[str]]:
    """섹터 목록 검증/수리.

    - enum에 없는 섹터명 → drop (티커/회사명 차단의 마지막 방어선)
    - 섹터-이유 불일치 → 이유가 가리키는 섹터로 교체(목록에 없을 때만), 아니면 drop

    Returns:
        (repaired, issues)
    """
    repaired: List[Dict] = []
    issues: List[str] = []
    existing_names = set()

    for s in sectors or []:
        name = (s.get("name") or "").strip()
        reason = (s.get("reason") or "").strip()
        if name not in VALID_SECTOR_NAMES:
            issues.append(f"{side} 비허용 섹터명 drop: '{name}'")
            continue
        if find_banned(reason):
            issues.append(f"{side} 금지어 포함 섹터 drop: '{name}'")
            continue
        ok, owner = check_sector_reason(name, reason)
        if not ok:
            if owner and owner not in existing_names and owner in VALID_SECTOR_NAMES:
                issues.append(f"{side} 섹터-이유 불일치: '{name}' → '{owner}' 교체")
                name = owner
            else:
                issues.append(f"{side} 섹터-이유 불일치 drop: '{name}' (이유: {reason[:30]}…)")
                continue
        if name in existing_names:
            issues.append(f"{side} 중복 섹터 drop: '{name}'")
            continue
        existing_names.add(name)
        repaired.append({"name": name, "reason": reason})

    return repaired, issues


# ──────────────────────────────────────────────────────────────
# 4) 슬라이드 간 중복 제거 — 토큰 Jaccard
# ──────────────────────────────────────────────────────────────
DUP_THRESHOLD = 0.6

_token_re = re.compile(r"[가-힣A-Za-z0-9.%]+")


def _tokens(text: str) -> set:
    return set(_token_re.findall((text or "").lower()))


def similarity(a: str, b: str) -> float:
    """정규화 토큰 Jaccard 유사도 (0.0~1.0)"""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def is_duplicate(text: str, against: List[str], threshold: float = DUP_THRESHOLD) -> bool:
    return any(similarity(text, other) >= threshold for other in against if other)


def dedupe_inner(inner: Dict) -> Tuple[Dict, List[str]]:
    """슬라이드 간 근사-중복 제거.

    - slide3_fact / slide4_fact: slide2 팩트나 해당 슬라이드 섹터 이유와 중복 → 비움 (FACT 박스 생략)
    - slide5_summaries: slide2 팩트 또는 앞선 요약과 중복 → 해당 요약 제거
    """
    issues: List[str] = []
    facts = (inner.get("slide2_facts") or [])

    for key, sectors_key in (("slide3_fact", "slide3_sectors"), ("slide4_fact", "slide4_sectors")):
        fact = (inner.get(key) or "")
        reasons = [s.get("reason", "") for s in (inner.get(sectors_key) or [])]
        if fact and is_duplicate(fact, facts + reasons):
            issues.append(f"{key} 중복 → FACT 박스 생략")
            inner[key] = ""

    kept: List[str] = []
    for summ in (inner.get("slide5_summaries") or []):
        if is_duplicate(summ, facts + kept):
            issues.append(f"slide5 요약 중복 drop: '{summ[:30]}…'")
            continue
        kept.append(summ)
    inner["slide5_summaries"] = kept

    return inner, issues


# ──────────────────────────────────────────────────────────────
# 5) 커버 한국어 강제
# ──────────────────────────────────────────────────────────────
_hangul_re = re.compile(r"[가-힣]")

GENERIC_HOOK = "오늘의 글로벌\n경제 시그널"
GENERIC_ONE_LINE = "주요 외신이 보도한 글로벌 매크로 이슈를 시그널로 정리했습니다."


def ensure_korean_cover(hook_title: str, one_line: str) -> Tuple[str, str, List[str]]:
    """커버 훅/한줄요약에 한글이 없으면 일반 한국어 문구로 교체 (영문 커버 방지)"""
    issues: List[str] = []
    if not _hangul_re.search(hook_title or ""):
        issues.append(f"영문/빈 hook_title 교체: '{(hook_title or '')[:20]}'")
        hook_title = GENERIC_HOOK
    if not _hangul_re.search(one_line or ""):
        issues.append(f"영문/빈 one_line 교체: '{(one_line or '')[:30]}'")
        one_line = GENERIC_ONE_LINE
    return hook_title, one_line, issues


# ──────────────────────────────────────────────────────────────
# 마스터 검증 — inner 전체
# ──────────────────────────────────────────────────────────────
def validate_inner(inner: Dict) -> Tuple[Dict, bool, List[str]]:
    """Slide 2~5 구조화 데이터 전체 검증/수리.

    Returns:
        (repaired_inner, viable, issues)
        viable=False면 호출 측에서 큐레이션 fallback을 사용해야 한다.
    """
    issues: List[str] = []
    inner = dict(inner)  # shallow copy

    # 팩트/요약/주목포인트 금지어 필터
    kept_facts = []
    for f in (inner.get("slide2_facts") or []):
        if find_banned(f):
            issues.append(f"금지어 팩트 drop: '{f[:30]}…'")
        else:
            kept_facts.append(f)
    inner["slide2_facts"] = kept_facts

    kept_summaries = []
    for s in (inner.get("slide5_summaries") or []):
        if find_banned(s):
            issues.append(f"금지어 요약 drop: '{s[:30]}…'")
        else:
            kept_summaries.append(s)
    inner["slide5_summaries"] = kept_summaries
    if find_banned((inner.get("slide5_watch_point") or "")):
        issues.append("금지어 watch_point 비움")
        inner["slide5_watch_point"] = ""

    # 섹터 검증/수리
    for key, side in (("slide3_sectors", "수혜"), ("slide4_sectors", "주의")):
        repaired, sec_issues = repair_sectors((inner.get(key) or []), side)
        inner[key] = repaired
        issues.extend(sec_issues)

    # 중복 제거
    inner, dup_issues = dedupe_inner(inner)
    issues.extend(dup_issues)

    # 최종 생존성
    viable = (
        len((inner.get("slide2_facts") or [])) >= 2
        and len((inner.get("slide3_sectors") or [])) >= 1
        and len((inner.get("slide4_sectors") or [])) >= 1
        and len((inner.get("slide5_summaries") or [])) >= 2
    )
    if not viable:
        issues.append("검증 후 콘텐츠 부족 → fallback 필요")

    for msg in issues:
        logger.warning(f"[validator] {msg}")
    return inner, viable, issues
