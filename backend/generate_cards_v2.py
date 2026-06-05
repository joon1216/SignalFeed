"""
SignalFeed 카드뉴스 V2 — 카드뉴스 공장 방식 (Session 41)

- Slide 1 (Cover): 고정 템플릿 유지 (Pixabay 이미지 + 다크 오버레이, Claude API 호출 없음 → 토큰 절약)
- Slide 2~5: Claude(Opus)가 매번 다른 자유 레이아웃으로 HTML 직접 생성 (잡지/뉴스레터 감성)
  · 종목 티커/회사명 금지, 섹터·업종으로만 표현
  · 수치 없는 팩트 금지, 예측/권유 표현 금지
  · API key 없거나 실패 시 → 내장 에디토리얼 템플릿 fallback
- 1080x1350px, Playwright device_scale_factor=2, 슬라이드별 독립 HTML 렌더링
"""

import os
import re
import sys
import json
import base64
import logging
from datetime import datetime

# 프로젝트 루트 sys.path 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from backend.modules.image_fetcher import ImageFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 디자인 토큰
# ──────────────────────────────────────────────────────────────
IVORY = "#F8F6F0"
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

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-4-7")

# ──────────────────────────────────────────────────────────────
# Slide 2~5 시스템 프롬프트 (카드뉴스 공장 — 자유 레이아웃)
# ──────────────────────────────────────────────────────────────
INNER_SYSTEM_PROMPT = f"""당신은 SignalFeed의 수석 에디토리얼 디자이너입니다.
Bloomberg + 한국 뉴스레터 감성을 합친 카드뉴스를 만듭니다.
매번 다른 레이아웃, AI 느낌 절대 금지, 잡지 페이지처럼.

## 가드레일 (반드시 지킬 것)

### 색상
- 메인 배경: {IVORY} (아이보리, 순백 #FFFFFF 절대 금지)
- 다크 배경: {DARK} (결론 슬라이드 등)
- 브랜드: {GREEN}
- 수치 인라인 하이라이트: {YELLOW}
- 수혜: {GREEN} / 주의: {RED}
- 구분선: {DIVIDER}

### 폰트
- Pretendard CDN 필수 (link: {PRETENDARD})
- 모든 텍스트 컨테이너에 style="word-break:keep-all;overflow-wrap:break-word;"

### 캔버스
- 각 슬라이드 루트 div: width:1080px; height:1350px; overflow:hidden; 그리고 반드시 id="slide-N" (N=슬라이드 번호)
- SIGNALFEED 좌상단 ({GREEN})
- 슬라이드 번호 우상단 (예: "2/5")

### 콘텐츠 절대 규칙
- 수치 없는 팩트 금지 (모든 핵심 팩트에 숫자 포함)
- 예측/권유 표현 금지 (예상/전망/추천/매수/매도 등 사용 금지)
- 모든 텍스트 한국어
- 종목 티커명/회사명 직접 언급 절대 금지 (S-Oil, GS, HMM, 대한항공, 삼성전자 등)
- 반드시 섹터/업종으로만 표현 (예: "정유업종" "항공사들" "반도체 기업" "방산업체")
- 제공된 팩트/수치만 사용. 새로운 숫자를 지어내지 말 것.

## 레이아웃 자유
4장(Slide 2~5) 각각 완전히 다른 레이아웃으로 설계.
아래 뉴스레터 요소를 자유롭게 조합:
- 얇은 선(1px)으로 섹션 구분 / 인라인 텍스트 하이라이트({YELLOW})
- pill 태그(카테고리·출처) / 체크마크(✓) 리스트
- 큰 숫자 + 작은 설명 / 이탤릭 섹션 라벨
- 좌측 accent 선(3px) / 비교 2단 레이아웃 / 인용구 스타일
매번 비슷한 카드 박스 쓰지 말 것. 각 슬라이드가 잡지 페이지처럼 느껴져야 함. PPT처럼 만들면 실패.

## 4장 역할
- Slide 2 [무슨 일이?]: 핵심 팩트 3개 + 수치 하이라이트({YELLOW})
- Slide 3 [수혜주는?]: 한국 수혜 섹터 (업종명만, 티커 절대 금지)
- Slide 4 [주의할 섹터는?]: 한국 주의 섹터 (업종명만, 티커 절대 금지)
- Slide 5 [오늘의 결론]: 3줄 요약 + 주목 포인트 + CTA 다크 박스("댓글에 '분석' 남겨주세요")

## 출력 형식 (엄격)
설명/주석 없이 아래 형식 그대로만 출력. 각 슬라이드는 완전한 단일 HTML 문서.
===SLIDE2===
<!DOCTYPE html>...전체 HTML...
===SLIDE3===
<!DOCTYPE html>...전체 HTML...
===SLIDE4===
<!DOCTYPE html>...전체 HTML...
===SLIDE5===
<!DOCTYPE html>...전체 HTML..."""


