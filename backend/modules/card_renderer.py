"""
SignalFeed 카드 렌더러 (Session 44)

구조화 스크립트(dict) → HTML 5장 → Playwright PNG.
디자인: 미니멀 크리미 베이지(GRAIN_BG #E8E5DF + grain 텍스처, 순백 금지),
폰 기준 큰 텍스트, 다크 커버(어그로 훅). 배경 색상의 단일 출처는 GRAIN_BG 상수.

레이아웃 원칙 (Session 44 결함 수정):
- Slide 2~4: 콘텐츠 블록이 가용 영역을 flex:1로 균등 점유 — 상단 거대 공백 불가
- FACT 박스는 fact 텍스트가 있을 때만 렌더 (중복 제거로 비워질 수 있음)
- 커버 출처는 content_validator.clean_sources를 거친 매체명만
"""

import os
import re
import base64
import logging
from datetime import datetime
from typing import Dict, List

from backend.modules.content_validator import clean_sources

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 디자인 토큰
# ──────────────────────────────────────────────────────────────
GRAIN_BG = "#E8E5DF"          # Slide 2~4 배경 (Session 43 확정, grain 텍스처와 합성)
DARK = "#0D0D0D"
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
    f'<link rel="stylesheet" crossorigin href="{PRETENDARD}"/>'
    "<style>"
    "*{margin:0;padding:0;box-sizing:border-box;}"
    "body{font-family:'Pretendard',sans-serif;}"
    ".kp{word-break:keep-all;overflow-wrap:break-word;}"
    "</style>"
)

GRAIN_SVG = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E"
    "%3Cfilter id='n'%3E"
    "%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E"
    "%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E"
    "%3C/svg%3E"
)


def hl(text: str, color: str = GREEN) -> str:
    """숫자+단위 자동 컬러 강조"""
    pattern = r"(\d[\d,]*\.?\d*\s*(?:%|p|원|달러|배럴|억|만|조|bp|개월|년|포인트)?)"

    def repl(m):
        return f'<span style="color:{color};font-weight:700;">{m.group(1).strip()}</span>'

    return re.sub(pattern, repl, text or "")


def img_to_base64(path: str) -> str:
    """이미지 → base64 data URI (Playwright file:// 접근 우회)"""
    if not path or not os.path.exists(path):
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


def _doc(inner_html: str, extra_css: str = "") -> str:
    head = HEAD + (f"<style>{extra_css}</style>" if extra_css else "")
    return f'<!DOCTYPE html><html lang="ko"><head>{head}</head><body>{inner_html}</body></html>'


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


# ──────────────────────────────────────────────────────────────
# Slide 1 — 커버 (다크 + Pixabay 이미지 + 어그로 훅)
# ──────────────────────────────────────────────────────────────
def slide_cover(hook_title: str, one_line: str, sources: List[str], img_uri: str) -> str:
    src_line = " · ".join(clean_sources(sources))   # 매체명만 — 헤드라인 노출 구조 차단
    date_str = datetime.now().strftime("%Y.%m.%d") + " · 글로벌 경제"
    hook_html = (hook_title or "").replace("\n", "<br/>")
    one_line = (one_line or "")[:90]

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
        f'<h1 style="color:#FFFFFF;font-weight:900;font-size:76px;line-height:1.15;margin-top:26px;">{hook_html}</h1>'
        f'<p style="color:#AAAAAA;font-size:24px;line-height:1.45;margin-top:24px;">{one_line}</p>'
        f'<p style="color:#555;font-size:16px;margin-top:auto;">{src_line}</p>'
        "</div>"
        f'<div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:{GREEN};"></div>'
        "</div>"
    )
    return _doc(inner)


# ──────────────────────────────────────────────────────────────
# Slide 2 — 무슨 일이? (팩트 블록이 영역 균등 점유 — 공백 제거)
# ──────────────────────────────────────────────────────────────
def build_context(inner: Dict, hook_title: str) -> str:
    headline = (hook_title or "").replace("\n", " ").strip() or "무슨 일이?"
    blocks = ""
    facts = inner.get("slide2_facts", [])[:3]
    for i, fact in enumerate(facts, 1):
        border = f"border-top:1px solid {DIVIDER};" if i > 1 else ""
        blocks += (
            f'<div style="flex:1;{border}display:flex;gap:28px;align-items:center;">'
            f'<span style="color:{GREEN};font-size:52px;font-weight:900;line-height:1;flex-shrink:0;">{i:02d}</span>'
            f'<p style="font-size:36px;font-weight:500;color:{TEXT_DARK};line-height:1.5;">{hl(fact)}</p>'
            "</div>"
        )
    content = (
        '<div class="content" style="height:100%;display:flex;flex-direction:column;">'
        + _brand_row(2)
        + f'<p style="font-style:italic;color:{TEXT_SUB};font-size:22px;margin:26px 0 12px;">무슨 일이?</p>'
        + f'<h1 style="font-size:58px;font-weight:900;color:{TEXT_DARK};line-height:1.2;margin-bottom:24px;">{headline}</h1>'
        + f'<div style="flex:1;display:flex;flex-direction:column;min-height:0;">{blocks}</div>'
        + f'<p style="font-size:16px;color:{TEXT_SUB};border-top:1px solid {DIVIDER};padding-top:20px;margin-top:16px;">{inner.get("slide2_source", "출처 · Reuters")}</p>'
        + "</div>"
    )
    root = (
        f'<div id="slide-2" class="kp" style="width:1080px;height:1350px;'
        f'padding:56px 72px;overflow:hidden;">{content}</div>'
    )
    return _doc(root, grain_style("slide-2", GRAIN_BG))


