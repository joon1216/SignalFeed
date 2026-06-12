# Session 44 — 코드베이스 감사 결과 (2026-06-12)

## 감사 방법
- 전체 import 그래프 추적 (`grep -r "from backend\|import backend"`)
- production 진입점 기준 도달 가능성 분석: `backend/pipeline.py`, `backend/generate_cards_v2.py`(→ Session 44에서 `generate_cards.py`로 교체)
- 실물 산출물(data/6_cards_v2) 시각 검사로 결함 5종 확인

## Production 경로 (Session 44 이후 단일화)
```
pipeline.py
 ├─ 1. collector.py      (RSS + Finnhub)
 ├─ 2. clusterer.py      (TF-IDF + UMAP + HDBSCAN)
 ├─ 3. content_gen.py    (Gemini 구조화 1회/클러스터 + validator + fact_checker + gen_cache)
 ├─ 4. generate_cards.py (card_renderer + image_fetcher + Playwright)
 └─ 5. shorts_gen.py     (미수정 — 다음 할 일)
```

## 삭제 목록 (git 히스토리에서 복구 가능)

### 레거시 IssueFit (정치 뉴스 시대, pivot 후 미사용)
| 파일 | LOC | 사유 |
|------|-----|------|
| `backend/modules/crawler.py` | 318 | 네이버 정치 뉴스 크롤러. 어디서도 import 안 됨 |
| `backend/modules/clawler_ver2.py` | 739 | 동일 (오타 파일명) |
| `backend/modules/crawler_v3.py` | 441 | 동일 |
| `backend/modules/summarizer.py` | 269 | Ollama 다관점 요약 (정치). 미사용 |
| `backend/modules/db_loader.py` | 176 | DB 의존 모듈 — 파일 기반 철학과 모순, 미사용 |
| `frontend/` (app.py 등) | 731+ | "정치 뉴스 이슈 분석" Streamlit 대시보드 — 현 데이터 구조와 불일치, 미사용 |
| `models/political_classifier/` | — | 정치 분류기 설정/토크나이저 잔재 |

### SignalFeed 초기 (Session 22에서 파이프라인에서 제거된 후 잔존)
| 파일 | LOC | 사유 |
|------|-----|------|
| `backend/modules/classifier.py` | 286 | FinBERT — Session 22에서 제거. torch/transformers 의존성의 유일한 사용처 |
| `backend/modules/auto_labeler.py` | 291 | GPT-4o-mini 레이블링 — 유료 API, 파이프라인에서 제거됨 |
| `backend/modules/fake_filter.py` | 304 | deprecated 표기. 화이트리스트는 collector, 다중소스 검증은 clusterer에 내장됨 |
| `backend/modules/card_gen.py` | 778 | Pillow 카드 생성 — HTML+Playwright로 대체 (Session 21) |
| `assets/` (colors.py, fonts) | — | card_gen 전용. 현 렌더러는 Pretendard CDN 사용 |

### 중복 생성 경로 단일화 (Session 44 Phase C에서 교체)
| 파일 | LOC | 사유 |
|------|-----|------|
| `backend/modules/html_card_gen.py` | 260 | 구 카드 경로(자유 HTML 스크린샷) — `card_renderer.py`로 대체 |
| `backend/generate_cards_v2.py` | 661 | 모듈화 리팩터링 → `generate_cards.py` + modules로 분해 |
| `backend/generate_cards_v3.py` | 427 | V2에 흡수된 실험 경로 |

### 루트 스크래치 스크립트
`screenshot_cards.py`, `test_cards.py`, `test_cover.py`, `test_gemini_response.py`, `test_regenerate.py` — 일회성 수동 테스트, pytest로 대체

### 구 테스트 (삭제된 모듈 대상)
`test_auto_labeler.py`, `test_card_gen.py`, `test_classifier.py`, `test_fake_filter.py`, `test_content_gen.py`(구 API)
→ Session 44 신규 테스트로 대체 (`test_content_validator.py`, `test_gen_cache.py`, `test_card_renderer.py`, `test_image_fetcher.py`, `test_fact_checker.py`)

## 의존성 정리 (requirements.txt)
제거: `torch`, `transformers`, `safetensors`(FinBERT 전용), `langchain`, `langchain-community`(사용처 전무),
`streamlit`, `plotly`(frontend 삭제), `fastapi`, `uvicorn`(미구현 Phase 3), `beautifulsoup4`(사용처 없음)
추가(실사용인데 누락이었던 것): `feedparser`, `google-genai`, `pydantic`, `yfinance`, `playwright`, `moviepy`, `gTTS`, `mplcyberpunk`, `jsonlines`, `pytest`

## 데이터/산출물 git 추적 해제
- `data/` 전체(128 파일, 카드 PNG 포함), `outputs/`, `reference/raw/`를 .gitignore에 추가하고 untrack
- 테스트에 필요한 데이터는 `tests/fixtures/`로 이동 (추적 유지)

## 실물 카드 결함 (data/6_cards_v2 기준, Phase C에서 해결)
1. **섹터-이유 불일치 (크리티컬)**: Slide 3 "바이오·제약"에 "보험·운용자산 수익률" 이유 — fallback CONTENT["6"] 데이터 자체 오류 + 정합성 검증 부재
2. **콘텐츠 중복**: Fed 5.50% 팩트가 Slide 2/3/5에, 셰일 4,150개 팩트가 Slide 2/4에 거의 그대로 반복 — 중복 검증 부재
3. **커버 하단 영문 헤드라인**: scripts.json `sources`에 Gemini가 헤드라인 문자열("Reuters: Record-low U.S. shale…")을 넣었는데 그대로 렌더 — 출처 정제 부재
4. **Slide 2~4 상단 거대 공백**: `flex:1` + `justify-content:center`가 콘텐츠 블록을 중앙 배치 → 상하 대칭 공백
5. **커버 이미지 미스매치**: Pixabay `order=popular` 첫 결과 무조건 사용 → tiny planet 왜곡 파노라마 선택됨

## 미수정 (다음 할 일로 기록)
- shorts_gen.py 차트/렌더 개선 — 의도적 미수정 (범위 통제)
- 클러스터링 노이즈 64% — 파라미터 튜닝 추후
- 자동 업로드 (Instagram Graph API / YouTube Data API) — Phase 2
- `docs/outlet_crawler_plan.md`, `docs/paper_summary.md` — 레거시 문서, 참고용으로 보존
