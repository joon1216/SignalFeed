"""
벤치마크 콘텐츠 수집기 (Session 44 — 레퍼런스 분석 시스템)

reference/urls.txt의 URL에서 분석용 이미지/썸네일을 reference/raw/{slug}/에 저장한다.
- Instagram: instaloader (공개 게시물, 로그인/API 키 불필요)
- YouTube: yt-dlp (썸네일 + 제목/메타데이터만 — 영상은 받지 않음)
- 도구 미설치/실패 시 해당 URL은 건너뛰고 안내 출력 (전체 중단 없음)

사용:
    venv/bin/pip install instaloader yt-dlp   # 선택 설치 (무료, 키 불필요)
    venv/bin/python backend/reference/collect.py
"""

import os
import re
import sys
import json
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

URLS_PATH = os.path.join(ROOT, "reference", "urls.txt")
RAW_DIR = os.path.join(ROOT, "reference", "raw")


def read_urls(path: str = URLS_PATH) -> list:
    if not os.path.exists(path):
        logger.warning(f"{path} 없음 — URL을 추가하세요.")
        return []
    urls = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def slugify(url: str) -> str:
    m = re.search(r"(?:instagram\.com/(?:p|reel)/|youtube\.com/(?:shorts/|watch\?v=)|youtu\.be/)([\w-]+)", url)
    core = m.group(1) if m else re.sub(r"\W+", "_", url)[-30:]
    platform = "ig" if "instagram.com" in url else "yt"
    return f"{platform}_{core}"


def collect_instagram(url: str, out_dir: str) -> bool:
    try:
        import instaloader
    except ImportError:
        logger.warning(f"instaloader 미설치 → skip: {url}  (venv/bin/pip install instaloader)")
        return False
    try:
        m = re.search(r"instagram\.com/(?:p|reel)/([\w-]+)", url)
        if not m:
            logger.warning(f"Instagram URL 파싱 실패: {url}")
            return False
        shortcode = m.group(1)
        loader = instaloader.Instaloader(
            dirname_pattern=out_dir, download_videos=False,
            download_video_thumbnails=True, save_metadata=True,
            download_comments=False, post_metadata_txt_pattern="{caption}",
        )
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        loader.download_post(post, target=os.path.basename(out_dir))
        logger.info(f"✅ Instagram 수집: {url} → {out_dir}")
        return True
    except Exception as e:
        logger.warning(f"Instagram 수집 실패 ({url}): {e}")
        return False


def collect_youtube(url: str, out_dir: str) -> bool:
    try:
        import yt_dlp
    except ImportError:
        logger.warning(f"yt-dlp 미설치 → skip: {url}  (venv/bin/pip install yt-dlp)")
        return False
    try:
        opts = {
            "skip_download": True,        # 영상은 받지 않음 — 썸네일/메타만
            "writethumbnail": True,
            "outtmpl": os.path.join(out_dir, "%(id)s.%(ext)s"),
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        meta = {k: info.get(k) for k in ("id", "title", "channel", "view_count", "like_count", "upload_date")}
        with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ YouTube 썸네일/메타 수집: {url} → {out_dir}")
        return True
    except Exception as e:
        logger.warning(f"YouTube 수집 실패 ({url}): {e}")
        return False


def main():
    urls = read_urls()
    if not urls:
        logger.info("수집할 URL 없음. reference/urls.txt에 벤치마크 URL을 추가하세요.")
        return
    ok = 0
    for url in urls:
        out_dir = os.path.join(RAW_DIR, slugify(url))
        os.makedirs(out_dir, exist_ok=True)
        if "instagram.com" in url:
            ok += collect_instagram(url, out_dir)
        elif "youtube.com" in url or "youtu.be" in url:
            ok += collect_youtube(url, out_dir)
        else:
            logger.warning(f"지원하지 않는 URL: {url}")
    logger.info(f"수집 완료: {ok}/{len(urls)}. 다음 단계 → reference/ANALYZE.md")


if __name__ == "__main__":
    main()