# ──────────────────────────────────────────────────────────────
# Slide 3~4 — 수혜/주의 섹터 (행이 영역 균등 점유, FACT 박스는 조건부)
# ──────────────────────────────────────────────────────────────
def build_sectors(num: int, label: str, top_tag: str, sectors: List[Dict],
                  fact_text: str, accent: str) -> str:
    rows = ""
    for s in sectors[:3]:
        rows += (
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;'
            f'border-left:5px solid {accent};padding-left:32px;">'
            f'<div style="font-size:84px;font-weight:900;color:{accent};line-height:1.05;">{s.get("name", "")}</div>'
            f'<div style="font-size:32px;color:#444;margin-top:16px;line-height:1.45;">{hl(s.get("reason", ""), accent)}</div>'
            "</div>"
        )
    fact_box = ""
    if fact_text:
        fact_box = (
            f'<div style="border-top:2px solid {accent};padding-top:22px;margin-top:18px;">'
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
        + f'<p style="font-style:italic;color:{accent};font-size:26px;font-weight:600;margin:26px 0 20px;">{label}</p>'
        + f'<div style="flex:1;display:flex;flex-direction:column;gap:24px;min-height:0;">{rows}</div>'
        + fact_box
        + "</div>"
    )
    root = (
        f'<div id="slide-{num}" class="kp" style="width:1080px;height:1350px;'
        f'padding:56px 72px;overflow:hidden;">{content}</div>'
    )
    return _doc(root, grain_style(f"slide-{num}", GRAIN_BG))


# ──────────────────────────────────────────────────────────────
# Slide 5 — 오늘의 결론 (다크)
# ──────────────────────────────────────────────────────────────
def build_conclusion(inner: Dict, extra_disclaimer: str = "") -> str:
    colors = [GREEN, RED, TEXT_SUB]
    sum_blocks = ""
    for i, text in enumerate(inner.get("slide5_summaries", [])[:3], 1):
        c = colors[(i - 1) % 3]
        sum_blocks += (
            '<div style="flex:1;display:flex;gap:24px;align-items:center;">'
            f'<span style="color:{c};font-size:60px;font-weight:900;line-height:1;flex-shrink:0;">{i:02d}.</span>'
            f'<p style="font-size:34px;font-weight:600;color:{TEXT_LIGHT};line-height:1.45;">{text}</p>'
            "</div>"
        )
    watch_html = ""
    watch = inner.get("slide5_watch_point", "")
    if watch:
        watch_html = (
            f'<div style="border-left:3px solid {GREEN};padding:6px 0 6px 28px;margin-bottom:26px;">'
            f'<div style="font-size:12px;font-weight:700;color:{GREEN};letter-spacing:0.1em;margin-bottom:10px;">주목 포인트</div>'
            f'<p style="font-size:28px;color:#AAA;line-height:1.5;">{hl(watch)}</p>'
            "</div>"
        )
    disc_html = (
        '<p style="font-size:13px;color:#555;text-align:center;margin-top:20px;">'
        "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다</p>"
    )
    if extra_disclaimer:
        disc_html = (
            f'<p style="font-size:15px;color:{YELLOW};text-align:center;margin-top:18px;line-height:1.4;">{extra_disclaimer}</p>'
            + disc_html
        )
    inner_html = (
        f'<div id="slide-5" class="kp" style="width:1080px;height:1350px;background:{DARK};'
        'padding:56px 72px;display:flex;flex-direction:column;overflow:hidden;">'
        + _brand_row(5)
        + f'<h2 style="color:{TEXT_LIGHT};font-size:60px;font-weight:900;margin-top:34px;">오늘의 결론</h2>'
        + f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;margin:28px 0;min-height:0;">{sum_blocks}</div>'
        + watch_html
        + f'<div style="background:{GREEN};border-radius:12px;padding:32px 40px;">'
        + '<p style="font-size:26px;font-weight:700;color:#000;">댓글에 \'분석\' 남겨주세요</p>'
        + '<p style="font-size:20px;color:#000;margin-top:8px;">→ 상세 리포트 DM으로 드립니다</p>'
        + "</div>"
        + disc_html
        + "</div>"
    )
    return _doc(inner_html)


# ──────────────────────────────────────────────────────────────
# 전체 렌더 + 스크린샷
# ──────────────────────────────────────────────────────────────
def render_slides(script: Dict, img_uri: str = "") -> Dict[int, str]:
    """검증 완료된 스크립트 → 슬라이드 5장 HTML 문서"""
    inner = script["inner"]
    return {
        1: slide_cover(script.get("hook_title", ""), script.get("one_line", ""),
                       script.get("sources", []), img_uri),
        2: build_context(inner, script.get("hook_title", "")),
        3: build_sectors(3, "이번 이슈, 누가 웃나?", "↑ 수혜",
                         inner.get("slide3_sectors", []), inner.get("slide3_fact", ""), GREEN),
        4: build_sectors(4, "이번 이슈, 누가 우나?", "↓ 주의",
                         inner.get("slide4_sectors", []), inner.get("slide4_fact", ""), RED),
        5: build_conclusion(inner, script.get("extra_disclaimer", "")),
    }


def screenshot_slides(docs: Dict[int, str], out_dir: str, temp_dir: str = "data/temp") -> List[str]:
    """Playwright로 HTML → PNG (1080x1350, Retina 2x)"""
    from playwright.sync_api import sync_playwright

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    saved = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        for n in sorted(docs):
            html = docs[n]
            with open(os.path.join(temp_dir, f"slide_{n}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            page.set_content(html, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(400)
            el = page.query_selector(f"#slide-{n}") or page
            path = os.path.join(out_dir, f"slide_{n}.png")
            el.screenshot(path=path)
            saved.append(path)
            logger.info(f"✅ slide_{n}.png 저장 → {out_dir}")
        browser.close()
    return saved
