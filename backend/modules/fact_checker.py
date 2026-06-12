"""
SignalFeed 팩트 검증 레이어
- 규칙 기반 경제 논리 검증 (매크로 이슈 → 한국 섹터 매핑, WICS 기준)
- yfinance 시장 데이터로 실제 추세 확인
LLM이 생성한 섹터 분석(수혜/주의)이 경제 상식과 일치하는지 검증한다.
"""

import yfinance as yf
import json
import logging

logger = logging.getLogger(__name__)

# 매크로 이슈 → 한국 섹터 매핑 테이블 (WICS 기준)
MACRO_ECONOMIC_RULES = {
    "유가 상승": {
        "ticker": "CL=F",
        "expected_trend": "up",
        "pos": {"에너지", "조선", "자본재", "방위산업"},
        "neg": {"운송", "유틸리티", "항공"}
    },
    "유가 하락": {
        "ticker": "CL=F",
        "expected_trend": "down",
        "pos": {"운송", "유틸리티", "항공"},
        "neg": {"에너지", "조선", "정유"}
    },
    "금리 인상": {
        "ticker": "^TNX",
        "expected_trend": "up",
        "pos": {"은행", "보험", "금융"},
        "neg": {"제약", "바이오", "건설", "소프트웨어"}
    },
    "금리 인하": {
        "ticker": "^TNX",
        "expected_trend": "down",
        "pos": {"제약", "바이오", "소프트웨어", "건설"},
        "neg": {"은행", "보험"}
    },
    "달러 강세": {
        "ticker": "KRW=X",
        "expected_trend": "up",
        "pos": {"자동차", "반도체", "IT"},
        "neg": {"항공", "음식료", "철강"}
    },
    "달러 약세": {
        "ticker": "KRW=X",
        "expected_trend": "down",
        "pos": {"항공", "음식료", "유통"},
        "neg": {"자동차", "반도체", "IT"}
    },
    "지정학 리스크": {
        "ticker": "CL=F",
        "expected_trend": "up",
        "pos": {"방위산업", "해운", "에너지"},
        "neg": {"여행", "항공", "소비재"}
    },
    "지정학 해소": {
        "ticker": "CL=F",
        "expected_trend": "down",
        "pos": {"여행", "항공", "소비재"},
        "neg": {"방위산업", "해운", "정유"}
    },
    "중국 경기 호조": {
        "ticker": "000001.SS",
        "expected_trend": "up",
        "pos": {"철강", "화학", "화장품", "엔터"},
        "neg": set()
    },
    "AI 반도체": {
        "ticker": "^IXIC",
        "expected_trend": "up",
        "pos": {"반도체", "IT", "전력설비"},
        "neg": set()
    }
}


# 카드 섹터명(KoreanSector enum) ↔ 룰 테이블 토큰 연결 (Session 44)
# enum 표기("은행·금융")와 룰 토큰("은행")이 달라 set 교집합이 발화하지 않던 문제 해결
SECTOR_ALIASES = {
    "은행·금융": {"은행", "금융"},
    "보험": {"보험"},
    "바이오·제약": {"바이오", "제약"},
    "건설업종": {"건설"},
    "정유업종": {"정유", "에너지"},
    "항공사들": {"항공"},
    "해운업체": {"해운", "운송"},
    "방산업체": {"방위산업"},
    "반도체 기업": {"반도체"},
    "IT·플랫폼": {"IT", "소프트웨어"},
    "유통·소비재": {"유통", "소비재"},
    "여행·레저": {"여행"},
    "화학업종": {"화학"},
    "자동차 제조사": {"자동차"},
    "전력·설비": {"전력설비", "유틸리티"},
    "철강·소재": {"철강"},
    "엔터·미디어": {"엔터"},
}

# 룰 토큰 → enum 섹터명 역매핑 (검증 실패 시 올바른 enum 섹터 제안용)
_TOKEN_TO_ENUM = {}
for _enum_name, _tokens in SECTOR_ALIASES.items():
    for _t in _tokens:
        _TOKEN_TO_ENUM.setdefault(_t, _enum_name)


def expand_sector_names(names):
    """enum 섹터명 목록 → 룰 토큰 집합 (자기 자신 포함)"""
    expanded = set()
    for n in names or []:
        expanded.add(n)
        expanded |= SECTOR_ALIASES.get(n, set())
    return expanded


def rule_tokens_to_enum(tokens):
    """룰 토큰 목록 → enum 섹터명 목록 (중복 제거, 순서 보존)"""
    out = []
    for t in tokens or []:
        enum_name = _TOKEN_TO_ENUM.get(t, t)
        if enum_name not in out:
            out.append(enum_name)
    return out


