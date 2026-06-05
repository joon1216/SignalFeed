"""
SignalFeed 카드뉴스 V3 — 뉴스레터 에디토리얼 스타일 (Session 38)

기존 카드 박스 UI 폐기 → 뉴스레터/편집 디자인:
- 얇은 선(border)으로만 구분, 텍스트 직접 배치 (박스 없음)
- 노란 하이라이트(#FFE566)로 수치/키워드 강조
- pill 태그로 카테고리/섹터/관련주 표시
- 손글씨 느낌 이탤릭 + 고딕 혼합 (Pretendard)
- 1080x1350px, Playwright device_scale_factor=2
"""

import os
import re
import sys
import json
import base64
import logging
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from backend.modules.image_fetcher import ImageFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# 디자인 토큰 — 뉴스레터 에디토리얼
# ──────────────────────────────────────────────────────────────
IVORY = "#F8F6F0"
DARK = "#0D0D0D"
TEXT_MAIN = "#1A1A1A"
TEXT_SUB = "#888888"
BORDER = "#D0CCC6"
BORDER_LIGHT = "#E8E4DE"
GREEN = "#00C853"
RED = "#FF3D3D"
YELLOW = "#FFE566"
PILL_BG = "#EEECEA"

PRETENDARD = "https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard-dynamic-subset.min.css"

HEAD = (
    '<meta charset="UTF-8">'
    f'<link rel="stylesheet" crossorigin href="{PRETENDARD}"/>'
    "<style>"
    "*{margin:0;padding:0;box-sizing:border-box;}"
    "body{font-family:'Pretendard',sans-serif;}"
    ".kp{word-break:keep-all;overflow-wrap:break-word;}"
    ".italic{font-style:italic;font-weight:500;}"
    "</style>"
)

DATE_STR = datetime.now().strftime("%Y.%m.%d")


def hl(text: str) -> str:
    """숫자+단위를 노란 하이라이트로 강조"""
    pattern = r"(\d[\d,]*\.?\d*\s*(?:%|p|원|달러|배럴|억|만|조|bp|개월|년|포인트)?)"

    def repl(m):
        token = m.group(1).strip()
        return f'<span style="background:{YELLOW};padding:0 5px;border-radius:2px;font-weight:700;color:{TEXT_MAIN};">{token}</span>'

    return re.sub(pattern, repl, text)


def img_to_base64(path: str) -> str:
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


def stock_pills(stocks: list, bg: str, color: str) -> str:
    pills = ""
    for st in stocks:
        pills += (
            f'<span style="display:inline-block;background:{bg};color:{color};'
            'font-size:22px;font-weight:600;padding:8px 18px;border-radius:20px;'
            'margin:0 10px 10px 0;">' + st + "</span>"
        )
    return pills


