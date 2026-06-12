"""discover.py 테스트 — 전부 mock 기반 (네트워크/instaloader/yt-dlp 불필요)"""

import json

import pytest

from backend.reference import discover as d


# ──────────────────────────────────────────────────────────
# 입력 파싱
# ──────────────────────────────────────────────────────────
class TestParseAccounts:
    def test_parses_ig_and_yt(self, tmp_path):
        path = tmp_path / "accounts.txt"
        path.write_text(
            "# 주석\n"
            "ig:@aiming_official\n"
            "ig:telonews_kr\n"
            "yt:https://www.youtube.com/@chan/shorts\n"
            "\n"
            "잘못된줄\n",
            encoding="utf-8",
        )
        accounts = d.parse_accounts(str(path))
        assert accounts == [
            ("ig", "aiming_official"),   # @ 제거
            ("ig", "telonews_kr"),
            ("yt", "https://www.youtube.com/@chan/shorts"),
        ]

    def test_missing_file(self, tmp_path):
        assert d.parse_accounts(str(tmp_path / "none.txt")) == []


# ──────────────────────────────────────────────────────────
# 랭킹 (순수 함수)
# ──────────────────────────────────────────────────────────
def ig_post(code, likes, comments=0):
    return {"shortcode": code, "likes": likes, "comments": comments,
            "date": "2026-06-01T00:00:00", "is_video": False}


class TestRankInstagram:
    def test_top5_by_engagement(self):
        posts = [ig_post(f"p{i}", likes=i * 100) for i in range(1, 11)]  # p10이 최고
        picked = d.rank_instagram(posts, followers=10000, account="acct")
        assert len(picked) == 5
        assert picked[0]["url"] == "https://www.instagram.com/p/p10/"
        rates = [c["metrics"]["engagement_rate"] for c in picked]
        assert rates == sorted(rates, reverse=True)

    def test_comments_count_in_engagement(self):
        posts = [ig_post("a", likes=100, comments=900), ig_post("b", likes=500)]
        picked = d.rank_instagram(posts, followers=1000, account="acct")
        assert picked[0]["url"].endswith("/a/")  # 100+900 > 500

    def test_zero_followers_no_crash(self):
        posts = [ig_post("a", 100), ig_post("b", 300)]
        picked = d.rank_instagram(posts, followers=0, account="acct")
        assert picked[0]["url"].endswith("/b/")  # raw 좋아요로 랭킹
        assert picked[0]["metrics"]["engagement_rate"] == 0.0

    def test_reason_includes_metrics(self):
        picked = d.rank_instagram([ig_post("a", 500, 50)], followers=10000, account="acct")
        assert "engagement" in picked[0]["reason"]
        assert picked[0]["account"] == "acct"


class TestRankYoutube:
    def test_ratio_ranking(self):
        entries = [
            {"url": "https://youtu.be/low", "title": "low", "view_count": 1000},
            {"url": "https://youtu.be/high", "title": "high", "view_count": 90000},
        ]
        picked = d.rank_youtube(entries, subscribers=10000, account="chan")
        assert picked[0]["url"].endswith("high")
        assert picked[0]["metrics"]["view_ratio"] == 9.0

    def test_zero_subscribers_falls_back_to_views(self):
        entries = [
            {"url": "u1", "title": "", "view_count": 10},
            {"url": "u2", "title": "", "view_count": 99},
        ]
        picked = d.rank_youtube(entries, subscribers=0, account="chan")
        assert picked[0]["url"] == "u2"
        assert "구독자 미확인" in picked[0]["reason"]

    def test_top_n_cap(self):
        entries = [{"url": f"u{i}", "title": "", "view_count": i} for i in range(10)]
        assert len(d.rank_youtube(entries, 100, "chan")) == 5


