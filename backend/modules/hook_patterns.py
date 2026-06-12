"""
레퍼런스 훅 패턴 로더 (Session 44 — 레퍼런스 분석 시스템)

reference/patterns.json에 축적된 벤치마크 패턴 토큰 중 'hook' 타입을 읽어
hook_title 생성 프롬프트에 주입할 텍스트 스니펫을 만든다.

patterns.json은 Claude Code 세션이 벤치마크 이미지를 직접 보고 추출·축적한다
(reference/ANALYZE.md 절차 참고). 파일이 없어도 안전하게 빈 문자열을 반환한다.
"""

import os
import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

DEFAULT_PATTERNS_PATH = "reference/patterns.json"


def load_patterns(path: str = DEFAULT_PATTERNS_PATH) -> List[Dict]:
    """patterns.json 로드 — 없거나 손상 시 빈 리스트"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("patterns", []) if isinstance(data, dict) else data
    except Exception as e:
        logger.warning(f"patterns.json 로드 실패: {e}")
        return []


def hook_prompt_snippet(path: str = DEFAULT_PATTERNS_PATH, max_patterns: int = 6) -> str:
    """hook 타입 패턴 → 프롬프트 주입용 텍스트. 패턴 없으면 ''"""
    hooks = [p for p in load_patterns(path) if p.get("type") == "hook"]
    if not hooks:
        return ""
    lines = ["[벤치마크에서 검증된 훅 패턴 — 아래 패턴 중 하나를 골라 변주하라]"]
    for p in hooks[:max_patterns]:
        token = p.get("token", "")
        desc = p.get("description", "")
        example = (p.get("examples") or [""])[0]
        lines.append(f"- {token}: {desc}" + (f' (예: "{example}")' if example else ""))
    return "\n".join(lines)
