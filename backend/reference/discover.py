"""
벤치마크 자동 발굴 (Session 45 — 레퍼런스 분석 시스템)

reference/accounts.txt의 계정 목록에서 성과 상위 게시물을 자동 선별해
reference/discovered.json + reference/urls.txt에 누적한다.

- Instagram (instaloader): 프로필 팔로워 수 + 최근 게시물 메타데이터만 수집
  (미디어 다운로드 없음). engagement_rate = (좋아요+댓글)/팔로워 상위 5개 선정.
  로그인 세션은 .env의 IG_SESSION_FILE (instaloader --login으로 생성한 세션 파일).
  요청은 보수적으로: 계정당 최근 50개, 게시물당 sleep, 계정 간 sleep.
- YouTube (yt-dlp, 키 불필요): --flat-playlist 메타데이터만 (다운로드 없음).
  구독자 대비 조회수 비율 상위 5개 선정.
- 실패한 계정은 건너뛰고 reference/failed.log에 기록.
- --collect: 선별된 게시물만 collect.py로 이미지/메타데이터 수집까지 실행.

사용:
    venv/bin/pip install instaloader yt-dlp     # 선택 설치
    venv/bin/python backend/reference/discover.py [--collect]
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ACCOUNTS_PATH = os.path.join(ROOT, "reference", "accounts.txt")
DISCOVERED_PATH = os.path.join(ROOT, "reference", "discovered.json")
URLS_PATH = os.path.join(ROOT, "reference", "urls.txt")
FAILED_LOG = os.path.join(ROOT, "reference", "failed.log")

MAX_POSTS = 50          # 계정당 최근 게시물 수 (보수적 상한)
TOP_N = 5               # 계정별 선정 수
SLEEP_PER_POST = 1.0    # 인스타 게시물 메타 요청 간 sleep
SLEEP_BETWEEN_ACCOUNTS = 10.0


# ──────────────────────────────────────────────────────────────
# 입력 파싱
# ──────────────────────────────────────────────────────────────
def parse_accounts(path: str = ACCOUNTS_PATH) -> List[Tuple[str, str]]:
    """accounts.txt → [("ig", 계정명) | ("yt", 채널URL)]"""
    if not os.path.exists(path):
        logger.warning(f"{path} 없음 — 계정을 추가하세요.")
        return []
    accounts: List[Tuple[str, str]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("ig:"):
                accounts.append(("ig", line[3:].strip().lstrip("@")))
            elif line.startswith("yt:"):
                accounts.append(("yt", line[3:].strip()))
            else:
                logger.warning(f"형식 오류 줄 skip: '{line}' (ig:계정명 / yt:채널URL)")
    return accounts


# ──────────────────────────────────────────────────────────────
# 랭킹 (순수 함수 — 네트워크 없음)
# ──────────────────────────────────────────────────────────────
def rank_instagram(posts: List[Dict], followers: int, account: str,
                   top_n: int = TOP_N) -> List[Dict]:
    """게시물 메타데이터 → engagement_rate 상위 top_n 후보"""
    if followers <= 0:
        logger.warning(f"@{account}: 팔로워 0 → engagement 계산 불가, raw 좋아요로 랭킹")
    scored = []
    for p in posts:
        likes = p.get("likes") or 0
        comments = p.get("comments") or 0
        rate = (likes + comments) / followers if followers > 0 else 0.0
        scored.append({
            "url": f"https://www.instagram.com/p/{p['shortcode']}/",
            "platform": "instagram",
            "account": account,
            "metrics": {"followers": followers, "likes": likes,
                        "comments": comments, "engagement_rate": round(rate, 5)},
            "reason": f"engagement {rate * 100:.2f}% (좋아요 {likes:,} + 댓글 {comments:,} / 팔로워 {followers:,})",
            "_sort": rate if followers > 0 else likes + comments,
        })
    scored.sort(key=lambda c: c["_sort"], reverse=True)
    for c in scored:
        c.pop("_sort")
    return scored[:top_n]


def rank_youtube(entries: List[Dict], subscribers: int, account: str,
                 top_n: int = TOP_N) -> List[Dict]:
    """영상 목록 → 구독자 대비 조회수 비율 상위 top_n 후보"""
    scored = []
    for e in entries:
        views = e.get("view_count") or 0
        ratio = views / subscribers if subscribers > 0 else 0.0
        scored.append({
            "url": e["url"],
            "platform": "youtube",
            "account": account,
            "metrics": {"subscribers": subscribers, "views": views,
                        "view_ratio": round(ratio, 3), "title": e.get("title", "")},
            "reason": (f"조회수/구독자 {ratio:.2f}x (조회 {views:,} / 구독 {subscribers:,})"
                       if subscribers > 0 else f"조회수 {views:,} (구독자 미확인)"),
            "_sort": ratio if subscribers > 0 else views,
        })
    scored.sort(key=lambda c: c["_sort"], reverse=True)
    for c in scored:
        c.pop("_sort")
    return scored[:top_n]


# ──────────────────────────────────────────────────────────────
# 네트워크 페처 (테스트에서는 mock)
# ──────────────────────────────────────────────────────────────
def _session_username(session_path: str) -> Optional[str]:
    """instaloader 세션 파일명(session-<username>)에서 username 유추"""
    base = os.path.basename(session_path)
    if base.startswith("session-"):
        return base[len("session-"):]
    return None


def fetch_instagram(handle: str, max_posts: int = MAX_POSTS) -> Tuple[int, List[Dict]]:
    """프로필 팔로워 수 + 최근 게시물 메타데이터 (미디어 다운로드 없음)"""
    import instaloader

    loader = instaloader.Instaloader(
        quiet=True, download_pictures=False, download_videos=False,
        download_video_thumbnails=False, save_metadata=False,
        download_comments=False,
    )
    session_file = os.getenv("IG_SESSION_FILE")
    if session_file and os.path.exists(session_file):
        username = os.getenv("IG_USERNAME") or _session_username(session_file)
        try:
            loader.load_session_from_file(username, session_file)
            logger.info(f"IG 세션 로드: {username}")
        except Exception as e:
            logger.warning(f"IG 세션 로드 실패 ({e}) → 익명으로 시도")
    else:
        logger.info("IG_SESSION_FILE 없음 → 익명으로 시도 (rate limit 더 엄격)")

    profile = instaloader.Profile.from_username(loader.context, handle)
    followers = profile.followers

    posts: List[Dict] = []
    for i, post in enumerate(profile.get_posts()):
        if i >= max_posts:
            break
        posts.append({
            "shortcode": post.shortcode,
            "likes": post.likes,
            "comments": post.comments,
            "date": post.date_utc.isoformat(),
            "is_video": post.is_video,
        })
        time.sleep(SLEEP_PER_POST)  # 보수적 요청 간격
    return followers, posts


def fetch_youtube(channel_url: str, max_videos: int = MAX_POSTS) -> Tuple[int, List[Dict]]:
    """채널 영상 목록 메타데이터 (--flat-playlist, 다운로드 없음)"""
    import yt_dlp

    opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "playlistend": max_videos,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)

    subscribers = info.get("channel_follower_count") or 0

    def flatten(node) -> List[Dict]:
        out = []
        for e in (node.get("entries") or []):
            if not e:
                continue
            if e.get("entries"):  # 채널 탭 중첩
                out.extend(flatten(e))
            else:
                out.append(e)
        return out

    entries = []
    for e in flatten(info)[:max_videos]:
        url = e.get("url") or (f"https://www.youtube.com/watch?v={e['id']}" if e.get("id") else None)
        if not url:
            continue
        entries.append({"url": url, "title": e.get("title", ""),
                        "view_count": e.get("view_count") or 0})
    return subscribers, entries


# ──────────────────────────────────────────────────────────────
# 출력
# ──────────────────────────────────────────────────────────────
def append_unique_urls(urls: List[str], path: str = URLS_PATH) -> List[str]:
    """urls.txt에 중복 없이 append. 새로 추가된 URL 목록 반환"""
    existing = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    existing.add(line)
    # 기존 파일·입력 내 중복 모두 제거 (순서 보존)
    seen, deduped = set(), []
    for u in urls:
        if u not in existing and u not in seen:
            seen.add(u)
            deduped.append(u)
    if deduped:
        with open(path, "a", encoding="utf-8") as f:
            for u in deduped:
                f.write(u + "\n")
    return deduped


def log_failure(account: str, error: str, path: str = FAILED_LOG) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{account}\t{error}\n")


def save_discovered(candidates: List[Dict], path: str = DISCOVERED_PATH) -> None:
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(candidates),
        "candidates": candidates,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 {len(candidates)}개 후보 저장 → {path}")


# ──────────────────────────────────────────────────────────────
# 메인 플로우
# ──────────────────────────────────────────────────────────────
def discover(accounts_path: str = ACCOUNTS_PATH, collect: bool = False) -> Dict:
    """계정 목록 → 성과 상위 후보 발굴 → discovered.json + urls.txt 누적"""
    accounts = parse_accounts(accounts_path)
    if not accounts:
        logger.info("발굴할 계정 없음. reference/accounts.txt에 ig:계정명 / yt:채널URL을 추가하세요.")
        return {"candidates": [], "added_urls": [], "failed": []}

    candidates: List[Dict] = []
    failed: List[str] = []

    for i, (platform, value) in enumerate(accounts):
        if i > 0:
            time.sleep(SLEEP_BETWEEN_ACCOUNTS)  # 계정 간 보수적 간격
        try:
            if platform == "ig":
                logger.info(f"📷 Instagram 발굴: @{value}")
                followers, posts = fetch_instagram(value)
                picked = rank_instagram(posts, followers, value)
            else:
                logger.info(f"▶️ YouTube 발굴: {value}")
                subscribers, entries = fetch_youtube(value)
                picked = rank_youtube(entries, subscribers, value)
            candidates.extend(picked)
            logger.info(f"   → {len(picked)}개 선정")
        except Exception as e:
            logger.warning(f"   ❌ 실패 → skip: {value} ({e})")
            log_failure(f"{platform}:{value}", str(e), FAILED_LOG)
            failed.append(f"{platform}:{value}")

    save_discovered(candidates, DISCOVERED_PATH)
    added = append_unique_urls([c["url"] for c in candidates], URLS_PATH)
    logger.info(f"urls.txt에 {len(added)}개 신규 추가 (중복 {len(candidates) - len(added)}개 제외)")

    if collect and candidates:
        from backend.reference.collect import collect_urls
        logger.info("선별 게시물 수집 시작 (collect.py)")
        collect_urls([c["url"] for c in candidates])

    return {"candidates": candidates, "added_urls": added, "failed": failed}


def main():
    parser = argparse.ArgumentParser(description="벤치마크 자동 발굴")
    parser.add_argument("--collect", action="store_true",
                        help="발굴 후 선별 게시물 이미지/메타데이터 수집까지 실행")
    args = parser.parse_args()
    result = discover(collect=args.collect)
    logger.info(f"발굴 완료: 후보 {len(result['candidates'])}개, "
                f"신규 URL {len(result['added_urls'])}개, 실패 {len(result['failed'])}개")


if __name__ == "__main__":
    main()
