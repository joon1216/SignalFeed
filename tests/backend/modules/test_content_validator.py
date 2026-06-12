"""content_validator 회귀 테스트 — Session 44 결함 C가 재발 불가능함을 증명"""

import pytest

from backend.modules.content_validator import (
    GENERIC_HOOK,
    KoreanSector,
    check_sector_reason,
    clean_sources,
    dedupe_inner,
    ensure_korean_cover,
    find_banned,
    is_duplicate,
    repair_sectors,
    similarity,
    validate_inner,
)

# 실물 카드(data/6_cards_v2, 2026-06-05)에 실제로 출력됐던 결함 데이터
DEFECT_BIO_SECTOR = {
    "name": "바이오·제약",
    "reason": "금리가 5.50%까지 오르며 보험·운용자산 수익률이 높아졌다.",
}
FACT_FED = (
    "미국 연준 위원 다수가 물가 상승 위험을 이유로 현재 금리 5.50% 수준에서 "
    "추가 인상 가능성을 언급하며 긴축 기조를 재확인했다."
)
FACT_EURO = "유로존 5월 소비자물가 상승률은 2.8%로 전월 2.6%에서 반등했다."
FACT_SHALE = "미국 셰일 유정 완결 대기 물량은 약 4,150개로 사상 최저 수준까지 줄었다."


# ──────────────────────────────────────────────────────────
# 결함 1: 섹터-이유 불일치
# ──────────────────────────────────────────────────────────
class TestSectorReasonCoherence:
    def test_insurance_reason_under_bio_is_mismatch(self):
        """바이오·제약에 보험 수익률 이유 → 불일치 검출 (실물 결함 재현)"""
        ok, owner = check_sector_reason(DEFECT_BIO_SECTOR["name"], DEFECT_BIO_SECTOR["reason"])
        assert ok is False
        assert owner == "보험"

    def test_mismatch_is_remapped_to_owner(self):
        repaired, issues = repair_sectors([DEFECT_BIO_SECTOR])
        assert repaired == [{"name": "보험", "reason": DEFECT_BIO_SECTOR["reason"]}]
        assert any("불일치" in i for i in issues)

    def test_mismatch_dropped_when_owner_already_present(self):
        sectors = [
            {"name": "보험", "reason": "운용자산 수익률이 5.50%까지 높아졌다."},
            DEFECT_BIO_SECTOR,
        ]
        repaired, _ = repair_sectors(sectors)
        names = [s["name"] for s in repaired]
        assert names == ["보험"]
        assert "바이오·제약" not in names

    def test_matching_reason_kept(self):
        ok, _ = check_sector_reason("은행·금융", "금리 인상으로 예대마진이 0.2%p 개선됐다.")
        assert ok is True
        ok, _ = check_sector_reason("바이오·제약", "신약 임상 결과 발표로 관심이 커졌다.")
        assert ok is True

    def test_generic_reason_allowed(self):
        ok, _ = check_sector_reason("은행·금융", "거시 환경 변화의 직접 영향권에 있다.")
        assert ok is True

    def test_non_enum_sector_dropped(self):
        """티커/회사명이 섹터명으로 들어오면 무조건 drop (구조 차단 최후 방어선)"""
        repaired, issues = repair_sectors([
            {"name": "삼성전자", "reason": "메모리 가격이 10% 올랐다."},
            {"name": "NVDA", "reason": "GPU 수요가 늘었다."},
        ])
        assert repaired == []
        assert len(issues) == 2

    def test_all_enum_values_are_industry_names(self):
        for s in KoreanSector:
            assert not s.value.isascii(), f"enum에 영문 티커 의심값: {s.value}"


