"""card_renderer 테스트 — HTML 구조 불변식 (Playwright 없이 문자열 레벨)"""

import json
import os

import pytest

from backend.modules.card_renderer import (
    build_conclusion,
    build_context,
    build_sectors,
    hl,
    render_slides,
    slide_cover,
    GREEN,
    RED,
)

FIXTURE = os.path.join(os.path.dirname(__file__), "../../fixtures/script_issue6.json")


@pytest.fixture
def script():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


class TestCover:
    def test_headline_sources_never_rendered(self):
        """결함 3 회귀: 헤드라인 출처가 들어와도 커버에는 매체명만 출력"""
        html = slide_cover(
            "물가 다시\n오를까?", "한줄 요약 2.8%",
            ["Reuters: Record-low U.S. shale well backlog curbs fast output gains"],
            img_uri="",
        )
        assert "Reuters" in html
        assert "Record-low" not in html
        assert "shale" not in html

    def test_hook_linebreak_rendered(self):
        html = slide_cover("물가 다시\n오를까?", "", ["Reuters"], "")
        assert "물가 다시<br/>오를까?" in html

    def test_no_image_still_valid(self):
        html = slide_cover("훅", "요약", ["Reuters"], "")
        assert 'id="slide-1"' in html
        assert "<img" not in html


class TestContextSlide:
    def test_fact_blocks_fill_area(self):
        """결함 4 회귀: 팩트 블록이 flex:1로 영역을 균등 점유 (상단 공백 불가)"""
        inner = {
            "slide2_facts": ["팩트 1 (5.50%)", "팩트 2 (2.8%)", "팩트 3 (4,150개)"],
            "slide2_source": "출처 · Reuters",
        }
        html = build_context(inner, "물가 다시\n오를까?")
        # 각 팩트 블록이 flex:1 — 3개 블록 모두
        assert html.count('<div style="flex:1;') >= 3
        # 콘텐츠 그룹을 가운데로 몰아 상하 공백을 만들던 패턴 부재
        assert "justify-content:center;\">" not in html.split('class="content"')[1].split("</h1>")[0]

    def test_number_highlighting(self):
        inner = {"slide2_facts": ["유로존 물가 2.8%로 반등"], "slide2_source": ""}
        html = build_context(inner, "훅")
        assert 'font-weight:700;">2.8%' in html


class TestSectorSlides:
    def test_fact_box_omitted_when_empty(self):
        """중복 제거로 비워진 FACT는 박스 자체가 렌더되지 않음"""
        sectors = [{"name": "은행·금융", "reason": "예대마진 0.2%p 개선"}]
        html = build_sectors(3, "누가 웃나?", "↑ 수혜", sectors, fact_text="", accent=GREEN)
        assert ">FACT<" not in html

    def test_fact_box_present_when_given(self):
        sectors = [{"name": "은행·금융", "reason": "예대마진 0.2%p 개선"}]
        html = build_sectors(3, "누가 웃나?", "↑ 수혜", sectors, "유로존 물가 2.8% 반등", GREEN)
        assert ">FACT<" in html

    def test_sector_rows_fill_area(self):
        """결함 4 회귀: 섹터 행 flex:1 균등 점유"""
        sectors = [
            {"name": "은행·금융", "reason": "이유 1%"},
            {"name": "보험", "reason": "이유 2%"},
        ]
        html = build_sectors(4, "누가 우나?", "↓ 주의", sectors, "", RED)
        assert html.count('<div style="flex:1;display:flex;flex-direction:column;justify-content:center;') == 2


class TestConclusion:
    def test_disclaimer_always_present(self):
        inner = {"slide5_summaries": ["요약 1"], "slide5_watch_point": ""}
        html = build_conclusion(inner)
        assert "본 콘텐츠는 AI 분석 정보이며 투자 권유가 아닙니다" in html

    def test_extra_disclaimer_added_on_warning(self):
        inner = {"slide5_summaries": ["요약 1"], "slide5_watch_point": ""}
        html = build_conclusion(inner, "※ 시장 지표가 엇갈리고 있습니다.")
        assert "※ 시장 지표가 엇갈리고 있습니다." in html


class TestRenderSlides:
    def test_five_docs_with_ids(self, script):
        docs = render_slides(script)
        assert sorted(docs) == [1, 2, 3, 4, 5]
        for n, html in docs.items():
            assert f'id="slide-{n}"' in html
            assert "1080px" in html and "1350px" in html

    def test_fixture_renders_all_content(self, script):
        docs = render_slides(script)
        assert "물가 다시<br/>오를까?" in docs[1]
        assert "은행·금융" in docs[3] and "보험" in docs[3]
        assert "건설업종" in docs[4]
        assert "투자 권유가 아닙니다" in docs[5]

    def test_hl_no_highlight_on_plain_text(self):
        assert hl("숫자가 없는 문장") == "숫자가 없는 문장"
