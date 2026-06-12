"""content_gen 테스트 — 캐시로 API 호출 차단, 결함 Gemini 출력의 수리/차단 (네트워크 없음)"""

import pytest

from backend.modules.content_gen import ContentGenerator, build_material
from backend.modules.content_validator import check_sector_reason, is_duplicate

CLUSTER_6 = {
    "cluster_id": 6,
    "cluster_label": "Fed rate hike inflation",
    "articles": [
        {"title": "More Fed policymakers eye possible rate hike as inflation risks rise",
         "summary": "Fed officials reaffirmed tightening bias at 5.50%.", "source": "Reuters"},
        {"title": "Euro zone inflation rebounds to 2.8% in May",
         "summary": "Up from 2.6% the prior month.", "source": "Reuters"},
    ],
}


def make_generator(tmp_path, use_cache=True):
    return ContentGenerator(use_cache=use_cache, allow_api=False,
                            cache_dir=str(tmp_path / "cache"))


class TestFallbackPath:
    def test_fallback_script_is_valid(self, tmp_path):
        gen = make_generator(tmp_path)
        script = gen.generate_script(CLUSTER_6, check_market=False)
        assert script["from_fallback"] is True
        # 커버는 한국어
        assert any("가" <= c <= "힣" for c in script["hook_title"])
        # 섹터-이유 정합성
        for s in script["inner"]["slide3_sectors"] + script["inner"]["slide4_sectors"]:
            ok, _ = check_sector_reason(s["name"], s["reason"])
            assert ok
        # 중복 없음
        facts = script["inner"]["slide2_facts"]
        for key in ("slide3_fact", "slide4_fact"):
            if script["inner"][key]:
                assert not is_duplicate(script["inner"][key], facts)
        # 팩트 체크는 섹터 논리 통과 (금리 인상 토픽)
        assert script["fact_check"]["status"] in ("passed", "warning")

    def test_unknown_cluster_uses_generic_fallback(self, tmp_path):
        gen = make_generator(tmp_path)
        cluster = {"cluster_id": 999, "cluster_label": "Something else",
                   "articles": [{"title": "t", "summary": "s", "source": "CNBC"}]}
        script = gen.generate_script(cluster, check_market=False)
        assert script["from_fallback"] is True
        assert any("가" <= c <= "힣" for c in script["hook_title"])
        assert script["sources"] == ["CNBC"]


class TestCache:
    def test_second_call_hits_cache(self, tmp_path):
        gen = make_generator(tmp_path)
        first = gen.generate_script(CLUSTER_6, check_market=False)
        assert first.get("from_cache") is False

        second = gen.generate_script(CLUSTER_6, check_market=False)
        assert second.get("from_cache") is True
        assert second["hook_title"] == first["hook_title"]

    def test_cache_hit_skips_api_and_fact_check(self, tmp_path):
        """quota 보호의 핵심: 캐시 적중 시 Gemini/yfinance 모두 호출되지 않음"""
        gen = make_generator(tmp_path)
        gen.generate_script(CLUSTER_6, check_market=False)

        def boom(*a, **k):
            raise AssertionError("캐시 적중 시 외부 호출이 발생하면 안 됨")

        gen._call_gemini = boom
        gen.fact_checker.validate = boom
        script = gen.generate_script(CLUSTER_6, check_market=True)
        assert script["from_cache"] is True

    def test_material_change_misses_cache(self, tmp_path):
        gen = make_generator(tmp_path)
        gen.generate_script(CLUSTER_6, check_market=False)
        other = dict(CLUSTER_6, cluster_label="totally different issue")
        script = gen.generate_script(other, check_market=False)
        assert script.get("from_cache") is False

    def test_build_material_deterministic(self):
        assert build_material(CLUSTER_6) == build_material(CLUSTER_6)


