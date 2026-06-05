"""
SignalFeed 카드뉴스 V2 — 카드뉴스 공장 방식 (Session 41~43)

- Slide 1 (Cover): 고정 템플릿 유지 (Pixabay 이미지 + 다크 오버레이, API 호출 없음 → 토큰 절약)
- Slide 2~5: Gemini 2.5 Flash가 "구조화 JSON(InnerSlides)"으로 출력
  · 섹터명은 KoreanSector enum으로 강제 → 종목 티커/회사명 근본 차단 (Session 43)
  · fact_checker로 섹터 경제 논리 + yfinance 시장 추세 검증 (Session 43)
  · 파이썬이 구조화 데이터로 HTML 렌더링 (큰 타이포 + grain 텍스처)
  · 수치 없는 팩트 금지, 예측/권유 표현 금지
  · API key 없거나 실패 시 → 내장 큐레이션 콘텐츠 fallback
- 1080x1350px, Playwright device_scale_factor=2, 슬라이드별 독립 HTML 렌더링
"""

import os
import re
import sys
import json
import time
import base64
import logging
from enum import Enum
from typing import List
from datetime import datetime

from pydantic import BaseModel

# 프로젝트 루트 sys.path 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from backend.modules.image_fetcher import ImageFetcher
from backend.modules.fact_checker import FactChecker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 디자인 토큰
# ──────────────────────────────────────────────────────────────
IVORY = "#F8F6F0"
GRAIN_BG = "#E8E5DF"          # Slide 2~4 grain 텍스처 배경 (Session 43)
DARK = "#0D0D0D"
DARK_SURFACE = "#161616"
CARD_SURFACE = "#EEECEA"
DIVIDER = "#D0CCC6"
GREEN = "#00C853"
RED = "#FF3D3D"
YELLOW = "#FFE566"
TEXT_DARK = "#1A1A1A"
TEXT_LIGHT = "#F5F5F5"
TEXT_SUB = "#888888"

PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"

HEAD = (
    '<meta charset="UTF-8">'
    '<script src="https://cdn.tailwindcss.com"></script>'
    f'<link rel="stylesheet" crossorigin href="{PRETENDARD}"/>'
    "<style>"
    "*{margin:0;padding:0;box-sizing:border-box;}"
    "body{font-family:'Pretendard',sans-serif;}"
    ".kp{word-break:keep-all;overflow-wrap:break-word;}"
    "</style>"
)

# grain 텍스처 (SVG fractalNoise, opacity 0.12) — Session 43
GRAIN_SVG = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E"
    "%3Cfilter id='n'%3E"
    "%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E"
    "%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E"
    "%3C/svg%3E"
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ──────────────────────────────────────────────────────────────
# 출력 스키마 (Session 43) — 섹터명 enum으로 티커 근본 차단
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
    바이오제약 = "바이오·제약"
    건설업종 = "건설업종"
    유통소비재 = "유통·소비재"
    전력설비 = "전력·설비"
    철강소재 = "철강·소재"
    엔터미디어 = "엔터·미디어"
    IT플랫폼 = "IT·플랫폼"
    여행레저 = "여행·레저"


class Sector(BaseModel):
    name: KoreanSector  # enum으로 강제 → 종목명 절대 못 씀
    reason: str


class InnerSlides(BaseModel):
    slide2_facts: List[str]
    slide2_source: str
    slide3_sectors: List[Sector]
    slide3_fact: str
    slide4_sectors: List[Sector]
    slide4_fact: str
    slide5_summaries: List[str]
    slide5_watch_point: str


ALLOWED_SECTORS = " · ".join(s.value for s in KoreanSector)