# ──────────────────────────────────────────────────────────
# 결함 2: 슬라이드 간 콘텐츠 중복
# ──────────────────────────────────────────────────────────
class TestDeduplication:
    def test_verbatim_fact_box_removed(self):
        """slide3 FACT가 slide2 팩트 그대로 → FACT 박스 비움 (실물 결함 재현)"""
        inner = {
            "slide2_facts": [FACT_FED, FACT_EURO, FACT_SHALE],
            "slide3_sectors": [], "slide4_sectors": [],
            "slide3_fact": FACT_FED,
            "slide4_fact": FACT_SHALE,
            "slide5_summaries": [],
        }
        out, issues = dedupe_inner(inner)
        assert out["slide3_fact"] == ""
        assert out["slide4_fact"] == ""
        assert len(issues) == 2

    def test_near_verbatim_summary_removed(self):
        """slide5 요약이 slide2 팩트의 근사 복제 → 제거 (실물 결함 재현)"""
        near_dup = ("미국 연준 위원들이 현재 금리 5.50% 수준에서 추가 인상 가능성을 "
                    "언급하며 긴축 기조를 재확인했다.")
        inner = {
            "slide2_facts": [FACT_FED, FACT_EURO],
            "slide3_sectors": [], "slide4_sectors": [],
            "slide3_fact": "", "slide4_fact": "",
            "slide5_summaries": [near_dup, "금리 수혜 업종과 부담 업종의 온도 차가 뚜렷해졌다."],
        }
        out, _ = dedupe_inner(inner)
        assert near_dup not in out["slide5_summaries"]
        assert len(out["slide5_summaries"]) == 1

    def test_fact_box_dup_of_sector_reason_removed(self):
        inner = {
            "slide2_facts": [FACT_EURO],
            "slide3_sectors": [{"name": "은행·금융", "reason": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다."}],
            "slide4_sectors": [],
            "slide3_fact": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다.",
            "slide4_fact": "",
            "slide5_summaries": [],
        }
        out, _ = dedupe_inner(inner)
        assert out["slide3_fact"] == ""

    def test_distinct_content_untouched(self):
        inner = {
            "slide2_facts": [FACT_FED, FACT_EURO, FACT_SHALE],
            "slide3_sectors": [], "slide4_sectors": [],
            "slide3_fact": "유로존 물가가 2.8%로 반등하면서 고금리 환경이 길어질 가능성이 커졌다.",
            "slide4_fact": "셰일 완결 대기 유정이 4,150개로 줄어 공급 측 유가 부담이 이어졌다.",
            "slide5_summaries": ["연준 긴축과 유로존 물가 반등이 겹치며 고금리 조건이 쌓였다."],
        }
        out, issues = dedupe_inner(dict(inner))
        assert out["slide3_fact"] == inner["slide3_fact"]
        assert out["slide4_fact"] == inner["slide4_fact"]
        assert len(out["slide5_summaries"]) == 1
        assert issues == []

    def test_similarity_symmetric_and_bounded(self):
        a, b = FACT_FED, FACT_EURO
        assert similarity(a, b) == similarity(b, a)
        assert 0.0 <= similarity(a, b) < 0.3
        assert similarity(a, a) == 1.0
        assert not is_duplicate(FACT_EURO, [FACT_FED, FACT_SHALE])


# ──────────────────────────────────────────────────────────
# 결함 3: 커버 출처 영문 헤드라인 노출
# ──────────────────────────────────────────────────────────
class TestSourceSanitization:
    def test_headline_strings_reduced_to_outlet(self):
        """scripts.json에 실제로 들어있던 헤드라인 출처 (실물 결함 재현)"""
        raw = [
            "Reuters: Record-low U.S. shale well backlog curbs fast output gains amid export surge",
            "Reuters: More Fed policymakers eye possible rate hike as inflation risks rise",
            "Reuters: Top euro zone countries see Iran inflation fallout broaden in May",
        ]
        assert clean_sources(raw) == ["Reuters"]

    def test_multiple_outlets_preserved(self):
        assert clean_sources(["CNBC", "Reuters", "Bloomberg", "AP"]) == ["CNBC", "Reuters", "Bloomberg"]

    def test_unknown_sources_dropped_with_default(self):
        assert clean_sources(["My Crypto Blog", "텔레그램 채널"]) == ["Reuters"]

    def test_empty_and_none(self):
        assert clean_sources([]) == ["Reuters"]
        assert clean_sources(None) == ["Reuters"]


# ──────────────────────────────────────────────────────────
# 커버 한국어 강제 (영문 훅 커버 방지)
# ──────────────────────────────────────────────────────────
class TestKoreanCover:
    def test_english_hook_replaced(self):
        hook, one_line, issues = ensure_korean_cover("Trump says he w", "Morning Bid: Who needs oil")
        assert hook == GENERIC_HOOK
        assert "가" <= one_line[0] <= "힣" or any("가" <= c <= "힣" for c in one_line)
        assert len(issues) == 2

    def test_korean_hook_kept(self):
        hook, one_line, issues = ensure_korean_cover("물가 다시\n오를까?", "연준 긴축 재확인.")
        assert hook == "물가 다시\n오를까?"
        assert issues == []


# ──────────────────────────────────────────────────────────
# 금지어 (예측/권유)
# ──────────────────────────────────────────────────────────
class TestBannedWords:
    @pytest.mark.parametrize("text", [
        "반도체가 오를 것으로 보인다",
        "지금이 매수 기회다",
        "하반기 상승이 예상된다",
        "은행주 추천",
    ])
    def test_banned_detected(self, text):
        assert find_banned(text)

    @pytest.mark.parametrize("text", [
        "반도체 수출이 10% 상승했다",
        "분석가는 변동성이 커졌다고 말했다",
        "긴축 기조를 재확인했다",
    ])
    def test_factual_past_tense_allowed(self, text):
        assert find_banned(text) == []


# ──────────────────────────────────────────────────────────
# 마스터 검증 — 실물 결함 전체를 한 번에
# ──────────────────────────────────────────────────────────
class TestValidateInnerRegression:
    def make_defective_inner(self):
        """2026-06-05 실물 카드의 결함을 그대로 재현한 입력"""
        return {
            "slide2_facts": [FACT_FED, FACT_EURO, FACT_SHALE],
            "slide2_source": "출처 · Reuters",
            "slide3_sectors": [
                {"name": "은행·금융", "reason": "금리 인상 기조가 강화되며 예대마진이 0.2%p 개선됐다."},
                DEFECT_BIO_SECTOR,  # 결함 1
            ],
            "slide3_fact": FACT_FED,  # 결함 2 (slide2 팩트 그대로)
            "slide4_sectors": [
                {"name": "건설업종", "reason": "조달 금리가 5.50%로 오르며 이자 부담이 커졌다."},
                {"name": "유통·소비재", "reason": "긴축 장기화와 유가 부담으로 소비·물류 비용이 가중됐다."},
            ],
            "slide4_fact": FACT_SHALE,  # 결함 2
            "slide5_summaries": [
                "미국 연준 위원들이 현재 금리 5.50% 수준에서 추가 인상 가능성을 언급하며 긴축 기조를 재확인했다.",  # 결함 2
                "유로존 물가가 2.8%로 반등하는 등 글로벌 인플레이션 압력이 확대됐다.",
                "한국 증시는 긴축 장기화와 유로존 물가 2.8% 반등 리스크에 대비할 필요성이 커졌다.",
            ],
            "slide5_watch_point": "다음 FOMC의 금리 결정과 유로존 물가 2.8% 흐름의 지속 여부.",
        }

    def test_all_real_defects_eliminated(self):
        inner, viable, issues = validate_inner(self.make_defective_inner())
        assert viable
        # 결함 1: 바이오·제약+보험이유 조합이 존재할 수 없음
        for s in inner["slide3_sectors"] + inner["slide4_sectors"]:
            ok, _ = check_sector_reason(s["name"], s["reason"])
            assert ok, f"섹터-이유 불일치 잔존: {s}"
        assert all(s["name"] != "바이오·제약" for s in inner["slide3_sectors"])
        # 결함 2: 슬라이드 간 근사-중복 잔존 불가
        facts = inner["slide2_facts"]
        for fact_key in ("slide3_fact", "slide4_fact"):
            if inner[fact_key]:
                assert not is_duplicate(inner[fact_key], facts)
        for summ in inner["slide5_summaries"]:
            assert not is_duplicate(summ, facts)
        assert issues  # 결함이 실제로 검출·수리되었음

    def test_insufficient_content_not_viable(self):
        inner = {
            "slide2_facts": ["팩트 하나뿐 1%"],
            "slide2_source": "",
            "slide3_sectors": [], "slide4_sectors": [],
            "slide3_fact": "", "slide4_fact": "",
            "slide5_summaries": [],
            "slide5_watch_point": "",
        }
        _, viable, _ = validate_inner(inner)
        assert viable is False