def hl(text: str, color: str = GREEN) -> str:
    """숫자+단위를 컬러 강조 (수치 자동 하이라이팅) — fallback 템플릿용"""
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
# 클러스터별 큐레이션 콘텐츠 (이슈 팩트 기반, 티커 없이 섹터만)
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
            {"name": "정유·에너지", "reason": "중동 공급 차질 우려로 브렌트유가 배럴당 85달러를 돌파하며 정제 마진이 개선됐다."},
            {"name": "방산", "reason": "중동 군사 긴장이 고조되며 글로벌 국방 예산 확대 기조가 이어졌다."},
        ],
        "bearish": [
            {"name": "항공·해운", "reason": "국제 유가가 3.8% 상승하며 연료비 부담이 가중됐다."},
            {"name": "자동차·화학", "reason": "원유·납사 원가가 동반 상승하며 수익성 압박이 커졌다."},
        ],
        "summaries": [
            {"text": "미·이란 협상이 금요일 분수령을 맞으며 중동 지정학 리스크가 커졌다.", "color": GREEN},
            {"text": "국제 유가가 85달러까지 강세를 보이며 항공·화학 등 원가 민감 업종이 부담을 받았다.", "color": RED},
            {"text": "투자 자금은 원유 대신 AI·기술주로 이동하는 모습이 관찰됐다.", "color": TEXT_SUB},
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
            {"name": "정유·에너지", "reason": "WTI가 85.20달러까지 오르며 정제 마진이 개선됐다."},
            {"name": "방산", "reason": "중동 군사 충돌로 글로벌 국방 예산 확대 기조가 강화됐다."},
        ],
        "bearish": [
            {"name": "항공·운송", "reason": "유가 3.8% 상승과 해상 운송로 불안으로 연료·물류비 부담이 커졌다."},
            {"name": "화학·정유전방", "reason": "원유·납사 원가 상승으로 수익성 압박이 가중됐다."},
        ],
        "summaries": [
            {"text": "미·이란 군사 충돌로 중동 지정학 리스크가 최고조에 달했다.", "color": GREEN},
            {"text": "유가 3.8%·금값 1.5% 상승 등 안전자산·원자재가 동반 강세를 보였다.", "color": RED},
            {"text": "VIX가 12.1% 급등하며 글로벌 위험회피 심리가 강해졌다.", "color": TEXT_SUB},
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
            {"name": "은행", "reason": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다."},
            {"name": "보험", "reason": "금리가 5.50%까지 오르며 보험사 운용자산 수익률이 높아졌다."},
        ],
        "bearish": [
            {"name": "건설·부동산", "reason": "조달 금리가 5.50%로 오르며 이자 부담이 커졌다."},
            {"name": "소비재·운송", "reason": "긴축 장기화와 유가 부담으로 소비·물류 비용이 가중됐다."},
        ],
        "summaries": [
            {"text": "연준 위원들이 추가 금리 인상 가능성을 언급하며 긴축 기조를 재확인했다.", "color": GREEN},
            {"text": "유로존 물가가 2.8%로 반등하는 등 글로벌 인플레이션 압력이 확대됐다.", "color": RED},
            {"text": "한국 증시는 긴축 장기화 리스크에 대비할 필요성이 커졌다.", "color": TEXT_SUB},
        ],
        "watch_point": "다음 FOMC의 금리 결정과 유로존 물가 2.8% 흐름의 지속 여부.",
    },
}


