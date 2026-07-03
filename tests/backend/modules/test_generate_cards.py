"""generate_cards.resolve_cover_keyword 테스트 — 토픽 1순위 (Session 45 결함 수정)"""

from backend.generate_cards import resolve_cover_keyword
from backend.modules.image_fetcher import ImageFetcher


def make_script(**kw):
    base = {
        "issue_id": "6",
        "hook_title": "환율 어디로\n가나?",
        "one_line": "달러·인도 외환 시장이 흔들렸다.",
        "image_keyword": "",
        "fact_check": {},
    }
    base.update(kw)
    return base


class TestTopicFirstKeyword:
    def test_stored_topic_beats_substring_noise(self):
        """실물 결함 재현: 텍스트에 'defense'가 섞여 있어도 저장된 토픽이 우선
        ('defense'→military 매핑으로 키보드 사진이 나오던 문제)"""
        script = make_script(
            one_line="달러 강세 속 defense 예산 언급으로 외환 시장이 출렁였다.",
            fact_check={"status": "passed", "topic": "달러 강세"},
        )
        kw = resolve_cover_keyword(script)
        assert kw == ImageFetcher.TOPIC_KEYWORDS["달러 강세"]
        assert "military" not in kw

    def test_topic_redetected_when_not_stored(self):
        script = make_script(
            hook_title="금리 인상\n또 오나?",
            one_line="연준이 금리 인상 가능성을 언급했다.",
            fact_check={},
        )
        assert resolve_cover_keyword(script) == ImageFetcher.TOPIC_KEYWORDS["금리 인상"]

    def test_substring_fallback_when_no_topic(self):
        """토픽 미감지 시 기존 부분 문자열 매핑으로 폴백"""
        script = make_script(
            hook_title="반도체 수출\n날았다",
            one_line="반도체 수출이 늘었다.",
            fact_check={},
        )
        kw = resolve_cover_keyword(script)
        # '반도체'는 detect_topic에서 'AI 반도체' 토픽으로 감지됨 → 토픽 키워드
        assert kw == ImageFetcher.TOPIC_KEYWORDS["AI 반도체"]

    def test_defense_topic_redetected_when_not_stored(self):
        """실물 결함 재현: '국방비 증가' 클러스터가 토픽 미감지로 빠져 부분 문자열
        매핑에서 'defense'→military 키보드 사진에 밀리던 문제 (Session 48)"""
        script = make_script(
            hook_title="국방비 증가\n어디에 영향?",
            one_line="싱가포르 샹그릴라 대화에서 국방비 증액이 논의되었다.",
            image_keyword="Military defense meeting",
            fact_check={},
        )
        kw = resolve_cover_keyword(script)
        assert kw == ImageFetcher.TOPIC_KEYWORDS["국방비 증가"]

    def test_default_when_nothing_matches(self):
        script = make_script(
            hook_title="오늘의 글로벌\n경제 시그널",
            one_line="주요 외신 보도를 정리했습니다.",
            fact_check={},
        )
        assert resolve_cover_keyword(script) == ImageFetcher.KEYWORD_MAPPING["default"]


class TestKeywordForTopic:
    def test_known_topics_mapped(self):
        for topic in ("유가 상승", "금리 인상", "달러 강세", "지정학 리스크"):
            assert ImageFetcher.keyword_for_topic(topic)

    def test_unknown_or_none(self):
        assert ImageFetcher.keyword_for_topic("새로운 토픽") is None
        assert ImageFetcher.keyword_for_topic(None) is None

    def test_all_rule_topics_have_keywords(self):
        """fact_checker 룰 테이블의 모든 토픽이 커버 키워드를 가짐"""
        from backend.modules.fact_checker import MACRO_ECONOMIC_RULES
        for topic in MACRO_ECONOMIC_RULES:
            assert ImageFetcher.keyword_for_topic(topic), f"토픽 키워드 누락: {topic}"
