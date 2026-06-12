"""
SignalFeed 카드 렌더링 엔트리 (Session 44 — 단일 production 경로)

scripts.json(검증 완료 구조화 스크립트) → 카드 5장 PNG.
이 단계는 Gemini를 호출하지 않는다 (Pixabay 이미지 검색만, 실패 시 단색 fallback).
렌더링 전에 validator를 한 번 더 통과시킨다 (defense in depth — 손으로 고친
scripts.json이나 구버전 파일이 들어와도 결함 카드가 나갈 수 없음).

사용:
    venv/bin/python backend/generate_cards.py                      # 모든 클러스터
    venv/bin/python backend/generate_cards.py --issue 6            # 특정 클러스터
    venv/bin/python backend/generate_cards.py --scripts path --out dir
"""

import os
import sys
import json
import argparse
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from backend.modules.card_renderer import img_to_base64, render_slides, screenshot_slides
from backend.modules.content_validator import ensure_korean_cover, validate_inner
from backend.modules.image_fetcher import ImageFetcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def prepare_script(script: dict) -> dict | None:
    """렌더링 전 재검증. 구버전 스키마/비생존 콘텐츠는 None."""
    if "inner" not in script:
        logger.warning(
            f"issue {script.get('issue_id')}: 구버전 스키마 (inner 없음) → skip. "
            "pipeline --steps 3 으로 scripts.json을 재생성하세요."
        )
        return None
    inner, viable, _ = validate_inner(script["inner"])
    if not viable:
        logger.warning(f"issue {script.get('issue_id')}: 검증 비생존 → skip")
        return None
    script = dict(script)
    script["inner"] = inner
    script["hook_title"], script["one_line"], _ = ensure_korean_cover(
        script.get("hook_title", ""), script.get("one_line", ""))
    return script


def fetch_cover_image(script: dict, temp_dir: str) -> str:
    """Pixabay 커버 이미지 → base64 data URI ('' 가능)"""
    fetcher = ImageFetcher()
    issue_text = " ".join([
        script.get("hook_title", "").replace("\n", " "),
        script.get("one_line", ""),
        script.get("image_keyword", ""),
    ])
    keyword = fetcher.get_keyword(issue_text)
    logger.info(f"Pixabay 검색어: '{keyword}'")
    os.makedirs(temp_dir, exist_ok=True)
    img_path = os.path.join(temp_dir, f"cover_{script.get('issue_id', '0')}.jpg")
    if not fetcher.fetch(keyword, img_path):
        logger.warning("Pixabay 실패 → 단색 fallback 배경")
        fetcher.save_fallback(img_path)
    return img_to_base64(img_path)


def generate_for_script(script: dict, out_dir: str, temp_dir: str = "data/temp") -> list:
    """스크립트 1개 → 카드 5장 PNG"""
    prepared = prepare_script(script)
    if prepared is None:
        return []
    img_uri = fetch_cover_image(prepared, temp_dir)
    docs = render_slides(prepared, img_uri)
    return screenshot_slides(docs, out_dir, temp_dir)


def generate_from_scripts(scripts_path: str = "data/3_generated/scripts.json",
                          out_root: str = "data/4_cards",
                          issue_id: str | None = None) -> int:
    """scripts.json 전체 → 클러스터별 카드 디렉토리"""
    with open(scripts_path, "r", encoding="utf-8") as f:
        scripts = json.load(f)

    total = 0
    for script in scripts:
        sid = str(script.get("issue_id", "0"))
        if issue_id is not None and sid != str(issue_id):
            continue
        out_dir = os.path.join(out_root, f"cluster_{sid}")
        saved = generate_for_script(script, out_dir)
        total += len(saved)
    logger.info(f"총 {total}장 카드 생성 완료 → {out_root}")
    return total


def main():
    parser = argparse.ArgumentParser(description="SignalFeed 카드 렌더링")
    parser.add_argument("--scripts", default="data/3_generated/scripts.json")
    parser.add_argument("--out", default="data/4_cards")
    parser.add_argument("--issue", default=None, help="특정 issue_id만 렌더")
    args = parser.parse_args()
    generate_from_scripts(args.scripts, args.out, args.issue)


if __name__ == "__main__":
    main()