# ──────────────────────────────────────────────────────────────
# 큐레이션 콘텐츠 (수치 포함 팩트)
# ──────────────────────────────────────────────────────────────
CONTENT = {
    "2": {
        "headline_pre": "",
        "headline_key": "미-이란 협상",
        "headline_post": " 불확실성 고조",
        "facts": [
            "미국·이란 핵 협상이 금요일 최종 국면에 접어들었다. 미국은 결렬 시 군사 조치 가능성까지 시사했다.",
            "사우디 TASI는 0.71% 올라 11,540.21p, 카타르 QE는 0.32% 내려 9,765.89p로 마감하며 중동 증시가 혼조세를 보였다.",
            "지정학 불확실성이 커지자 투자 자금은 원유 대신 AI·기술주로 이동하는 흐름이 나타났다.",
        ],
        "sources": ["Reuters", "CNBC"],
        "bullish": [
            {"name": "정유·에너지", "reason": "중동 공급 차질 우려로 브렌트유가 배럴당 85달러를 돌파하며 정제 마진이 개선됐다.",
             "stocks": ["S-Oil", "GS", "SK이노베이션"]},
            {"name": "방산", "reason": "중동 군사 긴장이 고조되며 글로벌 국방 예산 확대 기조가 이어졌다.",
             "stocks": ["한화에어로", "LIG넥스원"]},
        ],
        "bullish_fact": "정유주와 방산주가 유가·지정학 테마에 연동되며 강세를 보였다.",
        "bearish": [
            {"name": "항공·해운", "reason": "국제 유가가 3.8% 상승하며 연료비 부담이 가중됐다.",
             "stocks": ["대한항공", "HMM"]},
            {"name": "자동차·화학", "reason": "원유·납사 원가가 동반 상승하며 수익성 압박이 커졌다.",
             "stocks": ["LG화학", "롯데케미칼"]},
        ],
        "bearish_fact": "원가에 민감한 항공·화학 업종이 유가 상승에 직접 노출됐다.",
        "summaries": [
            "미·이란 협상이 금요일 분수령을 맞으며 중동 지정학 리스크가 커졌다.",
            "국제 유가가 85달러까지 강세를 보이며 항공·화학 등 원가 민감 업종이 부담을 받았다.",
            "투자 자금은 원유 대신 AI·기술주로 이동하는 모습이 관찰됐다.",
        ],
        "watch_point": "금요일 미·이란 협상 결과와 국제 유가 85달러선 지지 여부.",
    },
    "4": {
        "headline_pre": "",
        "headline_key": "미-이란 군사 충돌",
        "headline_post": " 중동 긴장 최고조",
        "facts": [
            "미국이 이란 군사 시설과 드론 기지를 수차례 공습했고, 이란도 공군 기지 공격으로 맞서며 긴장이 고조됐다.",
            "국제 유가(WTI)는 배럴당 85.20달러로 전주 대비 3.8% 올랐고, 국제 금값은 2,150달러로 1.5% 상승했다.",
            "원·달러 환율은 1,385원으로 0.7% 올랐고, 글로벌 변동성 지수(VIX)는 19.30으로 12.1% 뛰었다.",
        ],
        "sources": ["Reuters"],
        "bullish": [
            {"name": "정유·에너지", "reason": "WTI가 85.20달러까지 오르며 정제 마진이 개선됐다.",
             "stocks": ["S-Oil", "GS"]},
            {"name": "방산", "reason": "중동 군사 충돌로 글로벌 국방 예산 확대 기조가 강화됐다.",
             "stocks": ["한화에어로", "LIG넥스원"]},
        ],
        "bullish_fact": "정유주와 방산주가 유가·지정학 테마에 연동됐다.",
        "bearish": [
            {"name": "항공·운송", "reason": "유가 3.8% 상승과 해상 운송로 불안으로 연료·물류비 부담이 커졌다.",
             "stocks": ["대한항공", "HMM"]},
            {"name": "화학·정유전방", "reason": "원유·납사 원가 상승으로 수익성 압박이 가중됐다.",
             "stocks": ["LG화학", "롯데케미칼"]},
        ],
        "bearish_fact": "수출 중심 한국 경제는 에너지 비용 상승과 해상 운송 불안에 직접 노출됐다.",
        "summaries": [
            "미·이란 군사 충돌로 중동 지정학 리스크가 최고조에 달했다.",
            "유가 3.8%·금값 1.5% 상승 등 안전자산·원자재가 동반 강세를 보였다.",
            "VIX가 12.1% 급등하며 글로벌 위험회피 심리가 강해졌다.",
        ],
        "watch_point": "중동 군사 충돌 확전 여부와 원·달러 환율 1,385원선 흐름.",
    },
}


# ──────────────────────────────────────────────────────────────
# 슬라이드 빌더
# ──────────────────────────────────────────────────────────────
def slide_cover(hook_title: str, one_line: str, img_uri: str) -> str:
    hook_html = hook_title.replace("\n", "<br/>")
    img_tag = (
        f'<img src="{img_uri}" style="position:absolute;inset:0;width:100%;height:100%;'
        'object-fit:cover;object-position:center;"/>'
        if img_uri else ""
    )
    hashtags = ""
    for tag in ["#경제", "#글로벌"]:
        hashtags += (
            f'<span style="display:inline-block;background:#1A1A1A;color:#888;'
            'font-size:20px;padding:8px 18px;border-radius:20px;border:1px solid #333;'
            'margin-right:10px;">' + tag + "</span>"
        )

    return (
        f'<div id="slide-1" class="kp" style="width:1080px;height:1350px;position:relative;'
        f'overflow:hidden;background:{DARK};">'
        # 상단 55% 이미지
        f'<div style="position:absolute;top:0;left:0;right:0;height:55%;background:#1A1A1A;overflow:hidden;">{img_tag}</div>'
        # 하단 45% 텍스트
        f'<div style="position:absolute;top:55%;left:0;right:0;bottom:0;background:{DARK};'
        'padding:48px 72px;display:flex;flex-direction:column;">'
        # 상단 1px 선 + 브랜드/날짜
        '<div style="border-top:1px solid #333;padding-top:24px;display:flex;'
        'justify-content:space-between;align-items:center;">'
        f'<span style="color:{GREEN};font-size:14px;font-weight:700;letter-spacing:0.2em;">SIGNALFEED</span>'
        f'<span style="color:#666;font-size:14px;">{DATE_STR}</span>'
        "</div>"
        f'<h1 style="color:#FFFFFF;font-weight:900;font-size:80px;line-height:1.12;'
        'letter-spacing:-0.02em;margin-top:36px;">' + hook_html + "</h1>"
        f'<p style="color:#AAAAAA;font-size:24px;line-height:1.5;margin-top:28px;">{one_line}</p>'
        f'<div style="margin-top:auto;">{hashtags}</div>'
        "</div>"
        f'<div style="position:absolute;bottom:0;left:0;right:0;height:3px;background:{GREEN};"></div>'
        "</div>"
    )


