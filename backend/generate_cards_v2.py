"""
SignalFeed 카드뉴스 V2 — 아이보리 디자인 시스템 (Session 37)

Opus 품질 편집 디자인:
- Cover/Conclusion: 다크 (#0D0D0D)
- Context/Bullish/Bearish: 아이보리 (#F8F6F0, 순백 금지)
- Pretendard 900 헤드라인, 수치 자동 하이라이팅
- 1080x1350px, Playwright device_scale_factor=2
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
DIVIDER = "#E0DDD8"
GREEN = "#00C853"
RED = "#FF3D3D"
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
# 클러스터별 큐레이션 콘텐츠 (이슈 팩트 기반)
# ──────────────────────────────────────────────────────────────
CONTENT = {
    "2": {
        "facts": [
            "미국·이란 핵 협상이 금요일 최종 국면에 접어들었다. 미국 측은 협상 결렬 시 군사 조치 가능성까지 시사하며 긴장이 고조됐다.",
            "중동 증시는 혼조세였다. 사우디 TASI는 0.71% 올라 11,540.21p, 카타르 QE는 0.32% 내려 9,765.89p로 마감했다.",
            "지정학 불확실성이 커지자 투자 자금은 원유 대신 AI·기술주로 이동하는 흐름이 나타났다.",
        ],
        "source_line": "출처 · Reuters · CNBC",
        "bullish": [
            {"name": "정유·에너지", "reason": "중동 공급 차질 우려로 브렌트유가 배럴당 85달러를 돌파하며 정제 마진이 개선됐다."},
            {"name": "방산", "reason": "중동 군사 긴장이 고조되며 글로벌 국방 예산 확대 기조가 이어졌다."},
        ],
        "bullish_fact": "S-Oil·GS 등 정유주, 한화에어로스페이스·LIG넥스원 등 방산주가 유가·지정학 테마에 연동됐다.",
        "bearish": [
            {"name": "항공·해운", "reason": "국제 유가가 3.8% 상승하며 연료비 부담이 가중됐다."},
            {"name": "자동차·화학", "reason": "원유·납사 원가가 동반 상승하며 수익성 압박이 커졌다."},
        ],
        "bearish_fact": "대한항공 등 항공주, LG화학·롯데케미칼 등 화학주는 원가 상승에 민감하게 반응했다.",
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
        "bullish_fact": "S-Oil 등 정유주, 한화에어로스페이스 등 방산주가 유가·지정학 테마에 연동됐다.",
        "bearish": [
            {"name": "항공·운송", "reason": "유가 3.8% 상승과 해상 운송로 불안으로 연료·물류비 부담이 커졌다."},
            {"name": "화학·정유전방", "reason": "원유·납사 원가 상승으로 수익성 압박이 가중됐다."},
        ],
        "bearish_fact": "수출 중심의 한국 경제는 에너지 비용 상승과 해상 운송 불안에 직접 노출됐다.",
        "summaries": [
            {"text": "미·이란 군사 충돌로 중동 지정학 리스크가 최고조에 달했다.", "color": GREEN},
            {"text": "유가 3.8%·금값 1.5% 상승 등 안전자산·원자재가 동반 강세를 보였다.", "color": RED},
            {"text": "VIX가 12.1% 급등하며 글로벌 위험회피 심리가 강해졌다.", "color": TEXT_SUB},
        ],
        "watch_point": "중동 군사 충돌 확전 여부와 원·달러 환율 1,385원선 흐름.",
    },
}


def brand_header(page_num: int, title: str, title_color: str) -> str:
    """상단 다크 헤더바 (#1A1A1A, 100px)"""
    return (
        f'<div style="height:100px;background:{TEXT_DARK};display:flex;align-items:center;'
        'justify-content:space-between;padding:0 60px;flex-shrink:0;position:relative;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f'<span style="color:{TEXT_LIGHT};font-size:36px;font-weight:700;">{title}</span>'
        f'<span style="position:absolute;top:16px;right:60px;color:#555;font-size:14px;">{page_num}/5</span>'
        "</div>"
    )


def slide_cover(hook_title: str, one_line: str, sources: list, img_uri: str) -> str:
    src_line = " · ".join(sources[:3]) if sources else "Reuters"
    date_str = datetime.now().strftime("%Y.%m.%d") + " · 글로벌 경제"
    hook_html = hook_title.replace("\n", "<br/>")

    img_tag = (
        f'<img src="{img_uri}" style="position:absolute;inset:0;width:100%;height:100%;'
        'object-fit:cover;object-position:center;"/>'
        if img_uri else ""
    )

    return (
        f'<div id="slide-1" class="kp" style="width:1080px;height:1350px;position:relative;'
        f'overflow:hidden;background:{DARK};">'
        f'<span style="position:absolute;top:24px;right:32px;color:{TEXT_SUB};font-size:14px;z-index:3;">1/5</span>'
        # 상단 55% 이미지
        f'<div style="position:absolute;top:0;left:0;right:0;height:55%;background:#1A1A1A;overflow:hidden;">{img_tag}</div>'
        # 하단 45% 텍스트
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


def slide_context(facts: list, source_line: str) -> str:
    blocks = ""
    for i, fact in enumerate(facts[:3], 1):
        blocks += (
            f'<div style="flex:1;position:relative;background:{CARD_SURFACE};'
            f'border-left:4px solid {GREEN};border-radius:8px;padding:40px;overflow:hidden;'
            'display:flex;align-items:center;">'
            f'<span style="position:absolute;top:8px;right:28px;font-size:120px;font-weight:900;'
            f'color:{DIVIDER};line-height:1;">{i:02d}</span>'
            f'<p style="position:relative;z-index:2;font-size:28px;font-weight:500;'
            f'color:{TEXT_DARK};line-height:1.5;">{hl(fact)}</p>'
            "</div>"
        )

    return (
        f'<div id="slide-2" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'display:flex;flex-direction:column;overflow:hidden;">'
        + brand_header(2, "무슨 일이?", TEXT_LIGHT)
        + f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;padding:32px 60px 0;">{blocks}</div>'
        + f'<p style="font-size:16px;color:{TEXT_SUB};padding:24px 60px;">{source_line}</p>'
        + "</div>"
    )


def slide_sectors(page_num: int, title: str, title_color: str, sectors: list,
                  fact: str, card_bg: str, card_border: str, name_color: str,
                  fact_border: str) -> str:
    cards = ""
    for s in sectors[:3]:
        cards += (
            f'<div style="flex:1;background:{card_bg};border:1.5px solid {card_border};'
            'border-radius:16px;padding:40px;display:flex;flex-direction:column;justify-content:center;">'
            f'<div style="font-size:64px;font-weight:900;color:{name_color};line-height:1.05;">{s["name"]}</div>'
            f'<div style="font-size:26px;color:#444;margin-top:12px;line-height:1.45;">{hl(s["reason"], title_color)}</div>'
            "</div>"
        )

    fact_box = (
        f'<div style="background:{CARD_SURFACE};border-top:2px solid {fact_border};padding:32px 60px;">'
        f'<div style="font-size:14px;font-weight:700;color:{title_color};letter-spacing:0.12em;margin-bottom:12px;">FACT /</div>'
        f'<div style="font-size:22px;color:#555;line-height:1.5;">{hl(fact, title_color)}</div>'
        "</div>"
    )

    return (
        f'<div id="slide-{page_num}" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'display:flex;flex-direction:column;overflow:hidden;">'
        + brand_header(page_num, title, title_color)
        + f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;padding:32px 60px;">{cards}</div>'
        + fact_box
        + "</div>"
    )


def slide_conclusion(summaries: list, watch_point: str) -> str:
    sum_blocks = ""
    for s in summaries[:3]:
        sum_blocks += (
            f'<div style="background:{DARK_SURFACE};border-left:8px solid {s["color"]};'
            'border-radius:4px;padding:28px 32px;">'
            f'<p style="font-size:28px;font-weight:700;color:{TEXT_LIGHT};line-height:1.4;">{s["text"]}</p>'
            "</div>"
        )

    return (
        f'<div id="slide-5" class="kp" style="width:1080px;height:1350px;background:{DARK};'
        'padding:60px;display:flex;flex-direction:column;overflow:hidden;">'
        # 상단 브랜드
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:{GREEN};font-size:13px;font-weight:700;letter-spacing:0.15em;">SIGNALFEED</span>'
        f'<span style="color:{TEXT_SUB};font-size:14px;">5/5</span>'
        "</div>"
        f'<h2 style="color:{TEXT_LIGHT};font-size:64px;font-weight:900;margin-top:44px;">오늘의 핵심</h2>'
        # 요약 3블록 (중앙 영역 균등 분배로 공백 제거)
        f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:20px;margin-top:36px;">{sum_blocks}</div>'
        # 주목 포인트
        f'<div style="background:#111;border-left:4px solid {GREEN};padding:28px 32px;margin-top:28px;">'
        f'<div style="font-size:12px;font-weight:700;color:{GREEN};letter-spacing:0.1em;margin-bottom:10px;">주목 포인트</div>'
        f'<p style="font-size:22px;color:#AAA;line-height:1.5;">{hl(watch_point)}</p>'
        "</div>"
        # CTA 박스
        f'<div style="background:{GREEN};border-radius:12px;padding:36px 40px;margin-top:28px;">'
        '<p style="font-size:26px;font-weight:700;color:#000;">댓글에 \'분석\' 남겨주세요</p>'
        '<p style="font-size:20px;color:#000;margin-top:8px;">→ 상세 리포트 DM으로 드립니다</p>'
        "</div>"
        # 면책
        '<p style="font-size:13px;color:#444;text-align:center;margin-top:24px;">'
        "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다</p>"
        "</div>"
    )


def build_full_html(script: dict, content: dict, img_uri: str) -> str:
    hook_title = script.get("hook_title", "경제 뉴스")
    one_line = script.get("one_line", "")
    sources = script.get("sources", ["Reuters"])

    slides = [
        slide_cover(hook_title, one_line, sources, img_uri),
        slide_context(content["facts"], content["source_line"]),
        slide_sectors(3, "↑ 수혜주는?", GREEN, content["bullish"], content["bullish_fact"],
                      "#F0FFF4", "#A8E6C0", "#0A5C3A", GREEN),
        slide_sectors(4, "↓ 주의할 섹터는?", RED, content["bearish"], content["bearish_fact"],
                      "#FFF5F5", "#F5C4B3", "#8B2020", RED),
        slide_conclusion(content["summaries"], content["watch_point"]),
    ]
    body = "".join(slides)
    return f"<!DOCTYPE html><html lang=\"ko\"><head>{HEAD}</head><body>{body}</body></html>"


def select_cluster(scripts: list) -> dict:
    """hook_title이 한국어인 클러스터 우선 선택"""
    hangul = re.compile(r"[가-힣]")
    for s in scripts:
        title = s.get("hook_title", "")
        if hangul.search(title):
            logger.info(f"선택된 클러스터: issue_id={s.get('issue_id')} hook='{title.strip()}'")
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

    # Pixabay 이미지 fetch (hook_title + one_line + pexels_keyword 기반 키워드 자동 선택)
    fetcher = ImageFetcher()
    issue_text = " ".join([
        script.get("hook_title", "").replace("\n", " "),
        script.get("one_line", ""),
        script.get("pexels_keyword", ""),
    ])
    keyword = fetcher.get_keyword(issue_text)
    logger.info(f"Pixabay 검색어: '{keyword}' (이슈: {issue_text[:50]}...)")
    temp_dir = os.path.join(ROOT, "data/temp")
    os.makedirs(temp_dir, exist_ok=True)
    pexels_path = os.path.join(temp_dir, f"pixabay_v2_{issue_id}.jpg")
    if not fetcher.fetch(keyword, pexels_path):
        logger.warning("Pixabay 실패 → fallback 배경 사용")
        fetcher.save_fallback(pexels_path)
    img_uri = img_to_base64(pexels_path)
    logger.info(f"이미지 저장: {pexels_path} (base64 {len(img_uri)} bytes)")

    # HTML 생성
    html = build_full_html(script, content, img_uri)
    html_path = os.path.join(temp_dir, "cards_v2.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"HTML 저장: {html_path}")

    # Playwright 스크린샷
    out_dir = os.path.join(ROOT, "data/6_cards_v2")
    os.makedirs(out_dir, exist_ok=True)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1080, "height": 1350},
            device_scale_factor=2,
        )
        page.set_content(html, wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(500)

        for n in range(1, 6):
            el = page.query_selector(f"#slide-{n}")
            if not el:
                logger.warning(f"#slide-{n} 미발견")
                continue
            out_path = os.path.join(out_dir, f"slide_{n}.png")
            el.screenshot(path=out_path)
            logger.info(f"✅ slide_{n}.png 저장")

        browser.close()

    logger.info(f"카드 V2 생성 완료 → {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
