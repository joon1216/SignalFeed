"""
Gemini 생성 결과 캐시 (Session 44 — quota 보호)

material(클러스터 팩트 자료) 해시를 키로 생성 결과(JSON + fact_check)를 디스크에 저장.
디자인/렌더링 반복 시 Gemini·yfinance 호출 0회를 보장한다.

키 = sha256(model | prompt_version | material)
저장 위치 = data/cache/gen/{key}.json (gitignored)
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = "data/cache/gen"


class GenCache:
    """파일 기반 생성 결과 캐시"""

    def __init__(self, cache_dir: str = DEFAULT_CACHE_DIR):
        self.cache_dir = cache_dir

    @staticmethod
    def make_key(model: str, prompt_version: str, material: str) -> str:
        """모델/프롬프트 버전/자료 텍스트로 결정적 캐시 키 생성"""
        payload = "\x1f".join([model, prompt_version, material])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]

    def _path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def get(self, key: str) -> Optional[Dict]:
        """캐시 조회 — 없거나 손상 시 None"""
        path = self._path(key)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                entry = json.load(f)
            logger.info(f"✅ 캐시 적중: {key} (saved {entry.get('cached_at', '?')})")
            return entry.get("value")
        except Exception as e:
            logger.warning(f"캐시 읽기 실패 ({key}): {e}")
            return None

    def set(self, key: str, value: Dict) -> None:
        """캐시 저장"""
        os.makedirs(self.cache_dir, exist_ok=True)
        entry = {"cached_at": datetime.now().isoformat(timespec="seconds"), "value": value}
        try:
            with open(self._path(key), "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 캐시 저장: {key}")
        except Exception as e:
            logger.warning(f"캐시 쓰기 실패 ({key}): {e}")
