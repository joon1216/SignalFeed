# Session 44 — 중대 결정 기록 (2026-06-12)

베이스라인에서 벗어난 모든 중대 결정. 형식: 무엇 / 왜 / 트레이드오프 / 되돌리는 법.

---

## D1. Gemini 호출 단일화 — 클러스터당 2회 → 1회

- **무엇**: `content_gen.py`(훅+자유 HTML)와 `generate_cards_v2.py`(InnerSlides 구조화)가 각각 Gemini를 호출하던 이중 경로를, `content_gen.py`의 **단일 호출**(GeminiCardScript 스키마 = 커버 + 내지 전체)로 통합.
- **왜**: 무료 쿼터(실측 ~20 req/day)에서 클러스터당 2회 호출은 하루 처리량을 절반으로 깎음. 두 경로의 출력이 서로 어긋나는 것(예: scripts.json의 영문 hook과 v2의 한국어 hook 혼재)이 실물 결함의 직접 원인이기도 했음.
- **트레이드오프**: 한 번의 호출이 실패하면 커버+내지 모두 fallback. (완화: 캐시 + 큐레이션 fallback)
- **되돌리기**: git history의 `backend/modules/content_gen.py`(Session 40)와 `backend/generate_cards_v2.py`(Session 43) 복원.

## D2. 자유 HTML 생성(Session 32 방식) 완전 폐기 → 구조화 데이터 + Python 렌더러

- **무엇**: scripts.json의 `inner_slides`(Gemini가 만든 완성 HTML 4장) 필드 제거. Gemini는 **데이터만** 출력하고, HTML은 `card_renderer.py`가 결정적으로 생성.
- **왜**: 자유 HTML은 (a) 검증 불가능 — 티커/중복/금지어를 HTML 문자열에서 신뢰성 있게 잡을 수 없음, (b) 토큰 낭비 — HTML 보일러플레이트가 출력 토큰의 대부분, (c) 디자인 수정마다 재호출 필요. 불변 원칙 3·4(구조적 차단)는 구조화 출력에서만 성립.
- **트레이드오프**: 레이아웃 다양성 감소 (Gemini의 창의적 레이아웃 포기). 디자인 다양성은 레퍼런스 분석(목표 E) → 렌더러 개선 루프로 확보하는 방향.
- **되돌리기**: Session 42 `generate_cards_v2.py`의 `INNER_SYSTEM_PROMPT`(===SLIDEN=== 방식) 복원.

## D3. 진입점 단일화 — generate_cards_v2/v3 삭제, `backend/generate_cards.py` 신설

- **무엇**: 카드 생성 진입점을 `pipeline.py --steps 4` == `generate_cards.py` 하나로. `html_card_gen.py`(구 경로), `generate_cards_v2.py`, `generate_cards_v3.py` 삭제. 출력도 `data/6_cards_v2` → `data/4_cards/cluster_{id}/`로 통일.
- **왜**: 같은 일을 하는 경로가 3개 → 어떤 게 production인지 세션마다 혼선 (Session 39에서 실제 발생).
- **트레이드오프**: 익숙한 파일명 변경.
- **되돌리기**: `git revert` 또는 history에서 v2/v3 복원.

## D4. KoreanSector enum에 '보험' 추가 (16→17종)

- **무엇**: 보험을 독립 섹터로 추가.
- **왜**: 실물 결함 #1("바이오·제약"에 보험 수익률 이유)의 근본 원인 중 하나 — 금리 인상 수혜의 정석인 '보험'이 enum에 없어서 LLM/큐레이션이 이유를 엉뚱한 섹터에 붙임. fact_checker 룰 테이블(은행/보험/금융)과도 정합.
- **트레이드오프**: 없음에 가까움.
- **되돌리기**: enum에서 제거 + CURATED_FALLBACK 수정 + 테스트 수정.

## D5. 검증 책임을 코드로 이동 — `content_validator.py` 신설 (프롬프트 의존 폐기)

- **무엇**: 섹터-이유 정합성(시그니처 키워드 소유권), 슬라이드 간 중복(토큰 Jaccard ≥0.6), 출처 화이트리스트 정제, 금지어, 커버 한국어 강제를 렌더링 전 코드에서 강제. 렌더 직전에도 한 번 더 실행 (defense in depth).
- **왜**: 실물 결함 5종 중 3종(섹터 불일치, 중복, 영문 출처)이 "프롬프트로 금지"했는데도 출력됨. LLM 출력은 신뢰 불가가 전제.
- **트레이드오프**: 시그니처 키워드 테이블은 보수적(고정밀) 설계라 일부 불일치를 놓칠 수 있음 — 대신 오탐(정상 콘텐츠 잘못 drop)이 거의 없음. 키워드는 운영하며 추가.
- **되돌리기**: content_gen에서 validator 호출 제거 (비권장 — 회귀 테스트 86개가 깨짐).

## D6. fact_checker 동작 변경 3건

- **무엇**: (a) enum↔룰 토큰 alias 브리지 (`은행·금융`→{은행,금융}) — Session 43에서 "이름이 달라 교집합이 발화 안 함"이라고 기록된 문제 해결. (b) 섹터 논리 검증(failed)을 시장 추세(warning)보다 **먼저** — 치명 오류가 경고에 가려지던 순서 버그. (c) `"ai" in text` 부분 문자열 매칭 수정 (said/Ukraine 오탐) → 단어 경계 정규식.
- **왜**: 셋 다 팩트 정확성(불변 원칙 4) 직결 버그.
- **트레이드오프**: alias 브리지로 failed 발화가 늘어남 → fallback/교체가 더 자주 작동 (의도된 보수성).
- **되돌리기**: 각각 독립 수정이라 개별 revert 가능.