def _frame_header(right_label_html: str) -> str:
    """아이보리 슬라이드 상단 브랜드 행 + 1px 선"""
    return (
        '<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:{GREEN};font-size:14px;font-weight:700;letter-spacing:0.2em;">SIGNALFEED</span>'
        f"{right_label_html}"
        "</div>"
        f'<div style="border-top:1px solid {BORDER};margin-top:20px;"></div>'
    )


def slide_context(content: dict, page_label: str) -> str:
    facts = content["facts"]
    headline = (
        content["headline_pre"]
        + f'<span style="background:{YELLOW};padding:0 6px;border-radius:3px;">{content["headline_key"]}</span>'
        + content["headline_post"]
    )

    fact_rows = ""
    for i, fact in enumerate(facts[:3]):
        border = "" if i == 0 else f"border-top:1px solid {BORDER_LIGHT};"
        fact_rows += (
            f'<div style="flex:1;display:flex;align-items:center;gap:20px;padding:28px 0;{border}">'
            f'<span style="color:{GREEN};font-size:32px;font-weight:900;flex-shrink:0;line-height:1;">✓</span>'
            f'<p style="font-size:28px;color:{TEXT_MAIN};line-height:1.55;font-weight:400;">{hl(fact)}</p>'
            "</div>"
        )

    src_pills = ""
    for src in content["sources"]:
        src_pills += (
            f'<span style="display:inline-block;border:1px solid {BORDER};color:{TEXT_SUB};'
            'font-size:16px;padding:6px 16px;border-radius:18px;margin-right:10px;">' + src + "</span>"
        )

    return (
        f'<div id="slide-2" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'padding:72px;display:flex;flex-direction:column;overflow:hidden;">'
        + _frame_header(f'<span style="color:{TEXT_SUB};font-size:14px;" class="italic">In Brief</span>')
        + f'<p class="italic" style="color:{TEXT_SUB};font-size:20px;margin-top:40px;">무슨 일이?</p>'
        + f'<h2 style="font-size:56px;font-weight:900;color:{TEXT_MAIN};line-height:1.25;'
          'letter-spacing:-0.02em;margin-top:16px;">' + headline + "</h2>"
        + f'<div style="border-top:1px solid {BORDER};margin-top:36px;"></div>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{fact_rows}</div>'
        + f'<div style="border-top:1px solid {BORDER};padding-top:28px;">{src_pills}</div>'
        + f'<span style="color:{TEXT_SUB};font-size:14px;margin-top:20px;">{page_label}</span>'
        + "</div>"
    )


def slide_sectors(page_num: int, section_tag: str, tag_color: str, section_label: str,
                  sectors: list, fact: str, fact_color: str,
                  pill_bg: str, pill_color: str, name_color: str) -> str:
    tag_pill = (
        f'<span style="display:inline-block;background:{pill_bg};color:{tag_color};'
        'font-size:16px;font-weight:700;padding:6px 16px;border-radius:18px;">' + section_tag + "</span>"
    )

    sector_rows = ""
    for i, s in enumerate(sectors[:2]):
        border = "" if i == 0 else f"border-top:1px solid {BORDER};"
        sector_rows += (
            f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:28px 0;{border}">'
            f'<div style="font-size:72px;font-weight:900;color:{name_color};line-height:1.0;'
            'letter-spacing:-0.02em;">' + s["name"] + "</div>"
            f'<div style="font-size:26px;color:#555;line-height:1.5;margin-top:16px;">{hl(s["reason"])}</div>'
            f'<div style="margin-top:18px;">{stock_pills(s["stocks"], pill_bg, pill_color)}</div>'
            "</div>"
        )

    return (
        f'<div id="slide-{page_num}" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'padding:72px;display:flex;flex-direction:column;overflow:hidden;">'
        + _frame_header(tag_pill)
        + f'<p class="italic" style="color:{TEXT_SUB};font-size:20px;margin-top:40px;">{section_label}</p>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;margin-top:8px;">{sector_rows}</div>'
        + f'<div style="border-top:1px solid {BORDER};padding-top:24px;">'
        + f'<span style="font-size:14px;font-weight:700;color:{fact_color};letter-spacing:0.12em;">FACT /</span>'
        + f'<p style="font-size:20px;color:#555;line-height:1.5;margin-top:10px;">{fact}</p>'
        + "</div>"
        + f'<span style="color:{TEXT_SUB};font-size:14px;margin-top:18px;">{page_num}/5</span>'
        + "</div>"
    )


