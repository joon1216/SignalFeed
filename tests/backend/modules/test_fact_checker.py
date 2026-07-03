"""fact_checker 테스트 — alias 브리지, 검증 순서, 토픽 감지 (네트워크 없음)"""

from backend.modules.fact_checker import (
    FactChecker,
    expand_sector_names,
    rule_tokens_to_enum,
)


class TestAliases:
    def test_enum_name_expands_to_rule_tokens(self):
        expanded = expand_sector_names(["은행·금융", "바이오·제약"])
        assert {"은행", "금융", "바이오", "제약"} <= expanded

    def test_rule_tokens_map_back_to_enum(self):
        out = rule_tokens_to_enum(["은행", "보험", "금융"])
        assert "은행·금융" in out
        assert "보험" in out

    def test_unknown_token_passthrough(self):
        assert rule_tokens_to_enum(["조선"]) == ["조선"]


class TestSectorLogic:
    def setup_method(self):
        self.checker = FactChecker()

    def test_rate_hike_bio_as_beneficiary_fails(self):
        """금리 인상 이슈에서 바이오·제약을 수혜로 분류 → 경제 논리 오류 (실물 결함의 룰 레벨 차단)"""
        result = self.checker.validate(
            "연준 위원 다수 rate hike 금리 인상 가능성 언급",
            ["바이오·제약"], ["건설업종"],
            check_market=False,
        )
        assert result["status"] == "failed"
        assert "은행·금융" in result["correct_pos"] or "보험" in result["correct_pos"]

    def test_rate_hike_correct_sectors_pass(self):
        result = self.checker.validate(
            "연준 금리 인상 tightening",
            ["은행·금융", "보험"], ["건설업종", "바이오·제약"],
            check_market=False,
        )
        assert result["status"] == "passed"

    def test_sector_failure_not_masked_by_market_warning(self):
        """섹터 논리 오류는 시장 추세 경고보다 우선해야 함 (Session 44 순서 수정)"""
        checker = FactChecker()
        checker.verify_market_trend = lambda ticker, trend: (False, -2.0)  # 시장 불일치 강제
        result = checker.validate(
            "금리 인상 rate hike",
            ["바이오·제약"], [],
            check_market=True,
        )
        assert result["status"] == "failed"  # warning이 아니라 failed

    def test_market_mismatch_returns_warning(self):
        checker = FactChecker()
        checker.verify_market_trend = lambda ticker, trend: (False, -2.0)
        result = checker.validate(
            "금리 인상 rate hike",
            ["은행·금융"], ["건설업종"],
            check_market=True,
        )
        assert result["status"] == "warning"

    def test_unknown_topic_passes(self):
        result = self.checker.validate("새로운 정책 발표", ["반도체 기업"], ["은행·금융"],
                                       check_market=False)
        assert result["status"] == "passed"


class TestTopicDetection:
    def setup_method(self):
        self.checker = FactChecker()

    def test_ai_requires_word_boundary(self):
        """'said' 등 부분 문자열로 AI 토픽 오탐하지 않음 (Session 44 수정)"""
        assert self.checker.detect_topic("Officials said output rose") is None

    def test_ai_word_detected(self):
        assert self.checker.detect_topic("AI chip demand surged") == "AI 반도체"

    def test_rate_hike_korean(self):
        assert self.checker.detect_topic("연준 금리 인상 시사") == "금리 인상"

    def test_geopolitics(self):
        assert self.checker.detect_topic("missile strike conflict") == "지정학 리스크"

    def test_defense_spending_korean(self):
        """실물 결함 재현: '국방비 증가' 클러스터가 '알 수 없는 토픽'으로 빠져
        커버 이미지가 무관한 fallback 검색어로 밀리던 문제 (Session 48)"""
        assert self.checker.detect_topic("국방비 증가 어디에 영향?") == "국방비 증가"

    def test_defense_spending_english(self):
        assert self.checker.detect_topic(
            "Defense spending, China in Asia and lessons from Ukraine"
        ) == "국방비 증가"


class TestDefenseSpendingRule:
    def setup_method(self):
        self.checker = FactChecker()

    def test_defense_sector_as_beneficiary_passes(self):
        result = self.checker.validate(
            "국방비 증가 어디에 영향?",
            ["방산업체", "IT·플랫폼"], ["해운업체", "항공사들"],
            check_market=False,
        )
        assert result["status"] == "passed"