class TestDefectiveGeminiOutput:
    """실물 결함과 동일한 Gemini 출력이 와도 최종 스크립트에 결함이 남을 수 없음"""

    DEFECTIVE_RAW = {
        "hook_title": "Inflation rising again",  # 결함: 영문 훅
        "one_line": "Morning Bid: Who needs oil when there's AI to buy?",  # 결함: 영문
        "sources": ["Reuters: Record-low U.S. shale well backlog curbs fast output gains"],  # 결함: 헤드라인
        "image_keyword": "federal reserve building",
        "slide2_facts": [
            "미국 연준 위원 다수가 물가 상승 위험을 이유로 현재 금리 5.50% 수준에서 추가 인상 가능성을 언급하며 긴축 기조를 재확인했다.",
            "유로존 5월 소비자물가 상승률은 2.8%로 전월 2.6%에서 반등했다.",
            "미국 셰일 유정 완결 대기 물량은 약 4,150개로 사상 최저 수준까지 줄었다.",
        ],
        "slide2_source": "출처 · Reuters",
        "slide3_sectors": [
            {"name": "은행·금융", "reason": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다."},
            {"name": "바이오·제약", "reason": "금리가 5.50%까지 오르며 보험·운용자산 수익률이 높아졌다."},  # 결함
        ],
        "slide3_fact": "미국 연준 위원 다수가 물가 상승 위험을 이유로 현재 금리 5.50% 수준에서 추가 인상 가능성을 언급하며 긴축 기조를 재확인했다.",  # 결함: 중복
        "slide4_sectors": [
            {"name": "건설업종", "reason": "조달 금리가 5.50%로 오르며 이자 부담이 커졌다."},
            {"name": "유통·소비재", "reason": "긴축 장기화로 소비 여력이 줄었다."},
        ],
        "slide4_fact": "미국 셰일 유정 완결 대기 물량은 약 4,150개로 사상 최저 수준까지 줄었다.",  # 결함: 중복
        "slide5_summaries": [
            "미국 연준 위원들이 현재 금리 5.50% 수준에서 추가 인상 가능성을 언급하며 긴축 기조를 재확인했다.",  # 결함: 중복
            "금리 수혜 업종과 부담 업종의 온도 차가 뚜렷해졌다.",
            "셰일 공급 여력 축소가 유가 하방을 제한하는 요인으로 꼽혔다.",
        ],
        "slide5_watch_point": "다음 FOMC 금리 결정.",
    }

    def test_defects_repaired_end_to_end(self, tmp_path, monkeypatch):
        gen = ContentGenerator(use_cache=False, allow_api=True)
        gen.allow_api = True  # 키 없이도 _call_gemini 모킹 경로로
        monkeypatch.setattr(gen, "_call_gemini", lambda material: dict(self.DEFECTIVE_RAW))

        script = gen.generate_script(CLUSTER_6, check_market=False)

        # 결함 1: 섹터-이유 불일치 잔존 불가
        for s in script["inner"]["slide3_sectors"] + script["inner"]["slide4_sectors"]:
            ok, _ = check_sector_reason(s["name"], s["reason"])
            assert ok
        # 결함 2: 중복 잔존 불가
        facts = script["inner"]["slide2_facts"]
        for key in ("slide3_fact", "slide4_fact"):
            if script["inner"][key]:
                assert not is_duplicate(script["inner"][key], facts)
        for summ in script["inner"]["slide5_summaries"]:
            assert not is_duplicate(summ, facts)
        # 결함 3: 출처는 매체명만
        assert script["sources"] == ["Reuters"]
        # 영문 커버 잔존 불가
        assert any("가" <= c <= "힣" for c in script["hook_title"])
        assert any("가" <= c <= "힣" for c in script["one_line"])

    def test_hopeless_gemini_output_falls_back(self, tmp_path, monkeypatch):
        gen = ContentGenerator(use_cache=False, allow_api=True)
        gen.allow_api = True
        monkeypatch.setattr(gen, "_call_gemini",
                            lambda material: {"hook_title": "x", "slide2_facts": []})
        script = gen.generate_script(CLUSTER_6, check_market=False)
        assert script["from_fallback"] is True