def slide_conclusion(content: dict) -> str:
    summaries = content["summaries"]
    colors = [GREEN, RED, TEXT_SUB]
    sum_rows = ""
    for i, text in enumerate(summaries[:3]):
        border = "" if i == 0 else f"border-top:1px solid {BORDER_LIGHT};"
        sum_rows += (
            f'<div style="flex:1;display:flex;align-items:center;gap:24px;padding:24px 0;{border}">'
            f'<span style="color:{colors[i]};font-size:48px;font-weight:900;flex-shrink:0;'
            'line-height:1;">' + f"{i+1:02d}." + "</span>"
            f'<p style="font-size:28px;color:{TEXT_MAIN};line-height:1.45;font-weight:500;">{text}</p>'
            "</div>"
        )

    return (
        f'<div id="slide-5" class="kp" style="width:1080px;height:1350px;background:{IVORY};'
        'padding:72px;display:flex;flex-direction:column;overflow:hidden;">'
        + _frame_header('<span style="color:#888;font-size:14px;">5/5</span>')
        + f'<p class="italic" style="color:{TEXT_SUB};font-size:20px;margin-top:36px;">오늘의 핵심</p>'
        + f'<div style="flex:1;display:flex;flex-direction:column;justify-content:center;">{sum_rows}</div>'
        # 주목 포인트
        + f'<div style="border-left:3px solid {GREEN};padding-left:24px;margin-top:8px;">'
        + f'<p class="italic" style="color:{TEXT_SUB};font-size:14px;">주목 포인트 →</p>'
        + f'<p style="font-size:24px;color:{TEXT_MAIN};line-height:1.5;margin-top:10px;">{hl(content["watch_point"])}</p>'
        + "</div>"
        # CTA
        + '<div style="background:#1A1A1A;border-radius:12px;padding:32px 40px;margin-top:32px;">'
        + f'<p style="font-size:26px;font-weight:700;color:{IVORY};">댓글에 \'분석\' 남겨주세요</p>'
        + f'<p style="font-size:20px;color:{GREEN};margin-top:8px;">→ 상세 리포트 DM으로 드립니다</p>'
        + "</div>"
        + f'<div style="border-top:1px solid {BORDER};margin-top:28px;padding-top:18px;">'
        + '<p style="font-size:13px;color:#AAA;text-align:center;">'
        + "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다</p>"
        + "</div>"
        + "</div>"
    )


def build_full_html(script: dict, content: dict, img_uri: str) -> str:
    hook_title = script.get("hook_title", "경제 뉴스")
    one_line = script.get("one_line", "")

    slides = [
        slide_cover(hook_title, one_line, img_uri),
        slide_context(content, "2/5"),
        slide_sectors(3, "↑ 수혜", "#0A5C3A", "이번 이슈, 누가 웃나?",
                      content["bullish"], content["bullish_fact"], GREEN,
                      "#E8F5E9", "#0A5C3A", TEXT_MAIN),
        slide_sectors(4, "↓ 주의", "#8B2020", "이번 이슈, 누가 우나?",
                      content["bearish"], content["bearish_fact"], RED,
                      "#FFEBEE", "#8B2020", TEXT_MAIN),
        slide_conclusion(content),
    ]
    body = "".join(slides)
    return f'<!DOCTYPE html><html lang="ko"><head>{HEAD}</head><body>{body}</body></html>'


def select_cluster(scripts: list) -> dict:
    hangul = re.compile(r"[가-힣]")
    for s in scripts:
        if hangul.search(s.get("hook_title", "")):
            logger.info(f"선택된 클러스터: issue_id={s.get('issue_id')} hook='{s.get('hook_title','').strip()}'")
            return s
    logger.info("한국어 hook 없음 → 첫 번째 클러스터 사용")
    return scripts[0]


def main():
    scripts_path = os.path.join(ROOT, "data/3_generated/scripts.json")
    with open(scripts_path, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    script = select_cluster(scripts)
    issue_id = script.get("issue_id", "2")
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
    img_path = os.path.join(temp_dir, f"pixabay_v3_{issue_id}.jpg")
    if not fetcher.fetch(keyword, img_path):
        logger.warning("Pixabay 실패 → fallback 배경 사용")
        fetcher.save_fallback(img_path)
    img_uri = img_to_base64(img_path)
    logger.info(f"이미지 저장: {img_path} (base64 {len(img_uri)} bytes)")

    # HTML 생성
    html = build_full_html(script, content, img_uri)
    html_path = os.path.join(temp_dir, "cards_v3.html")
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

    logger.info(f"카드 V3 생성 완료 → {out_dir}")
    return out_dir


if __name__ == "__main__":
    main()