## D7. 생성 캐시 — `gen_cache.py` (quota 보호, 목표 D)

- **무엇**: `sha256(model | prompt_version | material)` 키로 검증·팩트체크 완료된 스크립트를 `data/cache/gen/`에 저장. 캐시 적중 시 Gemini와 yfinance 모두 호출 0회 (테스트로 증명).
- **왜**: 디자인 반복 작업이 quota를 태우던 문제. 같은 클러스터 자료 = 같은 결과여야 함.
- **트레이드오프**: 프롬프트를 바꾸면 `PROMPT_VERSION`을 올려야 캐시가 무효화됨 (잊으면 구버전 결과 재사용).
- **되돌리기**: `ContentGenerator(use_cache=False)`.

## D8. data/ 전체 git 추적 해제 (128 파일)

- **무엇**: `.gitignore`에 `data/`, `outputs/`, `reference/raw/` 추가, 기존 추적 파일 `git rm --cached`. 테스트용 데이터는 `tests/fixtures/`로 (추적 유지).
- **왜**: 불변 원칙 6 "데이터/산출물 파일은 .gitignore 준수". 카드 PNG가 커밋마다 diff를 오염시키고 레포를 비대화.
- **트레이드오프**: 과거 산출물은 git history에만 남음. 새 clone에는 data/가 비어 있음 (파이프라인 실행으로 재생성).
- **되돌리기**: `.gitignore`에서 해당 줄 제거 후 `git add data/`.

## D9. 레거시 대량 삭제 (frontend, models, assets, 모듈 9종, ~5,000 LOC)

- **무엇**: 정치 뉴스 시대(IssueFit) 코드 전부 + SignalFeed 초기의 미사용 모듈(FinBERT/auto_labeler/fake_filter/Pillow card_gen). 상세 목록은 `docs/audit_session44.md`.
- **왜**: import 그래프상 도달 불가. torch/transformers(수 GB) 의존성의 유일한 사용처가 죽은 코드였음.
- **트레이드오프**: fake_filter의 5-layer 방어 중 LLM screening/anomaly detection은 현 파이프라인에 대응물이 없음 (whitelist는 collector, 다중소스 검증은 clusterer에 내장). 필요 시 validator에 추가하는 게 옳은 위치.
- **되돌리기**: 전부 git history에 있음 (`git log --diff-filter=D`).

## D10. 렌더러에서 Tailwind CDN 제거

- **무엇**: `card_renderer.py`는 inline style만 사용 (구 코드는 Tailwind CDN을 로드했지만 실제로 안 씀).
- **왜**: 사용하지 않는 외부 JS 로드가 networkidle 대기를 늘리고, 오프라인 렌더를 깨뜨림. Pretendard CSS만 필요.
- **트레이드오프**: 향후 Tailwind 유틸리티를 쓰려면 다시 추가.
- **되돌리기**: HEAD 상수에 `<script src="https://cdn.tailwindcss.com">` 한 줄.

## D11. 1080x1350 5장 구조 유지 (변경 안 함)

- **무엇**: 베이스라인 유지.
- **왜**: 변경할 더 나은 근거를 찾지 못함 — Instagram 4:5가 피드 점유 최대 포맷이라는 기존 결정 유효.

## D12. 레퍼런스 분석 — 비전 API 대신 Claude Code 세션 직접 분석

- **무엇**: 수집(`backend/reference/collect.py`: instaloader/yt-dlp, **키 발급 불필요**) → 세션이 이미지를 Read로 직접 분석(`reference/ANALYZE.md`) → `patterns.json` 토큰 축적 → `hook_patterns.py`가 hook 타입을 Gemini 프롬프트에 자동 주입.
- **왜**: 외부 비전 API는 유료(불변 원칙 1 위반)거나 쿼터 소모. 세션 분석은 비용 0이고 품질이 더 높음.
- **트레이드오프**: 분석이 자동 배치가 아니라 세션 작업 (사람이 세션을 돌려야 패턴이 쌓임). instaloader/yt-dlp는 선택 설치 — 미설치 시 수집 skip (graceful).
- **되돌리기**: 해당 없음 (순수 추가).

## 키 발급 필요 항목 (불변 원칙 1)

이번 세션에서 **새로 키가 필요한 것은 없음**. 기존 선택 키 2종은 키 없이도 동작:
- `GEMINI_API_KEY` 없음 → 캐시/큐레이션 fallback 콘텐츠
- `PIXABAY_API_KEY` 없음 → 단색 배경 fallback

## 이 세션에서 의도적으로 안 한 것 (다음 할 일)

- shorts_gen.py 개선 (정적 차트 → 애니메이션, 구 API 테스트는 삭제만 — 신규 테스트 필요)
- 클러스터링 노이즈 64% 튜닝
- Gemini 라이브 호출 검증 (quota 보존 — 다음 quota 리셋 후 `pipeline --steps 3` 1회로 확인 권장)
- fake_filter의 LLM screening/anomaly detection 대응물
- 자동 업로드 (Phase 2)