# ──────────────────────────────────────────────────────────
# urls.txt 중복 제거 append / failed.log
# ──────────────────────────────────────────────────────────
class TestAppendUniqueUrls:
    def test_dedupes_against_existing_and_input(self, tmp_path):
        path = tmp_path / "urls.txt"
        path.write_text("# 주석\nhttps://a/\n", encoding="utf-8")
        added = d.append_unique_urls(["https://a/", "https://b/", "https://b/"], str(path))
        assert added == ["https://b/"]
        content = path.read_text(encoding="utf-8")
        assert content.count("https://a/") == 1
        assert content.count("https://b/") == 1

    def test_creates_file_if_missing(self, tmp_path):
        path = tmp_path / "urls.txt"
        added = d.append_unique_urls(["https://x/"], str(path))
        assert added == ["https://x/"]
        assert "https://x/" in path.read_text(encoding="utf-8")


def test_log_failure_appends_line(tmp_path):
    path = tmp_path / "failed.log"
    d.log_failure("ig:bad_account", "ConnectionError", str(path))
    d.log_failure("yt:bad_chan", "404", str(path))
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert "ig:bad_account" in lines[0] and "ConnectionError" in lines[0]


# ──────────────────────────────────────────────────────────
# discover 전체 플로우 (페처 mock)
# ──────────────────────────────────────────────────────────
@pytest.fixture
def wired(tmp_path, monkeypatch):
    """경로/슬립/페처를 전부 테스트용으로 배선"""
    accounts = tmp_path / "accounts.txt"
    accounts.write_text("ig:good_ig\nyt:https://www.youtube.com/@chan\nig:bad_ig\n",
                        encoding="utf-8")
    monkeypatch.setattr(d, "DISCOVERED_PATH", str(tmp_path / "discovered.json"))
    monkeypatch.setattr(d, "URLS_PATH", str(tmp_path / "urls.txt"))
    monkeypatch.setattr(d, "FAILED_LOG", str(tmp_path / "failed.log"))
    monkeypatch.setattr(d, "SLEEP_BETWEEN_ACCOUNTS", 0)

    def fake_ig(handle, max_posts=50):
        if handle == "bad_ig":
            raise ConnectionError("login required")
        return 10000, [ig_post(f"{handle}_{i}", likes=i * 50) for i in range(1, 8)]

    def fake_yt(url, max_videos=50):
        return 5000, [{"url": f"{url}/v{i}", "title": f"v{i}", "view_count": i * 1000}
                      for i in range(1, 8)]

    monkeypatch.setattr(d, "fetch_instagram", fake_ig)
    monkeypatch.setattr(d, "fetch_youtube", fake_yt)
    return tmp_path, accounts


class TestDiscoverFlow:
    def test_full_flow(self, wired, monkeypatch):
        tmp_path, accounts = wired
        result = d.discover(str(accounts), collect=False)

        # ig 5 + yt 5 (각 7개 중 상위 5), bad_ig는 실패
        assert len(result["candidates"]) == 10
        assert result["failed"] == ["ig:bad_ig"]

        # urls.txt에 10개 누적
        urls = (tmp_path / "urls.txt").read_text(encoding="utf-8").strip().splitlines()
        assert len(urls) == 10

        # failed.log 기록
        assert "ig:bad_ig" in (tmp_path / "failed.log").read_text(encoding="utf-8")

        # discovered.json 저장
        saved = json.loads((tmp_path / "discovered.json").read_text(encoding="utf-8"))
        assert len(saved["candidates"]) == 10

    def test_rerun_does_not_duplicate_urls(self, wired):
        tmp_path, accounts = wired
        d.discover(str(accounts), collect=False)
        result2 = d.discover(str(accounts), collect=False)
        assert result2["added_urls"] == []  # 전부 기존과 중복
        urls = (tmp_path / "urls.txt").read_text(encoding="utf-8").strip().splitlines()
        assert len(urls) == 10

    def test_collect_flag_invokes_collector(self, wired, monkeypatch):
        tmp_path, accounts = wired
        called = {}

        import backend.reference.collect as collect_mod
        monkeypatch.setattr(collect_mod, "collect_urls",
                            lambda urls: called.setdefault("urls", urls) or len(urls))

        result = d.discover(str(accounts), collect=True)
        assert called["urls"] == [c["url"] for c in result["candidates"]]

    def test_empty_accounts(self, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("# 비어있음\n", encoding="utf-8")
        result = d.discover(str(path))
        assert result == {"candidates": [], "added_urls": [], "failed": []}