# ──────────────────────────────────────────────────────────────
# Slide 2~5 시스템 프롬프트 (구조화 JSON 출력 — Session 43)
# ──────────────────────────────────────────────────────────────
INNER_SYSTEM_PROMPT = f"""당신은 SignalFeed의 수석 에디토리얼 에디터입니다.
글로벌 매크로 경제 이슈를 한국 주식시장 영향으로 분석해 카드뉴스 본문(Slide 2~5)을 작성합니다.

## 출력
구조화된 JSON으로만 출력합니다 (스키마 강제). 각 필드를 채우세요:
- slide2_facts: 핵심 팩트 3개 (각 문장에 구체적 수치 포함)
- slide2_source: 출처 (예: "출처 · Reuters")
- slide3_sectors: 한국 수혜 섹터 2~3개 (name + 수치 포함 reason)
- slide3_fact: 수혜 근거 핵심 팩트 1개 (수치 포함)
- slide4_sectors: 한국 주의 섹터 2~3개 (name + 수치 포함 reason)
- slide4_fact: 주의 근거 핵심 팩트 1개 (수치 포함)
- slide5_summaries: 3줄 요약 (각 1문장)
- slide5_watch_point: 앞으로 지켜볼 주목 포인트 1개 (수치 포함)

## 절대 규칙
- 모든 텍스트 한국어
- 수치 없는 팩트 금지 (모든 핵심 문장에 숫자 포함)
- 예측/권유 표현 금지 (예상/전망/추천/매수/매도 등 금지)
- 종목 티커명/회사명 직접 언급 절대 금지
- 섹터 name은 반드시 아래 허용 업종에서만 선택:
  {ALLOWED_SECTORS}
- 제공된 팩트/수치만 사용. 새로운 숫자를 지어내지 말 것."""


def hl(text: str, color: str = GREEN) -> str:
    """숫자+단위를 컬러 강조 (수치 자동 하이라이팅)"""
    pattern = r"(\d[\d,]*\.?\d*\s*(?:%|p|원|달러|배럴|억|만|조|bp|개월|년|포인트)?)"

    def repl(m):
        token = m.group(1).strip()
        return f'<span style="color:{color};font-weight:700;">{token}</span>'

    return re.sub(pattern, repl, text)


def img_to_base64(path: str) -> str:
    """이미지를 base64 data URI로 변환 (Playwright file:// 접근 우회)"""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
        return f"data:{mime};base64,{data}"
    except Exception as e:
        logger.warning(f"이미지 base64 변환 실패: {e}")
        return ""


