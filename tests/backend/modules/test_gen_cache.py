"""gen_cache 테스트 — quota 보호의 핵심 (캐시 적중 시 API 호출 0회)"""

import json
import os

from backend.modules.gen_cache import GenCache


class TestKey:
    def test_deterministic(self):
        k1 = GenCache.make_key("gemini-2.5-flash", "s44.1", "material A")
        k2 = GenCache.make_key("gemini-2.5-flash", "s44.1", "material A")
        assert k1 == k2

    def test_changes_with_material(self):
        k1 = GenCache.make_key("m", "v", "material A")
        k2 = GenCache.make_key("m", "v", "material B")
        assert k1 != k2

    def test_changes_with_prompt_version(self):
        k1 = GenCache.make_key("m", "s44.1", "same")
        k2 = GenCache.make_key("m", "s44.2", "same")
        assert k1 != k2


class TestRoundtrip:
    def test_set_get(self, tmp_path):
        cache = GenCache(str(tmp_path))
        value = {"hook_title": "물가 다시\n오를까?", "inner": {"slide2_facts": ["a 1%"]}}
        cache.set("abc123", value)
        assert cache.get("abc123") == value

    def test_miss_returns_none(self, tmp_path):
        cache = GenCache(str(tmp_path))
        assert cache.get("nonexistent") is None

    def test_corrupted_file_returns_none(self, tmp_path):
        cache = GenCache(str(tmp_path))
        path = os.path.join(str(tmp_path), "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not json")
        assert cache.get("bad") is None

    def test_delete_removes_entry(self, tmp_path):
        cache = GenCache(str(tmp_path))
        cache.set("k", {"a": 1})
        assert cache.get("k") is not None
        cache.delete("k")
        assert cache.get("k") is None

    def test_delete_missing_key_safe(self, tmp_path):
        GenCache(str(tmp_path)).delete("nonexistent")  # 예외 없이 통과

    def test_korean_preserved(self, tmp_path):
        cache = GenCache(str(tmp_path))
        cache.set("k", {"text": "유로존 물가 2.8% 반등"})
        raw = json.load(open(cache._path("k"), encoding="utf-8"))
        assert "유로존" in json.dumps(raw, ensure_ascii=False)
        assert cache.get("k")["text"] == "유로존 물가 2.8% 반등"