class FactChecker:
    """규칙 + yfinance 기반 팩트 검증"""

    def verify_market_trend(self, ticker, expected_trend):
        """yfinance로 최근 5일 추세가 예상 방향과 일치하는지 확인"""
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period="5d")
            if len(history) < 2:
                return True, 0.0
            start = history['Close'].iloc[0]
            end = history['Close'].iloc[-1]
            pct = ((end - start) / start) * 100
            if expected_trend == "up" and pct >= -0.5:
                return True, pct
            elif expected_trend == "down" and pct <= 0.5:
                return True, pct
            else:
                return False, pct
        except Exception as e:
            logging.error(f"yfinance 오류: {e}")
            return True, 0.0

    def detect_topic(self, text):
        """클러스터 텍스트에서 매크로 토픽 감지"""
        text_lower = text.lower()
        if any(k in text_lower for k in ["iran", "이란", "ceasefire", "휴전", "협상"]):
            return "지정학 해소"
        if any(k in text_lower for k in ["war", "conflict", "missile", "전쟁"]):
            return "지정학 리스크"
        if any(k in text_lower for k in ["oil rise", "opec cut", "유가 상승"]):
            return "유가 상승"
        if any(k in text_lower for k in ["oil fall", "oil drop", "유가 하락"]):
            return "유가 하락"
        if any(k in text_lower for k in ["rate hike", "금리 인상", "tightening"]):
            return "금리 인상"
        if any(k in text_lower for k in ["rate cut", "금리 인하", "pivot"]):
            return "금리 인하"
        if any(k in text_lower for k in ["dollar strong", "달러 강세"]):
            return "달러 강세"
        # "ai"는 단어 경계로만 매칭 (said/Ukraine 등 부분 문자열 오탐 방지)
        import re as _re
        if _re.search(r"\bai\b", text_lower) or any(
            k in text_lower for k in ["semiconductor", "반도체", "nvidia", "인공지능"]
        ):
            return "AI 반도체"
        return None

    def validate(self, macro_text, llm_pos_sectors, llm_neg_sectors, check_market=True):
        """
        매크로 텍스트와 LLM이 생성한 섹터 분석 검증

        섹터 논리(failed)를 시장 추세(warning)보다 먼저 검사한다 —
        경제 논리 오류가 시장 경고에 가려지지 않도록 (Session 44).
        enum 섹터명("은행·금융")은 alias로 룰 토큰("은행")에 매칭된다.

        Args:
            check_market: False면 yfinance 호출 생략 (테스트/캐시 재사용 시)

        Returns: {"status": "passed"/"failed"/"warning", "message": str, ...}
        """
        topic = self.detect_topic(macro_text)
        if not topic or topic not in MACRO_ECONOMIC_RULES:
            return {"status": "passed", "message": "알 수 없는 토픽, 검증 통과"}

        rule = MACRO_ECONOMIC_RULES[topic]

        # 1) 섹터 논리 검증 (alias 확장 후 교집합)
        pos_set = expand_sector_names(llm_pos_sectors)
        neg_set = expand_sector_names(llm_neg_sectors)

        wrong_pos = pos_set.intersection(rule.get("neg", set()))
        wrong_neg = neg_set.intersection(rule.get("pos", set()))

        if wrong_pos or wrong_neg:
            return {
                "status": "failed",
                "topic": topic,
                "message": f"경제 논리 오류: 수혜에 잘못 포함된 섹터 {wrong_pos}, 주의에 잘못 포함된 섹터 {wrong_neg}",
                "correct_pos": rule_tokens_to_enum(sorted(rule["pos"])),
                "correct_neg": rule_tokens_to_enum(sorted(rule.get("neg", set()))),
            }

        # 2) 시장 팩트 체크 (yfinance)
        if check_market and "ticker" in rule:
            is_valid, pct = self.verify_market_trend(
                rule["ticker"], rule["expected_trend"]
            )
            if not is_valid:
                return {
                    "status": "warning",
                    "topic": topic,
                    "message": f"시장 데이터 불일치: {rule['ticker']} 실제 {pct:.1f}% 변동 (예상 방향과 다름). 면책 문구 추가 권장."
                }

        return {"status": "passed", "topic": topic, "message": f"'{topic}' 검증 통과"}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    checker = FactChecker()

    # 정상 케이스: 지정학 리스크 → 방산 수혜, 항공 주의
    print(checker.validate("이란 전쟁 미사일 공격", ["방위산업", "해운"], ["항공", "여행"]))
    # 오류 케이스: 지정학 리스크인데 항공을 수혜로 분류
    print(checker.validate("이란 war conflict", ["항공"], ["방위산업"]))
    # 알 수 없는 토픽
    print(checker.validate("새로운 정책 발표", ["반도체"], ["은행"]))
