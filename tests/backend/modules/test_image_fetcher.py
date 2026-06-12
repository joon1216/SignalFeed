"""image_fetcher 테스트 — 키워드 매핑 + 왜곡 이미지 스코어링 (네트워크 없음)"""

from backend.modules.image_fetcher import ImageFetcher


def make_hit(tags, w=2000, h=3000, downloads=50000, url="http://example.com/img.jpg"):
    return {"tags": tags, "imageWidth": w, "imageHeight": h,
            "downloads": downloads, "largeImageURL": url}


class TestKeywordMapping:
    def setup_method(self):
        self.fetcher = ImageFetcher(api_key="dummy")

    def test_fed_mapping(self):
        assert self.fetcher.get_keyword("fed 의사록 공개") == ImageFetcher.KEYWORD_MAPPING["fed"]

    def test_rate_hike_mapping(self):
        kw = self.fetcher.get_keyword("연준 금리 인상 시사")
        assert kw == ImageFetcher.KEYWORD_MAPPING["금리 인상"]

    def test_default_fallback(self):
        kw = self.fetcher.get_keyword("전혀 매핑되지 않는 텍스트")
        assert kw == ImageFetcher.KEYWORD_MAPPING["default"]


class TestHitScoring:
    """커버 이미지 스타일 미스매치(tiny planet 등) 구조 차단 — Session 44 결함 5"""

    def test_panorama_rejected_over_normal(self):
        tiny_planet = make_hit("city, panorama, 360, night", downloads=900000)
        normal = make_hit("city, skyline, night, building", downloads=10000)
        best = ImageFetcher.pick_best([tiny_planet, normal])
        assert best is normal

    def test_illustration_rejected(self):
        illu = make_hit("finance, illustration, cartoon", downloads=500000)
        photo = make_hit("finance, office, desk", downloads=1000)
        assert ImageFetcher.pick_best([illu, photo]) is photo

    def test_extreme_aspect_penalized(self):
        pano = make_hit("city, skyline", w=8000, h=1000, downloads=900000)
        normal = make_hit("city, skyline", w=2000, h=3000, downloads=10000)
        assert ImageFetcher.pick_best([pano, normal]) is normal

    def test_all_bad_returns_none(self):
        hits = [
            make_hit("city, panorama, 360"),
            make_hit("abstract, wallpaper, render"),
        ]
        assert ImageFetcher.pick_best(hits) is None

    def test_empty_hits(self):
        assert ImageFetcher.pick_best([]) is None

    def test_popularity_breaks_ties(self):
        a = make_hit("city, skyline", downloads=100)
        b = make_hit("city, skyline", downloads=90000)
        assert ImageFetcher.pick_best([a, b]) is b