# ──────────────────────────────────────────────────────────────
# 클러스터별 큐레이션 콘텐츠 (이슈 팩트 기반, 티커 없이 섹터만) — fallback용
# ──────────────────────────────────────────────────────────────
CONTENT = {
    "2": {
        "facts": [
            "미국·이란 핵 협상이 금요일 최종 국면에 접어들었다. 협상 결렬 시 군사 조치 가능성까지 거론되며 긴장이 고조됐다.",
            "중동 증시는 혼조세였다. 사우디 TASI는 0.71% 올라 11,540.21p, 카타르 QE는 0.32% 내려 9,765.89p로 마감했다.",
            "지정학 불확실성이 커지자 투자 자금이 원유 대신 AI·기술주로 이동하는 흐름이 나타났다.",
        ],
        "source_line": "출처 · Reuters · CNBC",
        "bullish": [
            {"name": "정유업종", "reason": "중동 공급 차질 우려로 브렌트유가 배럴당 85달러를 돌파하며 정제 마진이 개선됐다."},
            {"name": "방산업체", "reason": "중동 군사 긴장이 고조되며 글로벌 국방 예산 확대 기조가 이어졌다."},
        ],
        "bearish": [
            {"name": "항공사들", "reason": "국제 유가가 3.8% 상승하며 연료비 부담이 가중됐다."},
            {"name": "화학업종", "reason": "원유·납사 원가가 동반 상승하며 수익성 압박이 커졌다."},
        ],
        "slide3_fact": "브렌트유가 배럴당 85달러를 넘어서며 에너지·방산 관련 업종에 우호적 환경이 조성됐다.",
        "slide4_fact": "국제 유가가 3.8% 상승하며 연료·원가 민감 업종의 비용 부담이 커졌다.",
        "summaries": [
            "미·이란 협상이 금요일 분수령을 맞으며 중동 지정학 리스크가 커졌다.",
            "국제 유가가 85달러까지 강세를 보이며 항공·화학 등 원가 민감 업종이 부담을 받았다.",
            "투자 자금은 원유 대신 AI·기술주로 이동하는 모습이 관찰됐다.",
        ],
        "watch_point": "금요일 미·이란 협상 결과와 국제 유가 85달러선 지지 여부.",
    },
    "4": {
        "facts": [
            "미국이 이란 군사 시설과 드론 기지를 수차례 공습했고, 이란도 공군 기지 공격으로 맞서며 중동 긴장이 연일 고조됐다.",
            "국제 유가(WTI)는 배럴당 85.20달러로 전주 대비 3.8% 올랐고, 국제 금값은 2,150달러로 1.5% 상승했다.",
            "원·달러 환율은 1,385원으로 0.7% 올랐고, 글로벌 증시 변동성 지수(VIX)는 19.30으로 12.1% 뛰었다.",
        ],
        "source_line": "출처 · Reuters",
        "bullish": [
            {"name": "정유업종", "reason": "WTI가 85.20달러까지 오르며 정제 마진이 개선됐다."},
            {"name": "방산업체", "reason": "중동 군사 충돌로 글로벌 국방 예산 확대 기조가 강화됐다."},
        ],
        "bearish": [
            {"name": "항공사들", "reason": "유가 3.8% 상승과 해상 운송로 불안으로 연료·물류비 부담이 커졌다."},
            {"name": "화학업종", "reason": "원유·납사 원가 상승으로 수익성 압박이 가중됐다."},
        ],
        "slide3_fact": "WTI가 배럴당 85.20달러로 3.8% 오르며 에너지·방산 업종에 우호적 환경이 형성됐다.",
        "slide4_fact": "유가 3.8% 상승과 운송로 불안으로 연료·물류 비용이 동반 상승했다.",
        "summaries": [
            "미·이란 군사 충돌로 중동 지정학 리스크가 최고조에 달했다.",
            "유가 3.8%·금값 1.5% 상승 등 안전자산·원자재가 동반 강세를 보였다.",
            "VIX가 12.1% 급등하며 글로벌 위험회피 심리가 강해졌다.",
        ],
        "watch_point": "중동 군사 충돌 확전 여부와 원·달러 환율 1,385원선 흐름.",
    },
    "6": {
        "facts": [
            "미국 연준 위원 다수가 물가 상승 위험을 이유로 추가 금리 인상 가능성을 언급하며 긴축 기조를 재확인했다.",
            "유로존 5월 소비자물가 상승률은 2.8%로 전월 2.6%에서 반등했다.",
            "미국 셰일 유정 완결 대기 물량은 약 4,150개로 사상 최저 수준까지 줄었다.",
        ],
        "source_line": "출처 · Reuters",
        "bullish": [
            {"name": "은행·금융", "reason": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다."},
            {"name": "바이오·제약", "reason": "금리가 5.50%까지 오르며 보험·운용자산 수익률이 높아졌다."},
        ],
        "bearish": [
            {"name": "건설업종", "reason": "조달 금리가 5.50%로 오르며 이자 부담이 커졌다."},
            {"name": "유통·소비재", "reason": "긴축 장기화와 유가 부담으로 소비·물류 비용이 가중됐다."},
        ],
        "slide3_fact": "기준금리가 5.50%까지 오르며 금융 업종의 예대마진이 0.2%p 개선됐다.",
        "slide4_fact": "조달 금리가 5.50%로 상승하며 금리 민감 업종의 이자 부담이 커졌다.",
        "summaries": [
            "연준 위원들이 추가 금리 인상 가능성을 언급하며 긴축 기조를 재확인했다.",
            "유로존 물가가 2.8%로 반등하는 등 글로벌 인플레이션 압력이 확대됐다.",
            "한국 증시는 긴축 장기화 리스크에 대비할 필요성이 커졌다.",
        ],
        "watch_point": "다음 FOMC의 금리 결정과 유로존 물가 2.8% 흐름의 지속 여부.",
    },
}


def build_material(script: dict, content: dict) -> str:
    """Gemini에게 전달할 팩트 자료 (티커 제외, 수치 포함)"""
    lines = []
    lines.append(f"[이슈] {script.get('hook_title', '').replace(chr(10), ' ')}")
    if script.get("one_line"):
        lines.append(f"[한줄 요약] {script['one_line']}")
    lines.append("")
    lines.append("[핵심 팩트 (수치 포함, 이 숫자만 사용)]")
    for i, f in enumerate(content["facts"], 1):
        lines.append(f"  {i}. {f}")
    lines.append("")
    lines.append("[수혜 섹터 참고 (Slide 3 — 허용 업종명만 사용)]")
    for s in content["bullish"]:
        lines.append(f"  - {s['name']}: {s['reason']}")
    lines.append("")
    lines.append("[주의 섹터 참고 (Slide 4 — 허용 업종명만 사용)]")
    for s in content["bearish"]:
        lines.append(f"  - {s['name']}: {s['reason']}")
    lines.append("")
    lines.append("[결론 3줄 요약 참고 (Slide 5)]")
    for s in content["summaries"]:
        lines.append(f"  - {s}")
    lines.append(f"[주목 포인트] {content['watch_point']}")
    lines.append(f"[{content['source_line']}]")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Slide 1 (Cover) — 고정 템플릿 (API 호출 없음)
# ──────────────────────────────────────────────────────────────
def _doc(inner_html: str, extra_css: str = "") -> str:
    head = HEAD + (f"<style>{extra_css}</style>" if extra_css else "")
    return f'<!DOCTYPE html><html lang="ko"><head>{head}</head><body>{inner_html}</body></html>'


def slide_cover(hook_title: str, one_line: str, sources: list, img_uri: str) -> str:
    src_line = " · ".join(sources[:3]) if sources else "Reuters"
    date_str = datetime.now().strftime("%Y.%m.%d") + " · 글로벌 경제"
    hook_html = hook_title.replace("\n", "<br/>")

    img_tag = (
        f'<img src="{img_uri}" style="position:absolute;inset:0;width:100%;height:100%;'
        'object-fit:cover;object-position:center;"/>'
        if img_uri else ""
    )

    inner = (
        f'<div id="slide-1" class="kp" style="width:1080px;height:1350px;position:relative;'
        f'overflow:hidden;background:{DARK};">'
        f'<span style="position:absolute;top:24px;right:32px;color:{TEXT_SUB};font-size:14px;z-index:3;">1/5</span>'
        f'<div style="position:absolute;top:0;left:0;right:0;height:55%;background:#1A1A1A;overflow:hidden;">{img_tag}</div>'
        f'<div style="position:absolute;top:55%;left:0;right:0;height:45%;background:{DARK};'
        'padding:48px 60px;display:flex;flex-direction:column;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f'<p style="color:#666;font-size:18px;margin-top:18px;">{date_str}</p>'
        f'<h1 style="color:#FFFFFF;font-weight:900;font-size:72px;line-height:1.15;margin-top:28px;">{hook_html}</h1>'
        f'<p style="color:#AAAAAA;font-size:22px;line-height:1.45;margin-top:24px;">{one_line}</p>'
        f'<p style="color:#555;font-size:16px;margin-top:auto;">{src_line}</p>'
        "</div>"
        f'<div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:{GREEN};"></div>'
        "</div>"
    )
    return _doc(inner)


# ──────────────────────────────────────────────────────────────
# Slide 2~5 — Gemini 구조화 출력 (InnerSlides JSON)
# ──────────────────────────────────────────────────────────────
def generate_inner_with_gemini(material: str):
    """Gemini 2.5 Flash 구조화 JSON 호출 (response_schema=InnerSlides). 실패 시 None."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY 없음 → fallback 콘텐츠 사용")
        return None
    try:
        from google import genai
        from google.genai import types
    except Exception as e:
        logger.warning(f"google-genai import 실패: {e} → fallback")
        return None

    client = genai.Client(api_key=api_key)
    user_prompt = (
        "아래 이슈 자료로 Slide 2~5 콘텐츠를 구조화 JSON으로 작성해줘. "
        "섹터 name은 반드시 허용된 업종 목록에서만 선택.\n\n" + material
    )
    for attempt in range(1, 4):
        try:
            logger.info(f"Gemini({GEMINI_MODEL}) 호출 (시도 {attempt}/3) — Slide 2~5 구조화 생성")
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=INNER_SYSTEM_PROMPT,
                    temperature=0.9,
                    response_mime_type="application/json",
                    response_schema=InnerSlides,
                ),
            )
            data = json.loads(resp.text or "{}")
            inner = normalize_inner(data)
            if inner:
                logger.info("✅ Gemini 구조화 출력 파싱 성공 (enum 섹터 강제)")
                return inner
            logger.warning("Gemini 출력 필드 부족 → 재시도")
        except Exception as e:
            logger.warning(f"Gemini 호출 실패 (시도 {attempt}/3): {e}")
        time.sleep(4)
    logger.warning("Gemini 3회 실패 → fallback")
    return None


def normalize_inner(data: dict):
    """InnerSlides JSON → 내부 렌더링 dict. 필수 필드 누락 시 None."""
    def sec(lst):
        out = []
        for s in lst or []:
            name = s.get("name")
            if name:
                out.append({"name": name, "reason": s.get("reason", "")})
        return out

    inner = {
        "slide2_facts": (data.get("slide2_facts") or [])[:3],
        "slide2_source": data.get("slide2_source") or "출처 · Reuters",
        "slide3_sectors": sec(data.get("slide3_sectors"))[:3],
        "slide3_fact": data.get("slide3_fact") or "",
        "slide4_sectors": sec(data.get("slide4_sectors"))[:3],
        "slide4_fact": data.get("slide4_fact") or "",
        "slide5_summaries": (data.get("slide5_summaries") or [])[:3],
        "slide5_watch_point": data.get("slide5_watch_point") or "",
    }
    if (not inner["slide2_facts"] or not inner["slide3_sectors"]
            or not inner["slide4_sectors"] or not inner["slide5_summaries"]):
        return None
    return inner


def inner_from_content(content: dict) -> dict:
    """fallback: 큐레이션 CONTENT → 렌더링 dict"""
    facts = content["facts"]
    return {
        "slide2_facts": facts[:3],
        "slide2_source": content["source_line"],
        "slide3_sectors": [{"name": s["name"], "reason": s["reason"]} for s in content["bullish"][:3]],
        "slide3_fact": content.get("slide3_fact") or (facts[1] if len(facts) > 1 else ""),
        "slide4_sectors": [{"name": s["name"], "reason": s["reason"]} for s in content["bearish"][:3]],
        "slide4_fact": content.get("slide4_fact") or (facts[2] if len(facts) > 2 else ""),
        "slide5_summaries": list(content["summaries"][:3]),
        "slide5_watch_point": content["watch_point"],
    }


def override_sectors(correct_names: list, old_sectors: list) -> list:
    """팩트 검증 실패 시 올바른 섹터로 교체 (reason은 기존 것 재사용)"""
    out = []
    for i, n in enumerate(correct_names[:2]):
        reason = ""
        if i < len(old_sectors):
            reason = old_sectors[i].get("reason", "")
        if not reason:
            reason = "이번 이슈의 직접 영향권에 있는 업종입니다."
        out.append({"name": n, "reason": reason})
    return out


# ──────────────────────────────────────────────────────────────
# Slide 2~5 — 파이썬 HTML 렌더러 (큰 타이포 + grain 텍스처, Session 43)
# ──────────────────────────────────────────────────────────────
def grain_style(sid: str, bg: str) -> str:
    return (
        f"#{sid}{{position:relative;background:{bg};}}"
        f"#{sid}::before{{content:'';position:absolute;inset:0;"
        f'background-image:url("{GRAIN_SVG}");background-size:180px 180px;'
        "opacity:0.12;pointer-events:none;z-index:0;}"
        f"#{sid} .content{{position:relative;z-index:1;}}"
    )


def _brand_row(num: int, right_html: str = "") -> str:
    right = right_html or f'<span style="color:{TEXT_SUB};font-size:14px;">{num}/5</span>'
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f"{right}"
        "</div>"
    )


def build_context(inner: dict, hook_title: str) -> str:
    """Slide 2 (무슨 일이?) — 헤드라인 60px, 팩트 34px, grain"""
    headline = hook_title.replace("\n", " ").strip() or "무슨 일이?"
    blocks = ""
    for i, fact in enumerate(inner["slide2_facts"][:3], 1):
        blocks += (
            f'<div style="padding:28px 0;border-top:1px solid {DIVIDER};display:flex;gap:28px;align-items:flex-start;">'
            f'<span style="color:{GREEN};font-size:48px;font-weight:900;line-height:1;flex-shrink:0;">{i:02d}</span>'
            f'<p style="font-size:34px;font-weight:500;color:{TEXT_DARK};line-height:1.5;">{hl(fact)}</p>'
            "</div>"
        )
    content = (
        '<div class="content" style="height:100%;display:flex;flex-direction:column;">'
        + _brand_row(2)
        + f'<p style="font-style:italic;color:{TEXT_SUB};font-size:22px;margin:20px 0 14px;">무슨 일이?</p>'
        + f'<h1 style="font-size:60px;font-weight:900;color:{TEXT_DARK};line-height:1.2;">{headline}</h1>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{blocks}</div>'
        + f'<p style="font-size:16px;color:{TEXT_SUB};border-top:1px solid {DIVIDER};padding-top:20px;">{inner["slide2_source"]}</p>'
        + "</div>"
    )
    root = (
        f'<div id="slide-2" class="kp" style="width:1080px;height:1350px;'
        f'padding:60px 72px;overflow:hidden;">{content}</div>'
    )
    return _doc(root, grain_style("slide-2", GRAIN_BG))


def build_sectors(num: int, label: str, top_tag: str, sectors: list, fact_text: str, accent: str) -> str:
    """Slide 3~4 (수혜/주의) — 섹터명 88px, 이유 32px, FACT 26px, 태그 24px, grain"""
    rows = ""
    for s in sectors[:3]:
        rows += (
            f'<div style="border-left:4px solid {accent};padding:8px 0 8px 30px;">'
            f'<div style="font-size:88px;font-weight:900;color:{accent};line-height:1.0;">{s["name"]}</div>'
            f'<div style="font-size:32px;color:#444;margin-top:14px;line-height:1.45;">{hl(s["reason"], accent)}</div>'
            "</div>"
        )
    fact_box = ""
    if fact_text:
        fact_box = (
            f'<div style="border-top:2px solid {accent};padding-top:22px;margin-top:10px;">'
            f'<span style="font-size:13px;font-weight:800;color:{accent};letter-spacing:0.12em;">FACT</span>'
            f'<p style="font-size:26px;color:{TEXT_DARK};line-height:1.45;margin-top:10px;">{hl(fact_text, accent)}</p>'
            "</div>"
        )
    right = (
        f'<span style="color:{accent};font-size:24px;font-weight:800;">{top_tag}'
        f'<span style="color:{TEXT_SUB};font-size:14px;font-weight:500;margin-left:12px;">{num}/5</span>'
        "</span>"
    )
    content = (
        '<div class="content" style="height:100%;display:flex;flex-direction:column;">'
        + _brand_row(num, right)
        + f'<p style="font-style:italic;color:{accent};font-size:24px;font-weight:600;margin:18px 0 8px;">{label}</p>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:30px;">{rows}</div>'
        + fact_box
        + "</div>"
    )
    root = (
        f'<div id="slide-{num}" class="kp" style="width:1080px;height:1350px;'
        f'padding:60px 72px;overflow:hidden;">{content}</div>'
    )
    return _doc(root, grain_style(f"slide-{num}", GRAIN_BG))


def build_conclusion(inner: dict, extra_disclaimer: str = "") -> str:
    """Slide 5 (오늘의 결론) — 번호 64px, 요약 34px, 주목 28px (다크, grain 없음)"""
    colors = [GREEN, RED, TEXT_SUB]
    sum_blocks = ""
    for i, text in enumerate(inner["slide5_summaries"][:3], 1):
        c = colors[(i - 1) % 3]
        sum_blocks += (
            '<div style="display:flex;gap:24px;align-items:baseline;padding:18px 0;">'
            f'<span style="color:{c};font-size:64px;font-weight:900;line-height:1;flex-shrink:0;">{i:02d}.</span>'
            f'<p style="font-size:34px;font-weight:600;color:{TEXT_LIGHT};line-height:1.4;">{text}</p>'
            "</div>"
        )
    disc_html = (
        '<p style="font-size:13px;color:#444;text-align:center;margin-top:20px;">'
        "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다</p>"
    )
    if extra_disclaimer:
        disc_html = (
            f'<p style="font-size:15px;color:{YELLOW};text-align:center;margin-top:18px;line-height:1.4;">{extra_disclaimer}</p>'
            + disc_html
        )
    inner_html = (
        f'<div id="slide-5" class="kp" style="width:1080px;height:1350px;background:{DARK};'
        'padding:60px 72px;display:flex;flex-direction:column;overflow:hidden;">'
        + _brand_row(5)
        + f'<h2 style="color:{TEXT_LIGHT};font-size:60px;font-weight:900;margin-top:36px;">오늘의 결론</h2>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{sum_blocks}</div>'
        + f'<div style="border-left:3px solid {GREEN};padding:6px 0 6px 28px;margin-bottom:26px;">'
        + f'<div style="font-size:12px;font-weight:700;color:{GREEN};letter-spacing:0.1em;margin-bottom:10px;">주목 포인트</div>'
        + f'<p style="font-size:28px;color:#AAA;line-height:1.5;">{hl(inner["slide5_watch_point"])}</p>'
        + "</div>"
        + f'<div style="background:{GREEN};border-radius:12px;padding:32px 40px;">'
        + '<p style="font-size:26px;font-weight:700;color:#000;">댓글에 \'분석\' 남겨주세요</p>'
        + '<p style="font-size:20px;color:#000;margin-top:8px;">→ 상세 리포트 DM으로 드립니다</p>'
        + "</div>"
        + disc_html
        + "</div>"
    )
    return _doc(inner_html)


# ──────────────────────────────────────────────────────────────
# 클러스터 선택
# ──────────────────────────────────────────────────────────────
def select_cluster(scripts: list) -> dict:
    """hook_title이 한국어인 클러스터 우선 선택 (fallback 영어 제외)"""
    hangul = re.compile(r"[가-힣]")
    for s in scripts:
        if hangul.search(s.get("hook_title", "")):
            logger.info(f"선택된 클러스터: issue_id={s.get('issue_id')} hook='{s.get('hook_title', '').strip()}'")
            return s
    logger.info("한국어 hook 없음 → 첫 번째 클러스터 사용")
    return scripts[0]


def main():
    scripts_path = os.path.join(ROOT, "data/3_generated/scripts.json")
    with open(scripts_path, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    script = select_cluster(scripts)
    issue_id = script.get("issue_id", "0")
    content = CONTENT.get(issue_id, CONTENT["2"])
    hook_title = script.get("hook_title", "경제 뉴스")
    one_line = script.get("one_line", "")

    # Slide 1 이미지 (Pixabay)
    fetcher = ImageFetcher()
    issue_text = " ".join([
        hook_title.replace("\n", " "),
        one_line,
        script.get("pexels_keyword", ""),
    ])
    keyword = fetcher.get_keyword(issue_text)
    logger.info(f"Pixabay 검색어: '{keyword}'")
    temp_dir = os.path.join(ROOT, "data/temp")
    os.makedirs(temp_dir, exist_ok=True)
    img_path = os.path.join(temp_dir, f"pixabay_v2_{issue_id}.jpg")
    if not fetcher.fetch(keyword, img_path):
        logger.warning("Pixabay 실패 → fallback 배경 사용")
        fetcher.save_fallback(img_path)
    img_uri = img_to_base64(img_path)

    # Slide 2~5 데이터 (Gemini 구조화 → 실패 시 fallback 콘텐츠)
    material = build_material(script, content)
    inner = generate_inner_with_gemini(material)
    if inner is None:
        inner = inner_from_content(content)
        logger.info("내장 큐레이션 콘텐츠로 Slide 2~5 데이터 구성")

    # 팩트 검증 (규칙 + yfinance)
    checker = FactChecker()
    macro_text = f"{hook_title.replace(chr(10), ' ')} {one_line}"
    fc = checker.validate(
        macro_text,
        [s["name"] for s in inner["slide3_sectors"]],
        [s["name"] for s in inner["slide4_sectors"]],
    )
    extra_disclaimer = ""
    status = fc.get("status")
    if status == "failed":
        logger.warning(f"⚠️ 팩트 검증 실패: {fc.get('message')}")
        cp = fc.get("correct_pos", [])
        cn = fc.get("correct_neg", [])
        if cp:
            inner["slide3_sectors"] = override_sectors(cp, inner["slide3_sectors"])
        if cn:
            inner["slide4_sectors"] = override_sectors(cn, inner["slide4_sectors"])
        logger.info("올바른 섹터로 교체 완료")
    elif status == "warning":
        logger.warning(f"⚠️ 팩트 검증 경고: {fc.get('message')}")
        extra_disclaimer = "※ 현재 시장 지표가 엇갈리고 있어 실제 반응은 다를 수 있습니다."
    else:
        logger.info(f"✅ 팩트 검증 통과: {fc.get('message', '')}")

    docs = {
        1: slide_cover(hook_title, one_line, script.get("sources", ["Reuters"]), img_uri),
        2: build_context(inner, hook_title),
        3: build_sectors(3, "이번 이슈, 누가 웃나?", "↑ 수혜", inner["slide3_sectors"], inner["slide3_fact"], GREEN),
        4: build_sectors(4, "이번 이슈, 누가 우나?", "↓ 주의", inner["slide4_sectors"], inner["slide4_fact"], RED),
        5: build_conclusion(inner, extra_disclaimer),
    }

    # 슬라이드별 독립 HTML 저장 + Playwright 스크린샷
    out_dir = os.path.join(ROOT, "data/6_cards_v2")
    os.makedirs(out_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        for n in range(1, 6):
            html = docs[n]
            with open(os.path.join(temp_dir, f"cards_v2_slide_{n}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            page.set_content(html, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(500)
            el = page.query_selector(f"#slide-{n}")
            if not el:
                logger.warning(f"#slide-{n} 미발견 → 페이지 전체 캡처")
                el = page
            el.screenshot(path=os.path.join(out_dir, f"slide_{n}.png"))
            logger.info(f"✅ slide_{n}.png 저장")
        browser.close()

    logger.info(f"카드 V2 생성 완료 → {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