def build_material(script: dict, content: dict) -> str:
    """Claude에게 전달할 팩트 자료 (티커 제외, 수치 포함)"""
    lines = []
    lines.append(f"[이슈] {script.get('hook_title', '').replace(chr(10), ' ')}")
    if script.get("one_line"):
        lines.append(f"[한줄 요약] {script['one_line']}")
    lines.append("")
    lines.append("[핵심 팩트 (수치 포함, 이 숫자만 사용)]")
    for i, f in enumerate(content["facts"], 1):
        lines.append(f"  {i}. {f}")
    lines.append("")
    lines.append("[수혜 섹터 (Slide 3 — 업종명만 사용)]")
    for s in content["bullish"]:
        lines.append(f"  - {s['name']}: {s['reason']}")
    lines.append("")
    lines.append("[주의 섹터 (Slide 4 — 업종명만 사용)]")
    for s in content["bearish"]:
        lines.append(f"  - {s['name']}: {s['reason']}")
    lines.append("")
    lines.append("[결론 3줄 요약 (Slide 5)]")
    for s in content["summaries"]:
        lines.append(f"  - {s['text']}")
    lines.append(f"[주목 포인트] {content['watch_point']}")
    lines.append(f"[{content['source_line']}]")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
# Slide 1 (Cover) — 고정 템플릿 (Claude 호출 없음)
# ──────────────────────────────────────────────────────────────
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
    return f'<!DOCTYPE html><html lang="ko"><head>{HEAD}</head><body>{inner}</body></html>'


# ──────────────────────────────────────────────────────────────
# Slide 2~5 — Claude(Opus) 공장 생성
# ──────────────────────────────────────────────────────────────
def generate_inner_with_claude(material: str) -> dict:
    """Claude(Opus) 단일 호출로 Slide 2~5 HTML 생성. 실패 시 None."""
    api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY 없음 → fallback 템플릿 사용")
        return None

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        logger.info(f"Claude({CLAUDE_MODEL}) 호출 — Slide 2~5 생성")
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=16000,
            system=[{
                "type": "text",
                "text": INNER_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    "아래 이슈 자료로 Slide 2~5를 각각 완전히 다른 잡지형 레이아웃으로 만들어줘. "
                    "출력은 시스템 프롬프트의 ===SLIDEN=== 형식만 사용.\n\n" + material
                ),
            }],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        slides = parse_claude_slides(text)
        if len(slides) == 4:
            logger.info("✅ Claude 4개 슬라이드 파싱 성공")
            return slides
        logger.warning(f"Claude 슬라이드 파싱 부족 ({len(slides)}/4) → fallback")
        return None
    except Exception as e:
        logger.warning(f"Claude 호출 실패: {e} → fallback")
        return None


