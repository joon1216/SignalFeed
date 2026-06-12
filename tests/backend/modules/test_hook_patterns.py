"""hook_patterns 테스트 — 레퍼런스 패턴 프롬프트 주입"""

import json

from backend.modules.hook_patterns import hook_prompt_snippet, load_patterns


def test_missing_file_returns_empty(tmp_path):
    assert load_patterns(str(tmp_path / "none.json")) == []
    assert hook_prompt_snippet(str(tmp_path / "none.json")) == ""


def test_hook_patterns_injected(tmp_path):
    path = tmp_path / "patterns.json"
    path.write_text(json.dumps({
        "patterns": [
            {"id": "a", "type": "hook", "token": "2줄 질문형 훅",
             "description": "질문으로 호기심 유발", "examples": ["물가 다시\n오를까?"]},
            {"id": "b", "type": "layout", "token": "번호 팩트", "description": "무관", "examples": []},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    snippet = hook_prompt_snippet(str(path))
    assert "2줄 질문형 훅" in snippet
    assert "번호 팩트" not in snippet  # hook 타입만 주입


def test_repo_seed_patterns_load():
    """레포에 시드된 reference/patterns.json이 유효해야 함"""
    patterns = load_patterns("reference/patterns.json")
    assert len(patterns) >= 3
    snippet = hook_prompt_snippet("reference/patterns.json")
    assert "훅" in snippet


def test_corrupted_file_safe(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{broken", encoding="utf-8")
    assert load_patterns(str(path)) == []