def parse_claude_slides(text: str) -> dict:
    """===SLIDEN=== 구분자로 슬라이드 HTML 분리"""
    slides = {}
    parts = re.split(r"===SLIDE([2-5])===", text)
    # parts: [pre, '2', html2, '3', html3, ...]
    for i in range(1, len(parts) - 1, 2):
        num = int(parts[i])
        html = parts[i + 1].strip()
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```$", "", html).strip()
        if "<" in html and f'id="slide-{num}"' in html:
            slides[num] = html
    return slides


# ──────────────────────────────────────────────────────────────
# Slide 2~5 — fallback 에디토리얼 템플릿
# ──────────────────────────────────────────────────────────────
def _doc(inner: str) -> str:
    return f'<!DOCTYPE html><html lang="ko"><head>{HEAD}</head><body>{inner}</body></html>'


def fallback_brand(num: int, label: str, label_color: str) -> str:
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f'<span style="color:{TEXT_SUB};font-size:14px;">{num}/5</span>'
        "</div>"
        f'<p style="font-style:italic;color:{label_color};font-size:20px;font-weight:500;margin-bottom:28px;">{label}</p>'
    )


def fallback_context(content: dict) -> str:
    blocks = ""
    for i, fact in enumerate(content["facts"][:3], 1):
        blocks += (
            f'<div style="padding:32px 0;border-top:1px solid {DIVIDER};display:flex;gap:28px;align-items:flex-start;">'
            f'<span style="color:{GREEN};font-size:40px;font-weight:900;line-height:1;flex-shrink:0;">{i:02d}</span>'
            f'<p style="font-size:30px;font-weight:500;color:{TEXT_DARK};line-height:1.5;">{hl(fact)}</p>'
            "</div>"
        )
    inner = (
        f'<div id="slide-2" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'padding:64px 72px;display:flex;flex-direction:column;overflow:hidden;">'
        + fallback_brand(2, "무슨 일이?", TEXT_SUB)
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{blocks}</div>'
        + f'<p style="font-size:16px;color:{TEXT_SUB};border-top:1px solid {DIVIDER};padding-top:20px;">{content["source_line"]}</p>'
        + "</div>"
    )
    return _doc(inner)


def fallback_sectors(num: int, label: str, sectors: list, accent: str) -> str:
    rows = ""
    for s in sectors[:3]:
        rows += (
            f'<div style="padding:36px 0;border-top:1px solid {DIVIDER};border-left:3px solid {accent};'
            'padding-left:32px;margin-bottom:4px;">'
            f'<div style="font-size:64px;font-weight:900;color:{accent};line-height:1.05;">{s["name"]}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:14px;line-height:1.45;">{hl(s["reason"], accent)}</div>'
            "</div>"
        )
    inner = (
        f'<div id="slide-{num}" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'padding:64px 72px;display:flex;flex-direction:column;overflow:hidden;">'
        + fallback_brand(num, label, accent)
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{rows}</div>'
        + "</div>"
    )
    return _doc(inner)


def fallback_conclusion(content: dict) -> str:
    sum_blocks = ""
    for i, s in enumerate(content["summaries"][:3], 1):
        sum_blocks += (
            f'<div style="display:flex;gap:24px;align-items:baseline;padding:22px 0;">'
            f'<span style="color:{s["color"]};font-size:24px;font-weight:900;flex-shrink:0;">{i:02d}.</span>'
            f'<p style="font-size:28px;font-weight:600;color:{TEXT_LIGHT};line-height:1.4;">{s["text"]}</p>'
            "</div>"
        )
    inner = (
        f'<div id="slide-5" class="kp" style="width:1080px;height:1350px;background:{DARK};'
        'padding:64px 72px;display:flex;flex-direction:column;overflow:hidden;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f'<span style="color:{TEXT_SUB};font-size:14px;">5/5</span>'
        "</div>"
        f'<h2 style="color:{TEXT_LIGHT};font-size:60px;font-weight:900;margin-top:40px;">오늘의 결론</h2>'
        f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{sum_blocks}</div>'
        f'<div style="border-left:3px solid {GREEN};padding:6px 0 6px 28px;margin-bottom:28px;">'
        f'<div style="font-size:12px;font-weight:700;color:{GREEN};letter-spacing:0.1em;margin-bottom:10px;">주목 포인트</div>'
        f'<p style="font-size:22px;color:#AAA;line-height:1.5;">{hl(content["watch_point"])}</p>'
        "</div>"
        f'<div style="background:{GREEN};border-radius:12px;padding:32px 40px;">'
        '<p style="font-size:26px;font-weight:700;color:#000;">댓글에 \'분석\' 남겨주세요</p>'
        '<p style="font-size:20px;color:#000;margin-top:8px;">→ 상세 리포트 DM으로 드립니다</p>'
        "</div>"
        '<p style="font-size:13px;color:#444;text-align:center;margin-top:24px;">'
        "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다</p>"
        "</div>"
    )
    return _doc(inner)


def fallback_inner(content: dict) -> dict:
    return {
        2: fallback_context(content),
        3: fallback_sectors(3, "이번 이슈, 누가 웃나?", content["bullish"], GREEN),
        4: fallback_sectors(4, "이번 이슈, 누가 우나?", content["bearish"], RED),
        5: fallback_conclusion(content),
    }


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

    # Slide 1 이미지 (Pixabay)
    fetcher = ImageFetcher()
    issue_text = " ".join([
        script.get("hook_title", "").replace("\n", " "),
        script.get("one_line", ""),
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

    # Slide 1 (고정) + Slide 2~5 (Claude 공장, 실패 시 fallback)
    material = build_material(script, content)
    inner = generate_inner_with_claude(material)
    if inner is None:
        inner = fallback_inner(content)
        logger.info("내장 에디토리얼 템플릿으로 Slide 2~5 생성")

    docs = {
        1: slide_cover(script.get("hook_title", "경제 뉴스"), script.get("one_line", ""),
                       script.get("sources", ["Reuters"]), img_uri),
        2: inner[2], 3: inner[3], 4: inner[4], 5: inner[5],
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
